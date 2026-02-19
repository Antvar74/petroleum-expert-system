"""
Completion Design Calculation Engine

Perforating design, fracture initiation/gradient, productivity ratio,
and gun configuration optimization for well completions.

References:
- API RP 19B: Evaluation of Well Perforators (Berea correction factors)
- Karakas & Tariq (1991): Semi-analytical productivity model for perforated completions
- Haimson & Fairhurst (1967): Hydraulic fracture initiation pressure
- Eaton (1969): Fracture gradient prediction from Poisson's ratio
- Bell (1984): Perforation orientation and stress effects
"""
import math
from typing import Dict, Any, List, Optional


class CompletionDesignEngine:
    """
    Implements completion engineering calculations for perforating,
    fracturing, and productivity analysis. All methods are @staticmethod.
    """

    # Standard gun configurations
    GUN_DATABASE = {
        "2-1/8": {"od_in": 2.125, "max_casing_id": 4.090, "typical_spf": 4, "phasing": [0, 60, 90]},
        "2-1/2": {"od_in": 2.500, "max_casing_id": 4.892, "typical_spf": 4, "phasing": [0, 60, 90]},
        "3-3/8": {"od_in": 3.375, "max_casing_id": 6.276, "typical_spf": 6, "phasing": [60, 90, 120]},
        "4-5/8": {"od_in": 4.625, "max_casing_id": 8.535, "typical_spf": 12, "phasing": [60, 90, 120]},
        "5":     {"od_in": 5.000, "max_casing_id": 8.921, "typical_spf": 12, "phasing": [60, 90, 120]},
        "7":     {"od_in": 7.000, "max_casing_id": 12.415, "typical_spf": 6, "phasing": [60, 120]},
    }

    # API RP 19B correction factor ranges
    STRESS_CF_RANGE = (0.60, 1.00)  # Effective stress correction
    TEMP_CF_RANGE = (0.85, 1.10)    # Temperature correction
    FLUID_CF_RANGE = (0.70, 1.00)   # Completion fluid correction

    @staticmethod
    def calculate_penetration_depth(
        penetration_berea_in: float,
        effective_stress_psi: float = 0.0,
        temperature_f: float = 200.0,
        completion_fluid: str = "brine",
        cement_strength_psi: float = 3000.0,
        casing_thickness_in: float = 0.50
    ) -> Dict[str, Any]:
        """
        Calculate corrected perforation penetration depth per API RP 19B.

        P_corrected = P_berea × CF_stress × CF_temp × CF_fluid × CF_cement × CF_casing

        Args:
            penetration_berea_in: penetration in Berea sandstone (inches) from gun spec
            effective_stress_psi: net confining stress (overburden - pore pressure)
            temperature_f: bottomhole temperature (°F)
            completion_fluid: type of fluid ("brine", "oil_based", "acid", "completion")
            cement_strength_psi: compressive strength of cement (psi)
            casing_thickness_in: casing wall thickness (inches)

        Returns:
            Dict with corrected penetration, correction factors, entry hole
        """
        # CF_stress: Higher stress reduces penetration (API RP 19B Section 5)
        if effective_stress_psi <= 0:
            cf_stress = 1.0
        elif effective_stress_psi < 3000:
            cf_stress = 1.0 - 0.05 * (effective_stress_psi / 3000)
        elif effective_stress_psi < 10000:
            cf_stress = 0.95 - 0.20 * ((effective_stress_psi - 3000) / 7000)
        else:
            cf_stress = max(0.60, 0.75 - 0.15 * ((effective_stress_psi - 10000) / 10000))

        # CF_temp: Temperature affects shaped charge jet
        if temperature_f < 200:
            cf_temp = 1.02
        elif temperature_f < 350:
            cf_temp = 1.02 - 0.07 * ((temperature_f - 200) / 150)
        elif temperature_f < 500:
            cf_temp = 0.95 - 0.10 * ((temperature_f - 350) / 150)
        else:
            cf_temp = max(0.80, 0.85 - 0.05 * ((temperature_f - 500) / 200))

        # CF_fluid: Completion fluid viscosity/density affects tunnel cleanup
        fluid_factors = {
            "brine": 0.95, "acid": 1.00, "oil_based": 0.80,
            "completion": 0.90, "water": 0.95, "diesel": 0.75
        }
        cf_fluid = fluid_factors.get(completion_fluid.lower(), 0.90)

        # CF_cement: Higher cement strength slightly restricts penetration
        if cement_strength_psi < 2000:
            cf_cement = 1.0
        elif cement_strength_psi < 5000:
            cf_cement = 1.0 - 0.03 * ((cement_strength_psi - 2000) / 3000)
        else:
            cf_cement = max(0.93, 0.97 - 0.04 * ((cement_strength_psi - 5000) / 5000))

        # CF_casing: Thicker casing absorbs more jet energy
        if casing_thickness_in < 0.3:
            cf_casing = 1.0
        elif casing_thickness_in < 0.6:
            cf_casing = 1.0 - 0.05 * ((casing_thickness_in - 0.3) / 0.3)
        else:
            cf_casing = max(0.90, 0.95 - 0.05 * ((casing_thickness_in - 0.6) / 0.4))

        # Total correction
        cf_total = cf_stress * cf_temp * cf_fluid * cf_cement * cf_casing
        penetration_corrected = penetration_berea_in * cf_total

        # Entry hole estimate (typically 50-70% of Berea rating)
        entry_hole_berea = penetration_berea_in * 0.10  # rough: entry ≈ 10% of length
        entry_hole_corrected = entry_hole_berea * cf_stress * cf_cement

        return {
            "penetration_berea_in": round(penetration_berea_in, 2),
            "penetration_corrected_in": round(penetration_corrected, 2),
            "penetration_corrected_ft": round(penetration_corrected / 12, 3),
            "entry_hole_corrected_in": round(entry_hole_corrected, 3),
            "correction_factors": {
                "cf_stress": round(cf_stress, 3),
                "cf_temperature": round(cf_temp, 3),
                "cf_fluid": round(cf_fluid, 3),
                "cf_cement": round(cf_cement, 3),
                "cf_casing": round(cf_casing, 3),
                "cf_total": round(cf_total, 3),
            },
            "efficiency_pct": round(cf_total * 100, 1),
        }

    @staticmethod
    def calculate_productivity_ratio(
        formation_permeability_md: float,
        perforation_length_in: float,
        perforation_radius_in: float,
        wellbore_radius_ft: float,
        spf: int,
        phasing_deg: int,
        formation_thickness_ft: float,
        kv_kh_ratio: float = 1.0,
        damage_radius_ft: float = 0.0,
        damage_permeability_md: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate productivity ratio using Karakas & Tariq (1991) model.

        J/J_ideal = 1 / (1 + S_total × (k_h / (141.2 × q × Bo × mu)))
        Simplified: PR = 1 / (1 + S_total / S_reference)

        S_total = S_p + S_v + S_wb + S_d

        Args:
            formation_permeability_md: horizontal permeability (mD)
            perforation_length_in: total perforation tunnel length (inches)
            perforation_radius_in: perforation tunnel radius (inches)
            wellbore_radius_ft: wellbore radius (ft)
            spf: shots per foot
            phasing_deg: gun phasing (degrees: 0, 60, 90, 120, 180, 360)
            formation_thickness_ft: net pay thickness (ft)
            kv_kh_ratio: vertical to horizontal permeability ratio
            damage_radius_ft: extent of damaged zone (ft) (0 = no damage)
            damage_permeability_md: permeability of damaged zone (mD)

        Returns:
            Dict with skin components, total skin, PR
        """
        r_w = wellbore_radius_ft
        l_p = perforation_length_in / 12.0  # convert to feet
        r_p = perforation_radius_in / 12.0  # convert to feet
        h = formation_thickness_ft
        k_h = formation_permeability_md
        k_v = k_h * kv_kh_ratio

        # Effective perforation spacing
        h_perf = 12.0 / spf if spf > 0 else h  # inches between perfs → feet
        h_perf_ft = h_perf / 12.0

        # Phasing-dependent constants (Karakas & Tariq Table 1)
        phasing_data = {
            0:   {"a_theta": -2.091, "b_theta": 0.0453, "c1": 1.6e-1, "c2": 2.675},
            60:  {"a_theta": -2.025, "b_theta": 0.0943, "c1": 2.6e-2, "c2": 4.532},
            90:  {"a_theta": -1.905, "b_theta": 0.1038, "c1": 6.6e-3, "c2": 5.320},
            120: {"a_theta": -1.898, "b_theta": 0.1023, "c1": 1.6e-3, "c2": 6.155},
            180: {"a_theta": -2.018, "b_theta": 0.0634, "c1": 2.3e-2, "c2": 3.550},
            360: {"a_theta": -2.091, "b_theta": 0.0453, "c1": 1.6e-1, "c2": 2.675},
        }
        p = phasing_data.get(phasing_deg, phasing_data[90])

        # S_p: Perforation pseudo-skin (plane flow)
        r_eff_w = r_w * math.exp(p["a_theta"])  # effective wellbore radius
        if l_p > 0 and r_eff_w > 0:
            s_p = math.log(r_eff_w / (r_w + l_p)) if (r_w + l_p) > r_eff_w else 0
        else:
            s_p = 0

        # S_v: Vertical pseudo-skin (convergence to perforation tunnels)
        if l_p > 0 and k_v > 0 and h_perf_ft > 0:
            h_d = h_perf_ft * math.sqrt(k_h / k_v) / l_p  # dimensionless
            r_pd = r_p / (h_perf_ft * (1 + math.sqrt(k_v / k_h))) if h_perf_ft > 0 else 0.01

            if h_d > 0 and r_pd > 0:
                a_coeff = p.get("a_theta", -1.905)
                b_coeff = p.get("b_theta", 0.1038)
                s_v = (10 ** (a_coeff + b_coeff * math.log10(r_pd))) * h_d if r_pd > 0 else 0
                s_v = max(0, min(s_v, 50))  # cap reasonable range
            else:
                s_v = 0
        else:
            s_v = 0

        # S_wb: Wellbore skin (flow convergence to wellbore)
        c1 = p["c1"]
        c2 = p["c2"]
        if r_p > 0 and r_w > 0:
            s_wb = c1 * math.exp(c2 * r_p / r_w) if (r_p / r_w) < 1 else c1
            s_wb = min(s_wb, 5)  # cap
        else:
            s_wb = 0

        # S_d: Damage skin
        if damage_radius_ft > 0 and damage_permeability_md > 0 and damage_permeability_md < k_h:
            s_d = (k_h / damage_permeability_md - 1) * math.log(damage_radius_ft / r_w)
            s_d = max(0, s_d)
        else:
            s_d = 0

        s_total = s_p + s_v + s_wb + s_d

        # Productivity Ratio: PR = ln(re/rw) / (ln(re/rw) + S_total)
        # Assume drainage radius ~ 660 ft (40-acre spacing)
        r_e = 660.0
        ln_re_rw = math.log(r_e / r_w) if r_w > 0 else 7.0
        pr = ln_re_rw / (ln_re_rw + s_total) if (ln_re_rw + s_total) > 0 else 0

        # Classification
        if pr >= 0.90:
            quality = "Excellent"
        elif pr >= 0.75:
            quality = "Good"
        elif pr >= 0.50:
            quality = "Fair"
        else:
            quality = "Poor"

        return {
            "skin_components": {
                "s_perforation": round(s_p, 3),
                "s_vertical": round(s_v, 3),
                "s_wellbore": round(s_wb, 4),
                "s_damage": round(s_d, 3),
            },
            "skin_total": round(s_total, 3),
            "productivity_ratio": round(pr, 4),
            "productivity_pct": round(pr * 100, 1),
            "quality": quality,
            "parameters_used": {
                "spf": spf, "phasing_deg": phasing_deg,
                "perf_length_in": round(perforation_length_in, 2),
                "perf_radius_in": round(perforation_radius_in, 3),
                "kv_kh": kv_kh_ratio,
            }
        }

    @staticmethod
    def calculate_underbalance(
        reservoir_pressure_psi: float,
        wellbore_pressure_psi: float,
        formation_permeability_md: float,
        formation_type: str = "sandstone"
    ) -> Dict[str, Any]:
        """
        Calculate underbalance for perforating and evaluate adequacy.

        ΔP_ub = P_reservoir - P_wellbore (positive = underbalanced)

        Args:
            reservoir_pressure_psi: formation/reservoir pressure (psi)
            wellbore_pressure_psi: wellbore pressure at perforation depth (psi)
            formation_permeability_md: formation permeability (mD)
            formation_type: "sandstone", "carbonate", "shale"

        Returns:
            Dict with underbalance, status, recommended range
        """
        delta_p = reservoir_pressure_psi - wellbore_pressure_psi
        is_underbalanced = delta_p > 0

        # Recommended underbalance ranges (industry guidelines)
        recommendations = {
            "sandstone": {
                "high_perm": (200, 500),    # >100 mD
                "med_perm": (500, 1500),    # 10-100 mD
                "low_perm": (1500, 3000),   # <10 mD
            },
            "carbonate": {
                "high_perm": (100, 300),
                "med_perm": (300, 1000),
                "low_perm": (1000, 2000),
            },
            "shale": {
                "high_perm": (500, 1000),
                "med_perm": (1000, 2000),
                "low_perm": (2000, 5000),
            }
        }

        rock = recommendations.get(formation_type.lower(), recommendations["sandstone"])
        if formation_permeability_md > 100:
            rec_range = rock["high_perm"]
            perm_class = "High (>100 mD)"
        elif formation_permeability_md > 10:
            rec_range = rock["med_perm"]
            perm_class = "Medium (10-100 mD)"
        else:
            rec_range = rock["low_perm"]
            perm_class = "Low (<10 mD)"

        # Status assessment
        if not is_underbalanced:
            status = "Overbalanced"
            recommendation = "Switch to underbalanced perforating for better cleanup"
        elif delta_p < rec_range[0]:
            status = "Insufficient Underbalance"
            recommendation = f"Increase underbalance to {rec_range[0]}-{rec_range[1]} psi"
        elif delta_p <= rec_range[1]:
            status = "Optimal"
            recommendation = "Underbalance within recommended range"
        else:
            status = "Excessive Underbalance"
            recommendation = f"Risk of sand influx/formation failure. Reduce to {rec_range[1]} psi max"

        return {
            "underbalance_psi": round(delta_p, 1),
            "is_underbalanced": is_underbalanced,
            "overbalance_psi": round(-delta_p, 1) if not is_underbalanced else 0,
            "status": status,
            "recommended_range_psi": list(rec_range),
            "permeability_class": perm_class,
            "formation_type": formation_type,
            "recommendation": recommendation,
        }

    @staticmethod
    def select_gun_configuration(
        casing_id_in: float,
        tubing_od_in: float = 0.0,
        max_pressure_psi: float = 15000,
        target_spf: int = 0,
        conveyed_by: str = "wireline"
    ) -> Dict[str, Any]:
        """
        Select optimal gun configuration based on casing geometry.

        Args:
            casing_id_in: casing inner diameter (inches)
            tubing_od_in: tubing OD if through-tubing (0 = casing guns)
            max_pressure_psi: maximum bottomhole pressure rating needed
            target_spf: desired shots per foot (0 = auto)
            conveyed_by: "wireline", "tubing", "coiled_tubing", "tcp"

        Returns:
            Dict with recommended guns, clearance check, alternatives
        """
        is_through_tubing = tubing_od_in > 0
        available_clearance = tubing_od_in - 0.5 if is_through_tubing else casing_id_in

        compatible_guns = []
        for name, spec in CompletionDesignEngine.GUN_DATABASE.items():
            clearance = casing_id_in - spec["od_in"]
            if clearance >= 0.25:  # minimum clearance 0.25"
                if is_through_tubing and spec["od_in"] > (tubing_od_in - 0.5):
                    continue
                compatible_guns.append({
                    "gun_size": name,
                    "od_in": spec["od_in"],
                    "clearance_in": round(clearance, 3),
                    "typical_spf": spec["typical_spf"],
                    "available_phasing": spec["phasing"],
                    "score": clearance * 0.3 + spec["typical_spf"] * 0.7,
                })

        # Sort by score (balance between clearance and shot density)
        compatible_guns.sort(key=lambda g: g["score"], reverse=True)

        recommended = compatible_guns[0] if compatible_guns else None

        # Conveyed method considerations
        convey_notes = {
            "wireline": "Standard deployment. Max gun length ~60 ft per run.",
            "tubing": "Tubing-conveyed perforating (TCP). Allows long intervals.",
            "coiled_tubing": "CT-conveyed. Good for horizontal wells.",
            "tcp": "TCP with packer. Allows underbalanced perforating.",
        }

        return {
            "recommended": recommended,
            "alternatives": compatible_guns[1:3] if len(compatible_guns) > 1 else [],
            "all_compatible": compatible_guns,
            "casing_id_in": casing_id_in,
            "is_through_tubing": is_through_tubing,
            "conveyed_by": conveyed_by,
            "conveyance_notes": convey_notes.get(conveyed_by, "Standard wireline."),
            "total_compatible_guns": len(compatible_guns),
        }

    @staticmethod
    def calculate_fracture_initiation(
        sigma_min_psi: float,
        sigma_max_psi: float,
        tensile_strength_psi: float,
        pore_pressure_psi: float,
        biot_coefficient: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate hydraulic fracture initiation pressure.
        Haimson & Fairhurst (1967):

        P_frac = 3σ_min - σ_max + T - α × P_pore

        For vertical well with σ_H and σ_h:
        P_breakdown = 3σ_h - σ_H + T_0 - P_p

        Args:
            sigma_min_psi: minimum horizontal stress (psi)
            sigma_max_psi: maximum horizontal stress (psi)
            tensile_strength_psi: rock tensile strength (psi)
            pore_pressure_psi: formation pore pressure (psi)
            biot_coefficient: Biot poroelastic coefficient (0-1)

        Returns:
            Dict with fracture initiation pressure, breakdown pressure, margins
        """
        # Haimson-Fairhurst breakdown pressure
        p_breakdown = (3.0 * sigma_min_psi - sigma_max_psi
                       + tensile_strength_psi
                       - biot_coefficient * pore_pressure_psi)

        # Fracture reopening (no tensile strength — fracture already exists)
        p_reopen = 3.0 * sigma_min_psi - sigma_max_psi - biot_coefficient * pore_pressure_psi

        # Closure pressure (minimum horizontal stress)
        p_closure = sigma_min_psi

        # ISIP estimate (instantaneous shut-in pressure)
        p_isip = sigma_min_psi * 1.02  # slightly above closure

        # Net pressure at breakdown
        net_pressure = p_breakdown - p_closure

        # Stress ratio
        stress_ratio = sigma_max_psi / sigma_min_psi if sigma_min_psi > 0 else 1.0

        # Fracture orientation
        if stress_ratio > 1.1:
            orientation = "Fracture perpendicular to σ_min (transverse if horizontal well)"
        else:
            orientation = "Near-isotropic stress — fracture direction uncertain"

        return {
            "breakdown_pressure_psi": round(p_breakdown, 1),
            "reopening_pressure_psi": round(p_reopen, 1),
            "closure_pressure_psi": round(p_closure, 1),
            "isip_estimate_psi": round(p_isip, 1),
            "net_pressure_psi": round(net_pressure, 1),
            "tensile_strength_psi": round(tensile_strength_psi, 1),
            "stress_ratio": round(stress_ratio, 3),
            "fracture_orientation": orientation,
            "stresses": {
                "sigma_min_psi": round(sigma_min_psi, 1),
                "sigma_max_psi": round(sigma_max_psi, 1),
                "pore_pressure_psi": round(pore_pressure_psi, 1),
            }
        }

    @staticmethod
    def calculate_fracture_gradient(
        depth_tvd_ft: float,
        pore_pressure_psi: float,
        overburden_stress_psi: float,
        poisson_ratio: float = 0.25,
        tectonic_stress_psi: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate fracture gradient using Eaton's method (1969).

        FG = (ν/(1-ν)) × (σ_ob - P_p)/D + P_p/D + σ_tect/D

        Args:
            depth_tvd_ft: true vertical depth (ft)
            pore_pressure_psi: pore pressure at TVD (psi)
            overburden_stress_psi: overburden stress at TVD (psi)
            poisson_ratio: Poisson's ratio of formation
            tectonic_stress_psi: additional tectonic stress component (psi)

        Returns:
            Dict with fracture gradient, equivalent pressures, profile data
        """
        if depth_tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        # Eaton's equation
        nu = poisson_ratio
        stress_ratio = nu / (1.0 - nu)

        # Matrix stress contribution
        matrix_stress = stress_ratio * (overburden_stress_psi - pore_pressure_psi)

        # Total fracture pressure
        frac_pressure = pore_pressure_psi + matrix_stress + tectonic_stress_psi

        # Gradients (psi/ft and ppg equivalent)
        frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
        frac_gradient_ppg = frac_gradient_psi_ft / 0.052
        pore_gradient_ppg = (pore_pressure_psi / depth_tvd_ft) / 0.052
        overburden_gradient_ppg = (overburden_stress_psi / depth_tvd_ft) / 0.052

        # Fracture window (pore to frac)
        window_ppg = frac_gradient_ppg - pore_gradient_ppg

        # Generate depth profile (every 1000 ft)
        profile = []
        for d in range(1000, int(depth_tvd_ft) + 1, 1000):
            d_ratio = d / depth_tvd_ft
            p_pore_d = pore_pressure_psi * d_ratio
            sigma_ob_d = overburden_stress_psi * d_ratio
            frac_p_d = p_pore_d + stress_ratio * (sigma_ob_d - p_pore_d) + tectonic_stress_psi * d_ratio
            profile.append({
                "depth_ft": d,
                "pore_pressure_ppg": round((p_pore_d / d) / 0.052, 2),
                "fracture_gradient_ppg": round((frac_p_d / d) / 0.052, 2),
                "overburden_ppg": round((sigma_ob_d / d) / 0.052, 2),
            })
        # Add exact TVD
        profile.append({
            "depth_ft": round(depth_tvd_ft),
            "pore_pressure_ppg": round(pore_gradient_ppg, 2),
            "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
            "overburden_ppg": round(overburden_gradient_ppg, 2),
        })

        return {
            "fracture_pressure_psi": round(frac_pressure, 1),
            "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
            "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
            "pore_gradient_ppg": round(pore_gradient_ppg, 2),
            "overburden_gradient_ppg": round(overburden_gradient_ppg, 2),
            "mud_weight_window_ppg": round(window_ppg, 2),
            "stress_ratio_nu": round(stress_ratio, 4),
            "poisson_ratio": poisson_ratio,
            "depth_profile": profile,
        }

    @staticmethod
    def optimize_perforation_design(
        casing_id_in: float,
        formation_permeability_md: float,
        formation_thickness_ft: float,
        reservoir_pressure_psi: float,
        wellbore_radius_ft: float = 0.354,
        kv_kh_ratio: float = 0.5,
        penetration_berea_in: float = 12.0,
        effective_stress_psi: float = 3000.0,
        temperature_f: float = 200.0,
        damage_radius_ft: float = 0.5,
        damage_permeability_md: float = 50.0
    ) -> Dict[str, Any]:
        """
        Optimize SPF and phasing combination for maximum productivity.

        Tests multiple configurations and ranks by productivity ratio.

        Args:
            All standard completion parameters

        Returns:
            Dict with ranked configurations, optimal selection, sensitivity data
        """
        eng = CompletionDesignEngine

        # Get corrected penetration
        pen = eng.calculate_penetration_depth(
            penetration_berea_in=penetration_berea_in,
            effective_stress_psi=effective_stress_psi,
            temperature_f=temperature_f,
        )
        corrected_pen_in = pen["penetration_corrected_in"]

        # Test configurations
        spf_options = [2, 4, 6, 8, 12]
        phasing_options = [0, 60, 90, 120, 180]

        results = []
        for spf in spf_options:
            for phasing in phasing_options:
                pr_result = eng.calculate_productivity_ratio(
                    formation_permeability_md=formation_permeability_md,
                    perforation_length_in=corrected_pen_in,
                    perforation_radius_in=corrected_pen_in * 0.04,  # ~4% of length
                    wellbore_radius_ft=wellbore_radius_ft,
                    spf=spf,
                    phasing_deg=phasing,
                    formation_thickness_ft=formation_thickness_ft,
                    kv_kh_ratio=kv_kh_ratio,
                    damage_radius_ft=damage_radius_ft,
                    damage_permeability_md=damage_permeability_md,
                )
                results.append({
                    "spf": spf,
                    "phasing_deg": phasing,
                    "productivity_ratio": pr_result["productivity_ratio"],
                    "skin_total": pr_result["skin_total"],
                    "quality": pr_result["quality"],
                })

        # Sort by PR descending
        results.sort(key=lambda r: r["productivity_ratio"], reverse=True)

        optimal = results[0]
        top_5 = results[:5]

        # SPF sensitivity (fix phasing at optimal)
        spf_sensitivity = []
        for r in results:
            if r["phasing_deg"] == optimal["phasing_deg"]:
                spf_sensitivity.append({
                    "spf": r["spf"],
                    "productivity_ratio": r["productivity_ratio"],
                    "skin_total": r["skin_total"],
                })

        # Phasing sensitivity (fix SPF at optimal)
        phasing_sensitivity = []
        for r in results:
            if r["spf"] == optimal["spf"]:
                phasing_sensitivity.append({
                    "phasing_deg": r["phasing_deg"],
                    "productivity_ratio": r["productivity_ratio"],
                    "skin_total": r["skin_total"],
                })

        return {
            "optimal_configuration": optimal,
            "top_5_configurations": top_5,
            "penetration_corrected_in": corrected_pen_in,
            "spf_sensitivity": spf_sensitivity,
            "phasing_sensitivity": phasing_sensitivity,
            "total_configurations_tested": len(results),
        }

    @staticmethod
    def calculate_full_completion_design(
        casing_id_in: float,
        formation_permeability_md: float,
        formation_thickness_ft: float,
        reservoir_pressure_psi: float,
        wellbore_pressure_psi: float,
        depth_tvd_ft: float,
        overburden_stress_psi: float,
        pore_pressure_psi: float,
        sigma_min_psi: float,
        sigma_max_psi: float,
        tensile_strength_psi: float = 500.0,
        poisson_ratio: float = 0.25,
        penetration_berea_in: float = 12.0,
        effective_stress_psi: float = 3000.0,
        temperature_f: float = 200.0,
        completion_fluid: str = "brine",
        wellbore_radius_ft: float = 0.354,
        kv_kh_ratio: float = 0.5,
        tubing_od_in: float = 0.0,
        damage_radius_ft: float = 0.5,
        damage_permeability_md: float = 50.0,
        formation_type: str = "sandstone",
    ) -> Dict[str, Any]:
        """
        Complete integrated completion design analysis.

        Returns:
            Dict with penetration, gun selection, underbalance, fracture,
            productivity optimization, summary and alerts.
        """
        eng = CompletionDesignEngine

        # 1. Penetration depth
        penetration = eng.calculate_penetration_depth(
            penetration_berea_in=penetration_berea_in,
            effective_stress_psi=effective_stress_psi,
            temperature_f=temperature_f,
            completion_fluid=completion_fluid,
        )

        # 2. Gun selection
        gun = eng.select_gun_configuration(
            casing_id_in=casing_id_in,
            tubing_od_in=tubing_od_in,
        )

        # 3. Underbalance analysis
        underbalance = eng.calculate_underbalance(
            reservoir_pressure_psi=reservoir_pressure_psi,
            wellbore_pressure_psi=wellbore_pressure_psi,
            formation_permeability_md=formation_permeability_md,
            formation_type=formation_type,
        )

        # 4. Fracture initiation
        fracture = eng.calculate_fracture_initiation(
            sigma_min_psi=sigma_min_psi,
            sigma_max_psi=sigma_max_psi,
            tensile_strength_psi=tensile_strength_psi,
            pore_pressure_psi=pore_pressure_psi,
        )

        # 5. Fracture gradient
        frac_gradient = eng.calculate_fracture_gradient(
            depth_tvd_ft=depth_tvd_ft,
            pore_pressure_psi=pore_pressure_psi,
            overburden_stress_psi=overburden_stress_psi,
            poisson_ratio=poisson_ratio,
        )

        # 6. Optimize perforation design
        optimization = eng.optimize_perforation_design(
            casing_id_in=casing_id_in,
            formation_permeability_md=formation_permeability_md,
            formation_thickness_ft=formation_thickness_ft,
            reservoir_pressure_psi=reservoir_pressure_psi,
            wellbore_radius_ft=wellbore_radius_ft,
            kv_kh_ratio=kv_kh_ratio,
            penetration_berea_in=penetration_berea_in,
            effective_stress_psi=effective_stress_psi,
            temperature_f=temperature_f,
            damage_radius_ft=damage_radius_ft,
            damage_permeability_md=damage_permeability_md,
        )

        # Build alerts
        alerts = []
        if penetration["efficiency_pct"] < 70:
            alerts.append(f"Low penetration efficiency {penetration['efficiency_pct']}% — review correction factors")
        if underbalance["status"] != "Optimal":
            alerts.append(f"Underbalance: {underbalance['status']} — {underbalance['recommendation']}")
        opt_conf = optimization["optimal_configuration"]
        if opt_conf["productivity_ratio"] < 0.5:
            alerts.append(f"Low productivity ratio {opt_conf['productivity_ratio']:.2f} — consider stimulation")
        if gun["total_compatible_guns"] == 0:
            alerts.append("No compatible guns found for this casing size!")
        if frac_gradient["mud_weight_window_ppg"] < 1.0:
            alerts.append(f"Narrow mud weight window {frac_gradient['mud_weight_window_ppg']:.1f} ppg — risk of losses")

        # Summary
        summary = {
            "penetration_corrected_in": penetration["penetration_corrected_in"],
            "penetration_efficiency_pct": penetration["efficiency_pct"],
            "recommended_gun": gun["recommended"]["gun_size"] if gun["recommended"] else "None",
            "optimal_spf": opt_conf["spf"],
            "optimal_phasing_deg": opt_conf["phasing_deg"],
            "productivity_ratio": opt_conf["productivity_ratio"],
            "skin_total": opt_conf["skin_total"],
            "underbalance_psi": underbalance["underbalance_psi"],
            "underbalance_status": underbalance["status"],
            "fracture_gradient_ppg": frac_gradient["fracture_gradient_ppg"],
            "mud_weight_window_ppg": frac_gradient["mud_weight_window_ppg"],
            "breakdown_pressure_psi": fracture["breakdown_pressure_psi"],
            "alerts": alerts,
        }

        return {
            "summary": summary,
            "penetration": penetration,
            "gun_selection": gun,
            "underbalance": underbalance,
            "fracture_initiation": fracture,
            "fracture_gradient": frac_gradient,
            "optimization": optimization,
            "alerts": alerts,
        }
