"""
Casing Design — Safety Factors Summary

Calculates and evaluates design safety factors for burst, collapse, and
tension against minimum required values. Identifies the governing
(most critical) criterion.

References:
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
- API RP 90: Annular Casing Pressure Management
"""
from typing import Dict, Any


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


def calculate_sf_vs_depth(
    burst_profile: list,
    collapse_profile: list,
    burst_rating_psi: float,
    collapse_rating_psi: float,
    tension_at_surface_lbs: float,
    tension_rating_lbs: float,
    casing_weight_ppf: float,
    mud_weight_ppg: float,
    casing_length_ft: float,
) -> Dict[str, Any]:
    """
    Calculate burst, collapse, and tension safety factors at each depth point.

    Produces a depth-wise SF profile for visualization (similar to Landmark WellPlan).

    burst_profile: list of {"tvd_ft": float, "burst_load_psi": float}
    collapse_profile: list of {"tvd_ft": float, "collapse_load_psi": float}

    References:
    - NORSOK D-010: Well Integrity in Drilling and Well Operations
    - API RP 90: Annular Casing Pressure Management
    """
    bf = 1.0 - mud_weight_ppg / 65.4

    sf_profile = []
    for i, bp in enumerate(burst_profile):
        depth = bp.get("tvd_ft", 0)
        burst_load = abs(bp.get("burst_load_psi", 0))
        collapse_load = 0
        if i < len(collapse_profile):
            collapse_load = abs(collapse_profile[i].get("collapse_load_psi", 0))

        # Tension decreases with depth (less string below)
        remaining = max(casing_length_ft - depth, 0)
        tension_at_depth = casing_weight_ppf * remaining * bf
        # At surface, use actual tension (includes all loads)
        if depth == 0:
            tension_at_depth = tension_at_surface_lbs

        sf_b = burst_rating_psi / burst_load if burst_load > 0 else 99.0
        sf_c = collapse_rating_psi / collapse_load if collapse_load > 0 else 99.0
        sf_t = tension_rating_lbs / tension_at_depth if tension_at_depth > 0 else 99.0

        sf_profile.append({
            "tvd_ft": round(depth, 0),
            "sf_burst": round(min(sf_b, 99.0), 2),
            "sf_collapse": round(min(sf_c, 99.0), 2),
            "sf_tension": round(min(sf_t, 99.0), 2),
            "governing_sf": round(min(sf_b, sf_c, sf_t, 99.0), 2),
        })

    if not sf_profile:
        return {"profile": [], "min_sf": 0, "min_sf_depth_ft": 0, "num_points": 0}

    # Find minimum SF and its depth
    min_point = min(sf_profile, key=lambda p: p["governing_sf"])

    return {
        "profile": sf_profile,
        "min_sf": min_point["governing_sf"],
        "min_sf_depth_ft": min_point["tvd_ft"],
        "num_points": len(sf_profile),
    }
