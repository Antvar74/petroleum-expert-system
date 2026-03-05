"""
Viscous/heavy sweep pill design for hole cleaning.

References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Industry best practices for sweep pill volumes
"""
from typing import Dict, Any


def design_sweep_pill(
    annular_volume_per_ft: float,
    annular_length: float,
    mud_weight: float,
    pill_weight_increment: float = 2.0,
    coverage_factor: float = 1.5,
) -> Dict[str, Any]:
    """
    Design a viscous/heavy sweep pill for hole cleaning.

    Args:
        annular_volume_per_ft: annular volume (bbl/ft)
        annular_length: length of annulus to sweep (ft)
        mud_weight: current mud weight (ppg)
        pill_weight_increment: extra weight over current mud (ppg)
        coverage_factor: annular volume coverage (typically 1.0-2.0)

    Returns:
        Dict with pill_volume_bbl, pill_weight_ppg, pill_length_ft
    """
    annular_vol = annular_volume_per_ft * annular_length
    pill_volume = annular_vol * coverage_factor
    pill_weight = mud_weight + pill_weight_increment

    # Pill length in the annulus
    pill_length = 0.0
    if annular_volume_per_ft > 0:
        pill_length = pill_volume / annular_volume_per_ft

    return {
        "pill_volume_bbl": round(pill_volume, 1),
        "pill_weight_ppg": round(pill_weight, 1),
        "pill_length_ft": round(pill_length, 0),
        "annular_volume_bbl": round(annular_vol, 1),
    }
