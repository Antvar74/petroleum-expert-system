"""
Casing Design — Burst Rating, Collapse Rating, and Temperature Derating

Burst rating via Barlow's formula (API 5C3), collapse rating via API TR 5C3
four-zone model (yield, plastic, transition, elastic), and temperature
derating per API TR 5C3 Annex G.

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe (collapse formulas, 4 zones)
- API 5CT: Specification for Casing and Tubing
- Barlow's formula: P_burst = 0.875 * 2 * Yp * t / OD
- API TR 5C3 Annex G: Temperature derating of yield strength
"""
import math
from typing import Dict, Any


def calculate_burst_rating(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    """
    Calculate burst rating using Barlow's formula (API 5C3).

    P_burst = 0.875 * 2 * Yp * t / OD

    The 0.875 factor accounts for 12.5% wall thickness tolerance.
    """
    if casing_od_in <= 0 or wall_thickness_in <= 0:
        return {"error": "Invalid dimensions"}

    p_burst = 0.875 * 2.0 * yield_strength_psi * wall_thickness_in / casing_od_in

    dt_ratio = casing_od_in / wall_thickness_in if wall_thickness_in > 0 else 0

    return {
        "burst_rating_psi": round(p_burst, 0),
        "yield_strength_psi": yield_strength_psi,
        "wall_thickness_in": wall_thickness_in,
        "od_in": casing_od_in,
        "dt_ratio": round(dt_ratio, 2),
    }


def calculate_collapse_rating(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    """
    Calculate collapse rating per API TR 5C3 (ISO 10400).

    Four collapse regimes based on D/t ratio:
    1. Yield Collapse: low D/t (thick-wall)
    2. Plastic Collapse: intermediate D/t
    3. Transition Collapse: intermediate-high D/t
    4. Elastic Collapse: high D/t (thin-wall)

    Each regime has its own formula with coefficients A, B, C, F, G.
    """
    if casing_od_in <= 0 or wall_thickness_in <= 0:
        return {"error": "Invalid dimensions"}

    dt = casing_od_in / wall_thickness_in
    yp = yield_strength_psi

    # API 5C3 empirical coefficients (functions of yield strength)
    # Approximated from API tables for common grades
    A = 2.8762 + 0.10679e-4 * yp + 0.21301e-10 * yp ** 2 - 0.53132e-16 * yp ** 3
    B = 0.026233 + 0.50609e-6 * yp
    C = -465.93 + 0.030867 * yp - 0.10483e-7 * yp ** 2 + 0.36989e-13 * yp ** 3

    # Transition boundaries (D/t ratios)
    # Yield-Plastic boundary
    try:
        dt_yp = (math.sqrt((A - 2) ** 2 + 8 * (B + C / yp)) + (A - 2)) / (2 * (B + C / yp))
    except (ValueError, ZeroDivisionError):
        dt_yp = 15.0

    # Plastic-Transition boundary
    F = 46.95e6 * (3 * B / A / (2 + B / A)) ** 3
    G = F * B / A

    try:
        dt_pt = yp * (A - F) / (C + yp * (B - G))
    except ZeroDivisionError:
        dt_pt = 25.0

    # Transition-Elastic boundary
    dt_te = 2 + B / A
    try:
        dt_te = 2.0 + yp * (B / A) / (3.0 * B / A / (2 + B / A))
    except ZeroDivisionError:
        dt_te = 30.0

    # Elastic collapse limit (D/t)
    # Ensure boundaries are ordered
    boundaries = sorted([dt_yp, dt_pt, dt_te])

    # Determine collapse zone and calculate rating
    if dt <= boundaries[0]:
        # Zone 1: Yield Collapse
        zone = "Yield"
        p_collapse = 2.0 * yp * ((dt - 1) / dt ** 2)
    elif dt <= boundaries[1]:
        # Zone 2: Plastic Collapse
        zone = "Plastic"
        p_collapse = yp * (A / dt - B) - C
    elif dt <= boundaries[2]:
        # Zone 3: Transition Collapse
        zone = "Transition"
        p_collapse = yp * (F / dt - G)
    else:
        # Zone 4: Elastic Collapse
        zone = "Elastic"
        p_collapse = 46.95e6 / (dt * (dt - 1) ** 2)

    p_collapse = max(p_collapse, 0.0)

    return {
        "collapse_rating_psi": round(p_collapse, 0),
        "collapse_zone": zone,
        "dt_ratio": round(dt, 2),
        "yield_strength_psi": yield_strength_psi,
        "boundaries": {
            "yield_plastic": round(boundaries[0], 2),
            "plastic_transition": round(boundaries[1], 2),
            "transition_elastic": round(boundaries[2], 2),
        },
    }


def derate_for_temperature(
    grade: str,
    yield_strength_psi: float,
    temperature_f: float,
    ambient_temperature_f: float = 70.0,
) -> Dict[str, Any]:
    """
    Derate yield strength for temperature (critical for HPHT).

    API TR 5C3 Annex G:
    sigma_y(T) = sigma_y_ambient * [1 - alpha * (T - T_ambient)]
    alpha depends on steel grade (~0.00035-0.0005 /degF for T > 200degF)
    """
    # Alpha coefficients by grade family (empirical, API TR 5C3)
    alpha_map = {
        "H40": 0.0003, "J55": 0.00035, "K55": 0.00035,
        "L80": 0.0004, "N80": 0.0004, "C90": 0.00042,
        "T95": 0.00045, "C110": 0.00045, "P110": 0.00045,
        "Q125": 0.0005, "V150": 0.00055,
    }
    alpha = alpha_map.get(grade, 0.0004)

    dT = temperature_f - ambient_temperature_f
    if dT <= 0:
        # No derating for temperatures at or below ambient
        return {
            "yield_derated_psi": yield_strength_psi,
            "derate_factor": 1.0,
            "temperature_f": temperature_f,
            "alpha": alpha,
            "grade": grade,
        }

    # Only apply derating above threshold (typically 200degF)
    threshold_f = 200.0
    if temperature_f < threshold_f:
        effective_dT = 0.0
    else:
        effective_dT = temperature_f - threshold_f

    derate_factor = 1.0 - alpha * effective_dT
    derate_factor = max(derate_factor, 0.5)  # minimum 50% derating

    yield_derated = yield_strength_psi * derate_factor

    return {
        "yield_derated_psi": round(yield_derated, 0),
        "derate_factor": round(derate_factor, 4),
        "temperature_f": temperature_f,
        "effective_dT": round(effective_dT, 1),
        "alpha": alpha,
        "grade": grade,
    }
