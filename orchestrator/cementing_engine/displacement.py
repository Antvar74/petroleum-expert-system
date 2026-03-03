"""
Cementing Engine — displacement schedule and fluid interface tracking.

References:
- Nelson & Guillot: Well Cementing Ch. 12 (Displacement mechanics)
- API RP 10B: Recommended Practice for Testing Well Cements
"""
from typing import List, Dict, Any, Optional


def calculate_displacement_schedule(
    spacer_volume_bbl: float,
    lead_cement_bbl: float,
    tail_cement_bbl: float,
    displacement_volume_bbl: float,
    pump_rate_bbl_min: float = 5.0,
    num_points: int = 30,
    pump_schedule: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Track fluid interfaces vs. cumulative barrels pumped.

    Returns schedule with key events:
      - Spacer away (spacer done pumping)
      - Lead away
      - Tail away
      - Plug bump (displacement complete)

    Parameters:
    - pump_rate_bbl_min: average pump rate (used when pump_schedule is None)
    - num_points: resolution of schedule curve
    - pump_schedule: optional variable rate schedule
      [{rate_bpm, volume_bbl, stage_name}] — multi-stage pumping
    """
    if pump_schedule is not None and len(pump_schedule) > 0:
        return _displacement_variable_rate(
            spacer_volume_bbl, lead_cement_bbl, tail_cement_bbl,
            displacement_volume_bbl, pump_schedule, num_points
        )

    if pump_rate_bbl_min <= 0:
        return {"error": "Pump rate must be > 0"}

    v_spacer_end = spacer_volume_bbl
    v_lead_end = v_spacer_end + lead_cement_bbl
    v_tail_end = v_lead_end + tail_cement_bbl
    v_plug_bump = v_tail_end + displacement_volume_bbl
    total_volume = v_plug_bump

    if total_volume <= 0:
        return {"error": "Total pump volume is zero"}

    schedule = []
    step = total_volume / max(num_points - 1, 1)
    for i in range(num_points):
        v_cum = min(i * step, total_volume)
        t_min = v_cum / pump_rate_bbl_min

        if v_cum <= v_spacer_end:
            current_fluid = "Spacer"
            pct_complete = (v_cum / v_spacer_end * 100) if v_spacer_end > 0 else 100
        elif v_cum <= v_lead_end:
            current_fluid = "Lead Cement"
            pct_complete = ((v_cum - v_spacer_end) / lead_cement_bbl * 100) if lead_cement_bbl > 0 else 100
        elif v_cum <= v_tail_end:
            current_fluid = "Tail Cement"
            pct_complete = ((v_cum - v_lead_end) / tail_cement_bbl * 100) if tail_cement_bbl > 0 else 100
        else:
            current_fluid = "Displacement (Mud)"
            pct_complete = ((v_cum - v_tail_end) / displacement_volume_bbl * 100) if displacement_volume_bbl > 0 else 100

        schedule.append({
            "cumulative_bbl": round(v_cum, 1),
            "time_min": round(t_min, 1),
            "current_fluid": current_fluid,
            "fluid_pct_complete": round(min(pct_complete, 100), 1),
            "job_pct_complete": round(v_cum / total_volume * 100, 1),
        })

    events = [
        {"event": "Spacer Away", "volume_bbl": round(v_spacer_end, 1),
         "time_min": round(v_spacer_end / pump_rate_bbl_min, 1)},
        {"event": "Lead Cement Away", "volume_bbl": round(v_lead_end, 1),
         "time_min": round(v_lead_end / pump_rate_bbl_min, 1)},
        {"event": "Tail Cement Away", "volume_bbl": round(v_tail_end, 1),
         "time_min": round(v_tail_end / pump_rate_bbl_min, 1)},
        {"event": "Plug Bump / End Displacement", "volume_bbl": round(v_plug_bump, 1),
         "time_min": round(v_plug_bump / pump_rate_bbl_min, 1)},
    ]

    total_time_min = v_plug_bump / pump_rate_bbl_min

    return {
        "schedule": schedule,
        "events": events,
        "total_volume_bbl": round(total_volume, 1),
        "total_time_min": round(total_time_min, 1),
        "total_time_hrs": round(total_time_min / 60, 2),
        "pump_rate_bbl_min": pump_rate_bbl_min,
    }


def _displacement_variable_rate(
    spacer_volume_bbl: float,
    lead_cement_bbl: float,
    tail_cement_bbl: float,
    displacement_volume_bbl: float,
    pump_schedule: List[Dict[str, Any]],
    num_points: int = 30,
) -> Dict[str, Any]:
    """
    Displacement schedule with variable pump rates (multi-stage).

    pump_schedule: [{rate_bpm, volume_bbl, stage_name}]
    Each stage pumps at its own rate for its specified volume.
    """
    stages = []
    cum_vol = 0.0
    cum_time = 0.0
    for stage in pump_schedule:
        rate = stage.get("rate_bpm", 5.0)
        vol = stage.get("volume_bbl", 0.0)
        name = stage.get("stage_name", "Stage")
        if rate <= 0 or vol <= 0:
            continue
        t_stage = vol / rate
        stages.append({
            "stage_name": name,
            "rate_bpm": rate,
            "volume_bbl": vol,
            "start_vol": cum_vol,
            "end_vol": cum_vol + vol,
            "start_time": cum_time,
            "end_time": cum_time + t_stage,
        })
        cum_vol += vol
        cum_time += t_stage

    if not stages:
        return {"error": "No valid stages in pump_schedule"}

    total_volume = cum_vol
    total_time = cum_time

    v_spacer_end = spacer_volume_bbl
    v_lead_end = v_spacer_end + lead_cement_bbl
    v_tail_end = v_lead_end + tail_cement_bbl
    v_plug_bump = v_tail_end + displacement_volume_bbl

    def vol_to_time(v: float) -> float:
        """Convert cumulative volume to time using variable rates."""
        remaining = v
        t = 0.0
        for s in stages:
            stage_vol = s["volume_bbl"]
            if remaining <= stage_vol:
                t += remaining / s["rate_bpm"]
                return t
            remaining -= stage_vol
            t += stage_vol / s["rate_bpm"]
        if stages:
            t += remaining / stages[-1]["rate_bpm"]
        return t

    schedule = []
    step = total_volume / max(num_points - 1, 1)
    for i in range(num_points):
        v_cum = min(i * step, total_volume)
        t_min = vol_to_time(v_cum)

        if v_cum <= v_spacer_end:
            current_fluid = "Spacer"
            pct = (v_cum / v_spacer_end * 100) if v_spacer_end > 0 else 100
        elif v_cum <= v_lead_end:
            current_fluid = "Lead Cement"
            pct = ((v_cum - v_spacer_end) / lead_cement_bbl * 100) if lead_cement_bbl > 0 else 100
        elif v_cum <= v_tail_end:
            current_fluid = "Tail Cement"
            pct = ((v_cum - v_lead_end) / tail_cement_bbl * 100) if tail_cement_bbl > 0 else 100
        else:
            current_fluid = "Displacement (Mud)"
            pct = ((v_cum - v_tail_end) / displacement_volume_bbl * 100) if displacement_volume_bbl > 0 else 100

        current_rate = stages[-1]["rate_bpm"]
        for s in stages:
            if s["start_vol"] <= v_cum <= s["end_vol"]:
                current_rate = s["rate_bpm"]
                break

        schedule.append({
            "cumulative_bbl": round(v_cum, 1),
            "time_min": round(t_min, 1),
            "current_fluid": current_fluid,
            "fluid_pct_complete": round(min(pct, 100), 1),
            "job_pct_complete": round(v_cum / total_volume * 100, 1),
            "pump_rate_bbl_min": current_rate,
        })

    events = [
        {"event": "Spacer Away", "volume_bbl": round(v_spacer_end, 1),
         "time_min": round(vol_to_time(v_spacer_end), 1)},
        {"event": "Lead Cement Away", "volume_bbl": round(v_lead_end, 1),
         "time_min": round(vol_to_time(v_lead_end), 1)},
        {"event": "Tail Cement Away", "volume_bbl": round(v_tail_end, 1),
         "time_min": round(vol_to_time(v_tail_end), 1)},
        {"event": "Plug Bump / End Displacement", "volume_bbl": round(v_plug_bump, 1),
         "time_min": round(vol_to_time(v_plug_bump), 1)},
    ]

    max_rate_stage = max(stages, key=lambda s: s["rate_bpm"])

    return {
        "schedule": schedule,
        "events": events,
        "stages": stages,
        "total_volume_bbl": round(total_volume, 1),
        "total_time_min": round(total_time, 1),
        "total_time_hrs": round(total_time / 60, 2),
        "critical_stage": max_rate_stage["stage_name"],
        "variable_rate": True,
    }
