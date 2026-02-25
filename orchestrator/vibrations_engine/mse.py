"""Mechanical Specific Energy (MSE) calculation.

References:
- Teale (1965): Mechanical Specific Energy concept
- Dupriest (2005): MSE-based drilling optimization
"""
import math
from typing import Dict, Any, Optional


def calculate_mse(
    wob_klb: float,
    torque_ftlb: float,
    rpm: float,
    rop_fph: float,
    bit_diameter_in: float,
    ucs_psi: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate Mechanical Specific Energy (Teale, 1965).

    MSE = (480 * T * RPM) / (d^2 * ROP) + (4 * WOB) / (pi * d^2)

    Where: T in ft-lbs, RPM in rev/min, d in inches, ROP in ft/hr, WOB in lbs

    Efficiency: eta = CCS / MSE (where CCS = confined compressive strength)

    Args:
        wob_klb: weight on bit (klbs)
        torque_ftlb: surface torque (ft-lbs)
        rpm: rotary speed (RPM)
        rop_fph: rate of penetration (ft/hr)
        bit_diameter_in: bit diameter (inches)

    Returns:
        Dict with MSE, components, efficiency estimate, founder point indicators
    """
    if bit_diameter_in <= 0 or rop_fph <= 0:
        return {"error": "Bit diameter and ROP must be > 0"}

    wob_lbs = wob_klb * 1000.0
    d = bit_diameter_in
    d_sq = d * d

    # MSE components
    mse_rotary = (480.0 * torque_ftlb * rpm) / (d_sq * rop_fph) if rop_fph > 0 else 0
    mse_thrust = (4.0 * wob_lbs) / (math.pi * d_sq)
    mse_total = mse_rotary + mse_thrust

    # Bit area
    bit_area = math.pi * d_sq / 4.0

    # Efficiency calculation
    if ucs_psi is not None and ucs_psi > 0 and mse_total > 0:
        efficiency_pct = round(min(100.0, ucs_psi / mse_total * 100.0), 1)
        classification_basis = "ucs_based"
        # UCS-based classification
        if efficiency_pct > 80:
            classification = "Efficient"
            color = "green"
        elif efficiency_pct > 40:
            classification = "Normal"
            color = "yellow"
        elif efficiency_pct > 20:
            classification = "Inefficient"
            color = "orange"
        else:
            classification = "Highly Inefficient"
            color = "red"
    else:
        efficiency_pct = None
        classification_basis = "absolute_mse"
        # Absolute MSE classification (existing thresholds)
        if mse_total < 20000:
            classification = "Efficient"
            color = "green"
        elif mse_total < 50000:
            classification = "Normal"
            color = "yellow"
        elif mse_total < 100000:
            classification = "Inefficient"
            color = "orange"
        else:
            classification = "Highly Inefficient"
            color = "red"

    return {
        "mse_total_psi": round(mse_total, 0),
        "mse_rotary_psi": round(mse_rotary, 0),
        "mse_thrust_psi": round(mse_thrust, 0),
        "rotary_pct": round(mse_rotary / mse_total * 100, 1) if mse_total > 0 else 0,
        "thrust_pct": round(mse_thrust / mse_total * 100, 1) if mse_total > 0 else 0,
        "bit_area_in2": round(bit_area, 2),
        "efficiency_pct": efficiency_pct,
        "classification_basis": classification_basis,
        "classification": classification,
        "color": color,
    }
