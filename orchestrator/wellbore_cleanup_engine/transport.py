"""
Cuttings transport calculations — CTR, transport velocity, concentration.

References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 4
"""
import math


def calculate_ctr(annular_velocity: float, slip_velocity: float) -> float:
    """
    Calculate Cuttings Transport Ratio.
    CTR = (Va - Vs) / Va

    Args:
        annular_velocity: annular velocity (ft/min)
        slip_velocity: cuttings slip velocity (ft/min)

    Returns:
        CTR (dimensionless, 0-1). Values > 0.55 indicate adequate cleaning.
    """
    if annular_velocity <= 0:
        return 0.0
    ctr = (annular_velocity - slip_velocity) / annular_velocity
    return max(ctr, 0.0)


def calculate_transport_velocity(
    annular_velocity: float,
    slip_velocity: float,
) -> float:
    """
    Net cuttings transport velocity.
    Vt = Va - Vs

    Returns:
        Transport velocity (ft/min). Positive = cuttings moving up.
    """
    return annular_velocity - slip_velocity


def calculate_cuttings_concentration(
    rop: float,
    hole_id: float,
    pipe_od: float,
    flow_rate: float,
    transport_velocity: float,
) -> float:
    """
    Estimate cuttings concentration in annulus (% by volume).

    Args:
        rop: rate of penetration (ft/hr)
        hole_id: hole diameter (inches)
        pipe_od: pipe OD (inches)
        flow_rate: pump rate (gpm)
        transport_velocity: net transport velocity (ft/min)

    Returns:
        Cuttings concentration (vol %)
    """
    if flow_rate <= 0 or transport_velocity <= 0:
        return 100.0

    # Bit area (generating cuttings)
    bit_area = math.pi * (hole_id / 2.0) ** 2  # in²

    # Volume rate of cuttings generated
    cutting_gen_rate = bit_area * (rop / 60.0) / 144.0  # ft³/min

    # Annular flow volume rate
    annular_area = math.pi * (hole_id ** 2 - pipe_od ** 2) / (4.0 * 144.0)  # ft²
    annular_flow = annular_area * transport_velocity  # ft³/min

    if annular_flow <= 0:
        return 100.0

    concentration = (cutting_gen_rate / (annular_flow + cutting_gen_rate)) * 100.0
    return round(min(concentration, 100.0), 2)
