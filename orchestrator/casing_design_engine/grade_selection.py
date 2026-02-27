"""
Casing Design — Grade Selection, Catalog Lookup, and Combination String Design

Automated grade selection that iterates through API 5CT grades to find the
lightest/cheapest option satisfying burst, collapse, and tension criteria.
Catalog lookup from expanded API 5CT database. Combination string design
optimizes cost by varying weight/grade along the string.

References:
- API 5CT: Specification for Casing and Tubing
- API TR 5C3 (ISO 10400): Collapse rating formulas
- NORSOK D-010: Well Integrity in Drilling and Well Operations
"""
import math
from typing import List, Dict, Any, Optional

from .constants import CASING_GRADES, CASING_CATALOG
from .ratings import calculate_collapse_rating


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
        CASING_GRADES.items(),
        key=lambda x: x[1]["yield_psi"]
    )

    for grade_name, grade_info in sorted_grades:
        yp = grade_info["yield_psi"]

        # Burst rating (Barlow)
        burst_rating = 0.875 * 2.0 * yp * wall_thickness_in / casing_od_in

        # Collapse rating (simplified — yield collapse for initial screening)
        dt = casing_od_in / wall_thickness_in
        collapse_result = calculate_collapse_rating(
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
    entries = CASING_CATALOG.get(od_key, [])

    if not entries:
        # Try nearest OD
        available = list(CASING_CATALOG.keys())
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
    catalog = CASING_CATALOG.get(od_key, [])
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
            yp = CASING_GRADES.get(opt["grade"], {}).get("yield_psi", 80000)

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
