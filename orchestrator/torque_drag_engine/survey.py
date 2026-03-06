"""
Torque & Drag Engine — Survey Calculations.

Minimum curvature method for TVD, North, East, DLS.

References:
- Applied Drilling Engineering (Bourgoyne et al.)
"""
import math
from typing import List, Dict, Any


def compute_survey_derived(stations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute TVD, North, East, DLS using minimum curvature method.
    Input: list of {md, inclination, azimuth} (degrees)
    Output: same list enriched with tvd, north, east, dls
    """
    if not stations:
        return []

    results = []
    # First station
    s0 = stations[0]
    s0_out = {
        "md": s0["md"],
        "inclination": s0["inclination"],
        "azimuth": s0["azimuth"],
        "tvd": s0.get("tvd", 0.0),
        "north": s0.get("north", 0.0),
        "east": s0.get("east", 0.0),
        "dls": 0.0
    }
    results.append(s0_out)

    for i in range(1, len(stations)):
        prev = stations[i - 1]
        curr = stations[i]

        delta_md = curr["md"] - prev["md"]
        if delta_md <= 0:
            results.append({
                "md": curr["md"],
                "inclination": curr["inclination"],
                "azimuth": curr["azimuth"],
                "tvd": results[-1]["tvd"],
                "north": results[-1]["north"],
                "east": results[-1]["east"],
                "dls": 0.0
            })
            continue

        inc1 = math.radians(prev["inclination"])
        inc2 = math.radians(curr["inclination"])
        azi1 = math.radians(prev["azimuth"])
        azi2 = math.radians(curr["azimuth"])

        # Dogleg angle
        cos_dl = (math.cos(inc2 - inc1)
                  - math.sin(inc1) * math.sin(inc2) * (1 - math.cos(azi2 - azi1)))
        cos_dl = max(-1.0, min(1.0, cos_dl))
        dl = math.acos(cos_dl)

        # Ratio factor (minimum curvature)
        if dl < 1e-7:
            rf = 1.0
        else:
            rf = (2.0 / dl) * math.tan(dl / 2.0)

        # Increments
        delta_tvd = (delta_md / 2.0) * (math.cos(inc1) + math.cos(inc2)) * rf
        delta_north = (delta_md / 2.0) * (
            math.sin(inc1) * math.cos(azi1) + math.sin(inc2) * math.cos(azi2)
        ) * rf
        delta_east = (delta_md / 2.0) * (
            math.sin(inc1) * math.sin(azi1) + math.sin(inc2) * math.sin(azi2)
        ) * rf

        # DLS in deg/100ft
        dls = math.degrees(dl) / delta_md * 100.0

        results.append({
            "md": curr["md"],
            "inclination": curr["inclination"],
            "azimuth": curr["azimuth"],
            "tvd": round(results[-1]["tvd"] + delta_tvd, 2),
            "north": round(results[-1]["north"] + delta_north, 2),
            "east": round(results[-1]["east"] + delta_east, 2),
            "dls": round(dls, 2)
        })

    return results
