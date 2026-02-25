"""Cumulative fatigue damage tracking (Miner's rule, S-N curves).

References:
- Miner (1945): Cumulative damage in fatigue
- API 5DP: Drill pipe specifications and endurance limits
"""
import math
from typing import Dict, Any, List, Optional

# Shared steel constants
STEEL_E = 30e6  # Young's modulus (psi)


def calculate_fatigue_damage(
    drillstring_od: float,
    drillstring_id: float,
    drillstring_grade: str = "S-135",
    survey_stations: Optional[List[Dict[str, float]]] = None,
    rpm: float = 120.0,
    hours_per_stand: float = 0.5,
    vibration_severity: float = 0.3,
    total_rotating_hours: float = 100.0
) -> Dict[str, Any]:
    """
    Calculate cumulative fatigue damage on drillstring using Miner's rule.

    Cyclic bending stress: sigma_bend = EI * curvature * OD/2
    Cycles per hour: N_cycles = RPM * 60
    S-N curve: N_f = (S_e / sigma_a)^b  where S_e = endurance limit
    Miner: D = Sum(n_i / N_f_i)  -> failure when D >= 1.0

    Args:
        drillstring_od: pipe OD (inches)
        drillstring_id: pipe ID (inches)
        drillstring_grade: 'E-75', 'X-95', 'G-105', 'S-135', 'V-150'
        survey_stations: list of {md_ft, inclination_deg, dls_deg_100ft}
        rpm: average RPM
        hours_per_stand: time per stand at each station (hours)
        vibration_severity: severity multiplier (0-1, from stick_slip or lateral)
        total_rotating_hours: total hours rotating (for uniform estimate)

    Returns:
        Dict with cumulative damage, remaining life, critical joints, S-N params.
    """
    e = STEEL_E

    # Endurance limits by grade (approximation from API 5DP)
    endurance_limits = {
        "E-75": 20000, "X-95": 22000, "G-105": 23000,
        "S-135": 25000, "V-150": 26000,
    }
    s_e = endurance_limits.get(drillstring_grade, 25000)  # psi (endurance limit)
    b_exponent = 5.0  # S-N slope exponent (typical for drillpipe)

    # Moment of inertia
    i_moment = math.pi * (drillstring_od ** 4 - drillstring_id ** 4) / 64.0

    cycles_per_hour = rpm * 60.0

    # If survey provided, compute per-station damage
    damage_by_station = []
    cumulative_damage = 0.0

    if survey_stations and len(survey_stations) > 0:
        for station in survey_stations:
            dls = station.get("dls_deg_100ft", 0)
            md = station.get("md_ft", 0)

            # Bending stress from DLS: sigma_b = E * OD * pi * DLS / (2 * 100 * 180 * 12)
            # DLS in deg/100ft -> curvature rad/in
            curvature_rad_in = dls * math.pi / (180.0 * 100.0 * 12.0)
            sigma_bend = e * (drillstring_od / 2.0) * curvature_rad_in

            # Add vibration-induced stress
            sigma_vib = sigma_bend * (1.0 + vibration_severity)

            # Cycles at this station
            n_cycles = cycles_per_hour * hours_per_stand

            # Cycles to failure from S-N curve
            if sigma_vib > 0 and sigma_vib < s_e * 5:
                n_f = (s_e / sigma_vib) ** b_exponent if sigma_vib > 0 else float("inf")
                n_f = max(n_f, 1.0)
            else:
                n_f = float("inf") if sigma_vib <= 0 else 1.0

            # Damage increment
            d_i = n_cycles / n_f if n_f > 0 and n_f != float("inf") else 0

            cumulative_damage += d_i

            damage_by_station.append({
                "md_ft": md,
                "dls_deg_100ft": dls,
                "bending_stress_psi": round(sigma_bend, 0),
                "total_cyclic_stress_psi": round(sigma_vib, 0),
                "cycles_applied": round(n_cycles, 0),
                "cycles_to_failure": round(n_f, 0) if n_f != float("inf") else "infinite",
                "damage_increment": round(d_i, 6),
                "cumulative_damage": round(cumulative_damage, 6),
            })
    else:
        # Uniform estimate: assume average DLS of 3 deg/100ft
        avg_dls = 3.0
        curvature_rad_in = avg_dls * math.pi / (180.0 * 100.0 * 12.0)
        sigma_bend = e * (drillstring_od / 2.0) * curvature_rad_in
        sigma_vib = sigma_bend * (1.0 + vibration_severity)
        total_cycles = cycles_per_hour * total_rotating_hours
        n_f = (s_e / sigma_vib) ** b_exponent if sigma_vib > 0 else float("inf")
        n_f = max(n_f, 1.0) if n_f != float("inf") else float("inf")
        cumulative_damage = total_cycles / n_f if n_f != float("inf") and n_f > 0 else 0

    # Remaining life estimate
    if cumulative_damage > 0:
        remaining_life_pct = max(0, (1.0 - cumulative_damage) * 100)
        if cumulative_damage < 1.0:
            # Hours remaining ~ total_hours * (1-D)/D
            hours_used = total_rotating_hours if not survey_stations else len(survey_stations) * hours_per_stand
            estimated_remaining_hours = hours_used * (1.0 - cumulative_damage) / cumulative_damage if cumulative_damage > 0 else float("inf")
        else:
            estimated_remaining_hours = 0
    else:
        remaining_life_pct = 100.0
        estimated_remaining_hours = float("inf")

    # Critical joints (highest damage)
    critical_joints = []
    if damage_by_station:
        sorted_stations = sorted(damage_by_station, key=lambda x: x["damage_increment"], reverse=True)
        critical_joints = sorted_stations[:3]

    return {
        "cumulative_damage": round(cumulative_damage, 6),
        "remaining_life_pct": round(remaining_life_pct, 1),
        "estimated_remaining_hours": round(estimated_remaining_hours, 1) if estimated_remaining_hours != float("inf") else "infinite",
        "status": "FAILED" if cumulative_damage >= 1.0 else ("WARNING" if cumulative_damage > 0.5 else "OK"),
        "endurance_limit_psi": s_e,
        "sn_exponent": b_exponent,
        "drillstring_grade": drillstring_grade,
        "damage_by_station": damage_by_station,
        "critical_joints": critical_joints,
        "rpm": rpm,
        "vibration_severity": vibration_severity,
    }
