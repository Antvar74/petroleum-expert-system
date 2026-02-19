"""
Vibrations & Stability Calculation Engine

Drillstring vibration analysis including axial (bit bounce), lateral (whirl),
torsional (stick-slip), and Mechanical Specific Energy optimization.

References:
- Paslay & Dawson (1984): Drillstring lateral vibrations and whirl
- Jansen & van den Steen (1995): Active damping of stick-slip vibrations
- Teale (1965): Mechanical Specific Energy concept
- Dupriest (2005): MSE-based drilling optimization
- Dunayevsky (1993): Stability of BHA in directional wells
"""
import math
from typing import Dict, Any, List, Optional


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
