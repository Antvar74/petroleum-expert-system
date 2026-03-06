"""
Torque & Drag Engine — Buckling Check & Casing ID Estimation.

References:
- Lubinski: Sinusoidal buckling — Fc = 2 * sqrt(EI * w * sin(inc) / r)
- Mitchell: Helical buckling — Fc = 2*sqrt(2) * sqrt(EI * w * sin(inc) / r)
"""
import math
from typing import Dict

# Steel properties
STEEL_E = 30e6          # Young's modulus, psi
STEEL_DENSITY = 490.0   # lb/ft³


def buckling_check(
    axial_force: float,
    inclination: float,
    ds: Dict,
    mud_weight: float,
    delta_md: float,
    md: float,
    casing_shoe_md: float
) -> str:
    """
    Check for sinusoidal and helical buckling.
    Lubinski (sinusoidal): Fc_sin = 2 * sqrt(E*I*w*sin(inc)/r)
    Mitchell (helical):    Fc_hel = 2 * sqrt(2) * sqrt(E*I*w*sin(inc)/r)
    """
    if axial_force >= 0:
        return "OK"  # Tension, no buckling

    od = ds["od"]
    id_inner = ds.get("id_inner", od - 1.0)

    # Moment of inertia
    i_moment = math.pi / 64.0 * (od**4 - id_inner**4)

    # Buoyed weight per inch
    bf = 1.0 - (mud_weight / 65.5)
    w_per_inch = ds["weight"] * bf / 12.0  # lb/in

    # Radial clearance — estimate wellbore ID
    if md < casing_shoe_md:
        hole_id = casing_id_estimate(od)
    else:
        hole_id = od + 3.0  # rough open hole clearance

    r = (hole_id - od) / 2.0  # radial clearance, inches
    if r <= 0:
        r = 0.5

    sin_inc = math.sin(inclination)
    if sin_inc < 0.01:
        sin_inc = 0.01  # Avoid division by zero in vertical

    ei = STEEL_E * i_moment

    # Critical forces
    fc_sin = 2.0 * math.sqrt(ei * w_per_inch * sin_inc / r)
    fc_hel = 2.0 * math.sqrt(2.0) * math.sqrt(ei * w_per_inch * sin_inc / r)

    compression = abs(axial_force)
    if compression > fc_hel:
        return "HELICAL"
    elif compression > fc_sin:
        return "SINUSOIDAL"
    return "OK"


def casing_id_estimate(pipe_od: float) -> float:
    """Estimate casing ID based on common pipe OD."""
    casing_map = {
        5.0: 8.681,    # 9-5/8" casing
        5.5: 8.681,
        3.5: 6.366,    # 7" casing
        4.5: 8.681,
        6.625: 10.772, # 11-3/4" casing
    }
    return casing_map.get(pipe_od, pipe_od + 3.5)
