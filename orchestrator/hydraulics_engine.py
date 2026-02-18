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
            if is_annular:
                dp = (f * mud_weight * v**2 * length) / (21.1 * d_eff)
            else:
                dp = (f * mud_weight * v**2 * length) / (25.8 * d_eff)

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
        surface_equipment_loss: float = 80.0
    ) -> Dict[str, Any]:
        """
        Calculate full hydraulic circuit: Surface -> DP -> BHA -> Bit -> Annular

        Parameters:
        - sections: list of {section_type, length, od, id_inner}
          section_type: 'drill_pipe', 'hwdp', 'collar', 'annulus_dp', 'annulus_dc', 'annulus_hwdp'
        - rheology_model: 'bingham_plastic' or 'power_law'
        """
        section_results = []
        total_pipe_loss = surface_equipment_loss
        total_annular_loss = 0.0

        for sec in sections:
            is_annular = "annulus" in sec.get("section_type", "")

            if rheology_model == "power_law":
                result = HydraulicsEngine.pressure_loss_power_law(
                    flow_rate=flow_rate,
                    mud_weight=mud_weight,
                    n=n, k=k,
                    length=sec["length"],
                    od=sec["od"],
                    id_inner=sec["id_inner"],
                    is_annular=is_annular
                )
            else:
                result = HydraulicsEngine.pressure_loss_bingham(
                    flow_rate=flow_rate,
                    mud_weight=mud_weight,
                    pv=pv, yp=yp,
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

        # ECD profile at various depths
        ecd_profile = []
        cum_annular = 0.0
        for sec in reversed(section_results):
            if "annulus" in sec.get("section_type", ""):
                cum_annular += sec["pressure_loss_psi"]
                depth_frac = cum_annular / total_annular_loss if total_annular_loss > 0 else 0
                est_tvd = tvd * (1 - depth_frac)  # rough depth estimate
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
