"""
Full casing design pipeline -- orchestrates all sub-module calculations.

References:
- API TR 5C3 (ISO 10400): Complete casing design workflow
- NORSOK D-010: Well integrity requirements
"""
import math
from typing import Dict, Any, List

from .constants import CASING_GRADES
from .loads import calculate_burst_load, calculate_collapse_load, calculate_tension_load
from .ratings import calculate_burst_rating, calculate_collapse_rating
from .corrections import calculate_biaxial_correction, calculate_triaxial_vme, calculate_hoop_stress_lame
from .grade_selection import select_casing_grade
from .safety_factors import calculate_safety_factors


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
    alerts = []

    # 1. Burst load
    burst_load = calculate_burst_load(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        gas_gradient_psi_ft=gas_gradient_psi_ft,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
    )

    # 2. Collapse load (full evacuation)
    collapse_load = calculate_collapse_load(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
        evacuation_level_ft=0.0,
    )

    # 3. Tension load
    tension_load = calculate_tension_load(
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

    grade_selection = select_casing_grade(
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
    burst_rating = calculate_burst_rating(
        casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
        yield_strength_psi=selected_yield,
    )

    collapse_rating = calculate_collapse_rating(
        casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
        yield_strength_psi=selected_yield,
    )

    # 6. Biaxial correction
    axial_stress = tension_load.get("axial_stress_psi", 0)
    biaxial = calculate_biaxial_correction(
        collapse_rating_psi=collapse_rating.get("collapse_rating_psi", 0),
        axial_stress_psi=axial_stress,
        yield_strength_psi=selected_yield,
    )

    # 7. Triaxial VME check
    # Use Lamé thick-wall equations for accurate hoop stress at max collapse depth
    lame_result = calculate_hoop_stress_lame(
        od_in=casing_od_in, id_in=casing_id_in,
        p_internal_psi=0.0,  # worst case: evacuated casing
        p_external_psi=max_collapse,
    )
    if "error" in lame_result:
        alerts.append(f"Lamé hoop stress error: {lame_result['error']} — triaxial VME result may be unreliable")
        hoop_stress = 0
        radial_stress = 0
    else:
        hoop_stress = lame_result["hoop_inner_psi"]
        radial_stress = lame_result["radial_inner_psi"]
    triaxial = calculate_triaxial_vme(
        axial_stress_psi=axial_stress,
        hoop_stress_psi=hoop_stress,
        radial_stress_psi=radial_stress,
        yield_strength_psi=selected_yield,
    )

    # 8. Safety factors
    area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)
    tension_rating_lbs = selected_yield * area

    safety_factors = calculate_safety_factors(
        burst_load_psi=max_burst,
        burst_rating_psi=burst_rating.get("burst_rating_psi", 0),
        collapse_load_psi=max_collapse,
        collapse_rating_psi=biaxial.get("corrected_collapse_psi", collapse_rating.get("collapse_rating_psi", 0)),
        tension_load_lbs=total_tension,
        tension_rating_lbs=tension_rating_lbs,
        sf_burst_min=sf_burst, sf_collapse_min=sf_collapse, sf_tension_min=sf_tension,
    )

    # Alerts (list initialized at function start)
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
