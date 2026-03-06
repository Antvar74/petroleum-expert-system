"""
Torque & Drag Engine — Hybrid Stiff-String Model.

Extends Johancsik soft-string with Mitchell EI-based lateral contact
force correction for BHA/collar sections and high-DLS zones.

References:
- Mitchell (1999), SPE 56901 — stiff-string correction
- Johancsik, Friesen & Dawson (1984), SPE 11380
"""
import math
from typing import List, Dict, Any

from .buckling import buckling_check, STEEL_E


def compute_torque_drag_stiff(
    survey: List[Dict[str, Any]],
    drillstring: List[Dict[str, Any]],
    friction_cased: float,
    friction_open: float,
    operation: str,
    mud_weight: float,
    wob: float = 0.0,
    rpm: float = 0.0,
    casing_shoe_md: float = 0.0,
    stiffness_threshold_dls: float = 3.0,
    stiffness_threshold_od: float = 6.0
) -> Dict[str, Any]:
    """
    Hybrid Stiff-String Model for Torque & Drag.

    Extends the Johancsik soft-string model with bending stiffness correction
    (Mitchell approximation) for BHA/collar sections or high-DLS zones.

    The stiff-string correction adds EI-based lateral contact force to the
    Johancsik normal force:
        F_contact = sqrt(Fn_soft^2 + (EI * curvature_change / L)^2)

    Stiffness correction is applied ONLY when:
        - Section OD >= stiffness_threshold_od (default 6", i.e., collars/BHA), OR
        - Local DLS > stiffness_threshold_dls (default 3 deg/100ft)

    Parameters:
    - Same as compute_torque_drag() plus:
    - stiffness_threshold_dls: DLS above which EI correction is applied (deg/100ft)
    - stiffness_threshold_od: OD above which EI correction is always applied (inches)

    Returns:
    - Same structure as compute_torque_drag() plus model='stiff_string' in summary
      and 'stiffness_correction' per station result
    """
    if len(survey) < 2:
        return {"error": "Need at least 2 survey stations"}

    direction = 1.0
    if operation in ("trip_in", "sliding"):
        direction = -1.0

    # Build drillstring map (same as soft-string)
    sorted_ds = sorted(drillstring, key=lambda x: x.get("order_from_bit", 0))
    ds_map = []
    cum = 0.0
    for sec in sorted_ds:
        ds_map.append({
            "start": cum,
            "end": cum + sec["length"],
            "weight": sec["weight"],
            "od": sec["od"],
            "id_inner": sec.get("id_inner", sec["od"] - 1.0)
        })
        cum += sec["length"]

    bit_md = survey[-1]["md"]

    def get_ds_at_md(md_val):
        dist_from_bit = max(bit_md - md_val, 0.0)
        for sec in ds_map:
            if sec["start"] <= dist_from_bit <= sec["end"]:
                return sec
        return ds_map[-1] if ds_map else {"weight": 20.0, "od": 5.0, "id_inner": 4.276}

    bf = 1.0 - (mud_weight / 65.5)
    e = STEEL_E

    station_results = []

    # Start at bit
    if operation in ("rotating", "sliding"):
        fa = -wob * 1000.0
    else:
        fa = 0.0

    cumulative_torque = 0.0

    # Process bottom to top
    for i in range(len(survey) - 1, 0, -1):
        s_lower = survey[i]
        s_upper = survey[i - 1]

        md_lower = s_lower["md"]
        md_upper = s_upper["md"]
        delta_md = md_lower - md_upper

        if delta_md <= 0:
            continue

        inc_lower = math.radians(s_lower["inclination"])
        inc_upper = math.radians(s_upper["inclination"])
        azi_lower = math.radians(s_lower["azimuth"])
        azi_upper = math.radians(s_upper["azimuth"])

        d_inc = inc_upper - inc_lower
        d_azi = azi_upper - azi_lower
        avg_inc = (inc_upper + inc_lower) / 2.0

        # Drillstring properties at midpoint
        mid_md = (md_lower + md_upper) / 2.0
        ds = get_ds_at_md(mid_md)

        # Buoyed weight
        w = ds["weight"] * bf * delta_md

        # Friction factor
        mu = friction_open
        if mid_md < casing_shoe_md:
            mu = friction_cased

        # --- Soft-string normal force (Johancsik) ---
        term1 = fa * d_inc + w * math.sin(avg_inc)
        term2 = fa * math.sin(avg_inc) * d_azi
        fn_soft = math.sqrt(term1**2 + term2**2)

        # --- Stiffness correction (Mitchell approximation) ---
        od = ds["od"]
        id_inner = ds.get("id_inner", od - 1.0)
        i_moment = math.pi / 64.0 * (od**4 - id_inner**4)  # in^4
        ei = e * i_moment  # lb-in^2

        # Dogleg / curvature change over interval
        cos_dl = (math.cos(inc_upper - inc_lower)
                  - math.sin(inc_lower) * math.sin(inc_upper) * (1 - math.cos(azi_upper - azi_lower)))
        cos_dl = max(-1.0, min(1.0, cos_dl))
        dl = math.acos(cos_dl)
        dls_local = math.degrees(dl) / delta_md * 100.0 if delta_md > 0 else 0.0

        # Decide whether to apply stiffness correction
        apply_stiff = (od >= stiffness_threshold_od) or (dls_local > stiffness_threshold_dls)
        stiff_correction = 0.0

        if apply_stiff and delta_md > 0:
            # Curvature change per unit length (rad/in)
            curvature_change = dl / (delta_md * 12.0)  # convert ft to inches
            # Bending stiffness force contribution
            f_ei = ei * curvature_change / (delta_md * 12.0)  # force from EI
            stiff_correction = f_ei
            fn = math.sqrt(fn_soft**2 + f_ei**2)
        else:
            fn = fn_soft

        # Drag force
        f_drag = mu * fn

        # Update axial force
        if operation == "rotating":
            fa = fa + w * math.cos(avg_inc)
        else:
            fa = fa + w * math.cos(avg_inc) + direction * f_drag

        # Torque
        torque_increment = 0.0
        if operation in ("rotating", "back_ream"):
            r_contact = od / 2.0 / 12.0
            torque_increment = mu * fn * r_contact
            cumulative_torque += torque_increment

        # Buckling check
        buckling = buckling_check(
            fa, avg_inc, ds, mud_weight, delta_md, mid_md, casing_shoe_md
        )

        station_results.append({
            "md": round(md_upper, 1),
            "tvd": s_upper.get("tvd", 0),
            "inclination": s_upper["inclination"],
            "axial_force": round(fa, 0),
            "normal_force": round(fn, 0),
            "normal_force_soft": round(fn_soft, 0),
            "stiffness_correction": round(stiff_correction, 0),
            "drag": round(f_drag, 0),
            "torque": round(cumulative_torque, 0),
            "dls_local": round(dls_local, 2),
            "buckling_status": buckling
        })

    station_results.reverse()

    surface_hookload = fa / 1000.0
    surface_torque = cumulative_torque

    alerts = []
    if surface_hookload < 0:
        alerts.append("Negative hookload at surface — check WOB/friction")
    for sr in station_results:
        if sr["buckling_status"] != "OK":
            alerts.append(f"Buckling at MD {sr['md']} ft: {sr['buckling_status']}")
            break

    max_side_force = max((sr["normal_force"] for sr in station_results), default=0)

    # Count stations with stiffness correction applied
    stiff_stations = sum(1 for sr in station_results if sr["stiffness_correction"] > 0)

    summary = {
        "surface_hookload_klb": round(surface_hookload, 1),
        "surface_torque_ftlb": round(surface_torque, 0),
        "max_side_force_lb": round(max_side_force, 0),
        "operation": operation,
        "friction_cased": friction_cased,
        "friction_open": friction_open,
        "buoyancy_factor": round(bf, 4),
        "model": "stiff_string",
        "stiff_stations_count": stiff_stations,
        "stiffness_threshold_dls": stiffness_threshold_dls,
        "stiffness_threshold_od": stiffness_threshold_od,
        "alerts": alerts
    }

    return {
        "station_results": station_results,
        "summary": summary
    }
