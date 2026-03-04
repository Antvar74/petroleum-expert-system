"""
CT Reach — maximum CT reach estimation based on helical buckling and yield limits.

Reference: Paslay-Dawson buckling criterion (1984); Bourgoyne et al. (1986)
"""
import math
from typing import Dict, Any

from .ct_geometry import STEEL_WEIGHT_WATER


def calculate_max_reach(
    ct_od: float,
    ct_id: float,
    wall_thickness: float,
    weight_per_ft: float,
    mud_weight: float,
    inclination: float,
    friction_factor: float,
    wellhead_pressure: float = 0.0,
    yield_strength_psi: float = 80000.0,
) -> Dict[str, Any]:
    """
    Estimate maximum CT reach based on helical buckling and yield limits.

    The CT will buckle when compressive force exceeds critical buckling load,
    limiting how far the CT can be pushed into a horizontal section.

    Args:
        ct_od: CT OD (inches)
        ct_id: CT ID (inches)
        wall_thickness: CT wall (inches)
        weight_per_ft: CT weight (lb/ft)
        mud_weight: fluid density (ppg)
        inclination: wellbore inclination (degrees)
        friction_factor: friction coefficient
        wellhead_pressure: surface pressure (psi)
        yield_strength_psi: CT yield strength (psi, typically 70–110 ksi)

    Returns:
        Dict with max_reach estimates and limiting factors
    """
    bf = 1.0 - (mud_weight / STEEL_WEIGHT_WATER)
    buoyed_wt_per_ft = weight_per_ft * max(bf, 0.01)

    # Moment of inertia and metal area
    I = math.pi / 64.0 * (ct_od ** 4 - ct_id ** 4)  # in⁴
    A_s = math.pi / 4.0 * (ct_od ** 2 - ct_id ** 2)  # in²

    E = 30e6  # Young's modulus for steel, psi

    # Radial clearance (assume 7" casing for typical CT ops)
    r_clearance = (7.0 - ct_od) / 2.0
    if r_clearance <= 0:
        r_clearance = 1.0

    incl_rad = math.radians(inclination)

    # --- Helical buckling limit (Paslay-Dawson) ---
    w_n = buoyed_wt_per_ft * math.sin(incl_rad) / 12.0  # lb/in normal component
    if w_n > 0 and r_clearance > 0:
        F_hb = math.sqrt(8.0 * E * I * w_n / r_clearance)
    else:
        F_hb = yield_strength_psi * A_s

    # --- Yield limit ---
    F_yield = yield_strength_psi * A_s

    # --- Pressure force at surface ---
    F_pressure = wellhead_pressure * math.pi / 4.0 * ct_od ** 2

    # Max horizontal reach
    max_push = max(F_hb, 0)
    friction_per_ft = (
        friction_factor * buoyed_wt_per_ft * math.sin(incl_rad)
        if inclination > 5
        else buoyed_wt_per_ft * friction_factor * 0.1
    )
    max_reach_ft = (max_push / friction_per_ft) if friction_per_ft > 0 else 50000.0
    max_reach_ft = min(max_reach_ft, 35000.0)

    limiting_factor = "Helical Buckling"
    if F_yield < F_hb:
        limiting_factor = "CT Yield Strength"
        max_reach_ft = min(max_reach_ft, F_yield / max(friction_per_ft, 0.01))

    return {
        "max_reach_ft": round(max_reach_ft, 0),
        "helical_buckling_load_lb": round(F_hb, 0),
        "yield_load_lb": round(F_yield, 0),
        "pressure_force_lb": round(F_pressure, 0),
        "limiting_factor": limiting_factor,
        "buoyed_wt_per_ft": round(buoyed_wt_per_ft, 3),
        "moment_of_inertia_in4": round(I, 6),
    }
