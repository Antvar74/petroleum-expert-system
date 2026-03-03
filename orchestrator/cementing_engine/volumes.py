"""
Cementing Engine — fluid volume calculations.

References:
- Nelson & Guillot: Well Cementing Ch. 10 (Volume calculations)
- API RP 10B-2: Recommended Practice for Testing Well Cements
"""
from typing import List, Dict, Any


def calculate_fluid_volumes(
    casing_od_in: float,
    casing_id_in: float,
    hole_id_in: float,
    casing_shoe_md_ft: float,
    toc_md_ft: float,
    float_collar_md_ft: float,
    lead_cement_density_ppg: float = 13.5,
    tail_cement_density_ppg: float = 16.0,
    tail_length_ft: float = 500.0,
    spacer_volume_bbl: float = 25.0,
    excess_pct: float = 50.0,
    rat_hole_ft: float = 50.0,
) -> Dict[str, Any]:
    """
    Calculate volumes of each fluid in the cementing job.

    Geometry:
      annular_capacity = (hole_id^2 - casing_od^2) / 1029.4   [bbl/ft]
      casing_capacity  = casing_id^2 / 1029.4                   [bbl/ft]

    Parameters:
    - casing_od_in / casing_id_in: casing dimensions
    - hole_id_in: open-hole diameter
    - casing_shoe_md_ft: measured depth of casing shoe
    - toc_md_ft: depth of top of cement (measured from surface)
    - float_collar_md_ft: depth of float collar
    - lead_cement_density_ppg / tail_cement_density_ppg: slurry densities
    - tail_length_ft: length of tail cement above shoe
    - spacer_volume_bbl: spacer volume
    - excess_pct: percentage excess cement for washouts (e.g., 50 = +50%)
    - rat_hole_ft: length below shoe (open hole below casing)
    """
    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    csg_cap = casing_id_in ** 2 / 1029.4

    if ann_cap <= 0 or csg_cap <= 0:
        return {"error": "Invalid geometry: check hole_id > casing_od and casing_id > 0"}

    cement_top_to_shoe = max(casing_shoe_md_ft - toc_md_ft, 0.0)

    tail_annular_length = min(tail_length_ft, cement_top_to_shoe)
    lead_annular_length = cement_top_to_shoe - tail_annular_length

    excess_factor = 1.0 + excess_pct / 100.0
    lead_annular_bbl = lead_annular_length * ann_cap * excess_factor
    tail_annular_bbl = tail_annular_length * ann_cap * excess_factor
    rat_hole_bbl = rat_hole_ft * ann_cap * excess_factor

    shoe_to_float = max(casing_shoe_md_ft - float_collar_md_ft, 0.0)
    tail_inside_bbl = shoe_to_float * csg_cap

    total_lead_bbl = lead_annular_bbl
    total_tail_bbl = tail_annular_bbl + tail_inside_bbl + rat_hole_bbl
    total_cement_bbl = total_lead_bbl + total_tail_bbl

    displacement_bbl = float_collar_md_ft * csg_cap

    # 1 sack Class G ≈ 1.15 ft³; 1 bbl = 5.615 ft³
    lead_sacks = total_lead_bbl * 5.615 / 1.15 if total_lead_bbl > 0 else 0
    tail_sacks = total_tail_bbl * 5.615 / 1.15 if total_tail_bbl > 0 else 0

    total_pump_bbl = spacer_volume_bbl + total_cement_bbl + displacement_bbl

    return {
        "annular_capacity_bbl_ft": round(ann_cap, 4),
        "casing_capacity_bbl_ft": round(csg_cap, 4),
        "lead_cement_bbl": round(total_lead_bbl, 1),
        "tail_cement_bbl": round(total_tail_bbl, 1),
        "total_cement_bbl": round(total_cement_bbl, 1),
        "lead_cement_sacks": round(lead_sacks, 0),
        "tail_cement_sacks": round(tail_sacks, 0),
        "spacer_volume_bbl": round(spacer_volume_bbl, 1),
        "displacement_volume_bbl": round(displacement_bbl, 1),
        "total_pump_volume_bbl": round(total_pump_bbl, 1),
        "lead_annular_length_ft": round(lead_annular_length, 0),
        "tail_annular_length_ft": round(tail_annular_length, 0),
        "shoe_track_length_ft": round(shoe_to_float, 0),
        "excess_pct": excess_pct,
        "lead_density_ppg": lead_cement_density_ppg,
        "tail_density_ppg": tail_cement_density_ppg,
    }


def calculate_fluid_volumes_caliper(
    caliper_data: List[Dict[str, float]],
    casing_od_in: float,
    toc_md_ft: float,
    casing_shoe_md_ft: float,
    lead_cement_density_ppg: float = 13.5,
    tail_cement_density_ppg: float = 16.0,
    tail_length_ft: float = 500.0,
    excess_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate annular volumes using caliper log data instead of gauge diameter.

    caliper_data: [{md, diameter}] — measured depth and actual hole diameter.
    Computes real annular volume per section and compares against nominal.

    Reference: API RP 10B-2 (standard OptiCem/CemCADE practice)
    """
    if not caliper_data or len(caliper_data) < 2:
        return {"error": "Caliper data requires at least 2 points"}
    if casing_od_in <= 0:
        return {"error": "Invalid casing OD"}

    sorted_cal = sorted(caliper_data, key=lambda p: p["md"])

    total_real_vol = 0.0
    total_nominal_vol = 0.0
    sections = []
    washout_max = 0.0
    washout_max_md = 0.0

    for i in range(len(sorted_cal) - 1):
        md_top = sorted_cal[i]["md"]
        md_bot = sorted_cal[i + 1]["md"]
        d_top = sorted_cal[i]["diameter"]
        d_bot = sorted_cal[i + 1]["diameter"]
        dL = md_bot - md_top
        if dL <= 0:
            continue

        d_avg = (d_top + d_bot) / 2.0
        d_nominal = min(d_top, d_bot)

        real_ann_cap = max((d_avg ** 2 - casing_od_in ** 2) / 1029.4, 0.0)
        nominal_ann_cap = max((d_nominal ** 2 - casing_od_in ** 2) / 1029.4, 0.0)

        real_vol = real_ann_cap * dL
        nominal_vol = nominal_ann_cap * dL

        wo_pct = ((d_avg - d_nominal) / d_nominal * 100) if d_nominal > 0 else 0.0
        if wo_pct > washout_max:
            washout_max = wo_pct
            washout_max_md = (md_top + md_bot) / 2.0

        total_real_vol += real_vol
        total_nominal_vol += nominal_vol

        sections.append({
            "md_top": round(md_top, 0),
            "md_bot": round(md_bot, 0),
            "caliper_avg_in": round(d_avg, 2),
            "annular_volume_bbl": round(real_vol, 2),
            "washout_pct": round(wo_pct, 1),
        })

    excess_real = (
        (total_real_vol - total_nominal_vol) / total_nominal_vol * 100
        if total_nominal_vol > 0 else 0.0
    )
    excess_factor = 1.0 + excess_pct / 100.0
    total_with_excess = total_real_vol * excess_factor

    return {
        "total_caliper_volume_bbl": round(total_real_vol, 1),
        "total_nominal_volume_bbl": round(total_nominal_vol, 1),
        "caliper_excess_pct": round(excess_real, 1),
        "total_with_user_excess_bbl": round(total_with_excess, 1),
        "washout_max_pct": round(washout_max, 1),
        "washout_max_md": round(washout_max_md, 0),
        "sections": sections,
        "num_sections": len(sections),
    }
