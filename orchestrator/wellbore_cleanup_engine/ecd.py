"""
Cuttings ECD (Equivalent Circulating Density) contribution.

Calculates the effective mud weight increase due to suspended cuttings
in the annulus during drilling operations.

References:
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 4
"""
from typing import Dict, Any


def calculate_cuttings_ecd_contribution(
    concentration_pct: float,
    cutting_density: float,
    mud_weight: float,
) -> Dict[str, Any]:
    """
    Calculate the ECD contribution from cuttings in the annulus.

    The effective mud weight increase due to suspended cuttings is:
    cuttings_ecd = (concentration_fraction) * (cutting_density - mud_weight)

    Parameters:
        concentration_pct: cuttings concentration (vol %)
        cutting_density: cuttings density (ppg, typically 21-22)
        mud_weight: base mud weight (ppg)

    Returns:
        Dict with cuttings_ecd_ppg, effective_mud_weight_ppg,
        concentration_fraction, density_difference_ppg
    """
    # Guards
    if concentration_pct <= 0:
        return {
            "cuttings_ecd_ppg": 0.0,
            "effective_mud_weight_ppg": round(mud_weight, 3),
            "concentration_fraction": 0.0,
            "density_difference_ppg": round(max(cutting_density - mud_weight, 0.0), 3),
        }

    conc = min(concentration_pct, 100.0)
    conc_frac = conc / 100.0

    # If cutting density <= mud weight, cuttings don't add to ECD
    delta_rho = cutting_density - mud_weight
    if delta_rho <= 0:
        return {
            "cuttings_ecd_ppg": 0.0,
            "effective_mud_weight_ppg": round(mud_weight, 3),
            "concentration_fraction": round(conc_frac, 4),
            "density_difference_ppg": 0.0,
        }

    cuttings_ecd = conc_frac * delta_rho
    effective_mw = mud_weight + cuttings_ecd

    return {
        "cuttings_ecd_ppg": round(cuttings_ecd, 3),
        "effective_mud_weight_ppg": round(effective_mw, 3),
        "concentration_fraction": round(conc_frac, 4),
        "density_difference_ppg": round(delta_rho, 3),
    }
