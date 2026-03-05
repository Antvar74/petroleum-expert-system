"""
Packer force components — piston, ballooning, temperature, fictitious buckling force,
and tubing movement (Hooke's law).

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Mitchell, R. & Samuel, R. (2009): How Good Is the Thin Shell Approximation
"""
from .geometry import STEEL_E, STEEL_ALPHA, STEEL_POISSON


def calculate_piston_force(
    pressure_below: float,
    pressure_above: float,
    seal_bore_area: float,
    tubing_ao: float,
    tubing_ai: float,
) -> float:
    """
    Piston effect force on packer.
    F_piston = P_below * (A_seal - A_i) - P_above * (A_seal - A_o)

    Args:
        pressure_below: pressure below packer (psi)
        pressure_above: pressure above packer (psi)
        seal_bore_area: packer seal bore area (in²)
        tubing_ao: tubing outer area (in²)
        tubing_ai: tubing inner area (in²)

    Returns:
        Piston force (lbs). Positive = tension, Negative = compression.
    """
    f_piston = (pressure_below * (seal_bore_area - tubing_ai)
                - pressure_above * (seal_bore_area - tubing_ao))
    return round(f_piston, 1)


def calculate_ballooning_force(
    delta_pi: float,
    delta_po: float,
    tubing_ai: float,
    tubing_ao: float,
    poisson_ratio: float = STEEL_POISSON,
) -> float:
    """
    Ballooning/reverse-ballooning force due to pressure changes.
    F_balloon = -2ν × (ΔP_i × A_i - ΔP_o × A_o)

    Args:
        delta_pi: change in internal pressure (psi) (final - initial)
        delta_po: change in external pressure (psi) (final - initial)
        tubing_ai: tubing inner area (in²)
        tubing_ao: tubing outer area (in²)
        poisson_ratio: Poisson's ratio (default 0.30)

    Returns:
        Ballooning force (lbs). Positive = tension.
    """
    f_balloon = -2.0 * poisson_ratio * (delta_pi * tubing_ai - delta_po * tubing_ao)
    return round(f_balloon, 1)


def calculate_temperature_force(
    delta_t: float,
    tubing_as: float,
    youngs_modulus: float = STEEL_E,
    thermal_expansion: float = STEEL_ALPHA,
) -> float:
    """
    Temperature effect force.
    F_temp = -E × A_s × α × ΔT

    Args:
        delta_t: average temperature change (°F) (final - initial)
        tubing_as: tubing steel cross-sectional area (in²)
        youngs_modulus: Young's modulus (psi)
        thermal_expansion: thermal expansion coefficient (1/°F)

    Returns:
        Temperature force (lbs). Heating → compression (negative).
    """
    f_temp = -youngs_modulus * tubing_as * thermal_expansion * delta_t
    return round(f_temp, 1)


def calculate_buckling_force(
    tubing_ai: float,
    tubing_ao: float,
    pressure_internal: float,
    pressure_external: float,
) -> float:
    """
    Buckling force (fictitious force concept — Lubinski).
    F_f = P_i × A_i - P_o × A_o

    If actual force at packer < -F_f, the string will buckle.

    Args:
        tubing_ai: tubing inner area (in²)
        tubing_ao: tubing outer area (in²)
        pressure_internal: internal pressure at packer (psi)
        pressure_external: external/annular pressure at packer (psi)

    Returns:
        Fictitious buckling force (lbs)
    """
    f_f = pressure_internal * tubing_ai - pressure_external * tubing_ao
    return round(f_f, 1)


def calculate_tubing_movement(
    force: float,
    tubing_length: float,
    tubing_as: float,
    youngs_modulus: float = STEEL_E,
) -> float:
    """
    Calculate tubing length change due to a force (Hooke's law).
    ΔL = F × L / (E × A_s)

    Args:
        force: applied force (lbs)
        tubing_length: tubing length (ft)
        tubing_as: steel cross-sectional area (in²)
        youngs_modulus: Young's modulus (psi)

    Returns:
        Length change (inches). Positive = elongation.
    """
    if tubing_as <= 0 or youngs_modulus <= 0:
        return 0.0
    # Convert length to inches for consistent units
    delta_l = force * (tubing_length * 12.0) / (youngs_modulus * tubing_as)
    return round(delta_l, 3)
