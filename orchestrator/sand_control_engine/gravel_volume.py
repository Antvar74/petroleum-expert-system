"""
Sand Control Engine — Gravel pack volume calculations.

References:
- Penberthy & Shaughnessy: Sand Control (SPE Series)
- V = annular_volume × pack_factor × washout_factor
- Gravel density packed: ~165 lb/ft³
- Capacity factor: 1 ft³ = 1/5.615 bbl
"""
import math
from typing import Dict, Any


def calculate_gravel_volume(
    hole_id: float,
    screen_od: float,
    interval_length: float,
    pack_factor: float = 1.4,
    washout_factor: float = 1.1
) -> Dict[str, Any]:
    """
    Calculate gravel volume required for packing.

    V = annular_volume × pack_factor × washout_factor

    Args:
        hole_id: open hole or casing ID (inches)
        screen_od: screen OD (inches)
        interval_length: completion interval length (ft)
        pack_factor: overfill factor (typically 1.3-1.5)
        washout_factor: hole enlargement factor (1.0 = gauge hole)

    Returns:
        Dict with gravel volume in bbl, ft³, lb
    """
    if hole_id <= screen_od:
        return {"error": "Hole ID must be larger than screen OD"}

    # Effective hole diameter (with washout)
    effective_hole_id = hole_id * math.sqrt(washout_factor)

    # Annular volume
    annular_area_in2 = math.pi / 4.0 * (effective_hole_id ** 2 - screen_od ** 2)
    annular_vol_ft3 = annular_area_in2 * interval_length / 144.0

    # Apply pack factor
    gravel_vol_ft3 = annular_vol_ft3 * pack_factor
    gravel_vol_bbl = gravel_vol_ft3 / 5.615

    # Weight (gravel density ≈ 165 lb/ft³ packed)
    gravel_weight_lb = gravel_vol_ft3 * 165.0

    ann_vol_per_ft_bbl = (annular_area_in2 / 144.0) / 5.615

    return {
        "gravel_volume_bbl": round(gravel_vol_bbl, 1),
        "gravel_volume_ft3": round(gravel_vol_ft3, 1),
        "gravel_weight_lb": round(gravel_weight_lb, 0),
        "annular_volume_bbl": round(annular_vol_ft3 / 5.615, 1),
        "annular_vol_per_ft_bbl": round(ann_vol_per_ft_bbl, 4),
        "effective_hole_id_in": round(effective_hole_id, 3),
        "pack_factor": pack_factor,
        "washout_factor": washout_factor,
        "interval_length_ft": interval_length
    }
