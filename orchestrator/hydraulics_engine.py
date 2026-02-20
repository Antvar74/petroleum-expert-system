"""
Hydraulics / ECD Dynamic Calculation Engine
Based on Bourgoyne et al. (Applied Drilling Engineering) and API RP 13D
References: Bingham Plastic & Power Law rheological models, Dodge-Metzner correlation
"""
import math
from typing import List, Dict, Any, Optional


class HydraulicsEngine:
    """
    Full hydraulic circuit calculator: pressure losses through the entire
    circulating system, bit hydraulics, ECD, and surge/swab analysis.
    """

    # Discharge coefficient for bit nozzles
    CD = 0.95

    # --- Phase 2: P/T Correction Methods ---

    @staticmethod
    def correct_density_pt(
        rho_surface: float, pressure: float, temperature: float,
        fluid_type: str = "wbm",
        p_ref: float = 14.7, t_ref: float = 70.0
    ) -> Dict[str, Any]:
        """
        Correct mud density for pressure and temperature effects.

        rho(P,T) = rho_0 * [1 + Cp*(P - P0)] * [1 / (1 + Ct*(T - T0))]

        Parameters:
        - rho_surface: surface mud density (ppg)
        - pressure: local pressure (psi)
        - temperature: local temperature (°F)
        - fluid_type: 'wbm' (water-based) or 'obm' (oil-based)
        - p_ref, t_ref: reference conditions (default: atmospheric, 70°F)

        Returns:
        - rho_corrected: corrected density (ppg)
        - pressure_effect, temperature_effect: individual contributions
        """
        if rho_surface <= 0:
            return {"rho_corrected": 0.0, "pressure_effect_ppg": 0.0,
                    "temperature_effect_ppg": 0.0, "fluid_type": fluid_type}

        # Compressibility and thermal expansion coefficients (API RP 13D)
        if fluid_type.lower() == "obm":
            cp = 5.0e-6   # compressibility (/psi) — OBM more compressible
            ct = 3.5e-4   # thermal expansion (/°F) — OBM expands more
        else:
            cp = 3.0e-6   # compressibility (/psi) — WBM
            ct = 2.0e-4   # thermal expansion (/°F) — WBM

        # Density correction
        pressure_factor = 1.0 + cp * (pressure - p_ref)
        temp_factor = 1.0 + ct * (temperature - t_ref)
        temp_factor = max(temp_factor, 0.5)  # Guard against extreme cooling

        rho_corrected = rho_surface * pressure_factor / temp_factor

        return {
            "rho_corrected": round(rho_corrected, 4),
            "pressure_effect_ppg": round(rho_surface * (pressure_factor - 1.0), 4),
            "temperature_effect_ppg": round(rho_surface * (1.0 - 1.0 / temp_factor), 4),
            "fluid_type": fluid_type
        }

    @staticmethod
    def correct_viscosity_pt(
        pv_surface: float, temperature: float,
        t_ref: float = 120.0, alpha: float = 0.015
    ) -> Dict[str, Any]:
        """
        Correct plastic viscosity for temperature using Arrhenius-type model.

        PV(T) = PV_ref * exp(-alpha * (T - T_ref))

        Parameters:
        - pv_surface: PV at reference temperature (cP)
        - temperature: local temperature (°F)
        - t_ref: reference temperature (°F, default 120°F — typical surface measurement)
        - alpha: temperature sensitivity coefficient (1/°F, default 0.015)

        Returns:
        - pv_corrected: corrected PV (cP)
        """
        if pv_surface <= 0:
            return {"pv_corrected": 0.0, "correction_factor": 1.0,
                    "t_ref": t_ref, "temperature": temperature}

        delta_t = temperature - t_ref
        correction = math.exp(-alpha * delta_t)
        # Clamp: don't allow PV to go below 10% or above 500% of surface value
        correction = max(0.1, min(correction, 5.0))

        pv_corrected = pv_surface * correction

        return {
            "pv_corrected": round(pv_corrected, 2),
            "correction_factor": round(correction, 4),
            "t_ref": t_ref,
            "temperature": temperature
        }

    @staticmethod
    def calculate_temperature_profile(
        t_surface: float, gradient: float, depths: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate temperature at each depth using a linear geothermal gradient.

        T(z) = T_surface + gradient * z

        Parameters:
        - t_surface: surface/mudline temperature (°F)
        - gradient: geothermal gradient (°F per ft, typical 1.0-1.5 per 100ft → 0.01-0.015)
        - depths: list of TVDs (ft)

        Returns:
        - list of {depth, temperature} dicts
        """
        return [
            {"depth_ft": round(d, 1),
             "temperature_f": round(t_surface + gradient * d, 2)}
            for d in depths
        ]

    @staticmethod
    def pressure_loss_bingham(
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        length: float,
        od: float,
        id_inner: float,
        is_annular: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate pressure loss using Bingham Plastic model.

        For pipe flow:
            Laminar:  dP = (PV * V * L) / (1500 * d²) + (YP * L) / (225 * d)
            Turbulent: dP = (f * MW * V² * L) / (25.8 * d)

        For annular flow:
            d_eff = d_hole - d_pipe (for velocity)
            d_hyd = d_hole - d_pipe (hydraulic diameter for Reynolds)

        Parameters:
        - flow_rate: gpm
        - mud_weight: ppg
        - pv: plastic viscosity (cP)
        - yp: yield point (lb/100ft²)
        - length: section length (ft)
        - od: outer diameter (inches) — hole/casing ID for annular
        - id_inner: inner diameter (inches) — pipe OD for annular
        - is_annular: True for annular flow
        """
        if length <= 0 or flow_rate <= 0:
            return HydraulicsEngine._zero_result()

        if is_annular:
            d_outer = od       # hole or casing ID
            d_inner = id_inner  # pipe OD
            # Annular velocity
            v = 24.5 * flow_rate / (d_outer**2 - d_inner**2)
            d_eff = d_outer - d_inner
        else:
            # Pipe velocity
            d_eff = id_inner
            v = 24.5 * flow_rate / (d_eff**2)
            d_outer = od
            d_inner = 0

        if d_eff <= 0:
            return HydraulicsEngine._zero_result()

        # Reynolds number (Bingham)
        if is_annular:
            re = 757.0 * mud_weight * v * d_eff / pv if pv > 0 else 99999
        else:
            re = 928.0 * mud_weight * v * d_eff / pv if pv > 0 else 99999

        # Hedstrom number for critical Re
        he = 37100.0 * mud_weight * yp * d_eff**2 / (pv**2) if pv > 0 else 0

        # Critical Reynolds (simplified)
        re_crit = 2100.0  # simplified; full solution uses He iteration
        if he > 0:
            re_crit = 2100.0 + 7.3 * (he**0.58)  # Hanks correlation approximation

        flow_regime = "laminar" if re < re_crit else "turbulent"

        if flow_regime == "laminar":
            if is_annular:
                dp = (pv * v * length) / (1000.0 * d_eff**2) + (yp * length) / (200.0 * d_eff)
            else:
                dp = (pv * v * length) / (1500.0 * d_eff**2) + (yp * length) / (225.0 * d_eff)
        else:
            # Turbulent: Fanning friction factor
            f = 0.0791 / (re**0.25) if re > 0 else 0.01
            v_fps = v / 60.0  # Convert ft/min to ft/s for Bourgoyne formula
            if is_annular:
                dp = (f * mud_weight * v_fps**2 * length) / (21.1 * d_eff)
            else:
                dp = (f * mud_weight * v_fps**2 * length) / (25.8 * d_eff)

        return {
            "pressure_loss_psi": round(dp, 1),
            "velocity_ft_min": round(v, 1),
            "reynolds": round(re, 0),
            "flow_regime": flow_regime,
            "d_eff": round(d_eff, 3)
        }

    @staticmethod
    def pressure_loss_power_law(
        flow_rate: float,
        mud_weight: float,
        n: float,
        k: float,
        length: float,
        od: float,
        id_inner: float,
        is_annular: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate pressure loss using Power Law model.
        tau = K * gamma^n

        Parameters:
        - n: flow behavior index (dimensionless)
        - k: consistency index (eq cP)
        """
        if length <= 0 or flow_rate <= 0 or n <= 0:
            return HydraulicsEngine._zero_result()

        if is_annular:
            d_outer = od
            d_inner = id_inner
            v = 24.5 * flow_rate / (d_outer**2 - d_inner**2)
            d_eff = d_outer - d_inner
        else:
            d_eff = id_inner
            v = 24.5 * flow_rate / (d_eff**2)

        if d_eff <= 0:
            return HydraulicsEngine._zero_result()

        # Generalized Reynolds number (Dodge-Metzner)
        if is_annular:
            na = (2.0 + 1.0 / n) / 3.0  # annular geometry factor
            re_g = (109000.0 * mud_weight * v**(2 - n) * d_eff**n) / (k * (na)**n)
        else:
            np_factor = (3.0 + 1.0 / n) / 4.0
            re_g = (89100.0 * mud_weight * v**(2 - n) * d_eff**n) / (k * (np_factor)**n)

        re_crit = 3470.0 - 1370.0 * n  # Dodge-Metzner critical Re

        flow_regime = "laminar" if re_g < re_crit else "turbulent"

        if flow_regime == "laminar":
            if is_annular:
                dp = (k * v**n * length) / (144000.0 * d_eff**(1 + n)) * (
                    (2 + 1.0 / n) / 0.0208
                )**n
            else:
                dp = (k * v**n * length) / (144000.0 * d_eff**(1 + n)) * (
                    (3 + 1.0 / n) / 0.0208
                )**n
            # Simplified: use direct formula
            # dP = (K * L) / (144000 * d^(1+n)) * (v * (3n+1)/(0.0208*n))^n  for pipe
            dp = max(dp, 0)
        else:
            # Turbulent friction factor (Dodge-Metzner)
            a = 1.0 / (4.0 * n**0.75)
            b = 0.395 / (n**1.2)
            # Iterative f solve — use initial guess
            f = 0.0791 / (re_g**0.25)
            for _ in range(10):
                rhs = a * math.log10(re_g * f**(1 - n / 2.0)) - b
                if rhs <= 0:
                    break
                f = 1.0 / (rhs**2)

            if is_annular:
                dp = (f * mud_weight * v**2 * length) / (21.1 * d_eff)
            else:
                dp = (f * mud_weight * v**2 * length) / (25.8 * d_eff)

        return {
            "pressure_loss_psi": round(dp, 1),
            "velocity_ft_min": round(v, 1),
            "reynolds": round(re_g, 0),
            "flow_regime": flow_regime,
            "d_eff": round(d_eff, 3),
            "n": n,
            "k": k
        }

    @staticmethod
    def fit_herschel_bulkley(fann_readings: Dict[str, float]) -> Dict[str, Any]:
        """
        Fit Herschel-Bulkley rheological parameters (tau_0, K, n) from
        standard FANN viscometer readings using iterative least-squares.

        Model: tau = tau_0 + K * gamma^n

        Parameters:
        - fann_readings: dict with keys r600, r300, r200, r100, r6, r3
          (dial readings at standard RPMs)

        Returns:
        - tau_0: yield stress (lbf/100ft²)
        - k_hb: consistency index
        - n_hb: flow behavior index
        - r_squared: goodness of fit
        - fann_readings: echo of input readings
        """
        # FANN RPM -> shear rate (1/s): gamma = 1.703 * RPM
        fann_rpm = {"r600": 600, "r300": 300, "r200": 200, "r100": 100, "r6": 6, "r3": 3}

        # Extract available readings
        readings = []
        for key in ["r3", "r6", "r100", "r200", "r300", "r600"]:
            val = fann_readings.get(key, 0.0)
            if val is not None and val > 0:
                gamma = 1.703 * fann_rpm[key]          # shear rate (1/s)
                tau = 1.0678 * val                      # shear stress (lbf/100ft²)
                readings.append((gamma, tau))

        # Guard: all zero or no valid readings
        if len(readings) < 2:
            return {
                "tau_0": 0.0, "k_hb": 0.0, "n_hb": 1.0,
                "r_squared": 0.0, "fann_readings": fann_readings
            }

        # Sort by shear rate ascending
        readings.sort(key=lambda x: x[0])

        # Initial tau_0 estimate: low-shear extrapolation (2*tau_3 - tau_6)
        tau_3 = 1.0678 * fann_readings.get("r3", 0.0)
        tau_6 = 1.0678 * fann_readings.get("r6", 0.0)
        tau_0 = max(2.0 * tau_3 - tau_6, 0.0)

        # Cap tau_0 below minimum measured shear stress
        tau_min = min(t for _, t in readings)
        if tau_0 >= tau_min:
            tau_0 = tau_min * 0.5

        best_tau_0, best_k, best_n, best_r2 = tau_0, 0.0, 1.0, -1.0

        # Iterative regression: ln(tau - tau_0) = ln(K) + n * ln(gamma)
        for iteration in range(5):
            ln_gamma = []
            ln_tau_adj = []
            for gamma, tau in readings:
                adj = tau - tau_0
                if adj > 1e-6:
                    ln_gamma.append(math.log(gamma))
                    ln_tau_adj.append(math.log(adj))

            if len(ln_gamma) < 2:
                break

            # Least-squares: y = a + b*x  →  ln(tau-tau0) = ln(K) + n*ln(gamma)
            n_pts = len(ln_gamma)
            sum_x = sum(ln_gamma)
            sum_y = sum(ln_tau_adj)
            sum_xx = sum(x * x for x in ln_gamma)
            sum_xy = sum(x * y for x, y in zip(ln_gamma, ln_tau_adj))

            denom = n_pts * sum_xx - sum_x * sum_x
            if abs(denom) < 1e-12:
                break

            n_hb = (n_pts * sum_xy - sum_x * sum_y) / denom
            ln_k = (sum_y - n_hb * sum_x) / n_pts
            k_hb = math.exp(ln_k)

            # Clamp n to physical range
            n_hb = max(0.05, min(n_hb, 1.5))

            # R-squared
            mean_y = sum_y / n_pts
            ss_tot = sum((y - mean_y) ** 2 for y in ln_tau_adj)
            ss_res = sum((y - (ln_k + n_hb * x)) ** 2 for x, y in zip(ln_gamma, ln_tau_adj))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

            if r2 > best_r2:
                best_tau_0, best_k, best_n, best_r2 = tau_0, k_hb, n_hb, r2

            # Update tau_0: find value that minimizes residuals
            # Use predicted tau at lowest shear rate minus measured
            gamma_low, tau_low = readings[0]
            tau_0_new = tau_low - k_hb * gamma_low ** n_hb
            tau_0_new = max(tau_0_new, 0.0)
            tau_0_new = min(tau_0_new, tau_min * 0.95)

            if abs(tau_0_new - tau_0) < 0.01:
                best_tau_0, best_k, best_n, best_r2 = tau_0_new, k_hb, n_hb, r2
                break
            tau_0 = tau_0_new

        # Fallback: 2-point fit from r300/r600 if regression diverged
        if best_r2 < 0.5 and best_k <= 0:
            r300 = fann_readings.get("r300", 0.0)
            r600 = fann_readings.get("r600", 0.0)
            if r300 > 0 and r600 > 0:
                tau300 = 1.0678 * r300
                tau600 = 1.0678 * r600
                best_n = math.log(tau600 / tau300) / math.log(2.0) if tau300 > 0 else 1.0
                best_n = max(0.05, min(best_n, 1.5))
                best_k = tau300 / (510.9 ** best_n)
                best_tau_0 = 0.0
                best_r2 = 0.95

        return {
            "tau_0": round(best_tau_0, 3),
            "k_hb": round(best_k, 6),
            "n_hb": round(best_n, 4),
            "r_squared": round(best_r2, 4),
            "fann_readings": fann_readings
        }

    @staticmethod
    def pressure_loss_herschel_bulkley(
        flow_rate: float, mud_weight: float,
        tau_0: float, k_hb: float, n_hb: float,
        length: float, od: float, id_inner: float,
        is_annular: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate pressure loss using Herschel-Bulkley model (API RP 13D / Metzner-Reed).

        Model: tau = tau_0 + K * gamma^n

        Parameters:
        - tau_0: yield stress (lbf/100ft²)
        - k_hb: consistency index
        - n_hb: flow behavior index (0 < n < 1 for shear-thinning)
        - is_annular: True for annular geometry

        Returns: dict with pressure_loss_psi, velocity, Reynolds, flow regime
        """
        if length <= 0 or flow_rate <= 0:
            result = HydraulicsEngine._zero_result()
            result.update({"tau_0": tau_0, "k_hb": k_hb, "n_hb": n_hb})
            return result

        if is_annular:
            d_eff = od - id_inner
            v = 24.5 * flow_rate / (od**2 - id_inner**2)  # ft/min
        else:
            d_eff = id_inner
            v = 24.5 * flow_rate / (d_eff**2)              # ft/min

        if d_eff <= 0 or v <= 0:
            result = HydraulicsEngine._zero_result()
            result.update({"tau_0": tau_0, "k_hb": k_hb, "n_hb": n_hb})
            return result

        # Ensure n_hb is in valid range
        n = max(0.05, min(n_hb, 1.5))

        # Wall shear rate (Metzner-Reed generalized)
        if is_annular:
            gamma_w = 144.0 * v / d_eff * (2.0 * n + 1.0) / (3.0 * n)
        else:
            gamma_w = 96.0 * v / d_eff * (3.0 * n + 1.0) / (4.0 * n)

        # Wall shear stress
        tau_w = tau_0 + k_hb * (gamma_w ** n)

        # Effective viscosity (cP) at the wall
        # mu_eff = tau_w / gamma_w * 47880 converts lbf/100ft² to cP at gamma_w
        # Simplified: mu_eff = tau_w * d_eff / (96 * v) for pipe (field units)
        if is_annular:
            mu_eff = tau_w * d_eff / (144.0 * v) if v > 0 else 1e6
        else:
            mu_eff = tau_w * d_eff / (96.0 * v) if v > 0 else 1e6

        mu_eff = max(mu_eff, 0.001)

        # Generalized Reynolds number
        re_g = 928.0 * mud_weight * v * d_eff / mu_eff

        # Critical Reynolds (Dodge-Metzner)
        re_crit = 3470.0 - 1370.0 * n

        if re_g < re_crit:
            # Laminar: dP = tau_w * L / (300 * d_eff) for pipe
            if is_annular:
                dp = tau_w * length / (300.0 * d_eff)
            else:
                dp = tau_w * length / (300.0 * d_eff)
            flow_regime = "laminar"
        else:
            # Turbulent: Fanning friction factor (Dodge-Metzner)
            a = 0.0791 / (re_g ** 0.25)  # simplified Fanning
            # More accurate: log(1/sqrt(f)) = (4.0/n^0.75)*log(Re*f^(1-n/2)) - 0.395/n^1.2
            # Use iterative or simplified power-law form
            a_coef = (math.log10(n) + 3.93) / 50.0
            b_coef = (1.75 - math.log10(n)) / 7.0
            f = a_coef / (re_g ** b_coef)
            f = max(f, 1e-6)

            if is_annular:
                dp = f * mud_weight * v**2 * length / (21.1 * d_eff)
            else:
                dp = f * mud_weight * v**2 * length / (25.8 * d_eff)
            flow_regime = "turbulent"

        return {
            "pressure_loss_psi": round(dp, 1),
            "velocity_ft_min": round(v, 1),
            "reynolds": round(re_g, 0),
            "flow_regime": flow_regime,
            "d_eff": round(d_eff, 3),
            "tau_0": tau_0,
            "k_hb": k_hb,
            "n_hb": n_hb
        }

    @staticmethod
    def calculate_bit_hydraulics(
        flow_rate: float,
        mud_weight: float,
        nozzle_sizes: List[float],
        total_system_loss: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate bit hydraulics: TFA, pressure drop, HSI, impact force, jet velocity.

        Parameters:
        - nozzle_sizes: list of nozzle sizes in 32nds of an inch
        - total_system_loss: total pressure loss in the system excluding bit (psi)
        """
        if not nozzle_sizes or flow_rate <= 0:
            return {"error": "Missing nozzle data or flow rate"}

        # Total Flow Area
        tfa = 0.0
        for noz in nozzle_sizes:
            d_inches = noz / 32.0
            tfa += math.pi / 4.0 * d_inches**2

        if tfa <= 0:
            return {"error": "Zero TFA"}

        # Bit pressure drop: dP = 8.311e-5 * MW * Q² / (Cd² * TFA²)
        cd = HydraulicsEngine.CD
        dp_bit = 8.311e-5 * mud_weight * flow_rate**2 / (cd**2 * tfa**2)

        # Nozzle velocity: Vn = Q / (3.117 * TFA)
        vn = flow_rate / (3.117 * tfa)

        # Hydraulic horsepower at bit
        hhp_bit = dp_bit * flow_rate / 1714.0

        # Bit diameter estimate (largest nozzle ring)
        max_noz = max(nozzle_sizes) / 32.0
        bit_area = math.pi / 4.0 * (max_noz * 4)**2  # rough estimate

        # HSI = HHP / bit_area (use standard bit sizes)
        # Common bit diameters based on nozzle count
        bit_diameters = {3: 8.5, 4: 8.5, 5: 12.25, 6: 12.25, 7: 17.5}
        n_noz = len(nozzle_sizes)
        bit_dia = bit_diameters.get(n_noz, 8.5)
        bit_area_actual = math.pi / 4.0 * bit_dia**2
        hsi = hhp_bit / bit_area_actual

        # Impact force: Fi = 0.01823 * Cd * Q * sqrt(MW * dP_bit)
        impact_force = 0.01823 * cd * flow_rate * math.sqrt(mud_weight * dp_bit)

        # Percent pressure at bit
        total_pressure = dp_bit + total_system_loss
        pct_at_bit = (dp_bit / total_pressure * 100.0) if total_pressure > 0 else 0

        return {
            "tfa_sqin": round(tfa, 4),
            "pressure_drop_psi": round(dp_bit, 0),
            "jet_velocity_fps": round(vn, 0),
            "hhp_bit": round(hhp_bit, 1),
            "hsi": round(hsi, 2),
            "impact_force_lb": round(impact_force, 0),
            "nozzle_count": n_noz,
            "nozzle_sizes_32nds": nozzle_sizes,
            "percent_at_bit": round(pct_at_bit, 1),
            "bit_diameter_assumed": bit_dia
        }

    @staticmethod
    def calculate_ecd_dynamic(
        mud_weight: float,
        tvd: float,
        annular_pressure_loss: float,
        cuttings_loading: float = 0.0,
        temperature_effect: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate dynamic ECD including cuttings and temperature effects.
        ECD = MW + cuttings + temp_effect + APL/(0.052*TVD)
        """
        if tvd <= 0:
            return {"ecd": mud_weight, "status": "Error: Zero TVD"}

        ecd_apl = annular_pressure_loss / (0.052 * tvd)
        ecd = mud_weight + cuttings_loading + temperature_effect + ecd_apl

        status = "Normal"
        margin = ecd - mud_weight
        if margin > 1.5:
            status = "HIGH — Risk of losses/fracturing"
        elif margin > 1.0:
            status = "Elevated — Monitor closely"
        elif margin < 0.2:
            status = "LOW — Poor hole cleaning likely"

        return {
            "ecd_ppg": round(ecd, 2),
            "ecd_from_apl": round(ecd_apl, 3),
            "cuttings_effect_ppg": round(cuttings_loading, 3),
            "temperature_effect_ppg": round(temperature_effect, 3),
            "total_margin_ppg": round(margin, 3),
            "status": status
        }

    @staticmethod
    def calculate_bha_pressure_breakdown(
        bha_tools: List[Dict[str, Any]],
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        rheology_model: str = "bingham_plastic",
        n: float = 0.5,
        k: float = 300.0,
        tau_0: float = 0.0,
        k_hb: float = 0.0,
        n_hb: float = 0.5
    ) -> Dict[str, Any]:
        """
        Calculate pressure loss breakdown for individual BHA tools.

        Each tool can have a loss_coefficient to model internal restrictions
        (e.g., motors, MWD/LWD tools with complex internal geometries).

        Args:
            bha_tools: list of dicts, each with:
                - tool_name: descriptive name (e.g., "PDM Motor 6-3/4")
                - tool_type: 'motor', 'mwd', 'lwd', 'stabilizer', 'collar',
                             'jar', 'reamer', 'crossover'
                - od: outer diameter (in)
                - id_inner: inner diameter (in)
                - length: tool length (ft)
                - loss_coefficient: multiplier for internal restrictions (default 1.0)
            flow_rate: circulation rate (gpm)
            mud_weight: mud weight (ppg)
            pv, yp: Bingham parameters
            rheology_model: 'bingham_plastic', 'power_law', or 'herschel_bulkley'
            n, k: Power Law parameters
            tau_0, k_hb, n_hb: Herschel-Bulkley parameters

        Returns:
            Dict with tools_breakdown[], total_bha_loss_psi, critical_tool
        """
        if not bha_tools or flow_rate <= 0:
            return {
                "tools_breakdown": [],
                "total_bha_loss_psi": 0.0,
                "critical_tool": None
            }

        tools_breakdown = []
        total_loss = 0.0
        max_dp_per_ft = 0.0
        critical_tool = None

        for tool in bha_tools:
            tool_name = tool.get("tool_name", "Unknown")
            tool_type = tool.get("tool_type", "collar")
            od = tool.get("od", 6.75)
            id_inner = tool.get("id_inner", 2.8125)
            length = tool.get("length", 30.0)
            loss_coeff = tool.get("loss_coefficient", 1.0)

            if length <= 0 or od <= 0 or id_inner <= 0:
                tools_breakdown.append({
                    "tool_name": tool_name,
                    "tool_type": tool_type,
                    "length": length,
                    "pressure_loss_psi": 0.0,
                    "velocity_ftmin": 0.0,
                    "regime": "none",
                    "loss_coefficient": loss_coeff,
                    "dp_per_ft": 0.0
                })
                continue

            # Calculate base pressure loss through the tool bore
            if rheology_model == "herschel_bulkley":
                result = HydraulicsEngine.pressure_loss_herschel_bulkley(
                    flow_rate=flow_rate, mud_weight=mud_weight,
                    tau_0=tau_0, k_hb=k_hb, n_hb=n_hb,
                    length=length, od=od, id_inner=id_inner,
                    is_annular=False
                )
            elif rheology_model == "power_law":
                result = HydraulicsEngine.pressure_loss_power_law(
                    flow_rate=flow_rate, mud_weight=mud_weight,
                    n=n, k=k,
                    length=length, od=od, id_inner=id_inner,
                    is_annular=False
                )
            else:
                result = HydraulicsEngine.pressure_loss_bingham(
                    flow_rate=flow_rate, mud_weight=mud_weight,
                    pv=pv, yp=yp,
                    length=length, od=od, id_inner=id_inner,
                    is_annular=False
                )

            # Apply loss coefficient (for motors, MWD, etc.)
            base_loss = result.get("pressure_loss_psi", 0.0)
            actual_loss = base_loss * loss_coeff

            # Pressure drop per foot (identifies bottleneck)
            dp_per_ft = actual_loss / length if length > 0 else 0.0

            tools_breakdown.append({
                "tool_name": tool_name,
                "tool_type": tool_type,
                "length": length,
                "pressure_loss_psi": round(actual_loss, 1),
                "velocity_ftmin": result.get("velocity_ft_min", 0.0),
                "regime": result.get("flow_regime", "unknown"),
                "loss_coefficient": loss_coeff,
                "dp_per_ft": round(dp_per_ft, 2)
            })

            total_loss += actual_loss

            if dp_per_ft > max_dp_per_ft:
                max_dp_per_ft = dp_per_ft
                critical_tool = tool_name

        return {
            "tools_breakdown": tools_breakdown,
            "total_bha_loss_psi": round(total_loss, 1),
            "critical_tool": critical_tool
        }

    @staticmethod
    def generate_pressure_waterfall(
        circuit_result: Dict[str, Any],
        bha_breakdown: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed pressure waterfall from circuit results.

        Breaks down total SPP into sequential steps from pump to annular return.
        If bha_breakdown is provided, expands BHA into individual tools.

        Args:
            circuit_result: output from calculate_full_circuit()
            bha_breakdown: optional output from calculate_bha_pressure_breakdown()

        Returns:
            Dict with waterfall_steps[], total_spp_psi
        """
        summary = circuit_result.get("summary", {})
        section_results = circuit_result.get("section_results", [])
        bit_hydraulics = circuit_result.get("bit_hydraulics", {})

        waterfall_steps = []
        cumulative = 0.0

        # 1. Surface Equipment
        surface_loss = summary.get("surface_equipment_psi", 0.0)
        cumulative += surface_loss
        waterfall_steps.append({
            "label": "Surface Equipment",
            "pressure_psi": round(surface_loss, 0),
            "cumulative_psi": round(cumulative, 0),
            "pct_of_total": 0.0  # calculated at the end
        })

        # 2. Pipe sections (non-annular, non-BHA)
        pipe_sections = [s for s in section_results if "annulus" not in s.get("section_type", "")]
        annular_sections = [s for s in section_results if "annulus" in s.get("section_type", "")]

        # If BHA breakdown is provided, separate collar/BHA from drillpipe/HWDP
        bha_tool_names = set()
        if bha_breakdown and bha_breakdown.get("tools_breakdown"):
            # Add BHA tools as individual steps
            for sec in pipe_sections:
                sec_type = sec.get("section_type", "")
                if sec_type in ("drill_pipe", "hwdp"):
                    loss = sec.get("pressure_loss_psi", 0.0)
                    cumulative += loss
                    label = "Drill Pipe" if sec_type == "drill_pipe" else "HWDP"
                    waterfall_steps.append({
                        "label": label,
                        "pressure_psi": round(loss, 0),
                        "cumulative_psi": round(cumulative, 0),
                        "pct_of_total": 0.0
                    })

            # BHA tools breakdown
            for tool in bha_breakdown["tools_breakdown"]:
                loss = tool.get("pressure_loss_psi", 0.0)
                cumulative += loss
                waterfall_steps.append({
                    "label": f"BHA: {tool['tool_name']}",
                    "pressure_psi": round(loss, 0),
                    "cumulative_psi": round(cumulative, 0),
                    "pct_of_total": 0.0
                })
        else:
            # No BHA breakdown — add pipe sections grouped
            for sec in pipe_sections:
                sec_type = sec.get("section_type", "")
                loss = sec.get("pressure_loss_psi", 0.0)
                cumulative += loss
                label_map = {
                    "drill_pipe": "Drill Pipe",
                    "hwdp": "HWDP",
                    "collar": "Drill Collars/BHA"
                }
                label = label_map.get(sec_type, sec_type.replace("_", " ").title())
                waterfall_steps.append({
                    "label": label,
                    "pressure_psi": round(loss, 0),
                    "cumulative_psi": round(cumulative, 0),
                    "pct_of_total": 0.0
                })

        # 3. Bit
        bit_loss = bit_hydraulics.get("pressure_drop_psi", summary.get("bit_loss_psi", 0.0))
        cumulative += bit_loss
        waterfall_steps.append({
            "label": "Bit Nozzles",
            "pressure_psi": round(bit_loss, 0),
            "cumulative_psi": round(cumulative, 0),
            "pct_of_total": 0.0
        })

        # 4. Annular sections
        for sec in annular_sections:
            sec_type = sec.get("section_type", "")
            loss = sec.get("pressure_loss_psi", 0.0)
            cumulative += loss
            label_map = {
                "annulus_dc": "Annular (DC)",
                "annulus_hwdp": "Annular (HWDP)",
                "annulus_dp": "Annular (DP)"
            }
            label = label_map.get(sec_type, sec_type.replace("_", " ").title())
            waterfall_steps.append({
                "label": label,
                "pressure_psi": round(loss, 0),
                "cumulative_psi": round(cumulative, 0),
                "pct_of_total": 0.0
            })

        # Calculate percentages
        total_spp = cumulative if cumulative > 0 else 1.0
        for step in waterfall_steps:
            step["pct_of_total"] = round(step["pressure_psi"] / total_spp * 100, 1)

        return {
            "waterfall_steps": waterfall_steps,
            "total_spp_psi": round(cumulative, 0)
        }

    @staticmethod
    def calculate_full_circuit(
        sections: List[Dict[str, Any]],
        nozzle_sizes: List[float],
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        tvd: float,
        rheology_model: str = "bingham_plastic",
        n: float = 0.5,
        k: float = 300.0,
        surface_equipment_loss: float = 80.0,
        tau_0: float = 0.0,
        k_hb: float = 0.0,
        n_hb: float = 0.5,
        fann_readings: Optional[Dict[str, float]] = None,
        use_pt_correction: bool = False,
        fluid_type: str = "wbm",
        t_surface: float = 80.0,
        geothermal_gradient: float = 0.012,
        annular_tvds: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate full hydraulic circuit: Surface -> DP -> BHA -> Bit -> Annular

        Parameters:
        - sections: list of {section_type, length, od, id_inner}
          section_type: 'drill_pipe', 'hwdp', 'collar', 'annulus_dp', 'annulus_dc', 'annulus_hwdp'
        - rheology_model: 'bingham_plastic', 'power_law', or 'herschel_bulkley'
        - tau_0, k_hb, n_hb: Herschel-Bulkley parameters (used if rheology_model='herschel_bulkley')
        - fann_readings: optional FANN viscometer readings for auto-fit H-B parameters
        - use_pt_correction: if True, apply P/T density and viscosity corrections per section
        - fluid_type: 'wbm' or 'obm' (for P/T correction coefficients)
        - t_surface: surface temperature (°F, for geothermal gradient)
        - geothermal_gradient: °F per ft (typical 0.010-0.015)
        - annular_tvds: optional list of TVD (ft) for each annular section (for accurate ECD)
        """
        # Auto-fit Herschel-Bulkley if FANN readings provided
        if rheology_model == "herschel_bulkley" and fann_readings is not None:
            hb_fit = HydraulicsEngine.fit_herschel_bulkley(fann_readings)
            tau_0 = hb_fit["tau_0"]
            k_hb = hb_fit["k_hb"]
            n_hb = hb_fit["n_hb"]

        section_results = []
        total_pipe_loss = surface_equipment_loss
        total_annular_loss = 0.0

        # Cumulative depth tracker for P/T correction
        cum_depth = 0.0

        for sec in sections:
            is_annular = "annulus" in sec.get("section_type", "")

            # Estimate mid-section TVD for P/T correction
            sec_length = sec["length"]
            mid_depth = cum_depth + sec_length / 2.0
            cum_depth += sec_length

            # Apply P/T corrections if enabled
            mw_local = mud_weight
            pv_local = pv
            yp_local = yp
            if use_pt_correction:
                t_local = t_surface + geothermal_gradient * mid_depth
                p_local = 0.052 * mud_weight * mid_depth  # hydrostatic estimate
                rho_corr = HydraulicsEngine.correct_density_pt(
                    mud_weight, p_local, t_local, fluid_type
                )
                mw_local = rho_corr["rho_corrected"]
                pv_corr = HydraulicsEngine.correct_viscosity_pt(pv, t_local)
                pv_local = pv_corr["pv_corrected"]
                # YP scales similarly to PV with temperature
                yp_corr_factor = pv_corr["correction_factor"]
                yp_local = yp * yp_corr_factor

            if rheology_model == "herschel_bulkley":
                result = HydraulicsEngine.pressure_loss_herschel_bulkley(
                    flow_rate=flow_rate,
                    mud_weight=mw_local,
                    tau_0=tau_0, k_hb=k_hb, n_hb=n_hb,
                    length=sec["length"],
                    od=sec["od"],
                    id_inner=sec["id_inner"],
                    is_annular=is_annular
                )
            elif rheology_model == "power_law":
                result = HydraulicsEngine.pressure_loss_power_law(
                    flow_rate=flow_rate,
                    mud_weight=mw_local,
                    n=n, k=k,
                    length=sec["length"],
                    od=sec["od"],
                    id_inner=sec["id_inner"],
                    is_annular=is_annular
                )
            else:
                result = HydraulicsEngine.pressure_loss_bingham(
                    flow_rate=flow_rate,
                    mud_weight=mw_local,
                    pv=pv_local, yp=yp_local,
                    length=sec["length"],
                    od=sec["od"],
                    id_inner=sec["id_inner"],
                    is_annular=is_annular
                )

            result["section_type"] = sec["section_type"]
            result["length"] = sec["length"]
            section_results.append(result)

            if is_annular:
                total_annular_loss += result["pressure_loss_psi"]
            else:
                total_pipe_loss += result["pressure_loss_psi"]

        # Bit hydraulics
        total_system_loss = total_pipe_loss + total_annular_loss
        bit_result = HydraulicsEngine.calculate_bit_hydraulics(
            flow_rate=flow_rate,
            mud_weight=mud_weight,
            nozzle_sizes=nozzle_sizes,
            total_system_loss=total_system_loss
        )

        bit_loss = bit_result.get("pressure_drop_psi", 0)
        total_spp = total_pipe_loss + bit_loss + total_annular_loss

        # ECD
        ecd_result = HydraulicsEngine.calculate_ecd_dynamic(
            mud_weight=mud_weight,
            tvd=tvd,
            annular_pressure_loss=total_annular_loss
        )

        # Multi-diameter annular analysis
        annular_analysis_sections = []
        annular_idx = 0
        for sec in section_results:
            if "annulus" in sec.get("section_type", ""):
                sec_velocity = sec.get("velocity_ft_min", 0.0)
                sec_od = sec.get("od", 0.0) if "od" in sec else 0.0
                sec_id = sec.get("id_inner", 0.0) if "id_inner" in sec else 0.0

                # Get TVD for this annular section if provided
                if annular_tvds and annular_idx < len(annular_tvds):
                    sec_tvd = annular_tvds[annular_idx]
                else:
                    sec_tvd = tvd  # fallback to total TVD

                # Local ECD for this section
                if sec_tvd > 0:
                    ecd_local = mud_weight + sec["pressure_loss_psi"] / (0.052 * sec_tvd)
                else:
                    ecd_local = mud_weight

                annular_analysis_sections.append({
                    "section_type": sec.get("section_type", ""),
                    "velocity_ftmin": round(sec_velocity, 1),
                    "ecd_local_ppg": round(ecd_local, 2),
                    "pressure_loss_psi": round(sec["pressure_loss_psi"], 1),
                    "tvd_ft": round(sec_tvd, 0)
                })
                annular_idx += 1

        # Identify critical annular section (lowest velocity or highest ECD)
        critical_section = None
        min_velocity = float("inf")
        if annular_analysis_sections:
            for asec in annular_analysis_sections:
                if 0 < asec["velocity_ftmin"] < min_velocity:
                    min_velocity = asec["velocity_ftmin"]
                    critical_section = asec["section_type"]

        annular_analysis = {
            "sections": annular_analysis_sections,
            "critical_section": critical_section,
            "min_velocity_ftmin": round(min_velocity, 1) if min_velocity < float("inf") else 0.0
        }

        # ECD profile at various depths (improved with TVDs when available)
        ecd_profile = []
        cum_annular = 0.0
        annular_secs_reversed = [s for s in reversed(section_results)
                                  if "annulus" in s.get("section_type", "")]
        for i, sec in enumerate(annular_secs_reversed):
            cum_annular += sec["pressure_loss_psi"]

            # Use real TVD if available, else estimate from depth fraction
            if annular_tvds and i < len(annular_tvds):
                est_tvd = annular_tvds[len(annular_tvds) - 1 - i]
            else:
                depth_frac = cum_annular / total_annular_loss if total_annular_loss > 0 else 0
                est_tvd = tvd * (1 - depth_frac)

            if est_tvd > 0:
                ecd_at_depth = mud_weight + cum_annular / (0.052 * est_tvd)
                ecd_profile.append({
                    "tvd": round(est_tvd, 0),
                    "ecd": round(ecd_at_depth, 2)
                })

        summary = {
            "total_spp_psi": round(total_spp, 0),
            "surface_equipment_psi": round(surface_equipment_loss, 0),
            "pipe_loss_psi": round(total_pipe_loss - surface_equipment_loss, 0),
            "bit_loss_psi": round(bit_loss, 0),
            "annular_loss_psi": round(total_annular_loss, 0),
            "ecd_at_td": ecd_result["ecd_ppg"],
            "ecd_status": ecd_result["status"],
            "flow_rate": flow_rate,
            "mud_weight": mud_weight,
            "rheology_model": rheology_model
        }

        return {
            "section_results": section_results,
            "bit_hydraulics": bit_result,
            "ecd": ecd_result,
            "ecd_profile": ecd_profile,
            "annular_analysis": annular_analysis,
            "summary": summary
        }

    @staticmethod
    def calculate_surge_swab(
        mud_weight: float,
        pv: float,
        yp: float,
        tvd: float,
        pipe_od: float,
        pipe_id: float,
        hole_id: float,
        pipe_velocity_fpm: float,
        pipe_open: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate surge and swab pressures (Bourgoyne model).

        Parameters:
        - pipe_velocity_fpm: tripping speed in ft/min (positive = running in / surge)
        - pipe_open: True if pipe is open-ended, False if closed
        """
        if tvd <= 0 or hole_id <= pipe_od:
            return {"error": "Invalid geometry"}

        # Clinging constant (Burkhardt)
        d_ratio = pipe_od / hole_id
        k_c = 0.45  # default clinging constant
        if d_ratio < 0.3:
            k_c = 0.3
        elif d_ratio > 0.7:
            k_c = 0.6

        # Effective velocity in annulus
        annular_area = math.pi / 4.0 * (hole_id**2 - pipe_od**2)
        pipe_displacement = math.pi / 4.0 * pipe_od**2

        if pipe_open:
            # Open pipe: fluid flows through pipe and annulus
            pipe_area_inner = math.pi / 4.0 * pipe_id**2
            flow_area = annular_area + pipe_area_inner
            v_eff = abs(pipe_velocity_fpm) * pipe_displacement / annular_area * k_c
        else:
            # Closed pipe: all displacement goes to annulus
            v_eff = abs(pipe_velocity_fpm) * pipe_displacement / annular_area

        # Calculate annular pressure loss at this effective velocity
        # Using Bingham model for annular flow
        d_eff = hole_id - pipe_od
        if d_eff <= 0:
            return {"error": "Zero annular gap"}

        # Equivalent flow rate
        q_equiv = v_eff * (hole_id**2 - pipe_od**2) / 24.5

        if q_equiv > 0:
            result = HydraulicsEngine.pressure_loss_bingham(
                flow_rate=q_equiv,
                mud_weight=mud_weight,
                pv=pv, yp=yp,
                length=tvd,  # approximate — full string length
                od=hole_id,
                id_inner=pipe_od,
                is_annular=True
            )
            surge_pressure = result["pressure_loss_psi"]
        else:
            surge_pressure = 0.0

        # Convert to EMW
        surge_emw = surge_pressure / (0.052 * tvd) if tvd > 0 else 0
        swab_emw = surge_emw  # magnitude is same, direction differs

        surge_ecd = mud_weight + surge_emw
        swab_ecd = mud_weight - swab_emw

        # Safety margins
        surge_margin = "OK"
        swab_margin = "OK"

        if surge_emw > 0.5:
            surge_margin = "WARNING — Risk of losses"
        if surge_emw > 1.0:
            surge_margin = "CRITICAL — Likely fracturing"

        if swab_emw > 0.3:
            swab_margin = "WARNING — Risk of kick/influx"
        if swab_emw > 0.5:
            swab_margin = "CRITICAL — Likely swabbing in formation fluid"

        return {
            "surge_pressure_psi": round(surge_pressure, 0),
            "swab_pressure_psi": round(surge_pressure, 0),
            "surge_emw_ppg": round(surge_emw, 2),
            "swab_emw_ppg": round(swab_emw, 2),
            "surge_ecd_ppg": round(surge_ecd, 2),
            "swab_ecd_ppg": round(swab_ecd, 2),
            "effective_velocity_fpm": round(v_eff, 1),
            "clinging_constant": k_c,
            "pipe_velocity_fpm": abs(pipe_velocity_fpm),
            "pipe_status": "open" if pipe_open else "closed",
            "surge_margin": surge_margin,
            "swab_margin": swab_margin
        }

    @staticmethod
    def _zero_result() -> Dict[str, Any]:
        return {
            "pressure_loss_psi": 0.0,
            "velocity_ft_min": 0.0,
            "reynolds": 0,
            "flow_regime": "none",
            "d_eff": 0.0
        }
