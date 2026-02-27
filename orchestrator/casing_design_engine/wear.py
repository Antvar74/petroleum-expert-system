"""
Casing Design — Wear and Corrosion Allowance

Reduces wall thickness for mechanical wear and corrosion over the
design life, then recalculates burst (Barlow) and collapse (API 5C3)
ratings with the remaining wall thickness.

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe
- API 5CT: Specification for Casing and Tubing
- NACE MR0175 / ISO 15156: Materials for use in H2S-containing environments
"""
from typing import Dict, Any

from .ratings import calculate_burst_rating, calculate_collapse_rating


def apply_wear_allowance(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
    wear_pct: float = 0.0,
    corrosion_rate_in_yr: float = 0.0,
    design_life_years: float = 20.0,
) -> Dict[str, Any]:
    """
    Reduce wall thickness for wear and corrosion, then recalculate ratings.

    - Wear: wall_remaining = wall * (1 - wear_pct/100)
    - Corrosion: wall_remaining -= corrosion_rate * design_life
    - Recalculate burst (Barlow) and collapse (API 5C3) with remaining wall
    """
    wall_worn = wall_thickness_in * (1.0 - wear_pct / 100.0)
    wall_corroded = wall_worn - corrosion_rate_in_yr * design_life_years
    wall_remaining = max(wall_corroded, 0.05)  # minimum wall

    remaining_pct = (wall_remaining / wall_thickness_in * 100) if wall_thickness_in > 0 else 0

    # Original ratings
    burst_orig = calculate_burst_rating(casing_od_in, wall_thickness_in, yield_strength_psi)
    collapse_orig = calculate_collapse_rating(casing_od_in, wall_thickness_in, yield_strength_psi)

    # Derated ratings
    burst_derated = calculate_burst_rating(casing_od_in, wall_remaining, yield_strength_psi)
    collapse_derated = calculate_collapse_rating(casing_od_in, wall_remaining, yield_strength_psi)

    return {
        "original_wall_in": wall_thickness_in,
        "remaining_wall_in": round(wall_remaining, 4),
        "remaining_wall_pct": round(remaining_pct, 1),
        "wear_loss_in": round(wall_thickness_in - wall_worn, 4),
        "corrosion_loss_in": round(corrosion_rate_in_yr * design_life_years, 4),
        "original_burst_psi": burst_orig.get("burst_rating_psi", 0),
        "derated_burst_psi": burst_derated.get("burst_rating_psi", 0),
        "burst_reduction_pct": round(
            (1 - burst_derated.get("burst_rating_psi", 0) / max(burst_orig.get("burst_rating_psi", 1), 1)) * 100, 1),
        "original_collapse_psi": collapse_orig.get("collapse_rating_psi", 0),
        "derated_collapse_psi": collapse_derated.get("collapse_rating_psi", 0),
        "collapse_reduction_pct": round(
            (1 - collapse_derated.get("collapse_rating_psi", 0) / max(collapse_orig.get("collapse_rating_psi", 1), 1)) * 100, 1),
        "design_life_years": design_life_years,
    }
