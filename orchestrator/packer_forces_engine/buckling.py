"""
Buckling analysis — critical helical buckling load and buckled length calculations.

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Paslay, P.R. & Dawson, R. (1984): New Buckling Equations for Curved Wellbores
- API TR 5C3: Casing and Tubing Buckling in Wellbores
"""
import math
from typing import Dict, Any

from .geometry import STEEL_E, STEEL_DENSITY_PPG


def calculate_helical_buckling_load(
    tubing_od: float,
    tubing_id: float,
    tubing_weight: float,
    casing_id: float,
    inclination: float = 0.0,
) -> float:
    """
    Critical helical buckling load (Lubinski/Paslay-Dawson).

    For vertical: F_cr = 2 * sqrt(E * I * w / r)
    For inclined: F_cr = 2 * sqrt(E * I * w * sin(θ) / r)

    Args:
        tubing_od: tubing OD (inches)
        tubing_id: tubing ID (inches)
        tubing_weight: buoyed weight per foot (lb/ft)
        casing_id: casing ID (inches)
        inclination: wellbore inclination (degrees)

    Returns:
        Critical buckling load (lbs). Compression exceeding this → helical buckling.
    """
    i_moment = math.pi * (tubing_od ** 4 - tubing_id ** 4) / 64.0

    r_clear = (casing_id - tubing_od) / 2.0
    if r_clear <= 0:
        return float('inf')

    w = abs(tubing_weight)
    if w <= 0:
        return float('inf')

    inc_rad = math.radians(inclination)
    sin_factor = math.sin(inc_rad) if inclination > 5 else 1.0

    f_cr = 2.0 * math.sqrt(STEEL_E * i_moment * w * sin_factor / r_clear)
    return round(f_cr, 0)


def calculate_buckling_length(
    axial_force: float,
    tubing_od: float = 3.5,
    tubing_id: float = 2.992,
    tubing_weight_ppf: float = 9.3,
    casing_id: float = 6.276,
    inclination_deg: float = 0.0,
    mud_weight_ppg: float = 8.34,
) -> Dict[str, Any]:
    """
    Calculate length of buckled tubing and associated effects.

    Sinusoidal: L_buckled = F / (w * sin(inc))
    Helicoidal: L_helix = sqrt(8 * EI * F) / (w * sin(inc) * r)
    Shortening: dL = F^2 * r^2 / (8 * EI * w * sin(inc))

    Args:
        axial_force: compressive force at packer (lbs, negative = compression)
        tubing_od, tubing_id: tubing dimensions (in)
        tubing_weight_ppf: buoyed weight per foot (lb/ft)
        casing_id: casing ID for clearance (in)
        inclination_deg: wellbore inclination (degrees)
        mud_weight_ppg: mud weight (ppg)

    Returns:
        Dict with buckled length, type, shortening, contact force.
    """
    i_moment = math.pi * (tubing_od ** 4 - tubing_id ** 4) / 64.0
    ei = STEEL_E * i_moment

    r_clearance = (casing_id - tubing_od) / 2.0
    if r_clearance <= 0:
        return {"error": "Casing ID must be larger than tubing OD"}

    bf = max(0.01, 1.0 - mud_weight_ppg / STEEL_DENSITY_PPG)
    w = abs(tubing_weight_ppf * bf)   # lb/ft buoyed
    w_in = w / 12.0                   # lb/in

    inc_rad = math.radians(inclination_deg)
    sin_inc = max(math.sin(inc_rad), 0.05)  # avoid singularity for vertical wells

    f_comp = abs(axial_force)

    # Critical buckling loads (Paslay-Dawson)
    f_cr_sin = math.sqrt(2.0 * ei * w_in * sin_inc / r_clearance) if r_clearance > 0 else float("inf")
    f_cr_hel = 2.0 * f_cr_sin

    if f_comp < f_cr_sin:
        buckling_type = "None"
        buckled_length = 0
        shortening = 0
        contact_force = 0
        max_bending_stress = 0
    elif f_comp < f_cr_hel:
        buckling_type = "Sinusoidal"
        buckled_length = f_comp / (w * sin_inc) if w * sin_inc > 0 else 0
        shortening = (f_comp ** 2 * r_clearance ** 2) / (8.0 * ei * w_in * sin_inc) / 12.0 if ei > 0 else 0
        contact_force = f_comp ** 2 / (4.0 * ei / r_clearance) / 12.0 if ei > 0 else 0
        max_bending_stress = r_clearance * (tubing_od / 2.0) * f_comp / (4.0 * i_moment) if i_moment > 0 else 0
    else:
        buckling_type = "Helicoidal"
        buckled_length = f_comp / (w * sin_inc) if w * sin_inc > 0 else 0
        shortening = (f_comp ** 2 * r_clearance ** 2) / (4.0 * ei * w_in * sin_inc) / 12.0 if ei > 0 else 0
        contact_force = f_comp ** 2 * r_clearance / (4.0 * ei) / 12.0 if ei > 0 else 0
        max_bending_stress = f_comp * r_clearance * (tubing_od / 2.0) / (4.0 * i_moment) if i_moment > 0 else 0

    return {
        "buckling_type": buckling_type,
        "buckled_length_ft": round(buckled_length, 1),
        "shortening_in": round(shortening, 3),
        "contact_force_lbf_per_ft": round(contact_force, 1),
        "max_bending_stress_psi": round(max_bending_stress, 0),
        "critical_load_sinusoidal_lbs": round(f_cr_sin, 0),
        "critical_load_helicoidal_lbs": round(f_cr_hel, 0),
        "axial_force_lbs": round(axial_force, 0),
        "radial_clearance_in": round(r_clearance, 3),
        "inclination_deg": inclination_deg,
    }
