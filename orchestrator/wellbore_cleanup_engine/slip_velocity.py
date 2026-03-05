"""
Cuttings slip velocity correlations — Moore and Larsen.

References:
- Moore correlation for slip velocity (vertical wells)
- Larsen, T.I., Pilehvari, A.A., & Azar, J.J. (1997):
  "Development of a New Cuttings-Transport Model..." SPE 36383
"""
import math
from typing import Dict, Any


def calculate_slip_velocity(
    mud_weight: float,
    pv: float,
    yp: float,
    cutting_size: float,
    cutting_density: float,
) -> float:
    """
    Calculate cuttings slip velocity using Moore correlation.

    Args:
        mud_weight: mud density (ppg)
        pv: plastic viscosity (cP)
        yp: yield point (lb/100ft²)
        cutting_size: mean cutting diameter (inches)
        cutting_density: cutting density (ppg, typically 21-22 for sandstone)

    Returns:
        Slip velocity (ft/min)
    """
    if cutting_size <= 0 or mud_weight <= 0:
        return 0.0

    # Apparent viscosity for Moore correlation
    mu_a = pv + 5.0 * yp  # simplified apparent viscosity (cP)
    if mu_a <= 0:
        mu_a = 1.0

    # Density difference
    delta_rho = cutting_density - mud_weight
    if delta_rho <= 0:
        return 0.0

    # Reynolds number estimate
    re_p = 15.47 * mud_weight * cutting_size * math.sqrt(
        delta_rho * cutting_size / mud_weight
    ) / mu_a

    if re_p < 1:
        # Stokes regime: Vs = 113.4 * d_in^2 * delta_rho / mu_a
        vs = 113.4 * (cutting_size ** 2) * delta_rho / mu_a
    elif re_p < 2000:
        # Intermediate regime (Moore)
        vs = 175.0 * cutting_size * math.sqrt(delta_rho / mud_weight)
    else:
        # Turbulent (Newton)
        vs = 175.0 * cutting_size * math.sqrt(delta_rho / mud_weight)

    return max(vs, 0.0)


def calculate_slip_velocity_larsen(
    mud_weight: float, pv: float, yp: float,
    cutting_size: float, cutting_density: float,
    inclination: float, rpm: float = 0.0,
    hole_id: float = 8.5, pipe_od: float = 5.0,
    annular_velocity: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate cuttings slip velocity using Larsen correlation (SPE 36383, 1997)
    for high-angle and horizontal wells (inclination > 30°).

    Extends Moore vertical slip with inclination, RPM, and bed erosion factors.

    Parameters:
        mud_weight: mud density (ppg)
        pv: plastic viscosity (cP)
        yp: yield point (lb/100ft²)
        cutting_size: mean cutting diameter (inches)
        cutting_density: cutting density (ppg)
        inclination: wellbore inclination (degrees from vertical)
        rpm: drillstring rotation speed (RPM)
        hole_id: hole inner diameter (inches)
        pipe_od: pipe outer diameter (inches)
        annular_velocity: actual annular velocity (ft/min, for transport calc)

    Returns:
        Dict with slip_velocity_ftmin, bed_erosion_velocity, effective_transport_velocity,
        rpm_factor, inclination_factor, correlation_used
    """
    # Base vertical slip velocity using Moore correlation
    vs_vertical = calculate_slip_velocity(
        mud_weight, pv, yp, cutting_size, cutting_density
    )

    inc_rad = math.radians(inclination)

    # Inclination factor (Larsen 1997)
    if inclination < 10.0:
        # Near-vertical: no correction needed
        f_inc = 1.0
    elif inclination <= 60.0:
        # Transition zone (30-60°): maximum settling tendency at ~45-60°
        f_inc = 1.0 + 0.3 * math.sin(2.0 * inc_rad)
    else:
        # High angle (60-90°): cuttings bed forms, reduced vertical component
        f_inc = 1.0 + 0.2 * (1.0 - math.cos(inc_rad))

    # Inclined slip velocity: vertical component corrected by inclination
    vs_inclined = vs_vertical * abs(math.cos(inc_rad)) * f_inc
    # For horizontal (cos~0), slip is dominated by bed behavior
    if inclination > 80.0:
        vs_inclined = max(vs_inclined, vs_vertical * 0.1)

    # RPM factor: drillstring rotation disturbs cuttings bed and improves transport
    if inclination > 30.0:
        if inclination >= 75.0:
            # Near-horizontal: RPM very effective
            f_rpm = 1.0 - min(rpm / 150.0, 0.5)
        else:
            # Inclined: RPM moderately effective
            f_rpm = 1.0 - min(rpm / 200.0, 0.4)
    else:
        f_rpm = 1.0  # RPM has minimal effect in vertical wells

    f_rpm = max(f_rpm, 0.3)  # Cap minimum reduction

    # Effective slip velocity
    vs_effective = vs_inclined * f_rpm

    # Bed erosion velocity (empirical): minimum annular velocity to erode
    # a stationary cuttings bed (applicable for inc > 60°)
    if inclination > 60.0:
        v_bed_erosion = 50.0 + 2.5 * (inclination - 60.0)
    elif inclination > 30.0:
        v_bed_erosion = 30.0 + (inclination - 30.0) * 0.67
    else:
        v_bed_erosion = 0.0

    # Effective transport velocity (if annular velocity provided)
    effective_transport = annular_velocity - vs_effective if annular_velocity > 0 else 0.0

    return {
        "slip_velocity_ftmin": round(vs_effective, 2),
        "vs_vertical_ftmin": round(vs_vertical, 2),
        "bed_erosion_velocity_ftmin": round(v_bed_erosion, 2),
        "effective_transport_velocity_ftmin": round(effective_transport, 2),
        "rpm_factor": round(f_rpm, 4),
        "inclination_factor": round(f_inc, 4),
        "inclination_deg": inclination,
        "correlation_used": "larsen",
    }
