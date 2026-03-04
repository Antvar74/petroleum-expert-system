"""
CT Geometry — coiled tubing dimensional properties.

Reference: ICoTA Coiled Tubing Manual
"""
import math
from typing import Dict, Any

STEEL_DENSITY = 490.0       # lb/ft³
STEEL_WEIGHT_WATER = 65.5   # ppg equivalent (used for buoyancy factor)
GRAVITY = 32.174            # ft/s²


def calculate_ct_dimensions(ct_od: float, wall_thickness: float) -> Dict[str, Any]:
    """
    Calculate coiled tubing geometric properties.

    Args:
        ct_od: CT outer diameter (inches)
        wall_thickness: CT wall thickness (inches)

    Returns:
        Dict with ct_id, cross_section areas, weight_per_ft
    """
    ct_id = ct_od - 2 * wall_thickness
    if ct_id <= 0 or ct_od <= 0:
        return {"error": "Invalid CT dimensions"}

    outer_area = math.pi / 4.0 * ct_od ** 2       # in²
    inner_area = math.pi / 4.0 * ct_id ** 2        # in²
    metal_area = outer_area - inner_area            # in²

    # Weight per foot: steel density × metal area / 144 (in²→ft²)
    weight_per_ft = STEEL_DENSITY * metal_area / 144.0  # lb/ft

    return {
        "ct_od_in": ct_od,
        "ct_id_in": round(ct_id, 3),
        "wall_thickness_in": wall_thickness,
        "outer_area_in2": round(outer_area, 4),
        "inner_area_in2": round(inner_area, 4),
        "metal_area_in2": round(metal_area, 4),
        "weight_per_ft_lb": round(weight_per_ft, 3),
    }
