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
    # 10. Multi-Scenario Burst (5 scenarios)
    # ===================================================================
    @staticmethod
    def calculate_burst_scenarios(
        tvd_ft: float,
        mud_weight_ppg: float,
        pore_pressure_ppg: float,
        gas_gradient_psi_ft: float = 0.1,
        cement_top_tvd_ft: float = 0.0,
        cement_density_ppg: float = 16.0,
        tubing_pressure_psi: float = 0.0,
        injection_pressure_psi: float = 0.0,
        injection_fluid_gradient: float = 0.433,
        dst_pressure_psi: float = 0.0,
        num_points: int = 20,
    ) -> Dict[str, Any]:
        """
        Multi-scenario burst analysis (API TR 5C3 / ISO 10400).

        Scenarios:
        1. Gas-to-surface — worst case for surface casing
        2. Displacement to gas — tubing full of gas, annulus with mud
        3. Tubing leak — tubing head pressure applied to casing
        4. Injection — injection pressure + fluid gradient
        5. DST — reservoir pressure at surface during drill stem test
        """
        if tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        p_reservoir = pore_pressure_ppg * 0.052 * tvd_ft

        scenarios = {}
        step = tvd_ft / max(num_points - 1, 1)

        # Helper: external pressure at depth
        def p_external(depth):
            if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
                return mud_weight_ppg * 0.052 * depth
            return (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                    cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft))

        # Scenario 1: Gas-to-surface
        profile_gts = []
        for i in range(num_points):
            d = i * step
            p_int = max(p_reservoir - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
            p_ext = p_external(d)
            profile_gts.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
        scenarios["gas_to_surface"] = {
            "profile": profile_gts,
            "max_burst_psi": max(p["burst_load_psi"] for p in profile_gts),
        }

        # Scenario 2: Displacement to gas
        profile_dtg = []
        for i in range(num_points):
            d = i * step
            p_int = max(p_reservoir - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
            p_ext = mud_weight_ppg * 0.052 * d  # annulus = mud (no cement backup)
            profile_dtg.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
        scenarios["displacement_to_gas"] = {
            "profile": profile_dtg,
            "max_burst_psi": max(p["burst_load_psi"] for p in profile_dtg),
        }

        # Scenario 3: Tubing leak
        p_tubing = tubing_pressure_psi if tubing_pressure_psi > 0 else 0.5 * p_reservoir
        profile_tl = []
        for i in range(num_points):
            d = i * step
            p_int = p_tubing + mud_weight_ppg * 0.052 * d
            p_ext = p_external(d)
            profile_tl.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
        scenarios["tubing_leak"] = {
            "profile": profile_tl,
            "max_burst_psi": max(p["burst_load_psi"] for p in profile_tl),
        }

        # Scenario 4: Injection
        p_inj = injection_pressure_psi if injection_pressure_psi > 0 else 0.0
        profile_inj = []
        for i in range(num_points):
            d = i * step
            p_int = p_inj + injection_fluid_gradient * d
            p_ext = p_external(d)
            profile_inj.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
        scenarios["injection"] = {
            "profile": profile_inj,
            "max_burst_psi": max(p["burst_load_psi"] for p in profile_inj),
        }

        # Scenario 5: DST
        p_dst = dst_pressure_psi if dst_pressure_psi > 0 else p_reservoir
        profile_dst = []
        for i in range(num_points):
            d = i * step
            p_int = max(p_dst - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
            p_ext = p_external(d)
            profile_dst.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
        scenarios["dst"] = {
            "profile": profile_dst,
            "max_burst_psi": max(p["burst_load_psi"] for p in profile_dst),
        }

        # Governing scenario
        governing = max(scenarios.items(), key=lambda x: x[1]["max_burst_psi"])

        return {
            "scenarios": scenarios,
            "governing_scenario": governing[0],
            "governing_burst_psi": governing[1]["max_burst_psi"],
            "num_scenarios": len(scenarios),
        }

    # ===================================================================
    # 11. Multi-Scenario Collapse (4 scenarios)
    # ===================================================================
    @staticmethod
    def calculate_collapse_scenarios(
        tvd_ft: float,
        mud_weight_ppg: float,
        pore_pressure_ppg: float,
        cement_top_tvd_ft: float = 0.0,
        cement_density_ppg: float = 16.0,
        partial_evacuation_ft: float = 0.0,
        depleted_pressure_ppg: float = 0.0,
        cement_slurry_density_ppg: float = 16.5,
        num_points: int = 20,
    ) -> Dict[str, Any]:
        """
        Multi-scenario collapse analysis.

        Scenarios:
        1. Full evacuation — worst case drilling
        2. Partial evacuation — fluid level drops to partial_evacuation_ft
        3. Cementing collapse — fresh cement outside, reduced inside
        4. Production collapse — reservoir depletion over life
        """
        if tvd_ft <= 0:
            return {"error": "TVD must be > 0"}

        scenarios = {}
        step = tvd_ft / max(num_points - 1, 1)

        # External pressure helper
        def p_external(depth):
            if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
                return mud_weight_ppg * 0.052 * depth
            return (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                    cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft))

        # Scenario 1: Full evacuation
        profile_fe = []
        for i in range(num_points):
            d = i * step
            p_ext = p_external(d)
            p_int = 0.0  # empty
            profile_fe.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
        scenarios["full_evacuation"] = {
            "profile": profile_fe,
            "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_fe),
        }

        # Scenario 2: Partial evacuation
        evac_ft = partial_evacuation_ft if partial_evacuation_ft > 0 else tvd_ft * 0.5
        profile_pe = []
        for i in range(num_points):
            d = i * step
            p_ext = p_external(d)
            p_int = 0.0 if d <= evac_ft else mud_weight_ppg * 0.052 * (d - evac_ft)
            profile_pe.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
        scenarios["partial_evacuation"] = {
            "profile": profile_pe,
            "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_pe),
        }

        # Scenario 3: Cementing collapse
        profile_cc = []
        for i in range(num_points):
            d = i * step
            # External: fresh cement (heavier) outside casing during cementing
            if d <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
                p_ext_cc = mud_weight_ppg * 0.052 * d
            else:
                p_ext_cc = (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                            cement_slurry_density_ppg * 0.052 * (depth - cement_top_tvd_ft)
                            if 'depth' in dir() else
                            mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                            cement_slurry_density_ppg * 0.052 * (d - cement_top_tvd_ft))
            # Internal: reduced pressure (partial lost returns)
            p_int_cc = mud_weight_ppg * 0.052 * d * 0.85  # 85% of original MW
            profile_cc.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext_cc - p_int_cc, 0)})
        scenarios["cementing_collapse"] = {
            "profile": profile_cc,
            "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_cc),
        }

        # Scenario 4: Production collapse (depletion)
        depleted_ppg = depleted_pressure_ppg if depleted_pressure_ppg > 0 else pore_pressure_ppg * 0.5
        profile_pd = []
        for i in range(num_points):
            d = i * step
            p_ext = p_external(d)
            # Internal: depleted reservoir pressure gradient
            p_int = depleted_ppg * 0.052 * d
            profile_pd.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
        scenarios["production_depletion"] = {
            "profile": profile_pd,
            "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_pd),
        }

        governing = max(scenarios.items(), key=lambda x: x[1]["max_collapse_psi"])

        return {
            "scenarios": scenarios,
            "governing_scenario": governing[0],
            "governing_collapse_psi": governing[1]["max_collapse_psi"],
            "num_scenarios": len(scenarios),
        }

    # ===================================================================
    # 12. Temperature Derating (API TR 5C3 Annex G)
    # ===================================================================
    @staticmethod
    def derate_for_temperature(
        grade: str,
        yield_strength_psi: float,
        temperature_f: float,
        ambient_temperature_f: float = 70.0,
    ) -> Dict[str, Any]:
        """
        Derate yield strength for temperature (critical for HPHT).

        API TR 5C3 Annex G:
        sigma_y(T) = sigma_y_ambient * [1 - alpha * (T - T_ambient)]
        alpha depends on steel grade (~0.00035-0.0005 /°F for T > 200°F)
        """
        # Alpha coefficients by grade family (empirical, API TR 5C3)
        alpha_map = {
            "H40": 0.0003, "J55": 0.00035, "K55": 0.00035,
            "L80": 0.0004, "N80": 0.0004, "C90": 0.00042,
            "T95": 0.00045, "C110": 0.00045, "P110": 0.00045,
            "Q125": 0.0005, "V150": 0.00055,
        }
        alpha = alpha_map.get(grade, 0.0004)

        dT = temperature_f - ambient_temperature_f
        if dT <= 0:
            # No derating for temperatures at or below ambient
            return {
                "yield_derated_psi": yield_strength_psi,
                "derate_factor": 1.0,
                "temperature_f": temperature_f,
                "alpha": alpha,
                "grade": grade,
            }

        # Only apply derating above threshold (typically 200°F)
        threshold_f = 200.0
        if temperature_f < threshold_f:
            effective_dT = 0.0
        else:
            effective_dT = temperature_f - threshold_f

        derate_factor = 1.0 - alpha * effective_dT
        derate_factor = max(derate_factor, 0.5)  # minimum 50% derating

        yield_derated = yield_strength_psi * derate_factor

        return {
            "yield_derated_psi": round(yield_derated, 0),
            "derate_factor": round(derate_factor, 4),
            "temperature_f": temperature_f,
            "effective_dT": round(effective_dT, 1),
            "alpha": alpha,
            "grade": grade,
        }

    # ===================================================================
    # 13. Expanded Casing Catalog (API 5CT)
    # ===================================================================
    CASING_CATALOG = {
        "4.500": [
            {"weight": 9.50, "id": 4.090, "wall": 0.205, "grade": "J55", "burst": 4380, "collapse": 2760},
            {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "J55", "burst": 6230, "collapse": 5430},
            {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "N80", "burst": 9060, "collapse": 8600},
            {"weight": 13.50, "id": 3.810, "wall": 0.345, "grade": "N80", "burst": 10790, "collapse": 11080},
            {"weight": 15.10, "id": 3.680, "wall": 0.410, "grade": "P110", "burst": 17530, "collapse": 17350},
        ],
        "5.500": [
            {"weight": 14.00, "id": 5.012, "wall": 0.244, "grade": "J55", "burst": 4270, "collapse": 2870},
            {"weight": 15.50, "id": 4.950, "wall": 0.275, "grade": "J55", "burst": 4810, "collapse": 3660},
            {"weight": 17.00, "id": 4.892, "wall": 0.304, "grade": "N80", "burst": 7740, "collapse": 6070},
            {"weight": 20.00, "id": 4.778, "wall": 0.361, "grade": "N80", "burst": 9190, "collapse": 8440},
            {"weight": 23.00, "id": 4.670, "wall": 0.415, "grade": "P110", "burst": 14510, "collapse": 13680},
        ],
        "7.000": [
            {"weight": 17.00, "id": 6.538, "wall": 0.231, "grade": "J55", "burst": 3180, "collapse": 1420},
            {"weight": 23.00, "id": 6.366, "wall": 0.317, "grade": "J55", "burst": 4360, "collapse": 3270},
            {"weight": 26.00, "id": 6.276, "wall": 0.362, "grade": "N80", "burst": 7250, "collapse": 5410},
            {"weight": 29.00, "id": 6.184, "wall": 0.408, "grade": "N80", "burst": 8160, "collapse": 6980},
            {"weight": 32.00, "id": 6.094, "wall": 0.453, "grade": "L80", "burst": 9070, "collapse": 8240},
            {"weight": 35.00, "id": 6.004, "wall": 0.498, "grade": "C90", "burst": 11210, "collapse": 10520},
            {"weight": 38.00, "id": 5.920, "wall": 0.540, "grade": "P110", "burst": 14850, "collapse": 13290},
        ],
        "9.625": [
            {"weight": 36.00, "id": 8.921, "wall": 0.352, "grade": "J55", "burst": 3520, "collapse": 2020},
            {"weight": 40.00, "id": 8.835, "wall": 0.395, "grade": "J55", "burst": 3950, "collapse": 2570},
            {"weight": 43.50, "id": 8.755, "wall": 0.435, "grade": "N80", "burst": 6330, "collapse": 4130},
            {"weight": 47.00, "id": 8.681, "wall": 0.472, "grade": "N80", "burst": 6870, "collapse": 4760},
            {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "C90", "burst": 8930, "collapse": 7040},
            {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "P110", "burst": 10910, "collapse": 9120},
        ],
        "10.750": [
            {"weight": 32.75, "id": 10.192, "wall": 0.279, "grade": "J55", "burst": 2500, "collapse": 920},
            {"weight": 40.50, "id": 10.050, "wall": 0.350, "grade": "J55", "burst": 3140, "collapse": 1580},
            {"weight": 45.50, "id": 9.950, "wall": 0.400, "grade": "N80", "burst": 5210, "collapse": 2710},
            {"weight": 51.00, "id": 9.850, "wall": 0.450, "grade": "N80", "burst": 5860, "collapse": 3480},
            {"weight": 55.50, "id": 9.760, "wall": 0.495, "grade": "P110", "burst": 8890, "collapse": 5210},
        ],
        "13.375": [
            {"weight": 48.00, "id": 12.715, "wall": 0.330, "grade": "J55", "burst": 2380, "collapse": 870},
            {"weight": 54.50, "id": 12.615, "wall": 0.380, "grade": "J55", "burst": 2740, "collapse": 1180},
            {"weight": 61.00, "id": 12.515, "wall": 0.430, "grade": "N80", "burst": 4510, "collapse": 1900},
            {"weight": 68.00, "id": 12.415, "wall": 0.480, "grade": "N80", "burst": 5030, "collapse": 2420},
            {"weight": 72.00, "id": 12.347, "wall": 0.514, "grade": "P110", "burst": 7430, "collapse": 3340},
        ],
        "20.000": [
            {"weight": 94.00, "id": 19.124, "wall": 0.438, "grade": "J55", "burst": 2110, "collapse": 520},
            {"weight": 106.50, "id": 18.936, "wall": 0.532, "grade": "K55", "burst": 2560, "collapse": 870},
            {"weight": 133.00, "id": 18.730, "wall": 0.635, "grade": "K55", "burst": 3060, "collapse": 1370},
        ],
    }

    @staticmethod
    def lookup_casing_catalog(
        casing_od_in: float,
        min_weight_ppf: float = 0.0,
        grade_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Look up casing options from expanded API 5CT catalog.

        Parameters:
        - casing_od_in: nominal OD (e.g., 9.625)
        - min_weight_ppf: minimum weight filter
        - grade_filter: filter by grade (e.g., 'N80')
        """
        od_key = f"{casing_od_in:.3f}"
        entries = CasingDesignEngine.CASING_CATALOG.get(od_key, [])

        if not entries:
            # Try nearest OD
            available = list(CasingDesignEngine.CASING_CATALOG.keys())
            return {"error": f"OD {casing_od_in} not in catalog. Available: {available}"}

        results = []
        for e in entries:
            if e["weight"] < min_weight_ppf:
                continue
            if grade_filter and e["grade"] != grade_filter:
                continue
            results.append(e.copy())

        return {
            "od_in": casing_od_in,
            "options": results,
            "count": len(results),
        }

    # ===================================================================
    # 14. Combination String Design
    # ===================================================================
    @staticmethod
    def design_combination_string(
        tvd_ft: float,
        casing_od_in: float,
        burst_profile: List[Dict[str, Any]],
        collapse_profile: List[Dict[str, Any]],
        tension_at_surface_lbs: float,
        casing_length_ft: float,
        mud_weight_ppg: float,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
        cost_per_lb: float = 0.50,
    ) -> Dict[str, Any]:
        """
        Design combination string with multiple weights/grades to optimize cost.

        Divides the string into sections by depth and selects minimum
        weight/grade that satisfies all safety factors.
        """
        od_key = f"{casing_od_in:.3f}"
        catalog = CasingDesignEngine.CASING_CATALOG.get(od_key, [])
        if not catalog:
            return {"error": f"No catalog data for OD {casing_od_in}"}

        # Sort catalog by weight (lightest = cheapest first)
        catalog_sorted = sorted(catalog, key=lambda c: c["weight"])

        # Divide string into sections (top, middle, bottom)
        num_sections = 3
        section_length = casing_length_ft / num_sections

        sections = []
        total_cost = 0.0
        total_weight_lbs = 0.0

        for sec_idx in range(num_sections):
            depth_from = sec_idx * section_length
            depth_to = (sec_idx + 1) * section_length
            depth_mid = (depth_from + depth_to) / 2.0

            # TVD fraction for this section
            tvd_frac = depth_mid / casing_length_ft if casing_length_ft > 0 else 0
            section_tvd = tvd_frac * tvd_ft

            # Find max burst load in this depth range
            max_burst_sec = 0
            for p in burst_profile:
                if depth_from <= p.get("tvd_ft", 0) <= depth_to:
                    max_burst_sec = max(max_burst_sec, p.get("burst_load_psi", 0))

            # Find max collapse load in this depth range
            max_collapse_sec = 0
            for p in collapse_profile:
                if depth_from <= p.get("tvd_ft", 0) <= depth_to:
                    max_collapse_sec = max(max_collapse_sec, p.get("collapse_load_psi", 0))

            # Tension at this depth (weight below)
            remaining_length = casing_length_ft - depth_from
            bf = 1.0 - mud_weight_ppg / 65.4
            tension_at_depth = tension_at_surface_lbs * (remaining_length / casing_length_ft) if casing_length_ft > 0 else 0

            # Select lightest option that satisfies all criteria
            selected = None
            for opt in catalog_sorted:
                wall = opt["wall"]
                yp = CasingDesignEngine.CASING_GRADES.get(opt["grade"], {}).get("yield_psi", 80000)

                burst_ok = opt["burst"] >= max_burst_sec * sf_burst if max_burst_sec > 0 else True
                collapse_ok = opt["collapse"] >= max_collapse_sec * sf_collapse if max_collapse_sec > 0 else True
                area = math.pi / 4.0 * (casing_od_in ** 2 - opt["id"] ** 2)
                tension_rating = yp * area
                tension_ok = tension_rating >= tension_at_depth * sf_tension if tension_at_depth > 0 else True

                if burst_ok and collapse_ok and tension_ok:
                    selected = opt
                    break

            if selected is None:
                # Use heaviest available
                selected = catalog_sorted[-1]

            sec_weight = selected["weight"] * section_length
            sec_cost = sec_weight * cost_per_lb
            total_weight_lbs += sec_weight
            total_cost += sec_cost

            sections.append({
                "section": sec_idx + 1,
                "depth_from_ft": round(depth_from, 0),
                "depth_to_ft": round(depth_to, 0),
                "grade": selected["grade"],
                "weight_ppf": selected["weight"],
                "id_in": selected["id"],
                "wall_in": selected["wall"],
                "burst_rating_psi": selected["burst"],
                "collapse_rating_psi": selected["collapse"],
                "length_ft": round(section_length, 0),
                "section_weight_lbs": round(sec_weight, 0),
                "section_cost": round(sec_cost, 0),
            })

        return {
            "sections": sections,
            "total_weight_lbs": round(total_weight_lbs, 0),
            "total_cost": round(total_cost, 0),
            "num_sections": num_sections,
            "casing_od_in": casing_od_in,
        }

    # ===================================================================
    # 15. Running Loads (API)
    # ===================================================================
    @staticmethod
    def calculate_running_loads(
        casing_weight_ppf: float,
        casing_length_ft: float,
        casing_od_in: float,
        casing_id_in: float,
        mud_weight_ppg: float,
        survey: Optional[List[Dict[str, float]]] = None,
        friction_factor: float = 0.30,
    ) -> Dict[str, Any]:
        """
        Calculate running loads (hookload during casing run).

        Components:
        - Weight: casing weight in mud (buoyed)
        - Drag: friction × normal force (from survey)
        - Shock: F_shock = 3200 * W_ppf (API formula for sudden stops)
        - Bending: F_bend = 64 * W_ppf * OD * DLS/100 (Lubinski)
        """
        bf = 1.0 - mud_weight_ppg / 65.4
        buoyed_weight = casing_weight_ppf * casing_length_ft * bf

        # Shock load (API)
        shock = 3200.0 * casing_weight_ppf

        # Drag from survey
        drag = 0.0
        max_dls = 0.0
        if survey and len(survey) >= 2:
            for i in range(1, len(survey)):
                md1 = survey[i - 1].get("md", 0)
                md2 = survey[i].get("md", 0)
                inc1 = math.radians(survey[i - 1].get("inclination", 0))
                inc2 = math.radians(survey[i].get("inclination", 0))
                dL = md2 - md1
                if dL <= 0:
                    continue
                avg_inc = (inc1 + inc2) / 2.0
                # Normal force = weight * sin(inc)
                w_section = casing_weight_ppf * dL * bf
                normal_force = w_section * math.sin(avg_inc)
                drag += friction_factor * abs(normal_force)

                # DLS for bending
                dl_rad = abs(inc2 - inc1)
                dls_100 = (dl_rad * 180.0 / math.pi) / dL * 100.0 if dL > 0 else 0
                max_dls = max(max_dls, dls_100)

        # Bending
        bending = 64.0 * casing_weight_ppf * casing_od_in * max_dls / 100.0

        # Total hookload
        total_hookload = buoyed_weight + drag + shock + bending

        # Cross-sectional area and stress
        area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)
        axial_stress = total_hookload / area if area > 0 else 0

        return {
            "buoyed_weight_lbs": round(buoyed_weight, 0),
            "drag_lbs": round(drag, 0),
            "shock_load_lbs": round(shock, 0),
            "bending_load_lbs": round(bending, 0),
            "total_hookload_lbs": round(total_hookload, 0),
            "axial_stress_psi": round(axial_stress, 0),
            "buoyancy_factor": round(bf, 4),
            "max_dls_deg_100ft": round(max_dls, 2),
            "friction_factor": friction_factor,
        }

    # ===================================================================
    # 16. Wear / Corrosion Allowance
    # ===================================================================
    @staticmethod
    def apply_wear_allowance(
        casing_od_in: float,
        wall_thickness_in: float,
        yield_strength_psi: float,
        wear_pct: float = 0.0,
        corrosion_rate_in_yr: float = 0.0,
        design_life_years: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Reduce wall thickness for wear and corrosion, then recalculate ratings.

        - Wear: wall_remaining = wall * (1 - wear_pct/100)
        - Corrosion: wall_remaining -= corrosion_rate * design_life
        - Recalculate burst (Barlow) and collapse (API 5C3) with remaining wall
        """
        wall_worn = wall_thickness_in * (1.0 - wear_pct / 100.0)
        wall_corroded = wall_worn - corrosion_rate_in_yr * design_life_years
        wall_remaining = max(wall_corroded, 0.05)  # minimum wall

        remaining_pct = (wall_remaining / wall_thickness_in * 100) if wall_thickness_in > 0 else 0

        # Original ratings
        burst_orig = CasingDesignEngine.calculate_burst_rating(casing_od_in, wall_thickness_in, yield_strength_psi)
        collapse_orig = CasingDesignEngine.calculate_collapse_rating(casing_od_in, wall_thickness_in, yield_strength_psi)

        # Derated ratings
        burst_derated = CasingDesignEngine.calculate_burst_rating(casing_od_in, wall_remaining, yield_strength_psi)
        collapse_derated = CasingDesignEngine.calculate_collapse_rating(casing_od_in, wall_remaining, yield_strength_psi)

        return {
            "original_wall_in": wall_thickness_in,
            "remaining_wall_in": round(wall_remaining, 4),
            "remaining_wall_pct": round(remaining_pct, 1),
            "wear_loss_in": round(wall_thickness_in - wall_worn, 4),
            "corrosion_loss_in": round(corrosion_rate_in_yr * design_life_years, 4),
            "original_burst_psi": burst_orig.get("burst_rating_psi", 0),
            "derated_burst_psi": burst_derated.get("burst_rating_psi", 0),
            "burst_reduction_pct": round(
                (1 - burst_derated.get("burst_rating_psi", 0) / max(burst_orig.get("burst_rating_psi", 1), 1)) * 100, 1),
            "original_collapse_psi": collapse_orig.get("collapse_rating_psi", 0),
            "derated_collapse_psi": collapse_derated.get("collapse_rating_psi", 0),
            "collapse_reduction_pct": round(
                (1 - collapse_derated.get("collapse_rating_psi", 0) / max(collapse_orig.get("collapse_rating_psi", 1), 1)) * 100, 1),
            "design_life_years": design_life_years,
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
