"""
Packer type classification — free, anchored, limited movement behavior.

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
"""
import math
from typing import Dict, Any

from .geometry import STEEL_E


def calculate_packer_force_by_type(
    packer_type: str,
    total_force_if_anchored: float,
    tubing_movement_if_free_in: float,
    stroke_in: float = 0.0,
    tubing_length_ft: float = 10000.0,
    tubing_as: float = 3.0,
    youngs_modulus: float = STEEL_E,
) -> Dict[str, Any]:
    """
    Calculate force/displacement based on packer type classification.

    Free (polished bore): tubing moves freely, force on packer = 0
    Anchored: no movement allowed, all force absorbed by packer
    Limited movement: hybrid — free until stroke exhausted, then anchored

    Args:
        packer_type: 'free', 'anchored', 'limited'
        total_force_if_anchored: force that would act if fully anchored (lbs)
        tubing_movement_if_free_in: movement that would occur if free (in)
        stroke_in: available stroke for limited-movement packer (in)
        tubing_length_ft: tubing length (ft)
        tubing_as: tubing steel area (in²)
        youngs_modulus: Young's modulus (psi)

    Returns:
        Dict with force_on_packer, tubing_displacement, packer_status.
    """
    pt = packer_type.lower().strip()

    if pt == "free":
        return {
            "packer_type": "free",
            "force_on_packer_lbs": 0.0,
            "tubing_displacement_in": round(tubing_movement_if_free_in, 3),
            "packer_status": "Free movement -- tubing moved",
            "seal_engagement": abs(tubing_movement_if_free_in) < 48.0,
            "remaining_stroke_in": None,
        }

    if pt == "anchored":
        return {
            "packer_type": "anchored",
            "force_on_packer_lbs": round(total_force_if_anchored, 0),
            "tubing_displacement_in": 0.0,
            "packer_status": "Anchored -- full force absorbed by packer",
            "seal_engagement": True,
            "remaining_stroke_in": None,
        }

    if pt == "limited":
        if abs(tubing_movement_if_free_in) <= stroke_in:
            return {
                "packer_type": "limited",
                "force_on_packer_lbs": 0.0,
                "tubing_displacement_in": round(tubing_movement_if_free_in, 3),
                "packer_status": "Limited -- within stroke (free behavior)",
                "seal_engagement": True,
                "remaining_stroke_in": round(stroke_in - abs(tubing_movement_if_free_in), 3),
            }
        else:
            excess_in = abs(tubing_movement_if_free_in) - stroke_in
            stiffness = youngs_modulus * tubing_as / (tubing_length_ft * 12.0) if tubing_length_ft > 0 else 1e6
            excess_force = stiffness * excess_in
            if tubing_movement_if_free_in < 0:
                excess_force = -excess_force

            actual_displacement = math.copysign(stroke_in, tubing_movement_if_free_in)

            return {
                "packer_type": "limited",
                "force_on_packer_lbs": round(excess_force, 0),
                "tubing_displacement_in": round(actual_displacement, 3),
                "packer_status": "Limited -- stroke exhausted (partially anchored)",
                "seal_engagement": True,
                "remaining_stroke_in": 0.0,
            }

    return {"error": f"Unknown packer type: {packer_type}. Use 'free', 'anchored', or 'limited'."}
