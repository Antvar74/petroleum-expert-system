"""
Casing Design Calculation Engine

Burst/collapse/tension load profiles, API 5C3 collapse rating (4 zones),
Barlow burst, biaxial correction, triaxial VME, grade selection,
and safety factor verification.

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe (collapse formulas, 4 zones)
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 7
- Barlow's formula: P_burst = 0.875 * 2 * Yp * t / OD
"""
import math
from typing import List, Dict, Any, Optional


class CasingDesignEngine:
    """
    Casing design engine implementing burst, collapse, tension loads,
    API 5C3 ratings, biaxial correction, triaxial VME stress check,
    and automated grade selection. All methods are @staticmethod.
    """

    # ---------------------------------------------------------------
    # Casing Grade Database (API 5CT)
    # ---------------------------------------------------------------
    CASING_GRADES = {
        "J55":  {"yield_psi": 55000,  "tensile_psi": 75000,  "color": "#4CAF50"},
        "K55":  {"yield_psi": 55000,  "tensile_psi": 95000,  "color": "#66BB6A"},
        "L80":  {"yield_psi": 80000,  "tensile_psi": 95000,  "color": "#2196F3"},
        "N80":  {"yield_psi": 80000,  "tensile_psi": 100000, "color": "#42A5F5"},
        "C90":  {"yield_psi": 90000,  "tensile_psi": 100000, "color": "#FF9800"},
        "T95":  {"yield_psi": 95000,  "tensile_psi": 105000, "color": "#FFA726"},
        "C110": {"yield_psi": 110000, "tensile_psi": 120000, "color": "#F44336"},
        "P110": {"yield_psi": 110000, "tensile_psi": 125000, "color": "#EF5350"},
        "Q125": {"yield_psi": 125000, "tensile_psi": 135000, "color": "#9C27B0"},
    }

    # Standard design factors (NORSOK D-010 / operator standards)
    DEFAULT_SF = {
        "burst": 1.10,
        "collapse": 1.00,  # API minimum; many operators use 1.0-1.125
        "tension": 1.60,   # body yield; connections may require 1.8
    }

    # ===================================================================
    # 1. Burst Load Profile
    # ===================================================================
    @staticmethod
    def calculate_burst_load(
        tvd_ft: float,
        mud_weight_ppg: float,
        pore_pressure_ppg: float,
        gas_gradient_psi_ft: float = 0.1,
        cement_top_tvd_ft: float = 0.0,
        cement_density_ppg: float = 16.0,
        num_points: int = 20,
    ) -> Dict[str, Any]:
        """
        Calculate burst load profile vs. depth.

        Design scenario: gas-to-surface (worst case for surface casing)
        - Internal pressure: gas column from TD to surface
        - External pressure (backup): mud/cement column outside

        Burst_load = P_internal - P_external at each depth

        Internal: P_int(z) = P_reservoir - gas_gradient * (TVD - z)
                  P_reservoir = pore_pressure * 0.052 * TVD
        External: P_ext(z) = mud_weight * 0.052 * z  (above cement)
                  P_ext(z) = cement_density * 0.052 * (z - cement_top) + ... (in cement)
        """
        if tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        # Reservoir pressure at TD
        p_reservoir = pore_pressure_ppg * 0.052 * tvd_ft

        profile = []
        step = tvd_ft / max(num_points - 1, 1)

        for i in range(num_points):
            depth = i * step

            # Internal pressure (gas to surface)
            p_internal = p_reservoir - gas_gradient_psi_ft * (tvd_ft - depth)
            p_internal = max(p_internal, 0.0)

            # External pressure (backup)
            if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
                p_external = mud_weight_ppg * 0.052 * depth
            else:
                # Above cement: mud; below cement top: cement
                p_external = (
                    mud_weight_ppg * 0.052 * cement_top_tvd_ft
                    + cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft)
                )

            burst_load = p_internal - p_external

            profile.append({
                "tvd_ft": round(depth, 0),
                "p_internal_psi": round(p_internal, 0),
                "p_external_psi": round(p_external, 0),
                "burst_load_psi": round(burst_load, 0),
            })

        max_burst = max(p["burst_load_psi"] for p in profile)
        max_burst_depth = next(p["tvd_ft"] for p in profile if p["burst_load_psi"] == max_burst)

        return {
            "profile": profile,
            "max_burst_load_psi": round(max_burst, 0),
            "max_burst_depth_ft": round(max_burst_depth, 0),
            "reservoir_pressure_psi": round(p_reservoir, 0),
            "scenario": "Gas to Surface",
        }

    # ===================================================================
    # 2. Collapse Load Profile
    # ===================================================================
    @staticmethod
    def calculate_collapse_load(
        tvd_ft: float,
        mud_weight_ppg: float,
        pore_pressure_ppg: float,
        cement_top_tvd_ft: float = 0.0,
        cement_density_ppg: float = 16.0,
        evacuation_level_ft: float = 0.0,
        num_points: int = 20,
    ) -> Dict[str, Any]:
        """
        Calculate collapse load profile vs. depth.

        Design scenario: full/partial evacuation
        - External pressure: mud/cement column
        - Internal pressure: empty or partially filled casing

        Collapse_load = P_external - P_internal at each depth
        """
        if tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        profile = []
        step = tvd_ft / max(num_points - 1, 1)

        for i in range(num_points):
            depth = i * step

            # External pressure
            if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
                p_external = mud_weight_ppg * 0.052 * depth
            else:
                p_external = (
                    mud_weight_ppg * 0.052 * cement_top_tvd_ft
                    + cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft)
                )

            # Internal pressure (evacuation scenario)
            if depth <= evacuation_level_ft:
                p_internal = 0.0  # empty above fluid level
            else:
                # Below evacuation level: mud weight inside
                p_internal = mud_weight_ppg * 0.052 * (depth - evacuation_level_ft)

            collapse_load = p_external - p_internal

            profile.append({
                "tvd_ft": round(depth, 0),
                "p_external_psi": round(p_external, 0),
                "p_internal_psi": round(p_internal, 0),
                "collapse_load_psi": round(collapse_load, 0),
            })

        max_collapse = max(p["collapse_load_psi"] for p in profile)
        max_collapse_depth = next(p["tvd_ft"] for p in profile if p["collapse_load_psi"] == max_collapse)

        return {
            "profile": profile,
            "max_collapse_load_psi": round(max_collapse, 0),
            "max_collapse_depth_ft": round(max_collapse_depth, 0),
            "scenario": "Full Evacuation" if evacuation_level_ft <= 0 else f"Partial Evacuation to {evacuation_level_ft} ft",
        }

    # ===================================================================
    # 3. Tension Load
    # ===================================================================
    @staticmethod
    def calculate_tension_load(
        casing_weight_ppf: float,
        casing_length_ft: float,
        mud_weight_ppg: float,
        casing_od_in: float,
        casing_id_in: float,
        buoyancy_applied: bool = True,
        shock_load: bool = True,
        bending_load_dls: float = 0.0,
        overpull_lbs: float = 50000.0,
    ) -> Dict[str, Any]:
        """
        Calculate tension load on casing string.

        Components:
        - Weight: W = weight_ppf * length (air weight)
        - Buoyancy factor: BF = 1 - MW/65.4 (steel density 65.4 ppg)
        - Shock load (Lubinski): F_shock = 3200 * W_ppf (for sudden stops)
        - Bending: F_bend = 63 * DLS * OD * W_ppf (API formula)
        - Overpull: additional pull for freeing stuck casing
        """
        # Air weight
        air_weight = casing_weight_ppf * casing_length_ft

        # Buoyancy
        bf = 1.0 - mud_weight_ppg / 65.4 if buoyancy_applied else 1.0
        buoyant_weight = air_weight * bf

        # Shock load (Lubinski approximation: 3200 * ppf)
        shock_lbs = 3200.0 * casing_weight_ppf if shock_load else 0.0

        # Bending load (from dogleg severity)
        bending_lbs = 63.0 * bending_load_dls * casing_od_in * casing_weight_ppf if bending_load_dls > 0 else 0.0

        # Total tension at surface
        total_tension = buoyant_weight + shock_lbs + bending_lbs + overpull_lbs

        # Cross-sectional area
        area_sq_in = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)

        # Axial stress
        axial_stress = total_tension / area_sq_in if area_sq_in > 0 else 0

        return {
            "air_weight_lbs": round(air_weight, 0),
            "buoyancy_factor": round(bf, 4),
            "buoyant_weight_lbs": round(buoyant_weight, 0),
            "shock_load_lbs": round(shock_lbs, 0),
            "bending_load_lbs": round(bending_lbs, 0),
            "overpull_lbs": round(overpull_lbs, 0),
            "total_tension_lbs": round(total_tension, 0),
            "axial_stress_psi": round(axial_stress, 0),
            "cross_section_area_sq_in": round(area_sq_in, 3),
        }

    # ===================================================================
    # 4. Burst Rating — Barlow's Formula
    # ===================================================================
    @staticmethod
    def calculate_burst_rating(
        casing_od_in: float,
        wall_thickness_in: float,
        yield_strength_psi: float,
    ) -> Dict[str, Any]:
        """
        Calculate burst rating using Barlow's formula (API 5C3).

        P_burst = 0.875 * 2 * Yp * t / OD

        The 0.875 factor accounts for 12.5% wall thickness tolerance.
        """
        if casing_od_in <= 0 or wall_thickness_in <= 0:
            return {"error": "Invalid dimensions"}

        p_burst = 0.875 * 2.0 * yield_strength_psi * wall_thickness_in / casing_od_in

        dt_ratio = casing_od_in / wall_thickness_in if wall_thickness_in > 0 else 0

        return {
            "burst_rating_psi": round(p_burst, 0),
            "yield_strength_psi": yield_strength_psi,
            "wall_thickness_in": wall_thickness_in,
            "od_in": casing_od_in,
            "dt_ratio": round(dt_ratio, 2),
        }

    # ===================================================================
    # 5. Collapse Rating — API 5C3 (4 zones)
    # ===================================================================
    @staticmethod
    def calculate_collapse_rating(
        casing_od_in: float,
        wall_thickness_in: float,
        yield_strength_psi: float,
    ) -> Dict[str, Any]:
        """
        Calculate collapse rating per API TR 5C3 (ISO 10400).

        Four collapse regimes based on D/t ratio:
        1. Yield Collapse: low D/t (thick-wall)
        2. Plastic Collapse: intermediate D/t
        3. Transition Collapse: intermediate-high D/t
        4. Elastic Collapse: high D/t (thin-wall)

        Each regime has its own formula with coefficients A, B, C, F, G.
        """
        if casing_od_in <= 0 or wall_thickness_in <= 0:
            return {"error": "Invalid dimensions"}

        dt = casing_od_in / wall_thickness_in
        yp = yield_strength_psi

        # API 5C3 empirical coefficients (functions of yield strength)
        # Approximated from API tables for common grades
        A = 2.8762 + 0.10679e-4 * yp + 0.21301e-10 * yp ** 2 - 0.53132e-16 * yp ** 3
        B = 0.026233 + 0.50609e-6 * yp
        C = -465.93 + 0.030867 * yp - 0.10483e-7 * yp ** 2 + 0.36989e-13 * yp ** 3

        # Transition boundaries (D/t ratios)
        # Yield-Plastic boundary
        try:
            dt_yp = (math.sqrt((A - 2) ** 2 + 8 * (B + C / yp)) + (A - 2)) / (2 * (B + C / yp))
        except (ValueError, ZeroDivisionError):
            dt_yp = 15.0

        # Plastic-Transition boundary
        F = 46.95e6 * (3 * B / A / (2 + B / A)) ** 3
        G = F * B / A

        try:
            dt_pt = yp * (A - F) / (C + yp * (B - G))
        except ZeroDivisionError:
            dt_pt = 25.0

        # Transition-Elastic boundary
        dt_te = 2 + B / A
        try:
            dt_te = 2.0 + yp * (B / A) / (3.0 * B / A / (2 + B / A))
        except ZeroDivisionError:
            dt_te = 30.0

        # Elastic collapse limit (D/t)
        # Ensure boundaries are ordered
        boundaries = sorted([dt_yp, dt_pt, dt_te])

        # Determine collapse zone and calculate rating
        if dt <= boundaries[0]:
            # Zone 1: Yield Collapse
            zone = "Yield"
            p_collapse = 2.0 * yp * ((dt - 1) / dt ** 2)
        elif dt <= boundaries[1]:
            # Zone 2: Plastic Collapse
            zone = "Plastic"
            p_collapse = yp * (A / dt - B) - C
        elif dt <= boundaries[2]:
            # Zone 3: Transition Collapse
            zone = "Transition"
            p_collapse = yp * (F / dt - G)
        else:
            # Zone 4: Elastic Collapse
            zone = "Elastic"
            p_collapse = 46.95e6 / (dt * (dt - 1) ** 2)

        p_collapse = max(p_collapse, 0.0)

        return {
            "collapse_rating_psi": round(p_collapse, 0),
            "collapse_zone": zone,
            "dt_ratio": round(dt, 2),
            "yield_strength_psi": yield_strength_psi,
            "boundaries": {
                "yield_plastic": round(boundaries[0], 2),
                "plastic_transition": round(boundaries[1], 2),
                "transition_elastic": round(boundaries[2], 2),
            },
        }

    # ===================================================================
    # 6. Biaxial Correction (API 5C3 Ellipse)
    # ===================================================================
    @staticmethod
    def calculate_biaxial_correction(
        collapse_rating_psi: float,
        axial_stress_psi: float,
        yield_strength_psi: float,
    ) -> Dict[str, Any]:
        """
        Reduce collapse resistance due to axial tension (API 5C3 ellipse).

        The presence of axial tension reduces the casing's ability to resist
        external pressure (collapse). The API 5C3 biaxial approach uses:

        Yp_effective = Yp * sqrt(1 - 0.75*(Sa/Yp)^2) - 0.5*(Sa/Yp)*Yp

        where Sa = axial stress (positive = tension).
        Then recalculate collapse with Yp_effective.
        """
        if yield_strength_psi <= 0:
            return {"error": "Yield strength must be > 0"}

        sa_ratio = axial_stress_psi / yield_strength_psi

        # Limit ratio to practical range
        sa_ratio = max(min(sa_ratio, 0.99), -0.99)

        # Effective yield strength under biaxial loading
        yp_eff = yield_strength_psi * (
            math.sqrt(1.0 - 0.75 * sa_ratio ** 2) - 0.5 * sa_ratio
        )
        yp_eff = max(yp_eff, 0.0)

        # Reduction factor
        reduction_factor = yp_eff / yield_strength_psi if yield_strength_psi > 0 else 1.0

        # Corrected collapse
        corrected_collapse = collapse_rating_psi * reduction_factor

        return {
            "original_collapse_psi": round(collapse_rating_psi, 0),
            "corrected_collapse_psi": round(corrected_collapse, 0),
            "reduction_factor": round(reduction_factor, 4),
            "effective_yield_psi": round(yp_eff, 0),
            "axial_stress_psi": round(axial_stress_psi, 0),
            "stress_ratio": round(sa_ratio, 4),
        }

    # ===================================================================
    # 7. Triaxial VME Stress Check
    # ===================================================================
    @staticmethod
    def calculate_triaxial_vme(
        axial_stress_psi: float,
        hoop_stress_psi: float,
        radial_stress_psi: float = 0.0,
        shear_stress_psi: float = 0.0,
        yield_strength_psi: float = 80000.0,
        safety_factor: float = 1.25,
    ) -> Dict[str, Any]:
        """
        Triaxial Von Mises Equivalent stress check.

        sigma_vme = sqrt(
            (sigma_a - sigma_h)^2 +
            (sigma_h - sigma_r)^2 +
            (sigma_r - sigma_a)^2 +
            6 * tau^2
        ) / sqrt(2)

        Pass if: sigma_vme < Yp / SF
        """
        sa = axial_stress_psi
        sh = hoop_stress_psi
        sr = radial_stress_psi
        tau = shear_stress_psi

        vme = math.sqrt(
            ((sa - sh) ** 2 + (sh - sr) ** 2 + (sr - sa) ** 2 + 6 * tau ** 2) / 2.0
        )

        allowable = yield_strength_psi / safety_factor
        utilization = vme / allowable if allowable > 0 else 999
        passes = vme < allowable

        status = "PASS" if passes else "FAIL"
        if utilization > 0.9 and passes:
            status = "MARGINAL"

        return {
            "vme_stress_psi": round(vme, 0),
            "allowable_psi": round(allowable, 0),
            "utilization_pct": round(utilization * 100, 1),
            "passes": passes,
            "status": status,
            "yield_strength_psi": yield_strength_psi,
            "safety_factor": safety_factor,
            "stress_components": {
                "axial_psi": round(sa, 0),
                "hoop_psi": round(sh, 0),
                "radial_psi": round(sr, 0),
                "shear_psi": round(tau, 0),
            },
        }

    # ===================================================================
    # 8. Grade Selection
    # ===================================================================
    @staticmethod
    def select_casing_grade(
        required_burst_psi: float,
        required_collapse_psi: float,
        required_tension_lbs: float,
        casing_od_in: float,
        wall_thickness_in: float,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
    ) -> Dict[str, Any]:
        """
        Select optimal casing grade that satisfies all three load criteria.

        Iterates through available grades (lightest/cheapest first) and
        selects the first grade where all safety factors are met.
        """
        if casing_od_in <= 0 or wall_thickness_in <= 0:
            return {"error": "Invalid casing dimensions"}

        area = math.pi / 4.0 * (casing_od_in ** 2 - (casing_od_in - 2 * wall_thickness_in) ** 2)

        candidates = []
        # Sort grades by yield strength (ascending = cheapest first)
        sorted_grades = sorted(
            CasingDesignEngine.CASING_GRADES.items(),
            key=lambda x: x[1]["yield_psi"]
        )

        for grade_name, grade_info in sorted_grades:
            yp = grade_info["yield_psi"]

            # Burst rating (Barlow)
            burst_rating = 0.875 * 2.0 * yp * wall_thickness_in / casing_od_in

            # Collapse rating (simplified — yield collapse for initial screening)
            dt = casing_od_in / wall_thickness_in
            collapse_result = CasingDesignEngine.calculate_collapse_rating(
                casing_od_in, wall_thickness_in, yp
            )
            collapse_rating = collapse_result.get("collapse_rating_psi", 0)

            # Tension rating (body yield)
            tension_rating = yp * area

            # Safety factors
            sf_b = burst_rating / required_burst_psi if required_burst_psi > 0 else 999
            sf_c = collapse_rating / required_collapse_psi if required_collapse_psi > 0 else 999
            sf_t = tension_rating / required_tension_lbs if required_tension_lbs > 0 else 999

            passes_burst = sf_b >= sf_burst
            passes_collapse = sf_c >= sf_collapse
            passes_tension = sf_t >= sf_tension
            passes_all = passes_burst and passes_collapse and passes_tension

            candidates.append({
                "grade": grade_name,
                "yield_psi": yp,
                "burst_rating_psi": round(burst_rating, 0),
                "collapse_rating_psi": round(collapse_rating, 0),
                "collapse_zone": collapse_result.get("collapse_zone", ""),
                "tension_rating_lbs": round(tension_rating, 0),
                "sf_burst": round(sf_b, 2),
                "sf_collapse": round(sf_c, 2),
                "sf_tension": round(sf_t, 2),
                "passes_burst": passes_burst,
                "passes_collapse": passes_collapse,
                "passes_tension": passes_tension,
                "passes_all": passes_all,
                "color": grade_info["color"],
            })

        # Find optimal (first that passes all)
        selected = next((c for c in candidates if c["passes_all"]), None)

        return {
            "selected_grade": selected["grade"] if selected else "None — no grade satisfies all criteria",
            "selected_details": selected,
            "all_candidates": candidates,
            "requirements": {
                "burst_psi": round(required_burst_psi, 0),
                "collapse_psi": round(required_collapse_psi, 0),
                "tension_lbs": round(required_tension_lbs, 0),
                "sf_burst": sf_burst,
                "sf_collapse": sf_collapse,
                "sf_tension": sf_tension,
            },
        }

    # ===================================================================
    # 9. Safety Factors Summary
    # ===================================================================
    @staticmethod
    def calculate_safety_factors(
        burst_load_psi: float,
        burst_rating_psi: float,
        collapse_load_psi: float,
        collapse_rating_psi: float,
        tension_load_lbs: float,
        tension_rating_lbs: float,
        sf_burst_min: float = 1.10,
        sf_collapse_min: float = 1.00,
        sf_tension_min: float = 1.60,
    ) -> Dict[str, Any]:
        """
        Calculate and evaluate safety factors for burst, collapse, and tension.
        """
        sf_burst = burst_rating_psi / burst_load_psi if burst_load_psi > 0 else 999.0
        sf_collapse = collapse_rating_psi / collapse_load_psi if collapse_load_psi > 0 else 999.0
        sf_tension = tension_rating_lbs / tension_load_lbs if tension_load_lbs > 0 else 999.0

        results = {
            "burst": {
                "load_psi": round(burst_load_psi, 0),
                "rating_psi": round(burst_rating_psi, 0),
                "safety_factor": round(sf_burst, 2),
                "minimum_sf": sf_burst_min,
                "passes": sf_burst >= sf_burst_min,
                "status": "PASS" if sf_burst >= sf_burst_min else "FAIL",
                "margin_pct": round((sf_burst / sf_burst_min - 1) * 100, 1),
            },
            "collapse": {
                "load_psi": round(collapse_load_psi, 0),
                "rating_psi": round(collapse_rating_psi, 0),
                "safety_factor": round(sf_collapse, 2),
                "minimum_sf": sf_collapse_min,
                "passes": sf_collapse >= sf_collapse_min,
                "status": "PASS" if sf_collapse >= sf_collapse_min else "FAIL",
                "margin_pct": round((sf_collapse / sf_collapse_min - 1) * 100, 1),
            },
            "tension": {
                "load_lbs": round(tension_load_lbs, 0),
                "rating_lbs": round(tension_rating_lbs, 0),
                "safety_factor": round(sf_tension, 2),
                "minimum_sf": sf_tension_min,
                "passes": sf_tension >= sf_tension_min,
                "status": "PASS" if sf_tension >= sf_tension_min else "FAIL",
                "margin_pct": round((sf_tension / sf_tension_min - 1) * 100, 1),
            },
        }

        all_pass = all(r["passes"] for r in results.values())
        governing = min(results.items(), key=lambda x: x[1]["safety_factor"])

        return {
            "results": results,
            "all_pass": all_pass,
            "governing_criterion": governing[0],
            "governing_sf": governing[1]["safety_factor"],
            "overall_status": "ALL PASS" if all_pass else "DESIGN FAILURE",
        }

    # ===================================================================
    # MASTER: Full Casing Design
    # ===================================================================
    @staticmethod
    def calculate_full_casing_design(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        wall_thickness_in: float = 0.472,
        casing_weight_ppf: float = 47.0,
        casing_length_ft: float = 10000.0,
        tvd_ft: float = 9500.0,
        mud_weight_ppg: float = 10.5,
        pore_pressure_ppg: float = 9.0,
        fracture_gradient_ppg: float = 16.5,
        gas_gradient_psi_ft: float = 0.1,
        cement_top_tvd_ft: float = 5000.0,
        cement_density_ppg: float = 16.0,
        bending_dls: float = 3.0,
        overpull_lbs: float = 50000.0,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
    ) -> Dict[str, Any]:
        """
        Run complete casing design analysis: burst/collapse/tension loads,
        ratings, biaxial correction, triaxial VME, grade selection,
        and safety factor verification.
        """
        # 1. Burst load
        burst_load = CasingDesignEngine.calculate_burst_load(
            tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
            gas_gradient_psi_ft=gas_gradient_psi_ft,
            cement_top_tvd_ft=cement_top_tvd_ft,
            cement_density_ppg=cement_density_ppg,
        )

        # 2. Collapse load (full evacuation)
        collapse_load = CasingDesignEngine.calculate_collapse_load(
            tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
            cement_top_tvd_ft=cement_top_tvd_ft,
            cement_density_ppg=cement_density_ppg,
            evacuation_level_ft=0.0,
        )

        # 3. Tension load
        tension_load = CasingDesignEngine.calculate_tension_load(
            casing_weight_ppf=casing_weight_ppf,
            casing_length_ft=casing_length_ft,
            mud_weight_ppg=mud_weight_ppg,
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            bending_load_dls=bending_dls, overpull_lbs=overpull_lbs,
        )

        # 4. Grade selection
        max_burst = burst_load.get("max_burst_load_psi", 0)
        max_collapse = collapse_load.get("max_collapse_load_psi", 0)
        total_tension = tension_load.get("total_tension_lbs", 0)

        grade_selection = CasingDesignEngine.select_casing_grade(
            required_burst_psi=max_burst,
            required_collapse_psi=max_collapse,
            required_tension_lbs=total_tension,
            casing_od_in=casing_od_in,
            wall_thickness_in=wall_thickness_in,
            sf_burst=sf_burst, sf_collapse=sf_collapse, sf_tension=sf_tension,
        )

        # Get selected grade's yield
        selected = grade_selection.get("selected_details")
        selected_yield = selected["yield_psi"] if selected else 80000

        # 5. Burst & Collapse ratings for selected grade
        burst_rating = CasingDesignEngine.calculate_burst_rating(
            casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
            yield_strength_psi=selected_yield,
        )

        collapse_rating = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
            yield_strength_psi=selected_yield,
        )

        # 6. Biaxial correction
        axial_stress = tension_load.get("axial_stress_psi", 0)
        biaxial = CasingDesignEngine.calculate_biaxial_correction(
            collapse_rating_psi=collapse_rating.get("collapse_rating_psi", 0),
            axial_stress_psi=axial_stress,
            yield_strength_psi=selected_yield,
        )

        # 7. Triaxial VME check
        # Hoop stress approximation: P_collapse * (D/t) / 2 at maximum collapse depth
        hoop_stress = max_collapse * (casing_od_in / wall_thickness_in) / 2 if wall_thickness_in > 0 else 0
        triaxial = CasingDesignEngine.calculate_triaxial_vme(
            axial_stress_psi=axial_stress,
            hoop_stress_psi=hoop_stress,
            yield_strength_psi=selected_yield,
        )

        # 8. Safety factors
        area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)
        tension_rating_lbs = selected_yield * area

        safety_factors = CasingDesignEngine.calculate_safety_factors(
            burst_load_psi=max_burst,
            burst_rating_psi=burst_rating.get("burst_rating_psi", 0),
            collapse_load_psi=max_collapse,
            collapse_rating_psi=biaxial.get("corrected_collapse_psi", collapse_rating.get("collapse_rating_psi", 0)),
            tension_load_lbs=total_tension,
            tension_rating_lbs=tension_rating_lbs,
            sf_burst_min=sf_burst, sf_collapse_min=sf_collapse, sf_tension_min=sf_tension,
        )

        # Alerts
        alerts = []
        if not safety_factors["all_pass"]:
            alerts.append(f"DESIGN FAILURE: {safety_factors['governing_criterion']} SF = "
                          f"{safety_factors['governing_sf']:.2f} < minimum")
        if triaxial["status"] == "FAIL":
            alerts.append(f"Triaxial VME FAIL: utilization {triaxial['utilization_pct']:.1f}%")
        if triaxial["status"] == "MARGINAL":
            alerts.append(f"Triaxial VME marginal: utilization {triaxial['utilization_pct']:.1f}%")
        if biaxial["reduction_factor"] < 0.8:
            alerts.append(f"Significant biaxial derating: collapse reduced by "
                          f"{(1 - biaxial['reduction_factor']) * 100:.0f}%")

        summary = {
            "selected_grade": grade_selection.get("selected_grade", ""),
            "max_burst_load_psi": max_burst,
            "max_collapse_load_psi": max_collapse,
            "total_tension_lbs": total_tension,
            "burst_rating_psi": burst_rating.get("burst_rating_psi", 0),
            "collapse_rating_psi": biaxial.get("corrected_collapse_psi", 0),
            "collapse_zone": collapse_rating.get("collapse_zone", ""),
            "tension_rating_lbs": round(tension_rating_lbs, 0),
            "sf_burst": safety_factors["results"]["burst"]["safety_factor"],
            "sf_collapse": safety_factors["results"]["collapse"]["safety_factor"],
            "sf_tension": safety_factors["results"]["tension"]["safety_factor"],
            "triaxial_status": triaxial["status"],
            "triaxial_utilization_pct": triaxial["utilization_pct"],
            "overall_status": safety_factors["overall_status"],
            "alerts": alerts,
        }

        return {
            "burst_load": burst_load,
            "collapse_load": collapse_load,
            "tension_load": tension_load,
            "burst_rating": burst_rating,
            "collapse_rating": collapse_rating,
            "biaxial_correction": biaxial,
            "triaxial_vme": triaxial,
            "grade_selection": grade_selection,
            "safety_factors": safety_factors,
            "summary": summary,
        }

    # ===================================================================
    # 10. Design Recommendations Generator
    # ===================================================================
    @staticmethod
    def generate_recommendations(result: Dict[str, Any]) -> List[str]:
        """
        Generate design recommendations from casing analysis results.

        Parameters:
        - result: output from calculate_full_casing_design()

        Returns list of plain-text recommendations.
        """
        recs: List[str] = []
        summary = result.get("summary", {})

        sf_burst = summary.get("sf_burst", 0)
        sf_collapse = summary.get("sf_collapse", 0)
        sf_tension = summary.get("sf_tension", 0)

        if summary.get("overall_status") != "ALL PASS":
            recs.append("FAIL: One or more design criteria not met. Upgrade grade or wall thickness.")

        if sf_burst > 3.0:
            recs.append(f"SF Burst ({sf_burst}) is very high — may be over-designed. Consider lighter grade.")
        if sf_collapse > 4.0:
            recs.append(f"SF Collapse ({sf_collapse}) is very high — consider cost optimization.")
        if sf_tension > 3.0:
            recs.append(f"SF Tension ({sf_tension}) is very high — verify overpull assumption.")

        if sf_burst < 1.2:
            recs.append("SF Burst is marginal. Verify gas migration scenario assumptions.")
        if sf_collapse < 1.1:
            recs.append("SF Collapse is marginal. Verify evacuation scenario and biaxial correction.")

        triaxial = summary.get("triaxial_status", "")
        if triaxial == "FAIL":
            recs.append("CRITICAL: Triaxial VME check fails. Upgrade grade immediately.")

        collapse_zone = summary.get("collapse_zone", "")
        if collapse_zone == "Elastic":
            recs.append("Collapse in elastic zone — thin-walled behavior. Consider heavier weight.")

        if not recs:
            recs.append("Design passes all criteria with adequate margins.")

        return recs
