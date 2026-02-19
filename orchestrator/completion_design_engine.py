"""
Completion Design Calculation Engine

Perforating design, fracture initiation/gradient, productivity ratio,
and gun configuration optimization for well completions.

Elite enhancements (Phase 7):
- IPR curves: Vogel (oil below Pb), Fetkovich (gas), Darcy (single-phase above Pb)
- VLP: Beggs & Brill (1973) multiphase flow in tubing
- Nodal Analysis: IPR-VLP intersection for operating point
- Fracture gradient: Daines (1982), Matthews-Kelly (1967) alternatives to Eaton
- Crushed zone skin: Karakas-Tariq 4th component (k/kcz damage near tunnel)
- Horizontal well productivity: Joshi (1991) model
- Expanded gun catalog: ~25 entries with TCP/wireline/CT types

References:
- API RP 19B: Evaluation of Well Perforators (Berea correction factors)
- Karakas & Tariq (1991): Semi-analytical productivity model for perforated completions
- Haimson & Fairhurst (1967): Hydraulic fracture initiation pressure
- Eaton (1969): Fracture gradient prediction from Poisson's ratio
- Bell (1984): Perforation orientation and stress effects
- Vogel (1968): Inflow Performance of Solution-Gas Drive Wells (JPT)
- Fetkovich (1973): Isochronal Testing of Oil Wells (SPE 4529)
- Beggs & Brill (1973): Two-Phase Flow in Pipes (U. Tulsa)
- Joshi (1991): Horizontal Well Technology (PennWell)
- Daines (1982): A Modified Fracture Gradient Prediction Method
- Matthews & Kelly (1967): How to Predict Formation Pressure and Fracture Gradient
"""
import math
from typing import Dict, Any, List, Optional, Tuple


class CompletionDesignEngine:
    """
    Implements completion engineering calculations for perforating,
    fracturing, and productivity analysis. All methods are @staticmethod.
    """

    # Expanded gun catalog — realistic entries based on public data
    # (Schlumberger PowerJet, Halliburton Piranha-class, Baker Atlas)
    # Organized by gun OD with full specs per entry
    GUN_DATABASE = {
        "2-1/8": {"od_in": 2.125, "max_casing_id": 4.090, "typical_spf": 4, "phasing": [0, 60, 90]},
        "2-1/2": {"od_in": 2.500, "max_casing_id": 4.892, "typical_spf": 4, "phasing": [0, 60, 90]},
        "3-3/8": {"od_in": 3.375, "max_casing_id": 6.276, "typical_spf": 6, "phasing": [60, 90, 120]},
        "4-5/8": {"od_in": 4.625, "max_casing_id": 8.535, "typical_spf": 12, "phasing": [60, 90, 120]},
        "5":     {"od_in": 5.000, "max_casing_id": 8.921, "typical_spf": 12, "phasing": [60, 90, 120]},
        "7":     {"od_in": 7.000, "max_casing_id": 12.415, "typical_spf": 6, "phasing": [60, 120]},
    }

    # Expanded catalog with detailed entries per gun (gun_type, EHD, penetration, pressure, temp)
    GUN_CATALOG = [
        # Through-tubing wireline guns (small OD)
        {"name": "WL-2125-STD", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
         "ehd_in": 0.26, "penetration_berea_in": 8.5, "spf": 4, "phasing": 0,
         "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 4.090},
        {"name": "WL-2125-DP", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
         "ehd_in": 0.30, "penetration_berea_in": 10.0, "spf": 4, "phasing": 60,
         "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 4.090},
        {"name": "WL-2500-STD", "od_in": 2.500, "gun_type": "wireline", "carrier_od_in": 2.500,
         "ehd_in": 0.29, "penetration_berea_in": 11.2, "spf": 4, "phasing": 60,
         "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 4.892},
        {"name": "WL-2500-HP", "od_in": 2.500, "gun_type": "wireline", "carrier_od_in": 2.500,
         "ehd_in": 0.33, "penetration_berea_in": 12.8, "spf": 6, "phasing": 60,
         "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 4.892},
        {"name": "WL-2750-BH", "od_in": 2.750, "gun_type": "wireline", "carrier_od_in": 2.750,
         "ehd_in": 0.32, "penetration_berea_in": 13.5, "spf": 6, "phasing": 60,
         "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 5.524},
        # Mid-range casing guns (wireline & TCP)
        {"name": "WL-3375-STD", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
         "ehd_in": 0.36, "penetration_berea_in": 15.0, "spf": 6, "phasing": 60,
         "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 6.276},
        {"name": "WL-3375-DP", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
         "ehd_in": 0.42, "penetration_berea_in": 17.3, "spf": 6, "phasing": 90,
         "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 6.276},
        {"name": "TCP-3375-UB", "od_in": 3.375, "gun_type": "tcp", "carrier_od_in": 3.375,
         "ehd_in": 0.38, "penetration_berea_in": 16.5, "spf": 6, "phasing": 60,
         "max_pressure_psi": 22000, "max_temp_f": 450, "max_casing_id": 6.276},
        # Large casing guns — high performance
        {"name": "WL-4500-STD", "od_in": 4.500, "gun_type": "wireline", "carrier_od_in": 4.500,
         "ehd_in": 0.42, "penetration_berea_in": 20.5, "spf": 12, "phasing": 60,
         "max_pressure_psi": 20000, "max_temp_f": 400, "max_casing_id": 8.535},
        {"name": "TCP-4500-DP", "od_in": 4.500, "gun_type": "tcp", "carrier_od_in": 4.500,
         "ehd_in": 0.50, "penetration_berea_in": 23.0, "spf": 12, "phasing": 60,
         "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.535},
        {"name": "WL-4625-HP", "od_in": 4.625, "gun_type": "wireline", "carrier_od_in": 4.625,
         "ehd_in": 0.45, "penetration_berea_in": 21.8, "spf": 12, "phasing": 90,
         "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 8.535},
        {"name": "TCP-4625-DP", "od_in": 4.625, "gun_type": "tcp", "carrier_od_in": 4.625,
         "ehd_in": 0.52, "penetration_berea_in": 24.5, "spf": 12, "phasing": 60,
         "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.535},
        {"name": "CT-4500-HP", "od_in": 4.500, "gun_type": "coiled_tubing", "carrier_od_in": 4.500,
         "ehd_in": 0.44, "penetration_berea_in": 21.0, "spf": 12, "phasing": 60,
         "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 8.535},
        {"name": "WL-5000-STD", "od_in": 5.000, "gun_type": "wireline", "carrier_od_in": 5.000,
         "ehd_in": 0.48, "penetration_berea_in": 23.5, "spf": 12, "phasing": 90,
         "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 8.921},
        {"name": "TCP-5000-DP", "od_in": 5.000, "gun_type": "tcp", "carrier_od_in": 5.000,
         "ehd_in": 0.55, "penetration_berea_in": 26.0, "spf": 12, "phasing": 60,
         "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.921},
        {"name": "WL-4750-EXT", "od_in": 4.750, "gun_type": "wireline", "carrier_od_in": 4.750,
         "ehd_in": 0.46, "penetration_berea_in": 22.0, "spf": 12, "phasing": 120,
         "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 8.921},
        # Large-bore guns for big casing
        {"name": "TCP-7000-STD", "od_in": 7.000, "gun_type": "tcp", "carrier_od_in": 7.000,
         "ehd_in": 0.70, "penetration_berea_in": 32.0, "spf": 6, "phasing": 60,
         "max_pressure_psi": 20000, "max_temp_f": 400, "max_casing_id": 12.415},
        {"name": "TCP-7000-DP", "od_in": 7.000, "gun_type": "tcp", "carrier_od_in": 7.000,
         "ehd_in": 0.85, "penetration_berea_in": 38.0, "spf": 6, "phasing": 120,
         "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 12.415},
        {"name": "WL-7000-HP", "od_in": 7.000, "gun_type": "wireline", "carrier_od_in": 7.000,
         "ehd_in": 0.72, "penetration_berea_in": 34.0, "spf": 6, "phasing": 60,
         "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 12.415},
        # HPHT specialty guns
        {"name": "TCP-3375-HPHT", "od_in": 3.375, "gun_type": "tcp", "carrier_od_in": 3.375,
         "ehd_in": 0.34, "penetration_berea_in": 14.0, "spf": 6, "phasing": 60,
         "max_pressure_psi": 30000, "max_temp_f": 550, "max_casing_id": 6.276},
        {"name": "TCP-4625-HPHT", "od_in": 4.625, "gun_type": "tcp", "carrier_od_in": 4.625,
         "ehd_in": 0.44, "penetration_berea_in": 20.0, "spf": 12, "phasing": 60,
         "max_pressure_psi": 30000, "max_temp_f": 550, "max_casing_id": 8.535},
        # Economy / shallow well guns
        {"name": "WL-2125-ECO", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
         "ehd_in": 0.22, "penetration_berea_in": 6.0, "spf": 2, "phasing": 0,
         "max_pressure_psi": 10000, "max_temp_f": 300, "max_casing_id": 4.090},
        {"name": "WL-3375-ECO", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
         "ehd_in": 0.30, "penetration_berea_in": 11.0, "spf": 4, "phasing": 0,
         "max_pressure_psi": 10000, "max_temp_f": 300, "max_casing_id": 6.276},
    ]

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

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: IPR Models (Vogel, Fetkovich, Darcy)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_ipr_vogel(
        reservoir_pressure_psi: float,
        bubble_point_psi: float,
        productivity_index_above_pb: float,
        num_points: int = 20
    ) -> Dict[str, Any]:
        """
        Vogel (1968) IPR for solution-gas drive wells (oil below bubble point).

        q/q_max = 1 - 0.2*(Pwf/Pr) - 0.8*(Pwf/Pr)^2

        If Pr > Pb: composite IPR — Darcy above Pb, Vogel below.

        Args:
            reservoir_pressure_psi: average reservoir pressure (psi)
            bubble_point_psi: bubble point pressure (psi)
            productivity_index_above_pb: PI above bubble point (STB/d/psi)
            num_points: number of IPR curve points

        Returns:
            Dict with Pwf[], q[], AOF, q_at_pb, composite flag
        """
        Pr = reservoir_pressure_psi
        Pb = bubble_point_psi
        PI = productivity_index_above_pb

        if Pr <= 0 or PI <= 0:
            return {"error": "Reservoir pressure and PI must be > 0",
                    "Pwf_psi": [], "q_oil_stbd": [], "AOF_stbd": 0.0}

        # Determine if composite (Pr > Pb) or pure Vogel (Pr <= Pb)
        is_composite = Pr > Pb

        if is_composite:
            # Flow rate at bubble point (Darcy: q_b = PI * (Pr - Pb))
            q_b = PI * (Pr - Pb)
            # Vogel q_max below bubble point
            q_v_max = q_b + PI * Pb / 1.8
            AOF = q_v_max
        else:
            # Pure Vogel: q_max = PI * Pr / 1.8
            q_b = 0.0
            q_v_max = PI * Pr / 1.8
            AOF = q_v_max

        # Generate IPR curve
        Pwf_list = []
        q_list = []
        step = Pr / max(num_points, 2)
        for i in range(num_points + 1):
            Pwf = Pr - i * step
            Pwf = max(0.0, Pwf)

            if is_composite and Pwf >= Pb:
                # Darcy region (above bubble point)
                q = PI * (Pr - Pwf)
            else:
                # Vogel region (below bubble point)
                if is_composite:
                    # Composite: q = q_b + (q_v_max - q_b)*[1 - 0.2*(Pwf/Pb) - 0.8*(Pwf/Pb)^2]
                    ratio = Pwf / Pb if Pb > 0 else 0.0
                    q = q_b + (q_v_max - q_b) * (1.0 - 0.2 * ratio - 0.8 * ratio ** 2)
                else:
                    # Pure Vogel
                    ratio = Pwf / Pr if Pr > 0 else 0.0
                    q = q_v_max * (1.0 - 0.2 * ratio - 0.8 * ratio ** 2)

            Pwf_list.append(round(Pwf, 1))
            q_list.append(round(max(0.0, q), 2))

        return {
            "Pwf_psi": Pwf_list,
            "q_oil_stbd": q_list,
            "AOF_stbd": round(AOF, 2),
            "q_at_bubble_point_stbd": round(q_b, 2),
            "reservoir_pressure_psi": round(Pr, 1),
            "bubble_point_psi": round(Pb, 1),
            "productivity_index": round(PI, 4),
            "is_composite": is_composite,
            "method": "vogel_composite" if is_composite else "vogel_pure",
        }

    @staticmethod
    def calculate_ipr_fetkovich(
        reservoir_pressure_psi: float,
        C_coefficient: float,
        n_exponent: float = 0.8,
        num_points: int = 20
    ) -> Dict[str, Any]:
        """
        Fetkovich (1973) IPR for gas and gas-condensate wells.

        q = C × (Pr² - Pwf²)^n

        Args:
            reservoir_pressure_psi: average reservoir pressure (psi)
            C_coefficient: back-pressure coefficient (Mscf/d/psi^2n)
            n_exponent: deliverability exponent (0.5-1.0)
            num_points: number of IPR curve points

        Returns:
            Dict with Pwf[], q_gas[], AOF
        """
        Pr = reservoir_pressure_psi
        C = C_coefficient
        n = max(0.5, min(n_exponent, 1.0))

        if Pr <= 0 or C <= 0:
            return {"error": "Reservoir pressure and C must be > 0",
                    "Pwf_psi": [], "q_gas_mscfd": [], "AOF_mscfd": 0.0}

        # AOF: q at Pwf=0
        AOF = C * (Pr ** 2) ** n

        Pwf_list = []
        q_list = []
        step = Pr / max(num_points, 2)
        for i in range(num_points + 1):
            Pwf = Pr - i * step
            Pwf = max(0.0, Pwf)
            delta_p2 = Pr ** 2 - Pwf ** 2
            delta_p2 = max(0.0, delta_p2)
            q = C * delta_p2 ** n
            Pwf_list.append(round(Pwf, 1))
            q_list.append(round(q, 2))

        return {
            "Pwf_psi": Pwf_list,
            "q_gas_mscfd": q_list,
            "AOF_mscfd": round(AOF, 2),
            "reservoir_pressure_psi": round(Pr, 1),
            "C_coefficient": C,
            "n_exponent": round(n, 3),
            "method": "fetkovich",
        }

    @staticmethod
    def calculate_ipr_darcy(
        permeability_md: float,
        net_pay_ft: float,
        Bo: float,
        mu_oil_cp: float,
        reservoir_pressure_psi: float,
        wellbore_radius_ft: float = 0.354,
        drainage_radius_ft: float = 660.0,
        skin: float = 0.0,
        num_points: int = 20
    ) -> Dict[str, Any]:
        """
        Darcy straight-line IPR for single-phase oil above bubble point.

        q = kh(Pr-Pwf) / [141.2 × Bo × mu × (ln(re/rw) + S)]

        Args:
            permeability_md: formation permeability (mD)
            net_pay_ft: net formation thickness (ft)
            Bo: oil formation volume factor (RB/STB)
            mu_oil_cp: oil viscosity (cp)
            reservoir_pressure_psi: reservoir pressure (psi)
            wellbore_radius_ft: wellbore radius (ft)
            drainage_radius_ft: drainage radius (ft)
            skin: total skin factor
            num_points: number of IPR curve points

        Returns:
            Dict with Pwf[], q[], PI, AOF
        """
        k = permeability_md
        h = net_pay_ft
        Pr = reservoir_pressure_psi
        rw = wellbore_radius_ft
        re = drainage_radius_ft

        if k <= 0 or h <= 0 or Bo <= 0 or mu_oil_cp <= 0 or Pr <= 0 or rw <= 0 or re <= rw:
            return {"error": "Invalid input parameters",
                    "Pwf_psi": [], "q_oil_stbd": [], "PI_stbd_psi": 0.0, "AOF_stbd": 0.0}

        ln_term = math.log(re / rw) + skin
        if ln_term <= 0:
            ln_term = 0.1  # Guard for very negative skin

        PI = k * h / (141.2 * Bo * mu_oil_cp * ln_term)
        AOF = PI * Pr

        Pwf_list = []
        q_list = []
        step = Pr / max(num_points, 2)
        for i in range(num_points + 1):
            Pwf = Pr - i * step
            Pwf = max(0.0, Pwf)
            q = PI * (Pr - Pwf)
            Pwf_list.append(round(Pwf, 1))
            q_list.append(round(max(0.0, q), 2))

        return {
            "Pwf_psi": Pwf_list,
            "q_oil_stbd": q_list,
            "PI_stbd_psi": round(PI, 4),
            "AOF_stbd": round(AOF, 2),
            "reservoir_pressure_psi": round(Pr, 1),
            "permeability_md": k,
            "net_pay_ft": h,
            "skin": round(skin, 2),
            "method": "darcy_linear",
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: VLP Beggs & Brill + Nodal Analysis
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_vlp_beggs_brill(
        tubing_id_in: float,
        well_depth_ft: float,
        wellhead_pressure_psi: float,
        oil_rate_stbd: float,
        water_cut: float = 0.0,
        glr_scf_stb: float = 500.0,
        oil_api: float = 35.0,
        gas_sg: float = 0.65,
        water_sg: float = 1.07,
        surface_temp_f: float = 100.0,
        bht_f: float = 200.0,
        num_points: int = 20,
        inclination_deg: float = 0.0
    ) -> Dict[str, Any]:
        """
        Simplified Beggs & Brill (1973) VLP for multiphase tubing flow.

        Calculates Pwf required at bottom for a given wellhead pressure and rate.
        dP/dz = (dP/dz)_gravity + (dP/dz)_friction

        Args:
            tubing_id_in: tubing inner diameter (inches)
            well_depth_ft: measured depth of tubing (ft)
            wellhead_pressure_psi: flowing wellhead pressure (psi)
            oil_rate_stbd: oil rate (STB/d)
            water_cut: water fraction (0-1)
            glr_scf_stb: gas-liquid ratio (scf/STB)
            oil_api: oil API gravity
            gas_sg: gas specific gravity (air=1)
            surface_temp_f: surface temperature (°F)
            bht_f: bottomhole temperature (°F)
            num_points: number of depth increments
            inclination_deg: well inclination from vertical (degrees)

        Returns:
            Dict with Pwf required, pressure profile, flow regime
        """
        d = tubing_id_in / 12.0  # feet
        A = math.pi * d ** 2 / 4.0  # flow area ft²
        L = well_depth_ft
        Pwh = wellhead_pressure_psi

        if d <= 0 or L <= 0 or oil_rate_stbd < 0:
            return {"error": "Invalid tubing geometry or rate",
                    "Pwf_required_psi": 0.0}

        if oil_rate_stbd == 0:
            # Static: Pwf = Pwh + hydrostatic
            rho_oil = 141.5 / (131.5 + oil_api) * 62.4  # lb/ft³ approx
            rho_water = water_sg * 62.4
            rho_liq = rho_oil * (1.0 - water_cut) + rho_water * water_cut
            hydrostatic = rho_liq * L * math.cos(math.radians(inclination_deg)) / 144.0
            return {
                "Pwf_required_psi": round(Pwh + hydrostatic, 1),
                "pressure_profile": [],
                "dominant_flow_regime": "static",
                "method": "beggs_brill_simplified",
            }

        # Oil properties (simple correlations)
        gamma_o = 141.5 / (131.5 + oil_api)  # oil SG
        rho_oil_sc = gamma_o * 62.4  # lb/ft³ at SC

        # Solution GOR (Standing correlation, simplified)
        # Rs = gas_sg * [(P/18.2 + 1.4) * 10^(0.0125*API - 0.00091*T)]^1.2048
        # We'll use a simpler approach: assume Rs proportional to pressure

        # Liquid rate
        q_liquid_stbd = oil_rate_stbd / (1.0 - water_cut) if water_cut < 1.0 else oil_rate_stbd
        q_oil = oil_rate_stbd
        q_water = q_liquid_stbd * water_cut

        # March down the tubing in increments
        dL = L / max(num_points, 2)
        P = Pwh
        cos_theta = math.cos(math.radians(inclination_deg))

        profile = [{"depth_ft": 0.0, "pressure_psi": round(P, 1)}]
        regime_counts = {"segregated": 0, "intermittent": 0, "distributed": 0, "transition": 0}

        for i in range(1, num_points + 1):
            depth = i * dL
            # Local temperature
            T_local = surface_temp_f + (bht_f - surface_temp_f) * (depth / L)
            T_R = T_local + 460.0

            # Approximate Rs at local P (Standing simplified)
            Rs = gas_sg * ((P / 18.2 + 1.4) * 10 ** (0.0125 * oil_api - 0.00091 * T_local)) ** 1.2048
            Rs = min(Rs, glr_scf_stb)  # Can't exceed total GLR

            # Free gas rate
            free_gas_glr = max(0.0, glr_scf_stb - Rs)

            # Oil formation volume factor Bo (Standing)
            Bo = 0.972 + 0.000147 * (Rs * (gas_sg / gamma_o) ** 0.5 + 1.25 * T_local) ** 1.175
            Bo = max(1.0, Bo)

            # Gas Z factor (simplified: Z ~ 1 at low P, use approx)
            Ppc = 677 + 15 * gas_sg - 37.5 * gas_sg ** 2
            Tpc = 168 + 325 * gas_sg - 12.5 * gas_sg ** 2
            Ppr = P / Ppc if Ppc > 0 else 1.0
            Tpr = T_R / Tpc if Tpc > 0 else 1.5
            Z = 1.0 - 3.52 * Ppr / (10 ** (0.9813 * Tpr)) + 0.274 * Ppr ** 2 / (10 ** (0.8157 * Tpr))
            Z = max(0.3, min(Z, 1.5))

            # In-situ velocities
            # Oil superficial velocity
            v_sl = (5.615 * q_oil * Bo + 5.615 * q_water * 1.0) / (86400.0 * A)  # ft/s
            # Gas superficial velocity
            if P > 0:
                Bg = 0.0283 * Z * T_R / P  # res ft³/scf
            else:
                Bg = 0.05
            v_sg = (q_oil * free_gas_glr * Bg) / (86400.0 * A)  # ft/s
            v_m = v_sl + v_sg  # mixture velocity

            if v_m <= 0:
                v_m = 0.001

            # Liquid holdup: Beggs & Brill
            lambda_L = v_sl / v_m if v_m > 0 else 1.0
            lambda_L = max(0.01, min(lambda_L, 1.0))

            # Froude number
            N_FR = v_m ** 2 / (32.174 * d) if d > 0 else 0

            # Flow pattern boundaries (Beggs & Brill)
            L1 = 316 * lambda_L ** 0.302
            L2 = 0.0009252 * lambda_L ** (-2.4684)
            L3 = 0.10 * lambda_L ** (-1.4516)
            L4 = 0.5 * lambda_L ** (-6.738)

            # Determine flow pattern
            if lambda_L < 0.01 and N_FR < L1:
                pattern = "segregated"
            elif lambda_L >= 0.01 and N_FR < L2:
                pattern = "segregated"
            elif lambda_L >= 0.01 and L2 <= N_FR <= L3:
                pattern = "transition"
            elif (0.01 <= lambda_L < 0.4 and L3 < N_FR <= L1) or (lambda_L >= 0.4 and L3 < N_FR <= L4):
                pattern = "intermittent"
            else:
                pattern = "distributed"

            regime_counts[pattern] = regime_counts.get(pattern, 0) + 1

            # Liquid holdup (horizontal) — Beggs & Brill
            if pattern == "segregated":
                a_bb, b_bb, c_bb = 0.980, 0.4846, 0.0868
            elif pattern == "intermittent":
                a_bb, b_bb, c_bb = 0.845, 0.5351, 0.0173
            elif pattern == "distributed":
                a_bb, b_bb, c_bb = 1.065, 0.5824, 0.0609
            else:
                a_bb, b_bb, c_bb = 0.920, 0.5100, 0.0500

            HL_0 = a_bb * lambda_L ** b_bb / (N_FR ** c_bb) if N_FR > 0 else lambda_L
            HL_0 = max(lambda_L, min(HL_0, 1.0))

            # Inclination correction
            inc_rad = math.radians(inclination_deg)
            NLv = 1.938 * v_sl * (rho_oil_sc / (72.0 * max(0.001, 72.0 - 60.0))) ** 0.25  # simplified
            C_factor = max(0.0, (1.0 - lambda_L) * math.log(
                max(1e-6, 0.011 * NLv ** 0.5 * lambda_L ** 0.2 * HL_0 ** 0.8)))

            psi_factor = 1.0 + C_factor * (math.sin(1.8 * inc_rad) - 0.333 * math.sin(1.8 * inc_rad) ** 3)
            HL = HL_0 * psi_factor
            HL = max(0.01, min(HL, 1.0))

            # Mixture density
            rho_l = rho_oil_sc * (1.0 - water_cut) + water_sg * 62.4 * water_cut
            rho_g = gas_sg * 28.97 * P / (10.73 * T_R * Z) if (T_R * Z) > 0 else 0.1
            rho_m = rho_l * HL + rho_g * (1.0 - HL)

            # Gravity pressure gradient (psi/ft)
            dp_dz_grav = rho_m * cos_theta / 144.0

            # Friction pressure gradient
            # Two-phase friction factor (Beggs & Brill)
            Re_ns = 1488.0 * rho_m * v_m * d / max(0.01, 1.0)  # simplified mu ~ 1 cp
            if Re_ns <= 0:
                f_ns = 0.01
            else:
                # Moody approximation
                f_ns = 0.0056 + 0.5 / Re_ns ** 0.32

            # Normalize friction factor for two-phase
            y_factor = lambda_L / (HL ** 2) if HL > 0 else 1.0
            if 1.0 < y_factor < 1.2:
                s_factor = math.log(2.2 * y_factor - 1.2)
            elif y_factor >= 1.2:
                s_factor = math.log(y_factor) / (-0.0523 + 3.182 * math.log(y_factor) - 0.8725 * math.log(y_factor) ** 2 + 0.01853 * math.log(y_factor) ** 4) if math.log(y_factor) != 0 else 0
            else:
                s_factor = 0.0

            f_tp = f_ns * math.exp(s_factor)

            dp_dz_fric = f_tp * rho_m * v_m ** 2 / (2.0 * 32.174 * d * 144.0) if d > 0 else 0

            # Total dp/dz
            dp_dz = dp_dz_grav + dp_dz_fric
            P += dp_dz * dL
            P = max(0.0, P)

            profile.append({"depth_ft": round(depth, 1), "pressure_psi": round(P, 1)})

        # Dominant flow regime
        dominant = max(regime_counts, key=regime_counts.get)

        return {
            "Pwf_required_psi": round(P, 1),
            "wellhead_pressure_psi": round(Pwh, 1),
            "pressure_profile": profile,
            "dominant_flow_regime": dominant,
            "flow_regime_distribution": regime_counts,
            "method": "beggs_brill_simplified",
            "parameters": {
                "tubing_id_in": tubing_id_in,
                "well_depth_ft": well_depth_ft,
                "oil_rate_stbd": oil_rate_stbd,
                "water_cut": water_cut,
                "glr_scf_stb": glr_scf_stb,
                "oil_api": oil_api,
            }
        }

    @staticmethod
    def calculate_nodal_analysis(
        ipr_Pwf: List[float],
        ipr_q: List[float],
        vlp_q_range: List[float],
        vlp_Pwf: List[float]
    ) -> Dict[str, Any]:
        """
        Find operating point at IPR-VLP intersection (nodal analysis at BH node).

        Interpolates both curves and finds intersection point.

        Args:
            ipr_Pwf: IPR Pwf values (psi), decreasing order
            ipr_q: IPR flow rates (STB/d), increasing with decreasing Pwf
            vlp_q_range: VLP flow rates (STB/d)
            vlp_Pwf: VLP Pwf required at each rate (psi)

        Returns:
            Dict with operating_point_q, operating_point_Pwf, stable flag
        """
        if not ipr_Pwf or not ipr_q or not vlp_q_range or not vlp_Pwf:
            return {"error": "Empty curve data",
                    "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

        if len(ipr_Pwf) != len(ipr_q) or len(vlp_q_range) != len(vlp_Pwf):
            return {"error": "Curve arrays must have equal length",
                    "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

        # Build q→Pwf functions by linear interpolation
        # IPR: sort by q ascending
        ipr_pairs = sorted(zip(ipr_q, ipr_Pwf), key=lambda x: x[0])
        # VLP: sort by q ascending
        vlp_pairs = sorted(zip(vlp_q_range, vlp_Pwf), key=lambda x: x[0])

        def _interp(pairs, q_val):
            """Linear interpolation in list of (q, Pwf) pairs."""
            if not pairs:
                return None
            if q_val <= pairs[0][0]:
                return pairs[0][1]
            if q_val >= pairs[-1][0]:
                return pairs[-1][1]
            for j in range(len(pairs) - 1):
                q1, p1 = pairs[j]
                q2, p2 = pairs[j + 1]
                if q1 <= q_val <= q2:
                    if q2 == q1:
                        return p1
                    frac = (q_val - q1) / (q2 - q1)
                    return p1 + frac * (p2 - p1)
            return pairs[-1][1]

        # Scan for intersection: find q where IPR_Pwf ≈ VLP_Pwf
        q_min = max(ipr_pairs[0][0], vlp_pairs[0][0])
        q_max = min(ipr_pairs[-1][0], vlp_pairs[-1][0])

        if q_max <= q_min:
            return {"error": "No overlapping rate range",
                    "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

        best_q = 0.0
        best_Pwf = 0.0
        best_diff = 1e12
        num_scan = 200

        for i in range(num_scan + 1):
            q = q_min + (q_max - q_min) * i / num_scan
            Pwf_ipr = _interp(ipr_pairs, q)
            Pwf_vlp = _interp(vlp_pairs, q)
            if Pwf_ipr is None or Pwf_vlp is None:
                continue
            diff = abs(Pwf_ipr - Pwf_vlp)
            if diff < best_diff:
                best_diff = diff
                best_q = q
                best_Pwf = (Pwf_ipr + Pwf_vlp) / 2.0

        # Check stability: at operating point, slope of VLP > slope of IPR
        # (VLP rising, IPR falling with q — standard stable condition)
        dq = max(1.0, best_q * 0.01)
        Pwf_ipr_lo = _interp(ipr_pairs, best_q - dq)
        Pwf_ipr_hi = _interp(ipr_pairs, best_q + dq)
        Pwf_vlp_lo = _interp(vlp_pairs, best_q - dq)
        Pwf_vlp_hi = _interp(vlp_pairs, best_q + dq)

        stable = True
        if Pwf_ipr_lo is not None and Pwf_ipr_hi is not None and Pwf_vlp_lo is not None and Pwf_vlp_hi is not None:
            slope_ipr = (Pwf_ipr_hi - Pwf_ipr_lo) / (2 * dq) if dq > 0 else 0
            slope_vlp = (Pwf_vlp_hi - Pwf_vlp_lo) / (2 * dq) if dq > 0 else 0
            # For stability: VLP slope > IPR slope (IPR falls, VLP rises)
            stable = slope_vlp > slope_ipr

        return {
            "operating_point_q": round(best_q, 2),
            "operating_point_Pwf_psi": round(best_Pwf, 1),
            "intersection_error_psi": round(best_diff, 2),
            "stable": stable,
            "q_range_min": round(q_min, 2),
            "q_range_max": round(q_max, 2),
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Alternative Fracture Gradient Methods
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_fracture_gradient_daines(
        depth_tvd_ft: float,
        pore_pressure_psi: float,
        overburden_stress_psi: float,
        poisson_ratio: float = 0.25,
        tectonic_stress_psi: float = 0.0,
        superimposed_tectonic_psi: float = 0.0
    ) -> Dict[str, Any]:
        """
        Daines (1982) fracture gradient with explicit tectonic stress correction.

        Fg = (nu/(1-nu)) × (sigma_ob - Pp)/D + Pp/D + sigma_tec/D + sigma_super/D

        Daines improves on Eaton by adding a superimposed tectonic stress
        calibrated from LOT/FIT data in the field.

        Args:
            depth_tvd_ft: true vertical depth (ft)
            pore_pressure_psi: pore pressure (psi)
            overburden_stress_psi: overburden stress (psi)
            poisson_ratio: Poisson's ratio
            tectonic_stress_psi: primary tectonic stress (psi)
            superimposed_tectonic_psi: superimposed tectonic stress from LOT calibration (psi)

        Returns:
            Dict with fracture gradient, comparison with Eaton
        """
        if depth_tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        nu = poisson_ratio
        stress_ratio = nu / (1.0 - nu)

        # Daines = Eaton + superimposed tectonic
        matrix_stress = stress_ratio * (overburden_stress_psi - pore_pressure_psi)
        frac_pressure = pore_pressure_psi + matrix_stress + tectonic_stress_psi + superimposed_tectonic_psi

        frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
        frac_gradient_ppg = frac_gradient_psi_ft / 0.052

        # Eaton baseline for comparison (no superimposed)
        frac_eaton = pore_pressure_psi + matrix_stress + tectonic_stress_psi
        eaton_ppg = (frac_eaton / depth_tvd_ft) / 0.052

        return {
            "fracture_pressure_psi": round(frac_pressure, 1),
            "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
            "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
            "eaton_baseline_ppg": round(eaton_ppg, 2),
            "tectonic_correction_ppg": round(frac_gradient_ppg - eaton_ppg, 2),
            "superimposed_tectonic_psi": round(superimposed_tectonic_psi, 1),
            "poisson_ratio": poisson_ratio,
            "method": "daines_1982",
        }

    @staticmethod
    def calculate_fracture_gradient_matthews_kelly(
        depth_tvd_ft: float,
        pore_pressure_psi: float,
        overburden_stress_psi: float,
        Ki: float = 0.0,
        depth_normal_psi_ft: float = 0.465
    ) -> Dict[str, Any]:
        """
        Matthews & Kelly (1967) fracture gradient using effective stress ratio Ki.

        Fg = Ki × (sigma_ob - Pp)/D + Pp/D

        Ki is empirically determined per geological province from LOT data.
        If Ki=0, it is estimated from depth (Gulf Coast correlation).

        Args:
            depth_tvd_ft: true vertical depth (ft)
            pore_pressure_psi: pore pressure (psi)
            overburden_stress_psi: overburden stress (psi)
            Ki: effective stress coefficient (0.3-0.9 typical). 0 = auto-estimate.
            depth_normal_psi_ft: normal pore pressure gradient (psi/ft)

        Returns:
            Dict with fracture gradient, Ki used
        """
        if depth_tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        # Auto-estimate Ki from depth (Gulf Coast correlation)
        if Ki <= 0:
            # Empirical: Ki increases with depth (compaction effect)
            # Shallow (<4000): Ki~0.4, Medium (4000-10000): Ki~0.5-0.7, Deep (>10000): Ki~0.7-0.85
            depth_equiv = depth_tvd_ft * depth_normal_psi_ft / max(0.001, pore_pressure_psi / depth_tvd_ft)
            if depth_equiv < 4000:
                Ki = 0.40 + 0.10 * (depth_equiv / 4000)
            elif depth_equiv < 10000:
                Ki = 0.50 + 0.20 * ((depth_equiv - 4000) / 6000)
            else:
                Ki = 0.70 + 0.15 * min(1.0, (depth_equiv - 10000) / 10000)
            Ki = max(0.3, min(Ki, 0.95))

        # Matthews-Kelly equation
        sigma_eff = overburden_stress_psi - pore_pressure_psi
        frac_pressure = Ki * sigma_eff + pore_pressure_psi

        frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
        frac_gradient_ppg = frac_gradient_psi_ft / 0.052

        return {
            "fracture_pressure_psi": round(frac_pressure, 1),
            "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
            "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
            "Ki_used": round(Ki, 4),
            "effective_stress_psi": round(sigma_eff, 1),
            "method": "matthews_kelly_1967",
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Crushed Zone Skin + Horizontal Productivity
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_crushed_zone_skin(
        formation_permeability_md: float,
        crushed_zone_permeability_md: float,
        crushed_zone_radius_in: float = 0.5,
        perforation_radius_in: float = 0.25
    ) -> Dict[str, Any]:
        """
        Karakas-Tariq 4th skin component: damaged/crushed zone around perforation tunnel.

        S_cz = (k/k_cz - 1) × ln(r_cz / r_perf)

        The crushed zone forms from shaped-charge impact, reducing permeability
        by 50-90% within a thin zone (0.25-1.0 inches) around the tunnel.

        Args:
            formation_permeability_md: undamaged formation k (mD)
            crushed_zone_permeability_md: crushed zone k (mD), typically 10-50% of k
            crushed_zone_radius_in: radius of crushed zone from tunnel center (inches)
            perforation_radius_in: perforation tunnel radius (inches)

        Returns:
            Dict with S_cz, k_ratio, radii used
        """
        k = formation_permeability_md
        k_cz = crushed_zone_permeability_md
        r_cz = crushed_zone_radius_in / 12.0  # ft
        r_p = perforation_radius_in / 12.0  # ft

        if k_cz <= 0 or r_p <= 0 or r_cz <= r_p:
            return {"S_crushed_zone": 0.0, "k_ratio": 1.0,
                    "note": "Invalid inputs — crushed zone skin set to 0"}

        k_ratio = k / k_cz
        if k_ratio <= 1.0:
            # No damage (crushed zone k >= formation k)
            return {"S_crushed_zone": 0.0, "k_ratio": round(k_ratio, 3),
                    "note": "No crushed zone damage"}

        S_cz = (k_ratio - 1.0) * math.log(r_cz / r_p)

        return {
            "S_crushed_zone": round(S_cz, 4),
            "k_ratio": round(k_ratio, 3),
            "k_formation_md": k,
            "k_crushed_zone_md": k_cz,
            "r_crushed_zone_in": crushed_zone_radius_in,
            "r_perforation_in": perforation_radius_in,
            "permeability_reduction_pct": round((1.0 - k_cz / k) * 100, 1),
        }

    @staticmethod
    def calculate_horizontal_productivity(
        horizontal_length_ft: float,
        kh_md: float,
        kv_md: float,
        formation_thickness_ft: float,
        drainage_radius_ft: float = 660.0,
        wellbore_radius_ft: float = 0.354,
        reservoir_pressure_psi: float = 5000.0,
        Pwf_psi: float = 3000.0,
        Bo: float = 1.2,
        mu_oil_cp: float = 1.0,
        skin: float = 0.0
    ) -> Dict[str, Any]:
        """
        Joshi (1991) horizontal well productivity model.

        q_h = kh × h × (Pr - Pwf) / [141.2 × Bo × mu ×
              (ln(a + sqrt(a² - (L/2)²))/(L/2) + (h/L)×ln(h/(2π×rw)))]

        a = (L/2) × [0.5 + sqrt(0.25 + (2re/L)^4)]^0.5

        Args:
            horizontal_length_ft: horizontal section length (ft)
            kh_md: horizontal permeability (mD)
            kv_md: vertical permeability (mD)
            formation_thickness_ft: net pay thickness (ft)
            drainage_radius_ft: drainage radius (ft)
            wellbore_radius_ft: wellbore radius (ft)
            reservoir_pressure_psi: reservoir pressure (psi)
            Pwf_psi: flowing BHP (psi)
            Bo: formation volume factor (RB/STB)
            mu_oil_cp: oil viscosity (cp)
            skin: total skin

        Returns:
            Dict with q_horizontal, PI, equivalent_vertical_wells, productivity_ratio
        """
        Lh = horizontal_length_ft
        h = formation_thickness_ft
        re = drainage_radius_ft
        rw = wellbore_radius_ft
        Pr = reservoir_pressure_psi
        Pwf = Pwf_psi

        if Lh <= 0 or kh_md <= 0 or h <= 0 or Bo <= 0 or mu_oil_cp <= 0 or rw <= 0:
            return {"error": "Invalid input parameters",
                    "q_horizontal_stbd": 0.0, "PI_horizontal": 0.0}

        # Anisotropy ratio
        kv_kh = kv_md / kh_md if kh_md > 0 else 1.0
        beta = math.sqrt(kh_md / kv_md) if kv_md > 0 else 1.0

        # Effective wellbore radius for horizontal well
        rw_eff = rw * (1.0 + beta) / (2.0 * beta) if beta > 0 else rw

        # Joshi's 'a' parameter (half-axis of drainage ellipse)
        ratio_re_L = 2.0 * re / Lh if Lh > 0 else 10.0
        a_param = (Lh / 2.0) * (0.5 + math.sqrt(0.25 + ratio_re_L ** 4)) ** 0.5

        # Horizontal drainage term
        inner_sqrt = a_param ** 2 - (Lh / 2.0) ** 2
        inner_sqrt = max(0.0, inner_sqrt)
        numerator_ln = a_param + math.sqrt(inner_sqrt)
        denominator_ln = Lh / 2.0

        if denominator_ln <= 0 or numerator_ln <= 0:
            return {"error": "Invalid geometry",
                    "q_horizontal_stbd": 0.0, "PI_horizontal": 0.0}

        term_h = math.log(numerator_ln / denominator_ln)

        # Vertical convergence term
        term_v = (h / Lh) * math.log(h / (2.0 * math.pi * rw_eff)) if (Lh > 0 and rw_eff > 0 and h > 0) else 0

        # Total denominator
        total_denom = 141.2 * Bo * mu_oil_cp * (term_h + term_v + skin * h / Lh)
        if total_denom <= 0:
            total_denom = 1.0

        # Horizontal flow rate
        delta_P = Pr - Pwf
        q_h = kh_md * h * delta_P / total_denom
        q_h = max(0.0, q_h)

        # Productivity index
        PI_h = kh_md * h / total_denom if total_denom > 0 else 0

        # Compare with vertical well (Darcy radial)
        ln_re_rw = math.log(re / rw) + skin if (re > rw) else 7.0
        denom_v = 141.2 * Bo * mu_oil_cp * ln_re_rw
        q_v = kh_md * h * delta_P / denom_v if denom_v > 0 else 0
        PI_v = kh_md * h / denom_v if denom_v > 0 else 0

        equiv_verticals = q_h / q_v if q_v > 0 else 0.0
        productivity_ratio = q_h / q_v if q_v > 0 else 0.0

        return {
            "q_horizontal_stbd": round(q_h, 2),
            "q_vertical_stbd": round(q_v, 2),
            "PI_horizontal": round(PI_h, 4),
            "PI_vertical": round(PI_v, 4),
            "equivalent_vertical_wells": round(equiv_verticals, 2),
            "productivity_ratio_h_v": round(productivity_ratio, 3),
            "a_parameter_ft": round(a_param, 1),
            "beta_anisotropy": round(beta, 3),
            "kv_kh_ratio": round(kv_kh, 4),
            "horizontal_length_ft": round(Lh, 1),
            "method": "joshi_1991",
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Expanded Gun Selection from Catalog
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def select_gun_from_catalog(
        casing_id_in: float,
        max_pressure_psi: float = 15000.0,
        max_temperature_f: float = 400.0,
        gun_type_filter: str = "",
        min_penetration_in: float = 0.0,
        target_spf: int = 0,
        conveyed_by: str = ""
    ) -> Dict[str, Any]:
        """
        Select optimal gun from expanded GUN_CATALOG with pressure/temp/type filters.

        Args:
            casing_id_in: casing inner diameter (inches)
            max_pressure_psi: maximum BHP the gun must withstand (psi)
            max_temperature_f: maximum BHT the gun must withstand (°F)
            gun_type_filter: filter by type: "wireline", "tcp", "coiled_tubing", "" = all
            min_penetration_in: minimum required Berea penetration (inches)
            target_spf: desired SPF (0 = any)
            conveyed_by: preferred conveyance method (maps to gun_type)

        Returns:
            Dict with ranked compatible guns, best selection, filters applied
        """
        catalog = CompletionDesignEngine.GUN_CATALOG
        compatible = []

        # Map conveyed_by to gun_type if specified
        type_filter = gun_type_filter.lower() if gun_type_filter else ""
        if conveyed_by and not type_filter:
            conv_map = {
                "wireline": "wireline", "tubing": "tcp", "tcp": "tcp",
                "coiled_tubing": "coiled_tubing", "ct": "coiled_tubing"
            }
            type_filter = conv_map.get(conveyed_by.lower(), "")

        for gun in catalog:
            # Casing clearance check
            clearance = casing_id_in - gun["od_in"]
            if clearance < 0.25:
                continue

            # Pressure rating check
            if gun["max_pressure_psi"] < max_pressure_psi:
                continue

            # Temperature rating check
            if gun["max_temp_f"] < max_temperature_f:
                continue

            # Gun type filter
            if type_filter and gun["gun_type"] != type_filter:
                continue

            # Min penetration filter
            if min_penetration_in > 0 and gun["penetration_berea_in"] < min_penetration_in:
                continue

            # SPF filter
            if target_spf > 0 and gun["spf"] != target_spf:
                continue

            # Score: balance penetration, clearance, SPF
            score = (gun["penetration_berea_in"] * 0.4
                     + gun["spf"] * 0.3
                     + clearance * 0.2
                     + gun["ehd_in"] * 10.0 * 0.1)

            compatible.append({
                "name": gun["name"],
                "od_in": gun["od_in"],
                "gun_type": gun["gun_type"],
                "penetration_berea_in": gun["penetration_berea_in"],
                "ehd_in": gun["ehd_in"],
                "spf": gun["spf"],
                "phasing": gun["phasing"],
                "max_pressure_psi": gun["max_pressure_psi"],
                "max_temp_f": gun["max_temp_f"],
                "clearance_in": round(clearance, 3),
                "score": round(score, 3),
            })

        compatible.sort(key=lambda g: g["score"], reverse=True)

        return {
            "recommended": compatible[0] if compatible else None,
            "alternatives": compatible[1:5] if len(compatible) > 1 else [],
            "all_compatible": compatible,
            "total_compatible": len(compatible),
            "filters_applied": {
                "casing_id_in": casing_id_in,
                "max_pressure_psi": max_pressure_psi,
                "max_temperature_f": max_temperature_f,
                "gun_type_filter": type_filter or "all",
                "min_penetration_in": min_penetration_in,
                "target_spf": target_spf,
            },
            "catalog_size": len(catalog),
        }
