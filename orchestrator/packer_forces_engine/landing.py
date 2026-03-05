"""
Landing conditions — tubing weight at packer with drag and buoyancy.

Defines the baseline state from which all subsequent force changes
(pressure, temperature) are calculated.

References:
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
- API TR 5C3: Casing and Tubing Buckling in Wellbores
"""
import math
from typing import Dict, Any, List, Optional

from .geometry import STEEL_DENSITY_PPG


def calculate_landing_conditions(
    tubing_sections: List[Dict[str, Any]],
    survey_stations: Optional[List[Dict[str, float]]] = None,
    mud_weight_ppg: float = 8.34,
    friction_factor: float = 0.30,
    packer_depth_tvd_ft: float = 10000.0,
    set_down_weight_lbs: float = 5000.0,
) -> Dict[str, Any]:
    """
    Calculate tubing weight at packer (landing conditions) and initial forces.

    Accounts for buoyancy, drag in deviated wells, and set-down weight.
    Landing conditions define the baseline from which all subsequent
    force changes (pressure, temperature) are calculated.

    Args:
        tubing_sections: list of {od, id_inner, length_ft, weight_ppf}
        survey_stations: list of {md_ft, inclination_deg} (optional for drag)
        mud_weight_ppg: mud weight (ppg)
        friction_factor: friction coefficient for drag (0.15-0.40)
        packer_depth_tvd_ft: packer TVD (ft)
        set_down_weight_lbs: additional weight for packer setting (lbs)

    Returns:
        Dict with tubing_weight_at_packer, buoyancy, drag, set_down_weight.
    """
    if not tubing_sections:
        return {"error": "No tubing sections provided"}

    bf = max(0.01, 1.0 - mud_weight_ppg / STEEL_DENSITY_PPG)

    total_weight_air = 0.0
    total_weight_buoyed = 0.0
    total_length_ft = 0.0

    for section in tubing_sections:
        w_ppf = section.get("weight_ppf", 9.3)
        l_ft = section.get("length_ft", 0)
        section_weight = w_ppf * l_ft
        total_weight_air += section_weight
        total_weight_buoyed += section_weight * bf
        total_length_ft += l_ft

    # Drag calculation
    total_drag = 0.0
    if survey_stations and len(survey_stations) > 1:
        for i in range(1, len(survey_stations)):
            md_prev = survey_stations[i - 1].get("md_ft", 0)
            md_curr = survey_stations[i].get("md_ft", 0)
            inc_prev = survey_stations[i - 1].get("inclination_deg", 0)
            inc_curr = survey_stations[i].get("inclination_deg", 0)

            dl = md_curr - md_prev
            inc_avg = math.radians((inc_prev + inc_curr) / 2.0)

            avg_ppf = total_weight_buoyed / total_length_ft if total_length_ft > 0 else 9.0
            w_segment = avg_ppf * dl

            drag_segment = friction_factor * abs(w_segment * math.sin(inc_avg))
            total_drag += drag_segment
    else:
        avg_inc = math.atan(0.3) if packer_depth_tvd_ft > 0 else 0.0
        total_drag = friction_factor * total_weight_buoyed * abs(math.sin(avg_inc)) * 0.3

    weight_at_packer = total_weight_buoyed - total_drag
    landing_force = weight_at_packer + set_down_weight_lbs

    return {
        "tubing_weight_air_lbs": round(total_weight_air, 0),
        "tubing_weight_buoyed_lbs": round(total_weight_buoyed, 0),
        "buoyancy_factor": round(bf, 4),
        "drag_force_lbs": round(total_drag, 0),
        "weight_at_packer_lbs": round(weight_at_packer, 0),
        "set_down_weight_lbs": round(set_down_weight_lbs, 0),
        "total_landing_force_lbs": round(landing_force, 0),
        "total_tubing_length_ft": round(total_length_ft, 1),
        "packer_depth_tvd_ft": packer_depth_tvd_ft,
        "friction_factor": friction_factor,
        "min_set_down_recommendations": {
            "typical_mechanical": 5000,
            "hydraulic_set": 0,
            "permanent": 10000,
        },
    }
