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
from .ratings import calculate_burst_rating, calculate_collapse_rating, derate_for_temperature
from .corrections import (
    calculate_biaxial_correction, calculate_biaxial_profile,
    calculate_triaxial_vme, calculate_hoop_stress_lame,
)
from .grade_selection import select_casing_grade
from .safety_factors import calculate_safety_factors, calculate_sf_vs_depth
from .scenarios import calculate_burst_scenarios, calculate_collapse_scenarios
from .connections import verify_connection
from .wear import apply_wear_allowance


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
    connection_type: str = "BTC",
    wear_pct: float = 0.0,
    corrosion_rate_in_yr: float = 0.0,
    design_life_years: float = 20.0,
    bottomhole_temp_f: float = 200.0,
    tubing_pressure_psi: float = 0.0,
    internal_fluid_density_ppg: float = 0.0,
    evacuation_level_ft: float = -1.0,
) -> Dict[str, Any]:
    """
    Run complete casing design analysis with multi-scenario loads,
    depth-varying biaxial correction, separated tension scenarios,
    connection verification, wear allowance, and temperature derating.

    Parameters:
    - evacuation_level_ft: -1 = auto (full evacuation = tvd_ft),
                            0 = casing full (no evacuation),
                           >0 = partial evacuation fluid level
    """
    alerts = []

    # Resolve evacuation level
    if evacuation_level_ft < 0:
        effective_evacuation = tvd_ft
    else:
        effective_evacuation = evacuation_level_ft

    # 1. Multi-scenario burst
    burst_scenarios = calculate_burst_scenarios(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        gas_gradient_psi_ft=gas_gradient_psi_ft,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
        tubing_pressure_psi=tubing_pressure_psi,
    )

    # Single-scenario burst for backward compatibility & profile
    burst_load = calculate_burst_load(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        gas_gradient_psi_ft=gas_gradient_psi_ft,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
    )

    # 2. Multi-scenario collapse
    collapse_scenarios = calculate_collapse_scenarios(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
    )

    # Single collapse with effective evacuation
    collapse_load = calculate_collapse_load(
        tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
        cement_top_tvd_ft=cement_top_tvd_ft,
        cement_density_ppg=cement_density_ppg,
        evacuation_level_ft=effective_evacuation,
    )

    # 3. Separated tension scenarios
    tension_running = calculate_tension_load(
        casing_weight_ppf=casing_weight_ppf,
        casing_length_ft=casing_length_ft,
        mud_weight_ppg=mud_weight_ppg,
        casing_od_in=casing_od_in, casing_id_in=casing_id_in,
        shock_load=True, bending_load_dls=bending_dls,
        overpull_lbs=0.0,
    )

    tension_stuck = calculate_tension_load(
        casing_weight_ppf=casing_weight_ppf,
        casing_length_ft=casing_length_ft,
        mud_weight_ppg=mud_weight_ppg,
        casing_od_in=casing_od_in, casing_id_in=casing_id_in,
        shock_load=False, bending_load_dls=bending_dls,
        overpull_lbs=overpull_lbs,
    )

    if tension_running["total_tension_lbs"] >= tension_stuck["total_tension_lbs"]:
        tension_load = tension_running
        tension_governing = "Running (Shock)"
    else:
        tension_load = tension_stuck
        tension_governing = "Stuck Pipe (Overpull)"

    # 4. Governing loads from multi-scenario
    max_burst = burst_scenarios.get("governing_burst_psi", burst_load.get("max_burst_load_psi", 0))
    max_collapse = collapse_scenarios.get("governing_collapse_psi", collapse_load.get("max_collapse_load_psi", 0))
    total_tension = tension_load.get("total_tension_lbs", 0)

    # 5. Grade selection
    grade_selection = select_casing_grade(
        required_burst_psi=max_burst,
        required_collapse_psi=max_collapse,
        required_tension_lbs=total_tension,
        casing_od_in=casing_od_in,
        wall_thickness_in=wall_thickness_in,
        sf_burst=sf_burst, sf_collapse=sf_collapse, sf_tension=sf_tension,
    )

    selected = grade_selection.get("selected_details")
    selected_yield = selected["yield_psi"] if selected else 80000

    # 6. Temperature derating
    selected_grade = grade_selection.get("selected_grade", "N80")
    temp_derate = derate_for_temperature(
        grade=selected_grade,
        yield_strength_psi=selected_yield,
        temperature_f=bottomhole_temp_f,
    )
    effective_yield = temp_derate["yield_derated_psi"]

    if temp_derate["derate_factor"] < 1.0:
        alerts.append(
            f"Temperature derating: yield reduced from {selected_yield:,.0f} to "
            f"{effective_yield:,.0f} psi ({temp_derate['derate_factor']:.2%}) at {bottomhole_temp_f}\u00b0F"
        )

    # 7. Burst & collapse ratings with effective yield
    burst_rating = calculate_burst_rating(
        casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
        yield_strength_psi=effective_yield,
    )
    collapse_rating = calculate_collapse_rating(
        casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
        yield_strength_psi=effective_yield,
    )

    # 8. Wear allowance
    wear_result = None
    if wear_pct > 0 or corrosion_rate_in_yr > 0:
        wear_result = apply_wear_allowance(
            casing_od_in=casing_od_in,
            wall_thickness_in=wall_thickness_in,
            yield_strength_psi=effective_yield,
            wear_pct=wear_pct,
            corrosion_rate_in_yr=corrosion_rate_in_yr,
            design_life_years=design_life_years,
        )
        if wear_result["remaining_wall_pct"] < 80:
            alerts.append(
                f"Wall thickness reduced to {wear_result['remaining_wall_pct']:.0f}% "
                f"({wear_result['remaining_wall_in']:.3f}\" remaining)"
            )
        burst_rating_design = wear_result["derated_burst_psi"]
        collapse_rating_design = wear_result["derated_collapse_psi"]
    else:
        burst_rating_design = burst_rating.get("burst_rating_psi", 0)
        collapse_rating_design = collapse_rating.get("collapse_rating_psi", 0)

    # 9. Biaxial correction (single-point for summary)
    axial_stress = tension_load.get("axial_stress_psi", 0)
    biaxial = calculate_biaxial_correction(
        collapse_rating_psi=collapse_rating_design,
        axial_stress_psi=axial_stress,
        yield_strength_psi=effective_yield,
    )

    # 10. Depth-varying biaxial profile
    governing_collapse_name = collapse_scenarios.get("governing_scenario", "full_evacuation")
    governing_collapse_profile = collapse_scenarios.get("scenarios", {}).get(
        governing_collapse_name, {}
    ).get("profile", [])

    biaxial_depth = calculate_biaxial_profile(
        collapse_profile=governing_collapse_profile,
        collapse_rating_psi=collapse_rating_design,
        casing_weight_ppf=casing_weight_ppf,
        casing_length_ft=casing_length_ft,
        casing_od_in=casing_od_in,
        casing_id_in=casing_id_in,
        mud_weight_ppg=mud_weight_ppg,
        yield_strength_psi=effective_yield,
        overpull_lbs=0.0,
    )

    # 11. Triaxial VME
    lame_result = calculate_hoop_stress_lame(
        od_in=casing_od_in, id_in=casing_id_in,
        p_internal_psi=0.0,
        p_external_psi=max_collapse,
    )
    if "error" in lame_result:
        alerts.append(f"Lam\u00e9 hoop stress error: {lame_result['error']}")
        hoop_stress = 0
        radial_stress = 0
    else:
        hoop_stress = lame_result["hoop_inner_psi"]
        radial_stress = lame_result["radial_inner_psi"]

    triaxial = calculate_triaxial_vme(
        axial_stress_psi=axial_stress,
        hoop_stress_psi=hoop_stress,
        radial_stress_psi=radial_stress,
        yield_strength_psi=effective_yield,
    )

    # 12. Connection verification
    area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)
    tension_rating_lbs = effective_yield * area

    connection = verify_connection(
        connection_type=connection_type,
        pipe_body_yield_lbs=tension_rating_lbs,
        burst_rating_psi=burst_rating_design,
        collapse_rating_psi=biaxial.get("corrected_collapse_psi", collapse_rating_design),
        applied_tension_lbs=total_tension,
        applied_burst_psi=max_burst,
        applied_collapse_psi=max_collapse,
        sf_tension=sf_tension,
        sf_burst=sf_burst,
    )

    if connection.get("is_weak_link"):
        alerts.append(
            f"Connection ({connection_type}) is weak link \u2014 "
            f"tension efficiency {connection.get('efficiency', 0)*100:.0f}%"
        )
    if not connection.get("passes_all", True):
        alerts.append(f"Connection ({connection_type}) FAILS design criteria")

    # 13. Safety factors
    effective_collapse_rating = biaxial.get("corrected_collapse_psi", collapse_rating_design)

    safety_factors = calculate_safety_factors(
        burst_load_psi=max_burst,
        burst_rating_psi=burst_rating_design,
        collapse_load_psi=max_collapse,
        collapse_rating_psi=effective_collapse_rating,
        tension_load_lbs=total_tension,
        tension_rating_lbs=tension_rating_lbs,
        sf_burst_min=sf_burst, sf_collapse_min=sf_collapse, sf_tension_min=sf_tension,
    )

    # 14. SF vs depth profile
    sf_vs_depth = calculate_sf_vs_depth(
        burst_profile=burst_load.get("profile", []),
        collapse_profile=collapse_load.get("profile", []),
        burst_rating_psi=burst_rating_design,
        collapse_rating_psi=effective_collapse_rating,
        tension_at_surface_lbs=total_tension,
        tension_rating_lbs=tension_rating_lbs,
        casing_weight_ppf=casing_weight_ppf,
        mud_weight_ppg=mud_weight_ppg,
        casing_length_ft=casing_length_ft,
    )

    # 15. Alerts
    if not safety_factors["all_pass"]:
        alerts.append(
            f"DESIGN FAILURE: {safety_factors['governing_criterion']} SF = "
            f"{safety_factors['governing_sf']:.2f} < minimum"
        )
    if triaxial["status"] == "FAIL":
        alerts.append(f"Triaxial VME FAIL: utilization {triaxial['utilization_pct']:.1f}%")
    if triaxial["status"] == "MARGINAL":
        alerts.append(f"Triaxial VME marginal: utilization {triaxial['utilization_pct']:.1f}%")
    if biaxial["reduction_factor"] < 0.8:
        alerts.append(
            f"Significant biaxial derating: collapse reduced by "
            f"{(1 - biaxial['reduction_factor']) * 100:.0f}%"
        )

    for criterion, data in safety_factors["results"].items():
        if data["safety_factor"] > 10:
            alerts.append(
                f"WARNING: SF {criterion} = {data['safety_factor']:.1f} is unusually high \u2014 "
                f"verify load case inputs"
            )

    # Build summary
    summary = {
        "selected_grade": grade_selection.get("selected_grade", ""),
        "max_burst_load_psi": max_burst,
        "max_collapse_load_psi": max_collapse,
        "total_tension_lbs": total_tension,
        "burst_rating_psi": burst_rating_design,
        "collapse_rating_psi": effective_collapse_rating,
        "collapse_rating_original_psi": collapse_rating.get("collapse_rating_psi", 0),
        "collapse_zone": collapse_rating.get("collapse_zone", ""),
        "tension_rating_lbs": round(tension_rating_lbs, 0),
        "sf_burst": safety_factors["results"]["burst"]["safety_factor"],
        "sf_collapse": safety_factors["results"]["collapse"]["safety_factor"],
        "sf_tension": safety_factors["results"]["tension"]["safety_factor"],
        "triaxial_status": triaxial["status"],
        "triaxial_utilization_pct": triaxial["utilization_pct"],
        "overall_status": safety_factors["overall_status"],
        "alerts": alerts,
        "governing_burst_scenario": burst_scenarios.get("governing_scenario", ""),
        "governing_collapse_scenario": collapse_scenarios.get("governing_scenario", ""),
        "tension_governing_scenario": tension_governing,
        "effective_yield_psi": effective_yield,
        "temp_derate_factor": temp_derate["derate_factor"],
    }

    return {
        "burst_load": burst_load,
        "collapse_load": collapse_load,
        "tension_load": tension_load,
        "burst_rating": burst_rating,
        "collapse_rating": collapse_rating,
        "biaxial_correction": biaxial,
        "biaxial_depth_profile": biaxial_depth,
        "triaxial_vme": triaxial,
        "grade_selection": grade_selection,
        "safety_factors": safety_factors,
        "sf_vs_depth": sf_vs_depth,
        "summary": summary,
        "burst_scenarios": burst_scenarios,
        "collapse_scenarios": collapse_scenarios,
        "tension_scenarios": {
            "running": tension_running,
            "stuck_pipe": tension_stuck,
            "governing": tension_governing,
        },
        "connection": connection,
        "wear": wear_result,
        "temperature_derating": temp_derate,
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
