"""
Tubing geometry — cross-sectional areas and steel material constants.

References:
- API TR 5C3: Casing and Tubing Buckling in Wellbores
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
"""
import math
from typing import Dict

# Steel material constants
STEEL_E = 30e6         # Young's modulus (psi)
STEEL_POISSON = 0.30   # Poisson's ratio
STEEL_ALPHA = 6.9e-6   # Thermal expansion coefficient (1/°F)
STEEL_DENSITY_PPG = 65.5  # Steel density (ppg) for buoyancy factor calculations


def calculate_tubing_areas(od: float, id_inner: float) -> Dict[str, float]:
    """
    Calculate tubing cross-sectional areas.

    Args:
        od: tubing outer diameter (inches)
        id_inner: tubing inner diameter (inches)

    Returns:
        Dict with ao, ai, as (outer, inner, steel areas in in²)
    """
    ao = math.pi * (od / 2.0) ** 2
    ai = math.pi * (id_inner / 2.0) ** 2
    a_steel = ao - ai
    return {
        "ao_in2": round(ao, 4),
        "ai_in2": round(ai, 4),
        "as_in2": round(a_steel, 4),
    }
