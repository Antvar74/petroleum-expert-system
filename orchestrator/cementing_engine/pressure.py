"""
Cementing Engine — pressure calculations.

Covers: free-fall, U-tube equilibrium, BHP schedule, and lift pressure.

References:
- Nelson & Guillot: Well Cementing Ch. 11 (Free-fall, U-tube)
- API RP 65-Part 2: Isolating Potential Flow Zones During Well Construction
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 3
"""
import math
from typing import Dict, Any


def calculate_free_fall(
    casing_shoe_tvd_ft: float,
    mud_weight_ppg: float,
    cement_density_ppg: float,
    casing_id_in: float,
    hole_id_in: float,
    casing_od_in: float,
    cement_column_ft: float = 0.0,
    friction_factor: float = 0.02,
) -> Dict[str, Any]:
    """
    Calculate free-fall height during cementing (corrected physical model).

    Physical model: cement falls inside casing while displacing mud
    upward in the annulus, until pressures equilibrate considering
    the volume-conservation coupling between both legs.

    Corrected formula (density does NOT cancel):
    h_ff = (rho_c - rho_m) * csg_cap * shoe_tvd /
           ((rho_c - rho_m) * csg_cap + rho_m * ann_cap + rho_c * csg_cap * friction)

    Friction drag opposes free-fall: F_drag = f * rho * V^2 * L / (2 * D_h)
    Simplified as friction_factor applied to driving pressure.
    """
    grad_mud = mud_weight_ppg * 0.052
    grad_cement = cement_density_ppg * 0.052

    if grad_cement <= grad_mud:
        return {
            "free_fall_height_ft": 0.0,
            "free_fall_occurs": False,
            "explanation": "No free-fall: cement density <= mud density",
            "cement_gradient_psi_ft": round(grad_cement, 4),
            "mud_gradient_psi_ft": round(grad_mud, 4),
        }

    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    csg_cap = casing_id_in ** 2 / 1029.4

    if ann_cap <= 0 or csg_cap <= 0:
        return {"error": "Invalid geometry"}

    vol_ratio = csg_cap / ann_cap
    delta_grad = grad_cement - grad_mud
    friction_resistance = friction_factor * grad_cement

    denominator = delta_grad * (1.0 + vol_ratio) + friction_resistance
    h_ff = 0.0 if denominator <= 0 else delta_grad * casing_shoe_tvd_ft / denominator
    h_ff = max(min(h_ff, casing_shoe_tvd_ft), 0.0)

    # Terminal velocity estimate (Stokes-modified for annular geometry)
    g = 32.174  # ft/s²
    rho_c_pcf = cement_density_ppg * 7.48
    rho_m_pcf = mud_weight_ppg * 7.48
    if rho_c_pcf > 0 and h_ff > 0:
        v_terminal = math.sqrt(2.0 * g * h_ff * (rho_c_pcf - rho_m_pcf) / rho_c_pcf)
        fall_time_sec = 2.0 * h_ff / max(v_terminal, 0.01)
    else:
        v_terminal = 0.0
        fall_time_sec = 0.0

    free_fall_vol_bbl = h_ff * csg_cap

    return {
        "free_fall_height_ft": round(h_ff, 1),
        "free_fall_volume_bbl": round(free_fall_vol_bbl, 1),
        "free_fall_occurs": h_ff > 10.0,
        "terminal_velocity_fts": round(v_terminal, 1),
        "estimated_fall_time_sec": round(fall_time_sec, 0),
        "cement_gradient_psi_ft": round(grad_cement, 4),
        "mud_gradient_psi_ft": round(grad_mud, 4),
        "delta_gradient_psi_ft": round(delta_grad, 4),
        "volume_ratio_csg_ann": round(vol_ratio, 3),
        "friction_factor": friction_factor,
        "explanation": (
            f"Cement free-falls ~{h_ff:.0f} ft due to {cement_density_ppg - mud_weight_ppg:.1f} ppg "
            f"density differential (friction-corrected)"
        ) if h_ff > 10 else "Minimal free-fall — manageable with standard procedures",
    }


def calculate_utube_effect(
    casing_shoe_tvd_ft: float,
    mud_weight_ppg: float,
    cement_density_ppg: float,
    cement_top_tvd_ft: float,
    casing_id_in: float,
    hole_id_in: float,
    casing_od_in: float,
    gel_strength_10s: float = 0.0,
    gel_strength_10min: float = 0.0,
    static_time_min: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate U-tube equilibrium when pumps stop, including gel strength resistance.

    Gel strength opposes flow: P_gel = 4 * tau_gel * L / D_h (Bingham in annular)
    If P_gel > hydrostatic imbalance → NO U-tube (gel holds the column).

    Parameters:
    - gel_strength_10s/10min: gel strength at 10 sec / 10 min (lbf/100sqft)
    - static_time_min: time since pumps stopped (for gel interpolation)
    """
    grad_mud = mud_weight_ppg * 0.052
    grad_cement = cement_density_ppg * 0.052

    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    csg_cap = casing_id_in ** 2 / 1029.4

    if ann_cap <= 0 or csg_cap <= 0:
        return {"error": "Invalid geometry"}

    cement_height_ann = max(casing_shoe_tvd_ft - cement_top_tvd_ft, 0.0)
    mud_height_ann = casing_shoe_tvd_ft - cement_height_ann

    p_annulus = grad_cement * cement_height_ann + grad_mud * mud_height_ann
    p_casing = grad_mud * casing_shoe_tvd_ft
    delta_p = p_annulus - p_casing

    # Gel interpolation (log between 10 s and 10 min)
    if static_time_min <= 0 or (gel_strength_10s <= 0 and gel_strength_10min <= 0):
        tau_gel = 0.0
    elif static_time_min <= 0.167:
        tau_gel = gel_strength_10s
    elif static_time_min >= 10.0:
        tau_gel = gel_strength_10min
    else:
        t_10s, t_10m = 0.167, 10.0
        frac = math.log(static_time_min / t_10s) / math.log(t_10m / t_10s)
        tau_gel = gel_strength_10s + frac * (gel_strength_10min - gel_strength_10s)

    d_h = hole_id_in - casing_od_in
    p_gel = 0.0
    if d_h > 0 and tau_gel > 0:
        p_gel = (
            4.0 * tau_gel * cement_height_ann / (300.0 * d_h)
            + 4.0 * tau_gel * casing_shoe_tvd_ft / (300.0 * casing_id_in)
        )

    net_delta_p = delta_p - p_gel
    gel_holds = net_delta_p <= 0

    if delta_p <= 0 or gel_holds:
        return {
            "utube_occurs": False,
            "pressure_imbalance_psi": round(max(delta_p, 0), 0),
            "gel_resistance_psi": round(p_gel, 0),
            "net_driving_pressure_psi": round(max(net_delta_p, 0), 0),
            "gel_holds_column": gel_holds and p_gel > 0,
            "fluid_drop_ft": 0.0,
            "fluid_drop_bbl": 0.0,
            "explanation": "Gel strength holds column — no U-tube flow" if gel_holds and p_gel > 0
                else "No U-tube: casing side is heavier or balanced",
            "p_annulus_psi": round(p_annulus, 0),
            "p_casing_psi": round(p_casing, 0),
        }

    combined_factor = (grad_cement - grad_mud) * (1 + csg_cap / ann_cap)
    h_drop = max(min(net_delta_p / combined_factor if combined_factor > 0 else 0.0,
                     casing_shoe_tvd_ft), 0.0)
    drop_vol = h_drop * csg_cap

    return {
        "utube_occurs": net_delta_p > 5.0,
        "pressure_imbalance_psi": round(delta_p, 0),
        "gel_resistance_psi": round(p_gel, 0),
        "net_driving_pressure_psi": round(net_delta_p, 0),
        "gel_holds_column": False,
        "fluid_drop_ft": round(h_drop, 1),
        "fluid_drop_bbl": round(drop_vol, 1),
        "p_annulus_psi": round(p_annulus, 0),
        "p_casing_psi": round(p_casing, 0),
        "explanation": (
            f"U-tube: {net_delta_p:.0f} psi net driving (after {p_gel:.0f} psi gel resistance) "
            f"causes ~{h_drop:.0f} ft fluid movement ({drop_vol:.1f} bbl)"
        ) if net_delta_p > 5 else "Negligible U-tube effect (gel partially resists)",
    }


def calculate_bhp_schedule(
    casing_shoe_tvd_ft: float,
    mud_weight_ppg: float,
    spacer_density_ppg: float,
    lead_cement_density_ppg: float,
    tail_cement_density_ppg: float,
    spacer_volume_bbl: float,
    lead_cement_bbl: float,
    tail_cement_bbl: float,
    displacement_volume_bbl: float,
    hole_id_in: float,
    casing_od_in: float,
    casing_id_in: float,
    pump_rate_bbl_min: float = 5.0,
    pv_mud: float = 15.0,
    yp_mud: float = 10.0,
    num_points: int = 30,
) -> Dict[str, Any]:
    """
    Calculate bottom-hole pressure (at shoe TVD) vs. cumulative
    volume pumped. Tracks hydrostatic changes as fluid column
    composition changes during displacement.

    BHP = P_hydrostatic_annulus + P_friction_annulus
    """
    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    csg_cap = casing_id_in ** 2 / 1029.4

    if ann_cap <= 0 or csg_cap <= 0 or casing_shoe_tvd_ft <= 0:
        return {"error": "Invalid geometry or TVD"}

    total_ann_ft = casing_shoe_tvd_ft
    total_vol = spacer_volume_bbl + lead_cement_bbl + tail_cement_bbl + displacement_volume_bbl

    if total_vol <= 0:
        return {"error": "Zero total volume"}

    d_eff = hole_id_in - casing_od_in
    if d_eff > 0 and pump_rate_bbl_min > 0:
        q_gpm = pump_rate_bbl_min * 42.0
        v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)
        dp_friction = (
            (pv_mud * v_ann * total_ann_ft) / (1000.0 * d_eff ** 2)
            + (yp_mud * total_ann_ft) / (200.0 * d_eff)
        )
    else:
        dp_friction = 0.0

    bhp_schedule = []
    step = total_vol / max(num_points - 1, 1)

    for i in range(num_points):
        v_cum = min(i * step, total_vol)
        t_min = v_cum / pump_rate_bbl_min if pump_rate_bbl_min > 0 else 0

        vol_in_annulus = v_cum
        ann_filled_ft = min(vol_in_annulus / ann_cap, total_ann_ft) if ann_cap > 0 else 0

        fluids_bbl = [
            ("Tail Cement", tail_cement_bbl, tail_cement_density_ppg),
            ("Lead Cement", lead_cement_bbl, lead_cement_density_ppg),
            ("Spacer", spacer_volume_bbl, spacer_density_ppg),
        ]

        remaining_ft = ann_filled_ft
        p_hydro = 0.0

        for _fname, fvol, fdens in fluids_bbl:
            if remaining_ft <= 0:
                break
            fluid_ft = min(fvol / ann_cap if ann_cap > 0 else 0, remaining_ft)
            if fluid_ft > 0:
                p_hydro += fdens * 0.052 * fluid_ft
                remaining_ft -= fluid_ft

        if remaining_ft > 0:
            p_hydro += mud_weight_ppg * 0.052 * remaining_ft

        unfilled_ft = total_ann_ft - ann_filled_ft
        if unfilled_ft > 0:
            p_hydro += mud_weight_ppg * 0.052 * unfilled_ft

        bhp = p_hydro + dp_friction

        bhp_schedule.append({
            "cumulative_bbl": round(v_cum, 1),
            "time_min": round(t_min, 1),
            "hydrostatic_psi": round(p_hydro, 0),
            "friction_psi": round(dp_friction, 0),
            "bhp_psi": round(bhp, 0),
            "bhp_ppg": round(bhp / (0.052 * casing_shoe_tvd_ft), 2) if casing_shoe_tvd_ft > 0 else 0,
        })

    max_bhp = max(p["bhp_psi"] for p in bhp_schedule)
    max_bhp_ppg = max(p["bhp_ppg"] for p in bhp_schedule)
    initial_bhp = bhp_schedule[0]["bhp_psi"] if bhp_schedule else 0
    final_bhp = bhp_schedule[-1]["bhp_psi"] if bhp_schedule else 0

    return {
        "bhp_schedule": bhp_schedule,
        "max_bhp_psi": round(max_bhp, 0),
        "max_bhp_ppg": round(max_bhp_ppg, 2),
        "initial_bhp_psi": round(initial_bhp, 0),
        "final_bhp_psi": round(final_bhp, 0),
        "friction_contribution_psi": round(dp_friction, 0),
        "total_volume_bbl": round(total_vol, 1),
    }


def calculate_lift_pressure(
    casing_shoe_tvd_ft: float,
    toc_tvd_ft: float,
    cement_density_ppg: float,
    mud_weight_ppg: float,
    hole_id_in: float,
    casing_od_in: float,
    casing_id_in: float,
    friction_factor: float = 1.0,
) -> Dict[str, Any]:
    """
    Calculate the surface pressure required to lift cement
    to the desired TOC (Top of Cement) in the annulus.

    P_lift = P_hydro_cement_column - P_hydro_mud_column + P_friction

    Parameters:
    - toc_tvd_ft: desired top of cement TVD
    - friction_factor: multiplier for friction (1.0 = standard)
    """
    cement_height_ft = casing_shoe_tvd_ft - toc_tvd_ft
    if cement_height_ft <= 0:
        return {
            "lift_pressure_psi": 0.0,
            "explanation": "TOC is at or below shoe — no lift needed",
        }

    p_cement = cement_density_ppg * 0.052 * cement_height_ft
    p_mud = mud_weight_ppg * 0.052 * cement_height_ft
    p_diff = p_cement - p_mud

    d_eff = hole_id_in - casing_od_in
    p_friction = 0.015 * cement_height_ft * friction_factor if d_eff > 0 else 0.0

    lift_pressure = max(p_diff + p_friction, 0.0)

    return {
        "lift_pressure_psi": round(lift_pressure, 0),
        "hydrostatic_cement_psi": round(p_cement, 0),
        "hydrostatic_mud_psi": round(p_mud, 0),
        "differential_psi": round(p_diff, 0),
        "friction_psi": round(p_friction, 0),
        "cement_height_ft": round(cement_height_ft, 0),
        "explanation": (
            f"Need {lift_pressure:.0f} psi surface pressure to lift "
            f"{cement_density_ppg} ppg cement {cement_height_ft:.0f} ft "
            f"against {mud_weight_ppg} ppg mud"
        ),
    }
