"""
Cementing Engine — full simulation pipeline and recommendations generator.

Orchestrates all sub-module calculations into a single job simulation.

References:
- Nelson & Guillot: Well Cementing (2nd Edition, Schlumberger)
- API Spec 10A / 10B / RP 10B-2
- API RP 65-Part 2
"""
import math
from typing import Dict, Any, List

from .constants import CEMENT_CLASSES, infer_cement_class
from .volumes import calculate_fluid_volumes
from .displacement import calculate_displacement_schedule
from .ecd import calculate_ecd_during_job
from .pressure import (
    calculate_free_fall,
    calculate_utube_effect,
    calculate_bhp_schedule,
    calculate_lift_pressure,
)


def calculate_full_cementing(
    casing_od_in: float = 9.625,
    casing_id_in: float = 8.681,
    hole_id_in: float = 12.25,
    casing_shoe_md_ft: float = 10000.0,
    casing_shoe_tvd_ft: float = 9500.0,
    toc_md_ft: float = 5000.0,
    toc_tvd_ft: float = 4750.0,
    float_collar_md_ft: float = 9900.0,
    mud_weight_ppg: float = 10.5,
    spacer_density_ppg: float = 11.5,
    lead_cement_density_ppg: float = 13.5,
    tail_cement_density_ppg: float = 16.0,
    tail_length_ft: float = 500.0,
    spacer_volume_bbl: float = 25.0,
    excess_pct: float = 50.0,
    rat_hole_ft: float = 50.0,
    pump_rate_bbl_min: float = 5.0,
    pv_mud: float = 15.0,
    yp_mud: float = 10.0,
    fracture_gradient_ppg: float = 16.5,
    pore_pressure_ppg: float = 9.0,
) -> Dict[str, Any]:
    """
    Run complete cementing simulation: volumes, displacement,
    ECD, free-fall, U-tube, BHP schedule, and lift pressure.
    """
    # 1. Volumes
    volumes = calculate_fluid_volumes(
        casing_od_in=casing_od_in, casing_id_in=casing_id_in,
        hole_id_in=hole_id_in, casing_shoe_md_ft=casing_shoe_md_ft,
        toc_md_ft=toc_md_ft, float_collar_md_ft=float_collar_md_ft,
        lead_cement_density_ppg=lead_cement_density_ppg,
        tail_cement_density_ppg=tail_cement_density_ppg,
        tail_length_ft=tail_length_ft, spacer_volume_bbl=spacer_volume_bbl,
        excess_pct=excess_pct, rat_hole_ft=rat_hole_ft,
    )

    if "error" in volumes:
        return volumes

    # 2. Displacement Schedule
    displacement = calculate_displacement_schedule(
        spacer_volume_bbl=volumes["spacer_volume_bbl"],
        lead_cement_bbl=volumes["lead_cement_bbl"],
        tail_cement_bbl=volumes["tail_cement_bbl"],
        displacement_volume_bbl=volumes["displacement_volume_bbl"],
        pump_rate_bbl_min=pump_rate_bbl_min,
    )

    # 3. ECD During Job
    ecd_during = calculate_ecd_during_job(
        casing_shoe_tvd_ft=casing_shoe_tvd_ft,
        hole_id_in=hole_id_in, casing_od_in=casing_od_in,
        mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
        lead_cement_density_ppg=lead_cement_density_ppg,
        tail_cement_density_ppg=tail_cement_density_ppg,
        pump_rate_bbl_min=pump_rate_bbl_min,
        pv_mud=pv_mud, yp_mud=yp_mud,
        fracture_gradient_ppg=fracture_gradient_ppg,
        pore_pressure_ppg=pore_pressure_ppg,
    )

    # 4. Free-Fall
    free_fall = calculate_free_fall(
        casing_shoe_tvd_ft=casing_shoe_tvd_ft,
        mud_weight_ppg=mud_weight_ppg,
        cement_density_ppg=tail_cement_density_ppg,
        casing_id_in=casing_id_in, hole_id_in=hole_id_in,
        casing_od_in=casing_od_in,
    )

    # 5. U-Tube
    utube = calculate_utube_effect(
        casing_shoe_tvd_ft=casing_shoe_tvd_ft,
        mud_weight_ppg=mud_weight_ppg,
        cement_density_ppg=lead_cement_density_ppg,
        cement_top_tvd_ft=toc_tvd_ft,
        casing_id_in=casing_id_in, hole_id_in=hole_id_in,
        casing_od_in=casing_od_in,
    )

    # 6. BHP Schedule
    bhp = calculate_bhp_schedule(
        casing_shoe_tvd_ft=casing_shoe_tvd_ft,
        mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
        lead_cement_density_ppg=lead_cement_density_ppg,
        tail_cement_density_ppg=tail_cement_density_ppg,
        spacer_volume_bbl=volumes["spacer_volume_bbl"],
        lead_cement_bbl=volumes["lead_cement_bbl"],
        tail_cement_bbl=volumes["tail_cement_bbl"],
        displacement_volume_bbl=volumes["displacement_volume_bbl"],
        hole_id_in=hole_id_in, casing_od_in=casing_od_in,
        casing_id_in=casing_id_in, pump_rate_bbl_min=pump_rate_bbl_min,
        pv_mud=pv_mud, yp_mud=yp_mud,
    )

    # 7. Lift Pressure
    lift = calculate_lift_pressure(
        casing_shoe_tvd_ft=casing_shoe_tvd_ft,
        toc_tvd_ft=toc_tvd_ft,
        cement_density_ppg=lead_cement_density_ppg,
        mud_weight_ppg=mud_weight_ppg,
        hole_id_in=hole_id_in, casing_od_in=casing_od_in,
        casing_id_in=casing_id_in,
    )

    # Assemble alerts
    alerts = ecd_during.get("alerts", [])[:]
    if free_fall.get("free_fall_occurs"):
        alerts.append(
            f"Free-fall detected: ~{free_fall['free_fall_height_ft']:.0f} ft — "
            f"consider staged cementing or float equipment"
        )
    if utube.get("utube_occurs"):
        alerts.append(
            f"U-tube effect: {utube['pressure_imbalance_psi']:.0f} psi imbalance — "
            f"hold pressure after pumps stop"
        )

    # FIX-CEM-001: Spacer height and contact-time validation
    # Reference: API RP 10B; Nelson & Guillot "Well Cementing" Ch.5 — minimum 500 ft OR 10 min
    ann_cap = volumes["annular_capacity_bbl_ft"]
    if ann_cap > 0:
        spacer_height_ft = spacer_volume_bbl / ann_cap
        contact_time_min = spacer_volume_bbl / pump_rate_bbl_min if pump_rate_bbl_min > 0 else 0.0
        if spacer_height_ft < 500 and contact_time_min < 10:
            min_vol_bbl = math.ceil(500 * ann_cap)
            alerts.append(
                f"Spacer height {spacer_height_ft:.0f} ft < 500 ft minimum and contact time "
                f"{contact_time_min:.1f} min < 10 min (API RP 10B / Nelson & Guillot Ch. 5). "
                f"Increase spacer to {min_vol_bbl} bbl minimum to achieve 500 ft annular height."
            )

    # FIX-CEM-003: Cement class vs depth validation (API Spec 10A)
    tail_class = infer_cement_class(tail_cement_density_ppg)
    if tail_class:
        max_depth_ft = CEMENT_CLASSES[tail_class]["depth_ft"]
        if casing_shoe_tvd_ft > max_depth_ft:
            alerts.append(
                f"INFO: Tail cement ({tail_cement_density_ppg} ppg, Class {tail_class}) at "
                f"{casing_shoe_tvd_ft:.0f} ft TVD exceeds API 10A max depth of {max_depth_ft:,} ft "
                f"for Class {tail_class}. Verify thickening time and retarder with supplier."
            )

    summary = {
        "total_cement_bbl": volumes["total_cement_bbl"],
        "total_cement_sacks": volumes["lead_cement_sacks"] + volumes["tail_cement_sacks"],
        "displacement_bbl": volumes["displacement_volume_bbl"],
        "total_pump_bbl": volumes["total_pump_volume_bbl"],
        "job_time_hrs": displacement.get("total_time_hrs", 0),
        "max_ecd_ppg": ecd_during.get("max_ecd_ppg", 0),
        "fracture_margin_ppg": ecd_during.get("min_fracture_margin_ppg", 0),
        "max_bhp_psi": bhp.get("max_bhp_psi", 0),
        "lift_pressure_psi": lift.get("lift_pressure_psi", 0),
        "free_fall_ft": free_fall.get("free_fall_height_ft", 0),
        "utube_psi": utube.get("pressure_imbalance_psi", 0),
        "ecd_status": ecd_during.get("status", ""),
        "alerts": alerts,
    }

    return {
        "volumes": volumes,
        "displacement": displacement,
        "ecd_during_job": ecd_during,
        "free_fall": free_fall,
        "utube": utube,
        "bhp_schedule": bhp,
        "lift_pressure": lift,
        "summary": summary,
    }


def generate_recommendations(result: Dict[str, Any]) -> List[str]:
    """
    Generate operational recommendations from cementing simulation results.

    Parameters:
    - result: output from calculate_full_cementing()
    """
    recs: List[str] = []
    summary = result.get("summary", {})

    # ECD management
    margin = summary.get("fracture_margin_ppg", 999)
    if margin < 0:
        recs.append("CRITICAL: ECD exceeds fracture gradient. Reduce pump rate or cement density.")
    elif margin < 0.3:
        recs.append("Tight ECD margin — consider reducing pump rate during cement displacement.")
    elif margin < 0.5:
        recs.append("Monitor ECD closely during tail cement placement.")

    # Free-fall
    ff = result.get("free_fall", {})
    if ff.get("free_fall_occurs"):
        h = ff.get("free_fall_height_ft", 0)
        if h > 1000:
            recs.append(f"Significant free-fall ({h} ft). Use staged cementing or low-density lead.")
        elif h > 300:
            recs.append(f"Moderate free-fall ({h} ft). Monitor returns and pressures carefully.")

    # U-tube
    if result.get("utube", {}).get("utube_occurs"):
        recs.append("U-tube effect detected. Hold back-pressure after displacement.")

    # Volume check
    if result.get("volumes", {}).get("total_cement_bbl", 0) > 600:
        recs.append("Large cement volume — verify mixing capacity and bulk storage.")

    # Job time
    if summary.get("job_time_hrs", 0) > 4:
        recs.append("Extended job time — verify slurry thickening time exceeds job duration + safety.")

    if not recs:
        recs.append("All parameters within normal operating range. Standard execution recommended.")

    return recs
