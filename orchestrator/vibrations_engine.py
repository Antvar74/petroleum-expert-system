"""
Vibrations & Stability Calculation Engine

Drillstring vibration analysis including axial (bit bounce), lateral (whirl),
torsional (stick-slip), and Mechanical Specific Energy optimization.

Elite enhancements (Phase 8):
- Multi-component BHA modal analysis (Transfer Matrix Method)
- 3D survey coupling for vibration map (depth-varying inclination)
- Bit-rock interaction model (PDC/roller cone excitation frequencies)
- Stabilizer placement optimization (node-based)
- Cumulative fatigue damage tracking (Miner's rule, S-N curves)

References:
- Paslay & Dawson (1984): Drillstring lateral vibrations and whirl
- Jansen & van den Steen (1995): Active damping of stick-slip vibrations
- Teale (1965): Mechanical Specific Energy concept
- Dupriest (2005): MSE-based drilling optimization
- Dunayevsky (1993): Stability of BHA in directional wells
- Mitchell (2003): Transfer Matrix analysis of BHA vibrations
- Miner (1945): Cumulative damage in fatigue
"""
import math
from typing import Dict, Any, List, Optional, Tuple


class VibrationsEngine:
    """
    Implements drillstring vibration analysis and drilling optimization.
    All methods are @staticmethod — no external dependencies beyond math.
    """

    # Steel properties
    STEEL_E = 30e6         # Young's modulus (psi)
    STEEL_DENSITY = 490.0  # lb/ft³ (steel density)
    GRAVITY = 32.174       # ft/s²

    @staticmethod
    def calculate_critical_rpm_axial(
        bha_length_ft: float,
        bha_od_in: float,
        bha_id_in: float,
        bha_weight_lbft: float,
        mud_weight_ppg: float = 10.0
    ) -> Dict[str, Any]:
        """
        Calculate critical RPM for axial vibrations (bit bounce).

        Natural frequency: fn = (1 / 2L) × sqrt(E / ρ)
        Critical RPM = fn × 60

        For BHA with buoyancy: ρ_eff = ρ_steel × (1 - MW/65.5)

        Args:
            bha_length_ft: BHA length (ft)
            bha_od_in: BHA outer diameter (inches)
            bha_id_in: BHA inner diameter (inches)
            bha_weight_lbft: BHA weight per foot (lb/ft)
            mud_weight_ppg: mud weight (ppg)

        Returns:
            Dict with critical RPM, natural frequency, harmonics
        """
        if bha_length_ft <= 0:
            return {"error": "BHA length must be > 0"}

        e = VibrationsEngine.STEEL_E
        rho_steel = VibrationsEngine.STEEL_DENSITY

        # Buoyancy factor
        bf = 1.0 - (mud_weight_ppg / 65.5)
        rho_eff = rho_steel * bf  # effective density lb/ft³

        # Convert to consistent units (psi and slugs/ft³)
        # E in psi = lbf/in², ρ in lb/ft³ → need lbm/in³
        rho_in3 = rho_eff / 1728.0  # lb/in³
        # Speed of sound in steel: c = sqrt(E/ρ) where ρ in lb/in³ and E in lb/in²
        # But need consistent: E (lb/in²), ρ (lbm/in³), g=386.4 in/s²
        g_in = 386.4  # in/s²
        c_steel = math.sqrt(e * g_in / rho_in3) if rho_in3 > 0 else 16000 * 12  # in/s

        # BHA length in inches
        l_in = bha_length_ft * 12.0

        # Natural frequency (1st mode)
        fn_1 = c_steel / (2.0 * l_in)  # Hz

        # Critical RPM
        rpm_critical_1 = fn_1 * 60.0

        # Harmonics (2nd and 3rd mode)
        fn_2 = 2 * fn_1
        fn_3 = 3 * fn_1
        rpm_critical_2 = fn_2 * 60.0
        rpm_critical_3 = fn_3 * 60.0

        # Safe operating bands
        safe_bands = []
        if rpm_critical_1 > 40:
            safe_bands.append({"min_rpm": 0, "max_rpm": round(rpm_critical_1 * 0.85)})
        if rpm_critical_2 - rpm_critical_1 > 20:
            safe_bands.append({
                "min_rpm": round(rpm_critical_1 * 1.15),
                "max_rpm": round(rpm_critical_2 * 0.85)
            })

        return {
            "critical_rpm_1st": round(rpm_critical_1, 0),
            "critical_rpm_2nd": round(rpm_critical_2, 0),
            "critical_rpm_3rd": round(rpm_critical_3, 0),
            "natural_freq_hz_1st": round(fn_1, 2),
            "natural_freq_hz_2nd": round(fn_2, 2),
            "buoyancy_factor": round(bf, 4),
            "safe_operating_bands": safe_bands,
            "mode": "Axial (Bit Bounce)",
        }

    @staticmethod
    def calculate_critical_rpm_lateral(
        bha_length_ft: float,
        bha_od_in: float,
        bha_id_in: float,
        bha_weight_lbft: float,
        hole_diameter_in: float,
        mud_weight_ppg: float = 10.0,
        inclination_deg: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate critical RPM for lateral vibrations (whirl).
        Paslay & Dawson (1984):

        RPM_crit = 4760 / (L × sqrt(BF × w / (E × I)))

        Where L in ft, w in lb/ft, E in psi, I in in⁴.

        Forward whirl occurs below critical RPM.
        Backward whirl occurs at and above critical RPM.

        Args:
            bha_length_ft: BHA length between stabilizers (ft)
            bha_od_in: BHA outer diameter (inches)
            bha_id_in: BHA inner diameter (inches)
            bha_weight_lbft: BHA weight per foot (lb/ft)
            hole_diameter_in: hole/casing inner diameter (inches)
            mud_weight_ppg: mud weight (ppg)
            inclination_deg: wellbore inclination (degrees)

        Returns:
            Dict with critical RPM, whirl type prediction, clearance
        """
        if bha_length_ft <= 0:
            return {"error": "BHA length must be > 0"}

        e = VibrationsEngine.STEEL_E
        bf = 1.0 - (mud_weight_ppg / 65.5)

        # Moment of inertia
        i_moment = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 64.0

        # Buoyed weight per foot
        w_buoyed = bha_weight_lbft * bf

        if w_buoyed <= 0 or i_moment <= 0:
            return {"error": "Invalid BHA parameters"}

        # Paslay-Dawson critical RPM
        # RPM_crit = 4760 / (L * sqrt(BF*w / (E*I)))
        denominator = bha_length_ft * math.sqrt(w_buoyed / (e * i_moment))
        rpm_critical = 4760.0 / denominator if denominator > 0 else 999

        # Radial clearance
        clearance = (hole_diameter_in - bha_od_in) / 2.0

        # Whirl severity factor (increases with clearance and inclination)
        inc_factor = 1.0 + 0.5 * math.sin(math.radians(inclination_deg))
        whirl_severity = clearance * inc_factor

        return {
            "critical_rpm": round(rpm_critical, 0),
            "mode": "Lateral (Whirl)",
            "radial_clearance_in": round(clearance, 3),
            "buoyed_weight_lbft": round(w_buoyed, 2),
            "moment_of_inertia_in4": round(i_moment, 2),
            "whirl_severity_factor": round(whirl_severity, 3),
            "prediction": "Forward Whirl risk below critical RPM" if rpm_critical > 60 else "High whirl risk",
        }

    @staticmethod
    def calculate_stick_slip_severity(
        surface_rpm: float,
        wob_klb: float,
        torque_ftlb: float,
        bit_diameter_in: float,
        bha_length_ft: float,
        bha_od_in: float,
        bha_id_in: float,
        mud_weight_ppg: float = 10.0,
        friction_factor: float = 0.25
    ) -> Dict[str, Any]:
        """
        Calculate stick-slip severity index.

        Severity = (ω_max - ω_min) / ω_avg

        Estimated from torque fluctuation model:
        - Friction torque at bit: T_friction = μ × WOB × R_bit / 3
        - Torsional spring constant: k_t = G × J / L
        - Angular displacement: Δθ = T_friction / k_t

        Severity classification:
        - < 0.5: Mild (normal drilling)
        - 0.5-1.0: Moderate (monitoring needed)
        - 1.0-1.5: Severe (adjust parameters)
        - > 1.5: Critical (bit stalling likely)

        Args:
            surface_rpm: surface rotary speed (RPM)
            wob_klb: weight on bit (klbs)
            torque_ftlb: surface torque (ft-lbs)
            bit_diameter_in: bit diameter (inches)
            bha_length_ft: BHA length (ft)
            bha_od_in: BHA OD (inches)
            bha_id_in: BHA ID (inches)
            mud_weight_ppg: mud weight (ppg)
            friction_factor: bit-formation friction coefficient

        Returns:
            Dict with severity index, classification, recommendations
        """
        if surface_rpm <= 0:
            return {"error": "RPM must be > 0"}

        # Friction torque at bit (ft-lbs)
        r_bit_ft = bit_diameter_in / (2.0 * 12.0)
        wob_lbs = wob_klb * 1000.0
        t_friction = friction_factor * wob_lbs * r_bit_ft / 3.0

        # Torsional stiffness of BHA
        # G = E / (2(1+ν)) ≈ 11.5e6 psi for steel
        g_shear = 11.5e6  # psi
        j_polar = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 32.0  # in⁴
        bha_length_in = bha_length_ft * 12.0

        k_torsion = g_shear * j_polar / bha_length_in if bha_length_in > 0 else 1e6  # in-lb/rad

        # Angular displacement (radians)
        t_friction_inlb = t_friction * 12.0  # convert to in-lb
        delta_theta = t_friction_inlb / k_torsion if k_torsion > 0 else 0

        # RPM fluctuation estimate
        # Δω ≈ 2 × δθ × ω_surface (simplified oscillation model)
        omega_surface = surface_rpm * 2.0 * math.pi / 60.0  # rad/s
        delta_omega = 2.0 * delta_theta * omega_surface

        # Severity
        severity = delta_omega / omega_surface if omega_surface > 0 else 0

        # Min/Max RPM at bit
        rpm_min_bit = max(0, surface_rpm * (1.0 - severity / 2.0))
        rpm_max_bit = surface_rpm * (1.0 + severity / 2.0)

        # Classification
        if severity < 0.5:
            classification = "Mild"
            color = "green"
            recommendation = "Normal drilling — no action needed"
        elif severity < 1.0:
            classification = "Moderate"
            color = "yellow"
            recommendation = "Monitor closely — consider increasing RPM or reducing WOB"
        elif severity < 1.5:
            classification = "Severe"
            color = "orange"
            recommendation = "Increase RPM to >120, reduce WOB, consider anti-stall tool"
        else:
            classification = "Critical"
            color = "red"
            recommendation = "Bit stalling likely — significantly reduce WOB and increase RPM"

        return {
            "severity_index": round(severity, 3),
            "classification": classification,
            "color": color,
            "rpm_min_at_bit": round(rpm_min_bit, 0),
            "rpm_max_at_bit": round(rpm_max_bit, 0),
            "surface_rpm": surface_rpm,
            "friction_torque_ftlb": round(t_friction, 0),
            "torsional_stiffness_inlb_rad": round(k_torsion, 0),
            "angular_displacement_deg": round(math.degrees(delta_theta), 2),
            "recommendation": recommendation,
        }

    @staticmethod
    def calculate_mse(
        wob_klb: float,
        torque_ftlb: float,
        rpm: float,
        rop_fph: float,
        bit_diameter_in: float
    ) -> Dict[str, Any]:
        """
        Calculate Mechanical Specific Energy (Teale, 1965).

        MSE = (480 × T × RPM) / (d² × ROP) + (4 × WOB) / (π × d²)

        Where: T in ft-lbs, RPM in rev/min, d in inches, ROP in ft/hr, WOB in lbs

        Efficiency: η = CCS / MSE (where CCS = confined compressive strength)

        Args:
            wob_klb: weight on bit (klbs)
            torque_ftlb: surface torque (ft-lbs)
            rpm: rotary speed (RPM)
            rop_fph: rate of penetration (ft/hr)
            bit_diameter_in: bit diameter (inches)

        Returns:
            Dict with MSE, components, efficiency estimate, founder point indicators
        """
        if bit_diameter_in <= 0 or rop_fph <= 0:
            return {"error": "Bit diameter and ROP must be > 0"}

        wob_lbs = wob_klb * 1000.0
        d = bit_diameter_in
        d_sq = d * d

        # MSE components
        mse_rotary = (480.0 * torque_ftlb * rpm) / (d_sq * rop_fph) if rop_fph > 0 else 0
        mse_thrust = (4.0 * wob_lbs) / (math.pi * d_sq)
        mse_total = mse_rotary + mse_thrust

        # Bit area
        bit_area = math.pi * d_sq / 4.0

        # Efficiency estimate (assume typical CCS ranges)
        # Shale: 5,000-15,000 psi, Sandstone: 10,000-30,000 psi, Limestone: 15,000-50,000 psi
        estimated_ccs = mse_total * 0.35  # typical ~35% mechanical efficiency
        efficiency_pct = min(100, (estimated_ccs / mse_total * 100)) if mse_total > 0 else 0

        # Founder point detection
        # MSE > 3× theoretical minimum suggests inefficiency (bit balling, vibrations)
        mse_theoretical_min = mse_total * 0.35  # approx CCS
        is_founder_point = mse_total > 3 * max(mse_theoretical_min, 5000)

        # Classification
        if mse_total < 20000:
            classification = "Efficient"
            color = "green"
        elif mse_total < 50000:
            classification = "Normal"
            color = "yellow"
        elif mse_total < 100000:
            classification = "Inefficient"
            color = "orange"
        else:
            classification = "Highly Inefficient"
            color = "red"

        return {
            "mse_total_psi": round(mse_total, 0),
            "mse_rotary_psi": round(mse_rotary, 0),
            "mse_thrust_psi": round(mse_thrust, 0),
            "rotary_pct": round(mse_rotary / mse_total * 100, 1) if mse_total > 0 else 0,
            "thrust_pct": round(mse_thrust / mse_total * 100, 1) if mse_total > 0 else 0,
            "bit_area_in2": round(bit_area, 2),
            "efficiency_pct": round(efficiency_pct, 1),
            "estimated_ccs_psi": round(estimated_ccs, 0),
            "is_founder_point": is_founder_point,
            "classification": classification,
            "color": color,
        }

    @staticmethod
    def calculate_stability_index(
        axial_result: Dict[str, Any],
        lateral_result: Dict[str, Any],
        stick_slip_result: Dict[str, Any],
        mse_result: Dict[str, Any],
        operating_rpm: float
    ) -> Dict[str, Any]:
        """
        Calculate combined stability index from all vibration modes.

        Index = weighted combination of all modes (0-100, higher = more stable).

        Args:
            axial_result: output from calculate_critical_rpm_axial
            lateral_result: output from calculate_critical_rpm_lateral
            stick_slip_result: output from calculate_stick_slip_severity
            mse_result: output from calculate_mse
            operating_rpm: current operating RPM

        Returns:
            Dict with stability index, per-mode scores, overall status
        """
        scores = {}

        # Axial score: distance from critical RPM (closer = worse)
        axial_crit = axial_result.get("critical_rpm_1st", 999)
        if axial_crit > 0:
            axial_ratio = abs(operating_rpm - axial_crit) / axial_crit
            scores["axial"] = min(100, axial_ratio * 100)
        else:
            scores["axial"] = 50

        # Lateral score: operating below critical = better
        lateral_crit = lateral_result.get("critical_rpm", 999)
        if lateral_crit > 0:
            if operating_rpm < lateral_crit * 0.85:
                scores["lateral"] = 90
            elif operating_rpm < lateral_crit:
                scores["lateral"] = 60
            elif operating_rpm < lateral_crit * 1.15:
                scores["lateral"] = 30  # near resonance
            else:
                scores["lateral"] = 50  # above resonance
        else:
            scores["lateral"] = 50

        # Stick-slip score
        ss_severity = stick_slip_result.get("severity_index", 0)
        scores["torsional"] = max(0, 100 - ss_severity * 66.7)

        # MSE score
        mse_val = mse_result.get("mse_total_psi", 50000)
        if mse_val < 20000:
            scores["mse"] = 95
        elif mse_val < 50000:
            scores["mse"] = 70
        elif mse_val < 100000:
            scores["mse"] = 40
        else:
            scores["mse"] = 15

        # Weighted overall
        weights = {"axial": 0.20, "lateral": 0.30, "torsional": 0.35, "mse": 0.15}
        overall = sum(scores[k] * weights[k] for k in scores)

        if overall >= 80:
            status = "Stable"
            color = "green"
        elif overall >= 60:
            status = "Marginal"
            color = "yellow"
        elif overall >= 40:
            status = "Unstable"
            color = "orange"
        else:
            status = "Critical"
            color = "red"

        return {
            "stability_index": round(overall, 1),
            "status": status,
            "color": color,
            "mode_scores": {k: round(v, 1) for k, v in scores.items()},
            "weights": weights,
            "operating_rpm": operating_rpm,
        }

    @staticmethod
    def generate_vibration_map(
        bit_diameter_in: float,
        bha_od_in: float,
        bha_id_in: float,
        bha_weight_lbft: float,
        bha_length_ft: float,
        hole_diameter_in: float,
        mud_weight_ppg: float = 10.0,
        wob_range: Optional[List[float]] = None,
        rpm_range: Optional[List[float]] = None,
        torque_base_ftlb: float = 10000,
        rop_base_fph: float = 50,
    ) -> Dict[str, Any]:
        """
        Generate RPM vs WOB vibration stability map (heatmap data).

        For each (RPM, WOB) combination, calculate stability and classify
        into zones: Stable (green), Marginal (yellow), Unstable (red).

        Args:
            Standard BHA and wellbore parameters
            wob_range: list of WOB values (klb) to test
            rpm_range: list of RPM values to test

        Returns:
            Dict with heatmap data, optimal zone, boundary curves
        """
        eng = VibrationsEngine

        if wob_range is None:
            wob_range = [5, 10, 15, 20, 25, 30, 35, 40]
        if rpm_range is None:
            rpm_range = [40, 60, 80, 100, 120, 140, 160, 180, 200]

        # Pre-calculate critical RPMs (independent of WOB/RPM operating point)
        axial = eng.calculate_critical_rpm_axial(
            bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft, mud_weight_ppg
        )
        lateral = eng.calculate_critical_rpm_lateral(
            bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft,
            hole_diameter_in, mud_weight_ppg
        )

        map_data = []
        optimal_point = {"wob": 0, "rpm": 0, "score": 0}

        for wob in wob_range:
            for rpm in rpm_range:
                # Estimate torque: T ≈ T_base × (WOB/WOB_base) × (RPM_factor)
                torque_est = torque_base_ftlb * (wob / 20.0) * (1.0 + 0.002 * (rpm - 100))
                torque_est = max(1000, torque_est)

                # Estimate ROP: simplified D-exponent influence
                rop_est = max(5, rop_base_fph * (wob / 20.0) * (rpm / 120.0))

                stick_slip = eng.calculate_stick_slip_severity(
                    surface_rpm=rpm, wob_klb=wob, torque_ftlb=torque_est,
                    bit_diameter_in=bit_diameter_in, bha_length_ft=bha_length_ft,
                    bha_od_in=bha_od_in, bha_id_in=bha_id_in, mud_weight_ppg=mud_weight_ppg,
                )
                mse = eng.calculate_mse(
                    wob_klb=wob, torque_ftlb=torque_est, rpm=rpm,
                    rop_fph=rop_est, bit_diameter_in=bit_diameter_in,
                )
                stability = eng.calculate_stability_index(
                    axial, lateral, stick_slip, mse, rpm
                )

                score = stability["stability_index"]
                point = {
                    "wob_klb": wob, "rpm": rpm,
                    "stability_index": score,
                    "status": stability["status"],
                    "stick_slip_severity": stick_slip.get("severity_index", 0),
                    "mse_psi": mse.get("mse_total_psi", 0),
                }
                map_data.append(point)

                if score > optimal_point["score"]:
                    optimal_point = {"wob": wob, "rpm": rpm, "score": score}

        return {
            "map_data": map_data,
            "wob_range": wob_range,
            "rpm_range": rpm_range,
            "optimal_point": optimal_point,
            "critical_rpm_axial": axial.get("critical_rpm_1st", 0),
            "critical_rpm_lateral": lateral.get("critical_rpm", 0),
        }

    @staticmethod
    def calculate_full_vibration_analysis(
        wob_klb: float,
        rpm: float,
        rop_fph: float,
        torque_ftlb: float,
        bit_diameter_in: float,
        dp_od_in: float = 5.0,
        dp_id_in: float = 4.276,
        dp_weight_lbft: float = 19.5,
        bha_length_ft: float = 300,
        bha_od_in: float = 6.75,
        bha_id_in: float = 2.813,
        bha_weight_lbft: float = 83.0,
        mud_weight_ppg: float = 10.0,
        hole_diameter_in: float = 8.5,
        inclination_deg: float = 0.0,
        friction_factor: float = 0.25
    ) -> Dict[str, Any]:
        """
        Complete vibration analysis combining all modes.

        Returns:
            Dict with all vibration analyses, stability index, vibration map, alerts
        """
        eng = VibrationsEngine

        # 1. Axial vibrations
        axial = eng.calculate_critical_rpm_axial(
            bha_length_ft=bha_length_ft,
            bha_od_in=bha_od_in,
            bha_id_in=bha_id_in,
            bha_weight_lbft=bha_weight_lbft,
            mud_weight_ppg=mud_weight_ppg,
        )

        # 2. Lateral vibrations
        lateral = eng.calculate_critical_rpm_lateral(
            bha_length_ft=bha_length_ft,
            bha_od_in=bha_od_in,
            bha_id_in=bha_id_in,
            bha_weight_lbft=bha_weight_lbft,
            hole_diameter_in=hole_diameter_in,
            mud_weight_ppg=mud_weight_ppg,
            inclination_deg=inclination_deg,
        )

        # 3. Stick-slip
        stick_slip = eng.calculate_stick_slip_severity(
            surface_rpm=rpm,
            wob_klb=wob_klb,
            torque_ftlb=torque_ftlb,
            bit_diameter_in=bit_diameter_in,
            bha_length_ft=bha_length_ft,
            bha_od_in=bha_od_in,
            bha_id_in=bha_id_in,
            mud_weight_ppg=mud_weight_ppg,
            friction_factor=friction_factor,
        )

        # 4. MSE
        mse = eng.calculate_mse(
            wob_klb=wob_klb,
            torque_ftlb=torque_ftlb,
            rpm=rpm,
            rop_fph=rop_fph,
            bit_diameter_in=bit_diameter_in,
        )

        # 5. Combined stability
        stability = eng.calculate_stability_index(
            axial_result=axial,
            lateral_result=lateral,
            stick_slip_result=stick_slip,
            mse_result=mse,
            operating_rpm=rpm,
        )

        # 6. Vibration map
        vib_map = eng.generate_vibration_map(
            bit_diameter_in=bit_diameter_in,
            bha_od_in=bha_od_in,
            bha_id_in=bha_id_in,
            bha_weight_lbft=bha_weight_lbft,
            bha_length_ft=bha_length_ft,
            hole_diameter_in=hole_diameter_in,
            mud_weight_ppg=mud_weight_ppg,
            torque_base_ftlb=torque_ftlb,
            rop_base_fph=rop_fph,
        )

        # Alerts
        alerts = []
        axial_crit = axial.get("critical_rpm_1st", 999)
        if abs(rpm - axial_crit) < axial_crit * 0.1:
            alerts.append(f"Operating near axial resonance ({axial_crit:.0f} RPM) — risk of bit bounce")
        lateral_crit = lateral.get("critical_rpm", 999)
        if abs(rpm - lateral_crit) < lateral_crit * 0.15:
            alerts.append(f"Operating near lateral critical RPM ({lateral_crit:.0f}) — whirl risk")
        ss_sev = stick_slip.get("severity_index", 0)
        if ss_sev > 1.0:
            alerts.append(f"Stick-slip severity {ss_sev:.2f} — {stick_slip.get('recommendation', '')}")
        if mse.get("is_founder_point", False):
            alerts.append("Founder point detected — MSE excessive, check bit condition")
        if stability["stability_index"] < 40:
            alerts.append(f"Critical stability index {stability['stability_index']:.0f} — modify drilling parameters")

        # Summary
        summary = {
            "stability_index": stability["stability_index"],
            "stability_status": stability["status"],
            "critical_rpm_axial": axial.get("critical_rpm_1st", 0),
            "critical_rpm_lateral": lateral.get("critical_rpm", 0),
            "stick_slip_severity": stick_slip.get("severity_index", 0),
            "stick_slip_class": stick_slip.get("classification", "N/A"),
            "mse_psi": mse.get("mse_total_psi", 0),
            "mse_efficiency_pct": mse.get("efficiency_pct", 0),
            "optimal_wob": vib_map["optimal_point"]["wob"],
            "optimal_rpm": vib_map["optimal_point"]["rpm"],
            "alerts": alerts,
        }

        return {
            "summary": summary,
            "axial_vibrations": axial,
            "lateral_vibrations": lateral,
            "stick_slip": stick_slip,
            "mse": mse,
            "stability": stability,
            "vibration_map": vib_map,
            "alerts": alerts,
        }

    # =====================================================================
    # Phase 8 Elite — Multi-Component BHA, 3D Survey, Bit-Rock, Stabilizers, Fatigue
    # =====================================================================

    @staticmethod
    def calculate_critical_rpm_lateral_multi(
        bha_components: List[Dict[str, Any]],
        mud_weight_ppg: float = 10.0,
        hole_diameter_in: float = 8.5,
        boundary_conditions: str = "pinned-pinned"
    ) -> Dict[str, Any]:
        """
        Multi-component BHA lateral critical RPM via Transfer Matrix Method (TMM).

        Each BHA component is modelled as a Euler-Bernoulli beam segment with
        its own EI, linear mass, and length. A 4×4 field transfer matrix is
        built per segment, and the product T = T_n · ... · T_1 is evaluated.
        Critical frequencies are found by scanning for sign changes of the
        appropriate determinant boundary condition.

        Args:
            bha_components: list of dicts, each with:
                - type (str): 'collar', 'stabilizer', 'motor', 'mwd', 'lwd', 'hwdp', 'jar', 'crossover'
                - od (float): outer diameter (in)
                - id_inner (float): inner diameter (in)
                - length_ft (float): segment length (ft)
                - weight_ppf (float): weight per foot (lb/ft)
            mud_weight_ppg: mud weight (ppg)
            hole_diameter_in: hole / casing ID (in)
            boundary_conditions: 'pinned-pinned' | 'fixed-pinned' | 'fixed-free'

        Returns:
            Dict with mode frequencies, critical RPMs (1st-3rd), component details.
        """
        if not bha_components:
            return {"error": "No BHA components provided"}

        e = VibrationsEngine.STEEL_E
        rho_steel = VibrationsEngine.STEEL_DENSITY
        bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)

        # Pre-compute per-component properties
        segments = []
        total_length_ft = 0.0
        for comp in bha_components:
            od = comp.get("od", 6.75)
            id_in = comp.get("id_inner", 2.813)
            l_ft = comp.get("length_ft", 30.0)
            w_ppf = comp.get("weight_ppf", 80.0)

            i_moment = math.pi * (od ** 4 - id_in ** 4) / 64.0  # in^4
            a_steel = math.pi * (od ** 2 - id_in ** 2) / 4.0    # in^2
            w_buoyed = w_ppf * bf  # lb/ft buoyed
            mass_per_in = (w_ppf / 386.4) / 12.0  # slug / in (mass per inch length)

            segments.append({
                "type": comp.get("type", "collar"),
                "od": od,
                "id_inner": id_in,
                "length_in": l_ft * 12.0,
                "length_ft": l_ft,
                "EI": e * i_moment,          # lb·in²
                "mass_per_in": mass_per_in,   # slug/in
                "w_buoyed_ppf": w_buoyed,
                "i_moment_in4": i_moment,
                "a_steel_in2": a_steel,
            })
            total_length_ft += l_ft

        if total_length_ft <= 0:
            return {"error": "Total BHA length must be > 0"}

        # --- TMM frequency sweep ---
        # For pinned-pinned: boundary is y=0, M=0 at both ends.
        # State vector [y, theta, M, V]. After transfer: T * [0, theta_0, 0, V_0]
        # Requirement: y_end = 0 and M_end = 0.
        # From state vector output: y_end = T[0][1]*theta_0 + T[0][3]*V_0 = 0
        #                            M_end = T[2][1]*theta_0 + T[2][3]*V_0 = 0
        # Non-trivial solution: det([[T01,T03],[T21,T23]]) = 0

        def _transfer_matrix_product(omega: float) -> List[List[float]]:
            """Build product of transfer matrices for all segments at angular freq omega."""
            # 4×4 identity
            T = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

            for seg in segments:
                L = seg["length_in"]
                ei = seg["EI"]
                m_per_in = seg["mass_per_in"]

                if L <= 0 or ei <= 0:
                    continue

                # lambda^4 = m*omega^2/EI
                lam4 = m_per_in * omega ** 2 / ei if ei > 0 else 0
                if lam4 <= 0:
                    # Zero frequency: rigid body transfer
                    F = [[1, L, 0, 0], [0, 1, 0, 0], [0, 0, 1, L], [0, 0, 0, 1]]
                else:
                    lam = lam4 ** 0.25
                    lL = lam * L

                    # Prevent overflow for very large lL
                    if lL > 20:
                        lL = 20.0

                    c = math.cos(lL)
                    s = math.sin(lL)
                    ch = math.cosh(lL)
                    sh = math.sinh(lL)

                    # Field transfer matrix (Euler-Bernoulli beam vibration)
                    # [y, theta, M, V] transfer
                    a11 = 0.5 * (c + ch)
                    a12 = 0.5 * (s / lam + sh / lam) if lam > 0 else L
                    a13 = 0.5 * (-c + ch) / (lam ** 2) if lam > 0 else 0
                    a14 = 0.5 * (-s + sh) / (lam ** 3) if lam > 0 else 0

                    a21 = 0.5 * (-lam * s + lam * sh)
                    a22 = 0.5 * (c + ch)
                    a23 = 0.5 * (s + sh) / lam if lam > 0 else 0
                    a24 = 0.5 * (-c + ch) / (lam ** 2) if lam > 0 else 0

                    a31 = 0.5 * (-lam ** 2 * c - lam ** 2 * ch) if lam > 0 else 0
                    a32 = 0.5 * (-lam * s + lam * sh)
                    a33 = 0.5 * (c + ch)
                    a34 = 0.5 * (s / lam + sh / lam) if lam > 0 else L

                    a41_base = 0.5 * (lam ** 3 * s - lam ** 3 * sh) if lam > 0 else 0
                    a42 = 0.5 * (-lam ** 2 * c - lam ** 2 * ch) if lam > 0 else 0
                    a43 = 0.5 * (-lam * s + lam * sh)
                    a44 = 0.5 * (c + ch)

                    # Adjust signs for EI*M convention
                    F = [
                        [a11,          a12,          a13 / ei if ei > 0 else 0,  a14 / ei if ei > 0 else 0],
                        [a21,          a22,          a23 / ei if ei > 0 else 0,  a24 / ei if ei > 0 else 0],
                        [a31 * ei,     a32 * ei,     a33,                         a34],
                        [a41_base * ei, a42 * ei,    a43,                         a44],
                    ]

                # Matrix multiply T = F * T
                T_new = [[0.0] * 4 for _ in range(4)]
                for i in range(4):
                    for j in range(4):
                        for k in range(4):
                            T_new[i][j] += F[i][k] * T[k][j]
                T = T_new

            return T

        def _boundary_det(omega: float) -> float:
            """Determinant of boundary condition sub-matrix."""
            T = _transfer_matrix_product(omega)
            if boundary_conditions == "pinned-pinned":
                # y=0,M=0 at start; y=0,M=0 at end
                # Free variables: theta_0, V_0 (indices 1,3)
                return T[0][1] * T[2][3] - T[0][3] * T[2][1]
            elif boundary_conditions == "fixed-pinned":
                # y=0,theta=0 at start; y=0,M=0 at end
                return T[0][2] * T[2][3] - T[0][3] * T[2][2]
            else:  # fixed-free
                # y=0,theta=0 at start; M=0,V=0 at end
                return T[2][2] * T[3][3] - T[2][3] * T[3][2]

        # Frequency scan: 0.1 to 200 rad/s in 500 steps
        omega_max = 200.0
        n_scan = 500
        d_omega = omega_max / n_scan
        modes = []
        prev_val = _boundary_det(0.1)
        for i in range(1, n_scan + 1):
            omega = 0.1 + i * d_omega
            val = _boundary_det(omega)
            if prev_val * val < 0 and len(modes) < 5:
                # Sign change — bisect to refine
                lo, hi = omega - d_omega, omega
                for _ in range(30):
                    mid = (lo + hi) / 2.0
                    mv = _boundary_det(mid)
                    if mv * _boundary_det(lo) < 0:
                        hi = mid
                    else:
                        lo = mid
                omega_root = (lo + hi) / 2.0
                freq_hz = omega_root / (2.0 * math.pi)
                rpm_crit = freq_hz * 60.0
                if rpm_crit > 5:  # Filter out numerical noise
                    modes.append({
                        "mode_number": len(modes) + 1,
                        "natural_freq_hz": round(freq_hz, 3),
                        "critical_rpm": round(rpm_crit, 1),
                        "omega_rad_s": round(omega_root, 4),
                    })
            prev_val = val

        # Fallback: if TMM found no modes, use weighted Paslay-Dawson
        if not modes:
            total_ei = sum(s["EI"] for s in segments)
            total_w = sum(s["w_buoyed_ppf"] for s in segments)
            avg_ei = total_ei / len(segments)
            avg_w = total_w / len(segments) if total_w > 0 else 1.0
            rpm_pd = 4760.0 / (total_length_ft * math.sqrt(avg_w / avg_ei)) if avg_ei > 0 else 120.0
            modes = [
                {"mode_number": 1, "natural_freq_hz": round(rpm_pd / 60.0, 3),
                 "critical_rpm": round(rpm_pd, 1), "omega_rad_s": round(rpm_pd / 60.0 * 2 * math.pi, 4)},
                {"mode_number": 2, "natural_freq_hz": round(rpm_pd * 2 / 60.0, 3),
                 "critical_rpm": round(rpm_pd * 2, 1), "omega_rad_s": round(rpm_pd * 2 / 60.0 * 2 * math.pi, 4)},
            ]

        # Component summary table
        comp_table = []
        for seg in segments:
            comp_table.append({
                "type": seg["type"],
                "od_in": seg["od"],
                "id_in": seg["id_inner"],
                "length_ft": seg["length_ft"],
                "EI_lb_in2": round(seg["EI"], 0),
                "buoyed_weight_ppf": round(seg["w_buoyed_ppf"], 2),
            })

        return {
            "modes": modes,
            "mode_1_critical_rpm": modes[0]["critical_rpm"] if modes else 0,
            "mode_2_critical_rpm": modes[1]["critical_rpm"] if len(modes) > 1 else 0,
            "mode_3_critical_rpm": modes[2]["critical_rpm"] if len(modes) > 2 else 0,
            "num_modes_found": len(modes),
            "total_bha_length_ft": round(total_length_ft, 1),
            "boundary_conditions": boundary_conditions,
            "components": comp_table,
            "method": "Transfer Matrix Method (TMM)",
        }

    @staticmethod
    def calculate_vibration_map_3d(
        survey_stations: List[Dict[str, float]],
        bha_od_in: float = 6.75,
        bha_id_in: float = 2.813,
        bha_weight_lbft: float = 83.0,
        bha_length_ft: float = 300.0,
        hole_diameter_in: float = 8.5,
        mud_weight_ppg: float = 10.0,
        rpm_range: Optional[List[float]] = None,
        wob_klb: float = 20.0
    ) -> Dict[str, Any]:
        """
        Generate a 3D vibration risk map: critical RPM as function of measured depth.

        Uses the Paslay-Dawson formula with depth-varying inclination from the
        actual survey to produce a critical-RPM vs MD profile, plus a risk matrix
        (MD × RPM) classifying each cell as green/yellow/red.

        Args:
            survey_stations: list of {md_ft, inclination_deg, azimuth_deg}
            bha_od_in, bha_id_in, bha_weight_lbft, bha_length_ft: BHA geometry
            hole_diameter_in: hole / casing ID
            mud_weight_ppg: mud weight (ppg)
            rpm_range: list of RPMs to evaluate (default 40-220 step 20)
            wob_klb: weight on bit (klbs)

        Returns:
            Dict with critical_rpm_by_depth, risk_map, safe_rpm_windows.
        """
        eng = VibrationsEngine

        if not survey_stations:
            return {"error": "No survey stations provided"}

        if rpm_range is None:
            rpm_range = list(range(40, 240, 20))

        bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)
        i_moment = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 64.0
        w_buoyed = bha_weight_lbft * bf
        e = VibrationsEngine.STEEL_E

        critical_by_depth = []
        risk_map = []

        for station in survey_stations:
            md = station.get("md_ft", 0)
            inc = station.get("inclination_deg", 0)

            # Paslay-Dawson with inclination correction
            # Weight component perpendicular to bore: w_lat = w * sin(inc)
            inc_rad = math.radians(inc)
            w_lateral = w_buoyed * max(math.sin(inc_rad), 0.05)  # min 0.05 to avoid singularity

            # DLS amplification — look at curvature between consecutive stations
            dls = station.get("dls_deg_100ft", 0)
            dls_factor = 1.0 + 0.1 * min(dls, 10.0)  # Higher DLS → lower effective critical RPM

            # Lateral critical RPM (Paslay-Dawson, gravity-loaded beam)
            denom = bha_length_ft * math.sqrt(w_lateral / (e * i_moment))
            rpm_crit_lateral = (4760.0 / denom / dls_factor) if denom > 0 else 999

            # Axial critical (same formula as base, independent of inc)
            rpm_crit_axial = eng.calculate_critical_rpm_axial(
                bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft, mud_weight_ppg
            ).get("critical_rpm_1st", 999)

            critical_by_depth.append({
                "md_ft": md,
                "inclination_deg": inc,
                "critical_rpm_lateral": round(rpm_crit_lateral, 0),
                "critical_rpm_axial": round(rpm_crit_axial, 0),
                "dls_factor": round(dls_factor, 3),
            })

            # Risk row for this depth across all RPMs
            for rpm_val in rpm_range:
                # Distance from lateral critical
                ratio_lat = abs(rpm_val - rpm_crit_lateral) / rpm_crit_lateral if rpm_crit_lateral > 0 else 1
                ratio_ax = abs(rpm_val - rpm_crit_axial) / rpm_crit_axial if rpm_crit_axial > 0 else 1

                # Stick-slip tendency increases with inc and wob
                ss_tendency = (wob_klb / 30.0) * (1.0 + 0.5 * math.sin(inc_rad))
                ss_reduction = max(0, 1.0 - rpm_val / 150.0)
                ss_risk = ss_tendency * ss_reduction

                # Combined risk score 0-1 (0 = safe, 1 = dangerous)
                risk_lateral = max(0, 1.0 - ratio_lat / 0.2) if ratio_lat < 0.2 else 0
                risk_axial = max(0, 1.0 - ratio_ax / 0.15) if ratio_ax < 0.15 else 0
                risk_ss = min(1.0, ss_risk)
                combined_risk = min(1.0, 0.4 * risk_lateral + 0.25 * risk_axial + 0.35 * risk_ss)

                if combined_risk < 0.3:
                    zone = "green"
                elif combined_risk < 0.6:
                    zone = "yellow"
                else:
                    zone = "red"

                risk_map.append({
                    "md_ft": md,
                    "rpm": rpm_val,
                    "risk_score": round(combined_risk, 3),
                    "zone": zone,
                })

        # Determine safe RPM windows per depth
        safe_windows = []
        for cd in critical_by_depth:
            md = cd["md_ft"]
            cr_lat = cd["critical_rpm_lateral"]
            cr_ax = cd["critical_rpm_axial"]
            # Safe: far from both criticals
            bands = []
            lower = min(cr_lat, cr_ax)
            if lower > 40:
                bands.append({"min_rpm": 40, "max_rpm": round(lower * 0.85)})
            upper_low = max(cr_lat, cr_ax)
            if upper_low * 1.15 < 220:
                bands.append({"min_rpm": round(upper_low * 1.15), "max_rpm": 220})
            safe_windows.append({"md_ft": md, "safe_bands": bands})

        return {
            "critical_rpm_by_depth": critical_by_depth,
            "risk_map": risk_map,
            "safe_rpm_windows": safe_windows,
            "rpm_range": rpm_range,
            "num_stations": len(survey_stations),
            "method": "Paslay-Dawson with 3D survey coupling",
        }

    @staticmethod
    def calculate_bit_excitation(
        bit_type: str,
        num_blades_or_cones: int,
        rpm: float,
        wob_klb: float,
        rock_ucs_psi: float = 15000.0,
        bit_diameter_in: float = 8.5,
        rop_fph: float = 50.0
    ) -> Dict[str, Any]:
        """
        Calculate bit-rock excitation frequencies and cutting forces.

        PDC bit: excitation at N_blades × RPM/60 (blade-passing frequency)
        Roller-cone: excitation at N_teeth × RPM/60 × 3 cones (tooth-striking)

        Resonance risk is assessed by proximity to BHA natural frequencies.

        Args:
            bit_type: 'pdc' or 'roller_cone'
            num_blades_or_cones: number of blades (PDC) or teeth per cone (roller)
            rpm: rotary speed (RPM)
            wob_klb: weight on bit (klb)
            rock_ucs_psi: rock unconfined compressive strength (psi)
            bit_diameter_in: bit diameter (inches)
            rop_fph: rate of penetration (ft/hr)

        Returns:
            Dict with excitation frequency, depth of cut, cutting force, harmonics.
        """
        if rpm <= 0 or bit_diameter_in <= 0:
            return {"error": "RPM and bit diameter must be > 0"}

        wob_lbs = wob_klb * 1000.0
        bit_area = math.pi * bit_diameter_in ** 2 / 4.0  # in²

        # Depth of cut per revolution
        rop_ipm = rop_fph * 12.0 / 60.0  # in/min
        doc_in = rop_ipm / rpm if rpm > 0 else 0  # in/rev

        # Cutting force estimate: F_c ≈ UCS × A_contact
        # A_contact ≈ DOC × bit_diameter (simplified ribbon area)
        a_contact = doc_in * bit_diameter_in  # in²
        cutting_force = rock_ucs_psi * a_contact  # lbs

        # Excitation frequency
        bit_type_lower = bit_type.lower().replace("-", "_").replace(" ", "_")
        if bit_type_lower in ("pdc", "fixed_cutter"):
            n_blades = max(1, num_blades_or_cones)
            excitation_freq_hz = n_blades * rpm / 60.0
            excitation_desc = f"PDC blade-passing: {n_blades} blades × {rpm} RPM"
        elif bit_type_lower in ("roller_cone", "tricone", "rc"):
            n_teeth = max(1, num_blades_or_cones)
            excitation_freq_hz = n_teeth * rpm / 60.0 * 3  # 3 cones
            excitation_desc = f"Roller-cone tooth-striking: {n_teeth} teeth × 3 cones × {rpm} RPM"
        else:
            excitation_freq_hz = num_blades_or_cones * rpm / 60.0
            excitation_desc = f"Generic: {num_blades_or_cones} elements × {rpm} RPM"

        # Harmonics
        harmonics = [
            {"harmonic": h, "freq_hz": round(excitation_freq_hz * h, 2)}
            for h in [1, 2, 3]
        ]

        return {
            "excitation_freq_hz": round(excitation_freq_hz, 2),
            "excitation_description": excitation_desc,
            "depth_of_cut_in": round(doc_in, 5),
            "cutting_force_lbs": round(cutting_force, 0),
            "contact_area_in2": round(a_contact, 4),
            "bit_type": bit_type_lower,
            "harmonics": harmonics,
            "rpm": rpm,
            "wob_klb": wob_klb,
            "rock_ucs_psi": rock_ucs_psi,
        }

    @staticmethod
    def check_resonance(
        excitation_freq_hz: float,
        natural_freqs_hz: List[float],
        tolerance_pct: float = 15.0
    ) -> Dict[str, Any]:
        """
        Check if bit excitation frequency is near any BHA natural frequency.

        Resonance occurs when f_excitation ≈ f_natural (within tolerance).
        Returns risk level and recommended RPM adjustments.

        Args:
            excitation_freq_hz: bit excitation frequency (Hz)
            natural_freqs_hz: list of BHA natural frequencies (Hz)
            tolerance_pct: proximity threshold for resonance warning (%)

        Returns:
            Dict with resonance_risk, nearest_mode, detuning recommendations.
        """
        if excitation_freq_hz <= 0 or not natural_freqs_hz:
            return {
                "resonance_risk": "low",
                "nearest_mode": None,
                "frequency_ratio": 0,
                "detuning_rpm_recommended": None,
                "color": "green",
            }

        nearest_mode = None
        min_ratio_diff = float("inf")
        nearest_freq = 0

        for idx, fn in enumerate(natural_freqs_hz):
            if fn <= 0:
                continue
            ratio = excitation_freq_hz / fn
            diff = abs(ratio - 1.0)
            if diff < min_ratio_diff:
                min_ratio_diff = diff
                nearest_mode = idx + 1
                nearest_freq = fn

        tol_frac = tolerance_pct / 100.0

        if min_ratio_diff < tol_frac * 0.5:
            risk = "critical"
            color = "red"
        elif min_ratio_diff < tol_frac:
            risk = "high"
            color = "orange"
        elif min_ratio_diff < tol_frac * 2:
            risk = "moderate"
            color = "yellow"
        else:
            risk = "low"
            color = "green"

        # Suggest detuning: shift RPM so excitation moves away from natural freq
        # f_excite = N * RPM/60 → RPM = f_excite * 60 / N
        # To move to 0.80 × fn: RPM_low = 0.80 * fn * 60 / N_blades (approx)
        # We suggest ±20% away from resonant RPM
        detuning_rpm = None
        if risk in ("critical", "high", "moderate") and nearest_freq > 0:
            resonant_rpm = nearest_freq * 60.0  # approximate (1:1 ratio)
            detuning_rpm = {
                "decrease_to": round(resonant_rpm * 0.80),
                "increase_to": round(resonant_rpm * 1.20),
            }

        return {
            "resonance_risk": risk,
            "nearest_mode": nearest_mode,
            "nearest_natural_freq_hz": round(nearest_freq, 2) if nearest_freq > 0 else None,
            "excitation_freq_hz": round(excitation_freq_hz, 2),
            "frequency_ratio": round(excitation_freq_hz / nearest_freq, 3) if nearest_freq > 0 else 0,
            "min_frequency_gap_pct": round(min_ratio_diff * 100, 1),
            "detuning_rpm_recommended": detuning_rpm,
            "color": color,
        }

    @staticmethod
    def optimize_stabilizer_placement(
        bha_components: List[Dict[str, Any]],
        hole_diameter_in: float = 8.5,
        target_rpm_range: Optional[Tuple[float, float]] = None,
        mud_weight_ppg: float = 10.0,
        num_candidates: int = 5
    ) -> Dict[str, Any]:
        """
        Determine optimal stabilizer position to maximise separation between
        operating RPM range and BHA natural frequencies.

        Strategy: insert a virtual "stabilizer" (pinned constraint) at various
        candidate positions along the BHA and evaluate which position shifts
        the critical RPM farthest from the target operating window.

        Args:
            bha_components: list of BHA component dicts (same format as TMM)
            hole_diameter_in: hole / casing ID (in)
            target_rpm_range: (min_rpm, max_rpm) operating window
            mud_weight_ppg: mud weight (ppg)
            num_candidates: number of candidate positions to evaluate

        Returns:
            Dict with optimal_position, frequency_separation, evaluated candidates.
        """
        eng = VibrationsEngine

        if not bha_components:
            return {"error": "No BHA components provided"}

        if target_rpm_range is None:
            target_rpm_range = (80, 160)

        rpm_low, rpm_high = target_rpm_range
        rpm_mid = (rpm_low + rpm_high) / 2.0

        # Total BHA length
        total_length_ft = sum(c.get("length_ft", 30.0) for c in bha_components)

        # Baseline critical RPM (no extra stabilizer)
        baseline = eng.calculate_critical_rpm_lateral_multi(
            bha_components, mud_weight_ppg, hole_diameter_in
        )
        baseline_rpm = baseline.get("mode_1_critical_rpm", 120)

        # Generate candidate positions (evenly spaced along BHA)
        candidates = []
        for i in range(1, num_candidates + 1):
            pos_frac = i / (num_candidates + 1)
            pos_ft = total_length_ft * pos_frac

            # Split BHA at this position into two spans → higher critical RPM
            # Approximate: shorter span → higher critical RPM
            span_1 = pos_ft
            span_2 = total_length_ft - pos_ft

            # Critical RPM scales as 1/L² approximately
            if span_1 > 0 and span_2 > 0:
                # The governing mode is the longer span
                governing_span = max(span_1, span_2)
                # Approximate new critical RPM
                rpm_new = baseline_rpm * (total_length_ft / governing_span) ** 2
                rpm_new = min(rpm_new, 500)  # cap at reasonable value
            else:
                rpm_new = baseline_rpm

            # Separation from operating window
            if rpm_new < rpm_low:
                separation = rpm_low - rpm_new
            elif rpm_new > rpm_high:
                separation = rpm_new - rpm_high
            else:
                separation = 0  # Inside operating window = bad

            # Clearance / standoff
            avg_od = sum(c.get("od", 6.75) for c in bha_components) / len(bha_components)
            standoff = (hole_diameter_in - avg_od) / 2.0

            candidates.append({
                "position_ft": round(pos_ft, 1),
                "position_pct": round(pos_frac * 100, 1),
                "estimated_critical_rpm": round(rpm_new, 0),
                "separation_from_window_rpm": round(separation, 0),
                "span_1_ft": round(span_1, 1),
                "span_2_ft": round(span_2, 1),
            })

        # Select best: maximum separation
        best = max(candidates, key=lambda c: c["separation_from_window_rpm"])

        # Standoff calculation
        avg_od = sum(c.get("od", 6.75) for c in bha_components) / len(bha_components)
        standoff_pct = ((hole_diameter_in - avg_od) / (hole_diameter_in - avg_od)) * 100 if hole_diameter_in > avg_od else 0
        # Actual standoff pct with stabilizer (blade OD ~ hole_id - 0.125")
        stab_od = hole_diameter_in - 0.125
        standoff_with_stab = ((stab_od - avg_od) / (hole_diameter_in - avg_od)) * 100 if hole_diameter_in > avg_od else 0

        return {
            "optimal_position_ft": best["position_ft"],
            "optimal_position_pct": best["position_pct"],
            "estimated_critical_rpm_after": best["estimated_critical_rpm"],
            "baseline_critical_rpm": round(baseline_rpm, 0),
            "frequency_separation_rpm": best["separation_from_window_rpm"],
            "target_rpm_range": list(target_rpm_range),
            "standoff_pct": round(min(standoff_with_stab, 100), 1),
            "candidates": candidates,
            "total_bha_length_ft": round(total_length_ft, 1),
        }

    @staticmethod
    def calculate_fatigue_damage(
        drillstring_od: float,
        drillstring_id: float,
        drillstring_grade: str = "S-135",
        survey_stations: Optional[List[Dict[str, float]]] = None,
        rpm: float = 120.0,
        hours_per_stand: float = 0.5,
        vibration_severity: float = 0.3,
        total_rotating_hours: float = 100.0
    ) -> Dict[str, Any]:
        """
        Calculate cumulative fatigue damage on drillstring using Miner's rule.

        Cyclic bending stress: σ_bend = EI × curvature × OD/2
        Cycles per hour: N_cycles = RPM × 60
        S-N curve: N_f = (S_e / σ_a)^b  where S_e = endurance limit
        Miner: D = Σ(n_i / N_f_i)  → failure when D ≥ 1.0

        Args:
            drillstring_od: pipe OD (inches)
            drillstring_id: pipe ID (inches)
            drillstring_grade: 'E-75', 'X-95', 'G-105', 'S-135', 'V-150'
            survey_stations: list of {md_ft, inclination_deg, dls_deg_100ft}
            rpm: average RPM
            hours_per_stand: time per stand at each station (hours)
            vibration_severity: severity multiplier (0-1, from stick_slip or lateral)
            total_rotating_hours: total hours rotating (for uniform estimate)

        Returns:
            Dict with cumulative damage, remaining life, critical joints, S-N params.
        """
        e = VibrationsEngine.STEEL_E

        # Endurance limits by grade (approximation from API 5DP)
        endurance_limits = {
            "E-75": 20000, "X-95": 22000, "G-105": 23000,
            "S-135": 25000, "V-150": 26000,
        }
        s_e = endurance_limits.get(drillstring_grade, 25000)  # psi (endurance limit)
        b_exponent = 5.0  # S-N slope exponent (typical for drillpipe)

        # Moment of inertia
        i_moment = math.pi * (drillstring_od ** 4 - drillstring_id ** 4) / 64.0

        cycles_per_hour = rpm * 60.0

        # If survey provided, compute per-station damage
        damage_by_station = []
        cumulative_damage = 0.0

        if survey_stations and len(survey_stations) > 0:
            for station in survey_stations:
                dls = station.get("dls_deg_100ft", 0)
                md = station.get("md_ft", 0)

                # Bending stress from DLS: σ_b = E × OD × π × DLS / (2 × 100 × 180 × 12)
                # DLS in deg/100ft → curvature rad/in
                curvature_rad_in = dls * math.pi / (180.0 * 100.0 * 12.0)
                sigma_bend = e * (drillstring_od / 2.0) * curvature_rad_in

                # Add vibration-induced stress
                sigma_vib = sigma_bend * (1.0 + vibration_severity)

                # Cycles at this station
                n_cycles = cycles_per_hour * hours_per_stand

                # Cycles to failure from S-N curve
                if sigma_vib > 0 and sigma_vib < s_e * 5:
                    n_f = (s_e / sigma_vib) ** b_exponent if sigma_vib > 0 else float("inf")
                    n_f = max(n_f, 1.0)
                else:
                    n_f = float("inf") if sigma_vib <= 0 else 1.0

                # Damage increment
                d_i = n_cycles / n_f if n_f > 0 and n_f != float("inf") else 0

                cumulative_damage += d_i

                damage_by_station.append({
                    "md_ft": md,
                    "dls_deg_100ft": dls,
                    "bending_stress_psi": round(sigma_bend, 0),
                    "total_cyclic_stress_psi": round(sigma_vib, 0),
                    "cycles_applied": round(n_cycles, 0),
                    "cycles_to_failure": round(n_f, 0) if n_f != float("inf") else "infinite",
                    "damage_increment": round(d_i, 6),
                    "cumulative_damage": round(cumulative_damage, 6),
                })
        else:
            # Uniform estimate: assume average DLS of 3 deg/100ft
            avg_dls = 3.0
            curvature_rad_in = avg_dls * math.pi / (180.0 * 100.0 * 12.0)
            sigma_bend = e * (drillstring_od / 2.0) * curvature_rad_in
            sigma_vib = sigma_bend * (1.0 + vibration_severity)
            total_cycles = cycles_per_hour * total_rotating_hours
            n_f = (s_e / sigma_vib) ** b_exponent if sigma_vib > 0 else float("inf")
            n_f = max(n_f, 1.0) if n_f != float("inf") else float("inf")
            cumulative_damage = total_cycles / n_f if n_f != float("inf") and n_f > 0 else 0

        # Remaining life estimate
        if cumulative_damage > 0:
            remaining_life_pct = max(0, (1.0 - cumulative_damage) * 100)
            if cumulative_damage < 1.0:
                # Hours remaining ~ total_hours × (1-D)/D
                hours_used = total_rotating_hours if not survey_stations else len(survey_stations) * hours_per_stand
                estimated_remaining_hours = hours_used * (1.0 - cumulative_damage) / cumulative_damage if cumulative_damage > 0 else float("inf")
            else:
                estimated_remaining_hours = 0
        else:
            remaining_life_pct = 100.0
            estimated_remaining_hours = float("inf")

        # Critical joints (highest damage)
        critical_joints = []
        if damage_by_station:
            sorted_stations = sorted(damage_by_station, key=lambda x: x["damage_increment"], reverse=True)
            critical_joints = sorted_stations[:3]

        return {
            "cumulative_damage": round(cumulative_damage, 6),
            "remaining_life_pct": round(remaining_life_pct, 1),
            "estimated_remaining_hours": round(estimated_remaining_hours, 1) if estimated_remaining_hours != float("inf") else "infinite",
            "status": "FAILED" if cumulative_damage >= 1.0 else ("WARNING" if cumulative_damage > 0.5 else "OK"),
            "endurance_limit_psi": s_e,
            "sn_exponent": b_exponent,
            "drillstring_grade": drillstring_grade,
            "damage_by_station": damage_by_station,
            "critical_joints": critical_joints,
            "rpm": rpm,
            "vibration_severity": vibration_severity,
        }
