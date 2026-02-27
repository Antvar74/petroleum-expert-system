"""
Casing Design — Running Loads (Hookload During Casing Run)

Calculates hookload components during casing running operations:
buoyed weight, drag from survey, shock load, and bending load.

References:
- API 5CT: Specification for Casing and Tubing
- Lubinski: Developments in Petroleum Engineering (shock load formula)
- API RP 7G: Drill Stem Design and Operating Limits (bending)
"""
import math
from typing import List, Dict, Any, Optional


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
    - Drag: friction x normal force (from survey)
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
