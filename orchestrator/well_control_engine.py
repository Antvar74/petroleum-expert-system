"""
Well Control / Kill Sheet Calculation Engine
Based on IWCF/IADC Well Control Standards
References: Well Control for the Drilling Team (IWCF), Applied Drilling Engineering (Bourgoyne)
"""
import math
from typing import Dict, Any, List, Optional


class WellControlEngine:
    """
    Complete well control calculation engine: kill sheet calculations,
    pressure schedules, multiple kill methods (Driller's, Wait & Weight,
    Volumetric, Bullhead).
    """

    HYDROSTATIC_CONSTANT = 0.052  # psi/ft/ppg

    # Dranchuk-Abou-Kassem (DAK) 11 coefficients for Z-factor correlation
    _DAK = {
        "A1": 0.3265, "A2": -1.0700, "A3": -0.5339, "A4": 0.01569,
        "A5": -0.05165, "A6": 0.5475, "A7": -0.7361, "A8": 0.6853,
        "A9": 0.6123, "A10": 0.10489, "A11": 0.68157
    }

    @staticmethod
    def calculate_z_factor(
        pressure: float, temperature: float, gas_gravity: float = 0.65
    ) -> Dict[str, Any]:
        """
        Calculate real gas Z-factor using Dranchuk-Abou-Kassem (DAK) correlation
        with Standing's pseudo-critical property correlations.

        Parameters:
        - pressure: absolute pressure (psia)
        - temperature: temperature (°F)
        - gas_gravity: gas specific gravity (air = 1.0), default 0.65

        Returns:
        - z_factor, pseudo-critical/reduced properties, convergence info
        """
        # Guard: non-physical inputs
        if pressure <= 0 or gas_gravity <= 0:
            return {
                "z_factor": 1.0,
                "pseudo_critical_pressure": 0.0,
                "pseudo_critical_temperature": 0.0,
                "pseudo_reduced_pressure": 0.0,
                "pseudo_reduced_temperature": 0.0,
                "iterations": 0,
                "converged": True
            }

        # Standing correlations for pseudo-critical properties
        sg = gas_gravity
        t_pc = 168.0 + 325.0 * sg - 12.5 * sg**2        # °R
        p_pc = 677.0 + 15.0 * sg - 37.5 * sg**2          # psia

        # Pseudo-reduced properties
        t_pr = (temperature + 460.0) / t_pc               # dimensionless
        p_pr = pressure / p_pc                             # dimensionless

        # Guard: very low temperature
        t_pr = max(t_pr, 1.05)

        # DAK coefficients
        A = WellControlEngine._DAK
        A1, A2, A3 = A["A1"], A["A2"], A["A3"]
        A4, A5, A6 = A["A4"], A["A5"], A["A6"]
        A7, A8, A9 = A["A7"], A["A8"], A["A9"]
        A10, A11 = A["A10"], A["A11"]

        # Newton-Raphson iteration
        z = 1.0  # initial guess
        converged = False
        max_iter = 15
        tol = 1e-6

        for i in range(max_iter):
            rho_r = 0.27 * p_pr / (z * t_pr)

            # F(Z) = Z - [1 + C1*rho + C2*rho^2 - C3*rho^5 + C4]
            c1 = (A1 + A2 / t_pr + A3 / t_pr**3 + A4 / t_pr**4 + A5 / t_pr**5)
            c2 = (A6 + A7 / t_pr + A8 / t_pr**2)
            c3 = A9 * (A7 / t_pr + A8 / t_pr**2)
            c4_exp = -A11 * rho_r**2
            c4 = A10 * (1.0 + A11 * rho_r**2) * (rho_r**2 / t_pr**3) * math.exp(c4_exp)

            f_z = z - (1.0 + c1 * rho_r + c2 * rho_r**2 - c3 * rho_r**5 + c4)

            # Derivative dF/dZ (chain rule: d_rho_r/dZ = -rho_r/Z)
            d_rho_dz = -rho_r / z
            dc4_drho = A10 * rho_r / t_pr**3 * (
                2.0 * (1.0 + A11 * rho_r**2) +
                2.0 * A11 * rho_r**2
            ) * math.exp(c4_exp) + A10 * (1.0 + A11 * rho_r**2) * (
                rho_r**2 / t_pr**3
            ) * math.exp(c4_exp) * (-2.0 * A11 * rho_r)

            df_dz = 1.0 - (c1 + 2.0 * c2 * rho_r - 5.0 * c3 * rho_r**4 + dc4_drho) * d_rho_dz

            if abs(df_dz) < 1e-15:
                break

            z_new = z - f_z / df_dz

            # Clamp to physical range
            z_new = max(0.05, min(z_new, 3.0))

            if abs(z_new - z) < tol:
                z = z_new
                converged = True
                break

            z = z_new

        return {
            "z_factor": round(z, 6),
            "pseudo_critical_pressure": round(p_pc, 2),
            "pseudo_critical_temperature": round(t_pc, 2),
            "pseudo_reduced_pressure": round(p_pr, 4),
            "pseudo_reduced_temperature": round(t_pr, 4),
            "iterations": i + 1,
            "converged": converged
        }

    @staticmethod
    def calculate_gas_volume(
        p1: float, t1: float, v1: float,
        p2: float, t2: float, gas_gravity: float = 0.65
    ) -> Dict[str, Any]:
        """
        Calculate gas volume at new conditions using real gas law (PV=ZnRT).

        V2 = V1 * (P1/P2) * (Z2/Z1) * (T2_R/T1_R)

        Parameters:
        - p1, t1, v1: initial pressure (psia), temperature (°F), volume (bbl)
        - p2, t2: final pressure (psia), temperature (°F)
        - gas_gravity: gas specific gravity (air = 1.0)

        Returns:
        - v2_bbl, z1, z2, expansion_ratio
        """
        if p2 <= 0:
            return {
                "v2_bbl": 0.0, "z1": 1.0, "z2": 1.0,
                "expansion_ratio": 0.0,
                "error": "Final pressure must be > 0",
                "p1": p1, "t1": t1, "v1": v1, "p2": p2, "t2": t2
            }

        if p1 <= 0 or v1 <= 0:
            return {
                "v2_bbl": 0.0, "z1": 1.0, "z2": 1.0,
                "expansion_ratio": 0.0,
                "p1": p1, "t1": t1, "v1": v1, "p2": p2, "t2": t2
            }

        # Calculate Z-factors at both conditions
        z1_result = WellControlEngine.calculate_z_factor(p1, t1, gas_gravity)
        z2_result = WellControlEngine.calculate_z_factor(p2, t2, gas_gravity)

        z1 = z1_result["z_factor"]
        z2 = z2_result["z_factor"]

        # Absolute temperatures (Rankine)
        t1_r = t1 + 460.0
        t2_r = t2 + 460.0

        # Real gas law: V2 = V1 * (P1/P2) * (Z2/Z1) * (T2_R/T1_R)
        v2 = v1 * (p1 / p2) * (z2 / z1) * (t2_r / t1_r)

        expansion_ratio = v2 / v1 if v1 > 0 else 0.0

        return {
            "v2_bbl": round(v2, 4),
            "z1": round(z1, 6),
            "z2": round(z2, 6),
            "expansion_ratio": round(expansion_ratio, 4),
            "p1": p1, "t1": t1, "v1": v1, "p2": p2, "t2": t2
        }

    @staticmethod
    def calculate_kill_sheet(
        depth_md: float,
        depth_tvd: float,
        original_mud_weight: float,
        casing_shoe_tvd: float,
        sidpp: float,
        sicp: float,
        pit_gain: float,
        scr_pressure: float,
        scr_rate: float,
        dp_capacity: float,
        annular_capacity: float,
        strokes_surface_to_bit: float,
        lot_emw: float,
        casing_id: float = 0.0,
        strokes_bit_to_surface: float = 0.0,
        total_strokes: float = 0.0
    ) -> Dict[str, Any]:
        """
        Complete kill sheet calculation.

        Parameters:
        - depth_md, depth_tvd: well depths (ft)
        - original_mud_weight: current mud weight (ppg)
        - casing_shoe_tvd: TVD of last casing shoe (ft)
        - sidpp: shut-in drill pipe pressure (psi)
        - sicp: shut-in casing pressure (psi)
        - pit_gain: observed pit gain (bbl)
        - scr_pressure: slow circulating rate pressure (psi)
        - scr_rate: slow circulating rate (spm)
        - dp_capacity: drill pipe capacity (bbl/ft)
        - annular_capacity: annular capacity (bbl/ft)
        - strokes_surface_to_bit: pump strokes from surface to bit
        - lot_emw: LOT/FIT equivalent mud weight (ppg)
        - casing_id: casing inside diameter (inches)
        """
        h = WellControlEngine.HYDROSTATIC_CONSTANT

        # ============================================================
        # 1. Formation Pressure
        # ============================================================
        # FP = Hydrostatic + SIDPP
        hydrostatic_original = original_mud_weight * h * depth_tvd
        formation_pressure = hydrostatic_original + sidpp

        # ============================================================
        # 2. Kill Mud Weight (KMW)
        # ============================================================
        # KMW = FP / (0.052 * TVD)
        if depth_tvd > 0:
            kill_mud_weight = formation_pressure / (h * depth_tvd)
        else:
            kill_mud_weight = original_mud_weight

        mud_weight_increase = kill_mud_weight - original_mud_weight

        # ============================================================
        # 3. Initial Circulating Pressure (ICP)
        # ============================================================
        # ICP = SIDPP + SCR pressure
        icp = sidpp + scr_pressure

        # ============================================================
        # 4. Final Circulating Pressure (FCP)
        # ============================================================
        # FCP = SCR * (KMW / OMW)
        if original_mud_weight > 0:
            fcp = scr_pressure * (kill_mud_weight / original_mud_weight)
        else:
            fcp = scr_pressure

        # ============================================================
        # 5. MAASP (Maximum Allowable Annular Surface Pressure)
        # ============================================================
        # MAASP = (LOT_emw - OMW) * 0.052 * shoe_TVD
        maasp = (lot_emw - original_mud_weight) * h * casing_shoe_tvd

        # MAASP with KMW
        maasp_with_kmw = (lot_emw - kill_mud_weight) * h * casing_shoe_tvd

        # ============================================================
        # 6. Influx Analysis
        # ============================================================
        # Influx height (approximate)
        if annular_capacity > 0:
            influx_height = pit_gain / annular_capacity
        else:
            influx_height = 0

        # Influx gradient
        # grad_influx = OMW * 0.052 - (SICP - SIDPP) / influx_height
        if influx_height > 0:
            influx_gradient = original_mud_weight * h - (sicp - sidpp) / influx_height
        else:
            influx_gradient = 0

        # Influx type classification
        if influx_gradient < 0.1:
            influx_type = "Gas (dry gas)"
        elif influx_gradient < 0.25:
            influx_type = "Gas (wet gas / condensate)"
        elif influx_gradient < 0.35:
            influx_type = "Oil"
        elif influx_gradient < 0.45:
            influx_type = "Salt Water"
        else:
            influx_type = "Weighted fluid / Unknown"

        # ============================================================
        # 7. Strokes and Volumes
        # ============================================================
        if strokes_bit_to_surface <= 0 and total_strokes > 0:
            strokes_bit_to_surface = total_strokes - strokes_surface_to_bit

        if total_strokes <= 0:
            total_strokes = strokes_surface_to_bit + strokes_bit_to_surface

        # Volume calculations
        dp_volume = dp_capacity * depth_md if dp_capacity > 0 else 0
        annular_volume = annular_capacity * depth_md if annular_capacity > 0 else 0
        total_circulating_volume = dp_volume + annular_volume

        # ============================================================
        # 8. Pressure Schedule
        # ============================================================
        schedule = WellControlEngine.generate_pressure_schedule(
            icp=icp, fcp=fcp,
            strokes_surface_to_bit=strokes_surface_to_bit
        )

        # ============================================================
        # Safety Checks
        # ============================================================
        alerts = []
        if sicp > maasp:
            alerts.append(f"CRITICAL: SICP ({sicp} psi) exceeds MAASP ({round(maasp)} psi)")
        if mud_weight_increase > 2.0:
            alerts.append(f"WARNING: Large MW increase required ({round(mud_weight_increase, 1)} ppg)")
        if influx_type.startswith("Gas"):
            alerts.append("WARNING: Gas influx — monitor for expansion during kill")
        if kill_mud_weight > lot_emw:
            alerts.append(f"CRITICAL: KMW ({round(kill_mud_weight, 1)} ppg) exceeds LOT ({lot_emw} ppg)")

        return {
            "formation_pressure_psi": round(formation_pressure, 0),
            "kill_mud_weight_ppg": round(kill_mud_weight, 2),
            "mud_weight_increase_ppg": round(mud_weight_increase, 2),
            "icp_psi": round(icp, 0),
            "fcp_psi": round(fcp, 0),
            "maasp_psi": round(maasp, 0),
            "maasp_with_kmw_psi": round(maasp_with_kmw, 0),
            "influx_height_ft": round(influx_height, 0),
            "influx_gradient_psi_ft": round(influx_gradient, 4),
            "influx_type": influx_type,
            "strokes_surface_to_bit": round(strokes_surface_to_bit, 0),
            "strokes_bit_to_surface": round(strokes_bit_to_surface, 0),
            "total_strokes": round(total_strokes, 0),
            "dp_volume_bbl": round(dp_volume, 1),
            "annular_volume_bbl": round(annular_volume, 1),
            "total_volume_bbl": round(total_circulating_volume, 1),
            "pressure_schedule": schedule,
            "alerts": alerts
        }

    @staticmethod
    def calculate_barite_requirements(
        current_mud_weight: float,
        target_mud_weight: float,
        system_volume_bbl: float,
        barite_sg: float = 4.20,
        sack_weight_lbs: float = 100.0
    ) -> Dict[str, Any]:
        """
        Calculate barite (weighting material) requirements to increase mud weight.

        Uses API standard formula for mixing calculations.

        Args:
            current_mud_weight: current mud weight (ppg)
            target_mud_weight: desired mud weight (ppg)
            system_volume_bbl: active system volume (bbl)
            barite_sg: specific gravity of barite (default 4.20)
            sack_weight_lbs: weight per sack (default 100 lbs)

        Returns:
            Dict with barite_lbs, barite_sacks, final_volume_increase_bbl, etc.
        """
        # Equivalent density of barite in ppg
        barite_ppg = barite_sg * 8.345  # 8.345 lbs/gal per SG unit = ppg

        # Guards
        if target_mud_weight <= current_mud_weight:
            return {
                "barite_lbs": 0.0,
                "barite_sacks": 0.0,
                "final_volume_increase_bbl": 0.0,
                "mix_time_estimate_hrs": 0.0,
                "barite_sg": barite_sg,
                "barite_ppg": round(barite_ppg, 1),
                "current_mw_ppg": current_mud_weight,
                "target_mw_ppg": target_mud_weight,
                "alert": "Target MW <= Current MW — no weighting needed"
            }

        if target_mud_weight >= barite_ppg:
            return {
                "error": f"Target MW ({target_mud_weight} ppg) >= barite density ({barite_ppg:.1f} ppg) — physically impossible",
                "barite_lbs": 0.0,
                "barite_sacks": 0.0,
                "final_volume_increase_bbl": 0.0,
                "mix_time_estimate_hrs": 0.0,
                "barite_sg": barite_sg,
                "barite_ppg": round(barite_ppg, 1),
                "current_mw_ppg": current_mud_weight,
                "target_mw_ppg": target_mud_weight
            }

        if system_volume_bbl <= 0 or current_mud_weight <= 0:
            return {
                "error": "Invalid input — system volume and current MW must be > 0",
                "barite_lbs": 0.0,
                "barite_sacks": 0.0,
                "final_volume_increase_bbl": 0.0,
                "mix_time_estimate_hrs": 0.0,
                "barite_sg": barite_sg,
                "barite_ppg": round(barite_ppg, 1),
                "current_mw_ppg": current_mud_weight,
                "target_mw_ppg": target_mud_weight
            }

        # API formula: lbs = 1470 * V * (MW_target - MW_current) / (barite_ppg - MW_target)
        # 1470 = 42 gal/bbl * 8.345 lbs/gal / 0.2386... ≈ conversion factor
        # Derivation: mass balance V_bbl * 42 * MW_t = V_bbl * 42 * MW_c + lbs * (1 - MW_t/barite_ppg * ...)
        barite_lbs = 1470.0 * system_volume_bbl * (target_mud_weight - current_mud_weight) / (barite_ppg - target_mud_weight)

        # Number of sacks
        barite_sacks = barite_lbs / sack_weight_lbs

        # Volume increase: displaced volume of barite added
        # 1 bbl = 350 lbs of water; barite at SG 4.2 → 350 * 4.2 = 1470 lbs/bbl
        volume_increase_bbl = barite_lbs / (barite_sg * 350.0)

        # Mix time estimate: ~2000 lbs/hr with standard hopper
        mix_time_hrs = barite_lbs / 2000.0

        return {
            "barite_lbs": round(barite_lbs, 0),
            "barite_sacks": round(barite_sacks, 1),
            "final_volume_increase_bbl": round(volume_increase_bbl, 1),
            "mix_time_estimate_hrs": round(mix_time_hrs, 1),
            "barite_sg": barite_sg,
            "barite_ppg": round(barite_ppg, 1),
            "current_mw_ppg": current_mud_weight,
            "target_mw_ppg": target_mud_weight
        }

    @staticmethod
    def generate_pressure_schedule(
        icp: float,
        fcp: float,
        strokes_surface_to_bit: float,
        intervals: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate linear pressure reduction schedule (ICP -> FCP)
        over strokes from surface to bit.

        Used in Wait & Weight method during first circulation.
        """
        if strokes_surface_to_bit <= 0:
            return []

        schedule = []
        stroke_increment = strokes_surface_to_bit / intervals
        pressure_drop_per_step = (icp - fcp) / intervals

        for i in range(intervals + 1):
            strokes = round(stroke_increment * i)
            pressure = icp - (pressure_drop_per_step * i)
            pct = (i / intervals) * 100

            schedule.append({
                "step": i,
                "strokes": strokes,
                "pressure_psi": round(pressure, 0),
                "percent_complete": round(pct, 0)
            })

        return schedule

    @staticmethod
    def calculate_drillers_method(
        kill_sheet: Dict[str, Any],
        scr_pressure: float
    ) -> Dict[str, Any]:
        """
        Driller's Method: Two-circulation kill.
        1st Circulation: Kill influx with original MW
        2nd Circulation: Displace kill mud weight

        Parameters:
        - kill_sheet: output from calculate_kill_sheet
        - scr_pressure: slow circulating rate pressure
        """
        sidpp = kill_sheet.get("icp_psi", 0) - scr_pressure
        icp = kill_sheet["icp_psi"]
        total_strokes = kill_sheet["total_strokes"]

        return {
            "method": "Driller's Method",
            "circulations": 2,
            "first_circulation": {
                "description": "Circulate out influx with original mud weight",
                "dp_pressure": icp,
                "maintain": "Constant drill pipe pressure",
                "duration_strokes": total_strokes,
                "notes": [
                    "Hold DP pressure constant at ICP",
                    "Adjust choke to maintain DP pressure",
                    "Monitor casing pressure — should decline as influx is displaced",
                    "Watch for gas expansion approaching surface"
                ]
            },
            "between_circulations": {
                "description": "Weight up mud to kill weight",
                "target_mw": kill_sheet["kill_mud_weight_ppg"],
                "volume_needed_bbl": kill_sheet["total_volume_bbl"]
            },
            "second_circulation": {
                "description": "Displace kill mud through entire system",
                "dp_pressure_start": icp,
                "dp_pressure_end": kill_sheet["fcp_psi"],
                "maintain": "Constant BHP via pressure schedule",
                "duration_strokes": total_strokes,
                "notes": [
                    "Follow ICP to FCP schedule while pumping to bit",
                    "Hold FCP constant from bit to surface",
                    "After complete displacement, SIDPP should be zero"
                ]
            },
            "advantages": [
                "Simple — no waiting to weight up",
                "Faster initial response",
                "Less calculation required"
            ],
            "disadvantages": [
                "Higher casing pressure during first circulation",
                "Two full circulations required",
                "Higher ECD during kill"
            ]
        }

    @staticmethod
    def calculate_wait_and_weight(
        kill_sheet: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Wait and Weight (Engineer's) Method: One-circulation kill.
        Weight up mud to kill weight, then circulate once.
        """
        return {
            "method": "Wait and Weight",
            "circulations": 1,
            "preparation": {
                "description": "Weight up mud to kill weight before circulating",
                "target_mw": kill_sheet["kill_mud_weight_ppg"],
                "volume_needed_bbl": kill_sheet["total_volume_bbl"],
                "notes": [
                    "Weight up entire surface volume to KMW",
                    "Monitor SIDPP — should remain constant",
                    "Prepare pressure schedule (ICP to FCP)"
                ]
            },
            "single_circulation": {
                "description": "Circulate kill mud through entire system",
                "icp": kill_sheet["icp_psi"],
                "fcp": kill_sheet["fcp_psi"],
                "pressure_schedule": kill_sheet["pressure_schedule"],
                "strokes_to_bit": kill_sheet["strokes_surface_to_bit"],
                "total_strokes": kill_sheet["total_strokes"],
                "notes": [
                    "Follow ICP to FCP schedule (surface to bit)",
                    "Hold FCP constant (bit to surface)",
                    "Adjust choke to maintain schedule",
                    "After full displacement, SIDPP should be zero",
                    "Close choke and verify well is dead"
                ]
            },
            "advantages": [
                "Lower casing pressures throughout",
                "Only one circulation required",
                "Preferred method for gas kicks"
            ],
            "disadvantages": [
                "Must wait to weight up mud (time)",
                "More complex pressure calculations",
                "Requires disciplined execution"
            ]
        }

    @staticmethod
    def calculate_volumetric(
        mud_weight: float,
        sicp: float,
        tvd: float,
        annular_capacity: float,
        lot_emw: float,
        casing_shoe_tvd: float,
        safety_margin_psi: float = 50.0,
        pressure_increment_psi: float = 100.0,
        gas_gravity: float = 0.65,
        bht: float = 150.0,
        use_real_gas: bool = False,
        kick_volume_bbl: float = 0.0
    ) -> Dict[str, Any]:
        """
        Volumetric Method: No circulation required (for when pumps are unavailable
        or pipe is stuck off-bottom).

        Allows controlled expansion of gas influx while maintaining BHP.

        Parameters:
        - safety_margin_psi: additional safety margin above SIDPP
        - pressure_increment_psi: pressure increase allowed per cycle
        - gas_gravity: gas SG for real gas Z-factor (default 0.65)
        - bht: bottom hole temperature (°F)
        - use_real_gas: if True, calculate gas expansion per cycle with Z-factor
        - kick_volume_bbl: initial kick volume (bbl), used when use_real_gas=True
        """
        h = WellControlEngine.HYDROSTATIC_CONSTANT

        # MAASP
        maasp = (lot_emw - mud_weight) * h * casing_shoe_tvd

        # Working pressure
        working_pressure = sicp + safety_margin_psi

        # Volume per cycle: V = (dP * annular_cap) / (MW * 0.052)
        # Volume to bleed to reduce annular pressure by pressure_increment
        if mud_weight > 0:
            volume_per_cycle = (pressure_increment_psi * annular_capacity) / (mud_weight * h)
        else:
            volume_per_cycle = 0

        # Estimate number of cycles for gas to reach surface
        # Gas height at bottom
        gas_pressure = mud_weight * h * tvd - sicp  # approximate
        if gas_pressure <= 0:
            gas_pressure = sicp

        # Number of cycles (rough estimate)
        if pressure_increment_psi > 0:
            n_cycles = max(1, round(tvd * annular_capacity * mud_weight * h / (pressure_increment_psi * annular_capacity * 10)))
            n_cycles = min(n_cycles, 50)  # cap at 50
        else:
            n_cycles = 10

        # Generate cycle plan
        cycles = []
        current_csg_pressure = sicp
        # Real gas tracking: estimate gas position and volume per cycle
        gas_vol_current = kick_volume_bbl if kick_volume_bbl > 0 else volume_per_cycle * 2
        p_bh = mud_weight * h * tvd  # initial BHP estimate

        for i in range(1, n_cycles + 1):
            allow_increase = current_csg_pressure + pressure_increment_psi
            if allow_increase > maasp:
                allow_increase = maasp

            cycle_bleed = volume_per_cycle

            # Real gas expansion: recalculate gas volume as it migrates up
            if use_real_gas and gas_vol_current > 0:
                # Approximate gas pressure at current depth (reduces each cycle)
                p_gas_old = p_bh - (i - 1) * pressure_increment_psi
                p_gas_new = p_gas_old - pressure_increment_psi
                p_gas_old = max(p_gas_old, 100.0)
                p_gas_new = max(p_gas_new, 100.0)
                # Temperature at approximate gas depth (linear gradient)
                t_frac = max(1.0 - i / max(n_cycles, 1), 0.05)
                t_gas = 80.0 + (bht - 80.0) * t_frac  # surface ~80F to BHT
                gas_expand = WellControlEngine.calculate_gas_volume(
                    p1=p_gas_old, t1=t_gas + 10, v1=gas_vol_current,
                    p2=p_gas_new, t2=t_gas, gas_gravity=gas_gravity
                )
                gas_vol_new = gas_expand["v2_bbl"]
                cycle_bleed = max(gas_vol_new - gas_vol_current, volume_per_cycle)
                gas_vol_current = gas_vol_new

            cycles.append({
                "cycle": i,
                "step_1": f"Allow casing pressure to increase by {pressure_increment_psi} psi to {round(allow_increase)} psi",
                "step_2": f"Bleed {round(cycle_bleed, 2)} bbl to reduce pressure by {pressure_increment_psi} psi",
                "step_3": f"Casing pressure returns to ~{round(current_csg_pressure + safety_margin_psi)} psi",
                "max_pressure": round(allow_increase),
                "volume_bled": round(cycle_bleed, 2)
            })
            current_csg_pressure = current_csg_pressure + safety_margin_psi * 0.1  # small increase per cycle

        return {
            "method": "Volumetric",
            "applicable_when": [
                "Cannot circulate (stuck pipe, failed pumps)",
                "Pipe off bottom",
                "Waiting on kill mud / equipment"
            ],
            "initial_conditions": {
                "sicp_psi": sicp,
                "mud_weight_ppg": mud_weight,
                "maasp_psi": round(maasp, 0),
                "working_pressure_psi": round(working_pressure, 0)
            },
            "parameters": {
                "pressure_increment_psi": pressure_increment_psi,
                "volume_per_cycle_bbl": round(volume_per_cycle, 2),
                "safety_margin_psi": safety_margin_psi,
                "estimated_cycles": n_cycles
            },
            "procedure": [
                "Record initial SICP",
                f"Set working pressure: SICP + {safety_margin_psi} psi = {round(working_pressure)} psi",
                f"Allow casing pressure to increase by {pressure_increment_psi} psi increments",
                f"Bleed {round(volume_per_cycle, 2)} bbl per increment to maintain BHP",
                "Repeat until gas reaches surface",
                "Consider lubricate & bleed or bullhead if gas volume is manageable"
            ],
            "cycles": cycles,
            "warnings": [
                "Monitor casing pressure continuously",
                f"Do not exceed MAASP ({round(maasp)} psi)",
                "Track cumulative volume bled",
                "Gas expansion accelerates near surface"
            ]
        }

    @staticmethod
    def calculate_kick_tolerance(
        mud_weight: float, shoe_tvd: float, lot_emw: float,
        well_depth_tvd: float, gas_gravity: float = 0.65,
        bht: float = 150.0, annular_capacity: float = 0.05,
        influx_type: str = "gas",
        shoe_depths: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate kick tolerance: maximum influx volume that can be circulated
        out without exceeding fracture pressure at the shoe.

        Parameters:
        - mud_weight: current mud weight (ppg)
        - shoe_tvd: casing shoe TVD (ft)
        - lot_emw: leak-off test equivalent mud weight (ppg)
        - well_depth_tvd: total well depth TVD (ft)
        - gas_gravity: gas SG for Z-factor calculation
        - bht: bottom hole temperature (°F)
        - annular_capacity: annular capacity (bbl/ft)
        - influx_type: 'gas' or 'liquid'
        - shoe_depths: optional list of shoe TVDs for multi-shoe KT table

        Returns:
        - kick_tolerance_bbl, kick_tolerance_psi (MAASP), max_influx_height,
          gas_gradient, kt_table (if multi-shoe)
        """
        h_const = WellControlEngine.HYDROSTATIC_CONSTANT

        # Guards
        if shoe_tvd <= 0 or well_depth_tvd <= 0:
            return {
                "kick_tolerance_bbl": 0.0, "kick_tolerance_psi": 0.0,
                "max_influx_height_ft": 0.0, "gas_gradient_psi_ft": 0.0,
                "maasp_psi": 0.0, "kt_table": [], "parameters": {},
                "alerts": ["Invalid depth inputs"]
            }

        # MAASP: Maximum Allowable Annular Surface Pressure
        maasp = (lot_emw - mud_weight) * h_const * shoe_tvd

        alerts = []
        if maasp <= 0:
            alerts.append("LOT EMW <= current mud weight — zero kick tolerance")
            return {
                "kick_tolerance_bbl": 0.0, "kick_tolerance_psi": round(maasp, 1),
                "max_influx_height_ft": 0.0, "gas_gradient_psi_ft": 0.0,
                "maasp_psi": 0.0, "kt_table": [], "parameters": {},
                "alerts": alerts
            }

        if influx_type == "gas":
            # Gas density at bottom hole conditions using real gas Z-factor
            p_bh = mud_weight * h_const * well_depth_tvd  # psi
            t_bh_r = bht + 460.0  # Rankine

            z_result = WellControlEngine.calculate_z_factor(p_bh, bht, gas_gravity)
            z_bh = z_result["z_factor"]

            # Gas density: rho_gas = 2.7 * SG * P / (Z * T_R)  (ppg)
            rho_gas = 2.7 * gas_gravity * p_bh / (z_bh * t_bh_r) if t_bh_r > 0 else 0.0

            # Gas gradient
            gas_gradient = rho_gas * h_const  # psi/ft
        else:
            # Liquid influx (e.g., salt water kick)
            rho_gas = 8.6  # typical salt water ppg
            gas_gradient = rho_gas * h_const

        # Mud gradient
        mud_gradient = mud_weight * h_const

        # Maximum influx height before fracturing at shoe
        gradient_diff = mud_gradient - gas_gradient
        if gradient_diff <= 0:
            alerts.append("Gas gradient >= mud gradient — infinite kick tolerance (unusual)")
            max_influx_height = well_depth_tvd - shoe_tvd  # limited by geometry
        else:
            max_influx_height = maasp / gradient_diff

        # Limit to available open hole
        open_hole_length = well_depth_tvd - shoe_tvd
        max_influx_height = min(max_influx_height, open_hole_length)

        # Kick tolerance in barrels
        kt_bbl = max_influx_height * annular_capacity

        # Build KT table for multiple shoe depths
        kt_table = []
        if shoe_depths:
            for s_tvd in shoe_depths:
                if s_tvd <= 0:
                    continue
                s_maasp = (lot_emw - mud_weight) * h_const * s_tvd
                if s_maasp <= 0:
                    kt_table.append({
                        "shoe_tvd": s_tvd, "maasp_psi": 0.0,
                        "max_height_ft": 0.0, "kt_bbl": 0.0
                    })
                    continue
                s_height = s_maasp / gradient_diff if gradient_diff > 0 else open_hole_length
                s_height = min(s_height, well_depth_tvd - s_tvd)
                kt_table.append({
                    "shoe_tvd": round(s_tvd, 0),
                    "maasp_psi": round(s_maasp, 1),
                    "max_height_ft": round(s_height, 1),
                    "kt_bbl": round(s_height * annular_capacity, 2)
                })

        return {
            "kick_tolerance_bbl": round(kt_bbl, 2),
            "kick_tolerance_psi": round(maasp, 1),
            "max_influx_height_ft": round(max_influx_height, 1),
            "gas_gradient_psi_ft": round(gas_gradient, 4),
            "maasp_psi": round(maasp, 1),
            "kt_table": kt_table,
            "parameters": {
                "mud_weight": mud_weight,
                "shoe_tvd": shoe_tvd,
                "lot_emw": lot_emw,
                "well_depth_tvd": well_depth_tvd,
                "gas_gravity": gas_gravity,
                "influx_type": influx_type,
                "annular_capacity": annular_capacity
            },
            "alerts": alerts
        }

    @staticmethod
    def calculate_bullhead(
        mud_weight: float,
        kill_mud_weight: float,
        depth_tvd: float,
        casing_shoe_tvd: float,
        lot_emw: float,
        dp_capacity: float,
        depth_md: float,
        formation_pressure: float
    ) -> Dict[str, Any]:
        """
        Bullheading: Pump kill fluid down the drill pipe (or annulus)
        to force the influx back into the formation.

        Used when: pipe is off bottom, cannot circulate conventionally,
        or in some coiled tubing operations.
        """
        h = WellControlEngine.HYDROSTATIC_CONSTANT

        # Required surface pump pressure to bullhead
        # P_pump = Formation_Pressure - Hydrostatic(KMW) + Friction_Loss
        hydrostatic_kill = kill_mud_weight * h * depth_tvd
        friction_estimate = 0.05 * depth_md  # rough 50 psi/1000ft

        pump_pressure = formation_pressure - hydrostatic_kill + friction_estimate
        if pump_pressure < 0:
            pump_pressure = 0

        # Pressure at casing shoe during bullhead
        shoe_pressure = pump_pressure + kill_mud_weight * h * casing_shoe_tvd - friction_estimate * (casing_shoe_tvd / depth_tvd)
        frac_pressure_at_shoe = lot_emw * h * casing_shoe_tvd

        # Volume to displace
        displacement_volume = dp_capacity * depth_md

        # Safety check
        shoe_margin = frac_pressure_at_shoe - shoe_pressure
        shoe_safe = shoe_margin > 0

        return {
            "method": "Bullhead",
            "applicable_when": [
                "Cannot circulate (string not at bottom)",
                "H2S kick (need to push gas back immediately)",
                "Underground blowout containment",
                "Slim hole / coiled tubing operations"
            ],
            "calculations": {
                "formation_pressure_psi": round(formation_pressure, 0),
                "hydrostatic_kill_mud_psi": round(hydrostatic_kill, 0),
                "estimated_friction_psi": round(friction_estimate, 0),
                "required_pump_pressure_psi": round(pump_pressure, 0),
                "displacement_volume_bbl": round(displacement_volume, 1),
                "kill_mud_weight_ppg": round(kill_mud_weight, 2)
            },
            "shoe_integrity": {
                "pressure_at_shoe_psi": round(shoe_pressure, 0),
                "frac_pressure_at_shoe_psi": round(frac_pressure_at_shoe, 0),
                "margin_psi": round(shoe_margin, 0),
                "safe": shoe_safe
            },
            "procedure": [
                f"Weight up {round(displacement_volume, 1)} bbl of kill mud to {round(kill_mud_weight, 2)} ppg",
                f"Line up to pump down drill pipe at controlled rate",
                f"Expected surface pressure: ~{round(pump_pressure, 0)} psi",
                "Pump at slow rate, monitoring annular pressure",
                "Continue until influx is pushed back into formation",
                "Monitor for losses at casing shoe"
            ],
            "warnings": [] if shoe_safe else [
                f"CRITICAL: Estimated shoe pressure ({round(shoe_pressure)} psi) approaches/exceeds frac pressure ({round(frac_pressure_at_shoe)} psi)",
                "Risk of underground blowout if shoe breaks down",
                "Consider alternative kill method"
            ]
        }

    @staticmethod
    def pre_record_kill_sheet(
        well_name: str,
        depth_md: float,
        depth_tvd: float,
        original_mud_weight: float,
        casing_shoe_tvd: float,
        casing_id: float,
        dp_od: float,
        dp_id: float,
        dp_length: float,
        dc_od: float,
        dc_id: float,
        dc_length: float,
        scr_pressure: float,
        scr_rate: float,
        lot_emw: float,
        pump_output: float = 0.1,
        hole_size: float = 8.5
    ) -> Dict[str, Any]:
        """
        Pre-record static kill sheet data (before any kick occurs).
        Calculates volumes, capacities, and strokes.

        Parameters:
        - pump_output: pump output per stroke (bbl/stroke)
        - hole_size: open hole diameter (inches)
        """
        h = WellControlEngine.HYDROSTATIC_CONSTANT

        # ============================================================
        # Capacity Calculations
        # ============================================================
        # Pipe capacity (bbl/ft) = ID² / 1029.4
        dp_capacity = dp_id**2 / 1029.4
        dc_capacity = dc_id**2 / 1029.4

        # Annular capacity (bbl/ft) = (hole² - pipe²) / 1029.4
        # Open hole around DC
        ann_oh_dc = (hole_size**2 - dc_od**2) / 1029.4
        # Open hole around DP
        ann_oh_dp = (hole_size**2 - dp_od**2) / 1029.4
        # Cased hole around DP
        ann_cased_dp = (casing_id**2 - dp_od**2) / 1029.4

        # ============================================================
        # Volume Calculations
        # ============================================================
        dp_volume = dp_capacity * dp_length
        dc_volume = dc_capacity * dc_length
        total_string_volume = dp_volume + dc_volume

        # Cased hole length (approximate)
        cased_length = depth_md - (depth_md - dp_length)  # simplified
        open_hole_length = depth_md - cased_length if cased_length < depth_md else 0

        ann_cased_vol = ann_cased_dp * max(0, dp_length - dc_length)  # approximate
        ann_oh_dp_vol = ann_oh_dp * max(0, open_hole_length - dc_length)
        ann_oh_dc_vol = ann_oh_dc * dc_length
        total_annular_volume = ann_cased_vol + ann_oh_dp_vol + ann_oh_dc_vol
        total_well_volume = total_string_volume + total_annular_volume

        # ============================================================
        # Stroke Calculations
        # ============================================================
        if pump_output > 0:
            strokes_dp = dp_volume / pump_output
            strokes_dc = dc_volume / pump_output
            strokes_surface_to_bit = strokes_dp + strokes_dc
            strokes_annular = total_annular_volume / pump_output
            strokes_bit_to_surface = strokes_annular
            total_strokes = strokes_surface_to_bit + strokes_bit_to_surface
        else:
            strokes_dp = strokes_dc = strokes_surface_to_bit = 0
            strokes_annular = strokes_bit_to_surface = total_strokes = 0

        # ============================================================
        # Pre-calculated values
        # ============================================================
        hydrostatic = original_mud_weight * h * depth_tvd
        maasp = (lot_emw - original_mud_weight) * h * casing_shoe_tvd

        return {
            "well_name": well_name,
            "status": "pre-recorded",
            "well_data": {
                "depth_md": depth_md,
                "depth_tvd": depth_tvd,
                "mud_weight_ppg": original_mud_weight,
                "casing_shoe_tvd": casing_shoe_tvd,
                "casing_id": casing_id,
                "hole_size": hole_size
            },
            "drillstring": {
                "dp_od": dp_od, "dp_id": dp_id, "dp_length": dp_length,
                "dc_od": dc_od, "dc_id": dc_id, "dc_length": dc_length
            },
            "capacities_bbl_ft": {
                "dp_capacity": round(dp_capacity, 5),
                "dc_capacity": round(dc_capacity, 5),
                "annular_oh_dc": round(ann_oh_dc, 5),
                "annular_oh_dp": round(ann_oh_dp, 5),
                "annular_cased_dp": round(ann_cased_dp, 5)
            },
            "volumes_bbl": {
                "dp_volume": round(dp_volume, 1),
                "dc_volume": round(dc_volume, 1),
                "total_string_volume": round(total_string_volume, 1),
                "annular_cased": round(ann_cased_vol, 1),
                "annular_open_dp": round(ann_oh_dp_vol, 1),
                "annular_open_dc": round(ann_oh_dc_vol, 1),
                "total_annular_volume": round(total_annular_volume, 1),
                "total_well_volume": round(total_well_volume, 1)
            },
            "strokes": {
                "pump_output_bbl_stk": pump_output,
                "strokes_dp": round(strokes_dp, 0),
                "strokes_dc": round(strokes_dc, 0),
                "strokes_surface_to_bit": round(strokes_surface_to_bit, 0),
                "strokes_bit_to_surface": round(strokes_bit_to_surface, 0),
                "total_strokes": round(total_strokes, 0)
            },
            "circulation": {
                "scr_pressure_psi": scr_pressure,
                "scr_rate_spm": scr_rate
            },
            "reference_values": {
                "hydrostatic_psi": round(hydrostatic, 0),
                "lot_emw_ppg": lot_emw,
                "maasp_psi": round(maasp, 0)
            }
        }
