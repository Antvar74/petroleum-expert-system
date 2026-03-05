"""
Annular velocity and minimum flow rate calculations.

References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Va = 24.51 × Q / (Dh² - Dp²)
"""
from .constants import get_min_annular_velocity


def calculate_annular_velocity(
    flow_rate: float,
    hole_id: float,
    pipe_od: float,
) -> float:
    """
    Calculate annular velocity.

    Args:
        flow_rate: pump rate (gpm)
        hole_id: hole inner diameter (inches)
        pipe_od: pipe outer diameter (inches)

    Returns:
        Annular velocity (ft/min)
    """
    if hole_id <= pipe_od:
        return 0.0
    annular_area = hole_id ** 2 - pipe_od ** 2
    if annular_area <= 0:
        return 0.0
    # Va = 24.51 * Q / (Dh² - Dp²)
    return 24.51 * flow_rate / annular_area


def calculate_minimum_flow_rate(
    hole_id: float,
    pipe_od: float,
    inclination: float,
) -> float:
    """
    Calculate minimum flow rate for adequate hole cleaning (API RP 13D).

    Args:
        hole_id: hole diameter (inches)
        pipe_od: pipe OD (inches)
        inclination: wellbore inclination (degrees)

    Returns:
        Minimum flow rate (gpm)
    """
    if hole_id <= pipe_od:
        return 0.0

    annular_area = hole_id ** 2 - pipe_od ** 2
    min_av = get_min_annular_velocity(inclination)

    # Va = 24.51 * Q / (Dh² - Dp²) → Q = Va * (Dh² - Dp²) / 24.51
    return min_av * annular_area / 24.51
