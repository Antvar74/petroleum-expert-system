"""
Torque & Drag Engine — Johancsik Soft-String Model.

References:
- Johancsik, Friesen & Dawson (1984), SPE 11380
- Applied Drilling Engineering (Bourgoyne et al.)
"""
import math
from typing import List, Dict, Any, Optional

from .buckling import buckling_check, casing_id_estimate, STEEL_E


def compute_torque_drag(
    survey: List[Dict[str, Any]],
    drillstring: List[Dict[str, Any]],
    friction_cased: float,
    friction_open: float,
    operation: str,
    mud_weight: float,
    wob: float = 0.0,
    rpm: float = 0.0,
    casing_shoe_md: float = 0.0,
    ecd_profile: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Johancsik Soft-String Model for Torque & Drag.

    Parameters:
    - survey: list of stations with md, inclination, azimuth (degrees)
    - drillstring: list of sections with od, id_inner, weight (lb/ft), length, order_from_bit
    - friction_cased/open: friction factors
    - operation: 'rotating', 'sliding', 'trip_in', 'trip_out', 'back_ream'
    - mud_weight: ppg
    - wob: weight on bit (klb) — only for rotating/sliding
    - rpm: rotary speed (only for rotating)
    - casing_shoe_md: casing shoe depth for friction factor selection
    - ecd_profile: optional list of {tvd, ecd} from HydraulicsEngine for
      local buoyancy correction. If provided, uses ECD at each station
      instead of constant mud_weight for buoyancy factor.
    """
    if len(survey) < 2:
        return {"error": "Need at least 2 survey stations"}

    # Determine direction factor
    direction = 1.0  # +1 for trip out (tension increases going up)
    if operation in ("trip_in", "sliding"):
        direction = -1.0

    # Build weight profile per station from drillstring
    sorted_ds = sorted(drillstring, key=lambda x: x.get("order_from_bit", 0))

    # Build cumulative length map from bit
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
        """Get drillstring properties at a given MD."""
        dist_from_bit = bit_md - md_val
        if dist_from_bit < 0:
            dist_from_bit = 0
        for sec in ds_map:
            if sec["start"] <= dist_from_bit <= sec["end"]:
                return sec
        return ds_map[-1] if ds_map else {"weight": 20.0, "od": 5.0, "id_inner": 4.276}

    # Buoyancy factor (base — may be overridden per-station with ECD profile)
    bf = 1.0 - (mud_weight / 65.5)
    use_ecd_buoyancy = ecd_profile is not None and len(ecd_profile) >= 2

    def _interpolate_ecd(tvd_val):
        """Linearly interpolate ECD at a given TVD from the ECD profile."""
        if not ecd_profile or len(ecd_profile) < 2:
            return mud_weight
        sorted_prof = sorted(ecd_profile, key=lambda p: p.get("tvd", 0))
        if tvd_val <= sorted_prof[0]["tvd"]:
            return sorted_prof[0]["ecd"]
        if tvd_val >= sorted_prof[-1]["tvd"]:
            return sorted_prof[-1]["ecd"]
        for j in range(len(sorted_prof) - 1):
            t0, t1 = sorted_prof[j]["tvd"], sorted_prof[j + 1]["tvd"]
            if t0 <= tvd_val <= t1:
                frac = (tvd_val - t0) / (t1 - t0) if (t1 - t0) > 0 else 0
                return sorted_prof[j]["ecd"] + frac * (sorted_prof[j + 1]["ecd"] - sorted_prof[j]["ecd"])
        return mud_weight

    station_results = []

    # Start at bit: axial force = -WOB (compression) for drilling operations
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

        # Buoyed weight: use local ECD for buoyancy if profile available
        if use_ecd_buoyancy:
            est_tvd_mid = mid_md * math.cos(avg_inc)
            ecd_local = _interpolate_ecd(est_tvd_mid)
            bf_local = 1.0 - (ecd_local / 65.5)
        else:
            bf_local = bf
        w = ds["weight"] * bf_local * delta_md

        # Friction factor selection
        mu = friction_open
        if mid_md < casing_shoe_md:
            mu = friction_cased

        # Normal force (Johancsik)
        term1 = fa * d_inc + w * math.sin(avg_inc)
        term2 = fa * math.sin(avg_inc) * d_azi
        fn = math.sqrt(term1**2 + term2**2)

        # Drag force (base)
        f_drag = mu * fn

        # Buckling check — BEFORE force update so we can add post-buckling drag
        buckling = buckling_check(
            fa, avg_inc, ds, mud_weight, delta_md, mid_md, casing_shoe_md
        )

        # Post-buckling drag (Mitchell 1999 / Lubinski)
        f_drag_extra = 0.0
        torque_extra = 0.0
        if buckling != "OK" and fa < 0:
            od = ds["od"]
            id_inner = ds.get("id_inner", od - 1.0)
            i_mom = math.pi / 64.0 * (od**4 - id_inner**4)
            ei_local = STEEL_E * i_mom

            if mid_md < casing_shoe_md:
                hole_id = casing_id_estimate(od)
            else:
                hole_id = od + 3.0
            r_clear = max((hole_id - od) / 2.0, 0.5)

            w_per_in = ds["weight"] * bf / 12.0
            compression = abs(fa)

            if buckling == "SINUSOIDAL":
                sin_inc = max(math.sin(avg_inc), 0.01)
                w_n = w_per_in * sin_inc
                if w_n > 0 and r_clear > 0:
                    f_drag_extra = mu * compression**2 / (4.0 * w_n * r_clear * delta_md * 12.0)
            elif buckling == "HELICAL":
                if ei_local > 0:
                    f_drag_extra = mu * r_clear * compression**2 / (2.0 * ei_local) * delta_md * 12.0

            if operation in ("rotating", "back_ream"):
                r_contact_in = od / 2.0
                torque_extra = mu * r_clear * compression * r_contact_in / 12.0

        f_drag_total = f_drag + f_drag_extra

        # Update axial force going upward
        if operation == "rotating":
            fa = fa + w * math.cos(avg_inc)
        else:
            fa = fa + w * math.cos(avg_inc) + direction * f_drag_total

        # Torque calculation
        torque_increment = 0.0
        if operation in ("rotating", "back_ream"):
            r_contact = ds["od"] / 2.0 / 12.0
            torque_increment = mu * fn * r_contact + torque_extra
            cumulative_torque += torque_increment

        station_results.append({
            "md": round(md_upper, 1),
            "tvd": s_upper.get("tvd", 0),
            "inclination": s_upper["inclination"],
            "axial_force": round(fa, 0),
            "normal_force": round(fn, 0),
            "drag": round(f_drag_total, 0),
            "drag_extra_buckling": round(f_drag_extra, 0),
            "torque": round(cumulative_torque, 0),
            "buckling_status": buckling
        })

    # Reverse so results go top to bottom
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

    summary = {
        "surface_hookload_klb": round(surface_hookload, 1),
        "surface_torque_ftlb": round(surface_torque, 0),
        "max_side_force_lb": round(max_side_force, 0),
        "operation": operation,
        "friction_cased": friction_cased,
        "friction_open": friction_open,
        "buoyancy_factor": round(bf, 4),
        "alerts": alerts
    }

    return {
        "station_results": station_results,
        "summary": summary
    }
