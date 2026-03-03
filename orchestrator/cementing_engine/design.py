"""
Cementing Engine — spacer optimization and centralizer design.

References:
- API RP 10D-2: Centralizer Placement (Standoff calculation)
- Nelson & Guillot: Well Cementing Ch. 5 (Spacer design)
"""
import math
from typing import List, Dict, Any


def optimize_spacer(
    mud_density_ppg: float,
    mud_pv: float,
    mud_yp: float,
    slurry_density_ppg: float,
    slurry_pv: float,
    slurry_yp: float,
    hole_id_in: float,
    casing_od_in: float,
    casing_shoe_tvd_ft: float,
    pump_rate_bbl_min: float = 5.0,
    min_contact_time_min: float = 10.0,
    min_contact_length_ft: float = 500.0,
) -> Dict[str, Any]:
    """
    Calculate optimal spacer volume and properties.

    Rules:
    - Density: intermediate between mud and cement
    - Rheology hierarchy: PV_wash < PV_spacer < PV_mud for efficient displacement
    - Minimum 500 ft contact length OR 10 min contact time (API RP 10B)
    - Velocity > 150 ft/min for turbulent regime
    """
    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    if ann_cap <= 0 or pump_rate_bbl_min <= 0:
        return {"error": "Invalid annular geometry or pump rate"}

    q_gpm = pump_rate_bbl_min * 42.0
    v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)

    vol_from_length = min_contact_length_ft * ann_cap
    vol_from_time = pump_rate_bbl_min * min_contact_time_min
    spacer_volume = max(vol_from_length, vol_from_time)

    spacer_density = (mud_density_ppg + slurry_density_ppg) / 2.0
    spacer_pv = (mud_pv + slurry_pv) / 2.0 * 0.8
    spacer_yp = (mud_yp + slurry_yp) / 2.0 * 0.7

    contact_time = spacer_volume / pump_rate_bbl_min
    contact_length = spacer_volume / ann_cap

    d_eff = hole_id_in - casing_od_in
    if d_eff > 0 and spacer_pv > 0:
        re = 928 * spacer_density * v_ann * d_eff / spacer_pv
        flow_regime = "turbulent" if re > 2100 else "laminar"
    else:
        re = 0
        flow_regime = "unknown"

    return {
        "spacer_volume_bbl": round(spacer_volume, 1),
        "spacer_density_ppg": round(spacer_density, 1),
        "spacer_pv": round(spacer_pv, 1),
        "spacer_yp": round(spacer_yp, 1),
        "contact_time_min": round(contact_time, 1),
        "contact_length_ft": round(contact_length, 0),
        "annular_velocity_ftmin": round(v_ann, 1),
        "reynolds_number": round(re, 0),
        "flow_regime": flow_regime,
        "density_hierarchy_ok": mud_density_ppg < spacer_density < slurry_density_ppg,
        "rheology_hierarchy_ok": spacer_pv < mud_pv,
    }


def design_centralizers(
    casing_od_in: float,
    hole_id_in: float,
    casing_weight_ppf: float,
    inclination_profile: List[Dict[str, float]],
    centralizer_type: str = "bow_spring",
    target_standoff_pct: float = 67.0,
    restoring_force_lbf: float = 500.0,
) -> Dict[str, Any]:
    """
    Calculate centralizer spacing and standoff.

    Reference: API RP 10D-2 (Centralizer Placement)
    - Standoff without centralizer: SO_0 = radial_clearance * (1 - W*sin(inc)/F_restore)
    - Target: standoff > 67% (industry standard for good cement placement)
    """
    if hole_id_in <= casing_od_in:
        return {"error": "Hole ID must be > casing OD"}

    radial_clearance = (hole_id_in - casing_od_in) / 2.0

    if not inclination_profile:
        inclination_profile = [{"md": 0, "inc": 0}]

    if centralizer_type == "rigid":
        k_stiffness = 2000.0
    else:
        k_stiffness = restoring_force_lbf / radial_clearance if radial_clearance > 0 else 500.0

    results_by_section = []
    total_centralizers = 0
    total_drag_extra = 0.0

    for i in range(len(inclination_profile)):
        station = inclination_profile[i]
        md = station.get("md", 0)
        inc = station.get("inc", 0)
        inc_rad = math.radians(inc)

        w_lateral = casing_weight_ppf * math.sin(inc_rad)

        if k_stiffness > 0 and radial_clearance > 0:
            deflection = w_lateral * 40.0 / k_stiffness
            so_no_cent = max(1.0 - deflection / radial_clearance, 0.0) * 100.0
        else:
            so_no_cent = 100.0

        target_factor = 1.0 - target_standoff_pct / 100.0
        if w_lateral > 0.01 and target_factor > 0:
            spacing = restoring_force_lbf / (w_lateral * target_factor)
            spacing = max(min(spacing, 120.0), 20.0)
        else:
            spacing = 120.0

        section_length = 500.0
        if i < len(inclination_profile) - 1:
            section_length = inclination_profile[i + 1].get("md", md + 500) - md
        num_in_section = max(int(math.ceil(section_length / spacing)), 1)
        total_centralizers += num_in_section

        drag_per_cent = (
            0.3 * restoring_force_lbf if centralizer_type == "bow_spring"
            else 0.15 * restoring_force_lbf
        )
        section_drag = drag_per_cent * num_in_section
        total_drag_extra += section_drag

        results_by_section.append({
            "md_ft": round(md, 0),
            "inclination_deg": round(inc, 1),
            "standoff_no_cent_pct": round(so_no_cent, 1),
            "spacing_ft": round(spacing, 0),
            "num_centralizers": num_in_section,
            "drag_force_lbf": round(section_drag, 0),
        })

    return {
        "total_centralizers": total_centralizers,
        "total_drag_extra_lbf": round(total_drag_extra, 0),
        "centralizer_type": centralizer_type,
        "target_standoff_pct": target_standoff_pct,
        "restoring_force_lbf": restoring_force_lbf,
        "radial_clearance_in": round(radial_clearance, 3),
        "sections": results_by_section,
    }
