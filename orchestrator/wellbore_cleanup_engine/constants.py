"""
Physical constants and API RP 13D recommended minimums for hole cleaning.

References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 4
"""

# Physical constants
GRAVITY = 32.174        # ft/s² (acceleration due to gravity)
WATER_DENSITY = 8.34    # ppg (fresh water)

# Minimum annular velocities (API RP 13D)
MIN_AV_VERTICAL = 120.0      # ft/min for <30° inclination
MIN_AV_HIGH_ANGLE = 150.0    # ft/min for >60° inclination
MIN_AV_TRANSITION = 130.0    # ft/min for 30-60° inclination


def get_min_annular_velocity(inclination: float) -> float:
    """
    Return minimum annular velocity for a given inclination (API RP 13D).

    Args:
        inclination: wellbore inclination (degrees from vertical)

    Returns:
        Minimum annular velocity (ft/min)
    """
    if inclination < 30:
        return MIN_AV_VERTICAL
    elif inclination > 60:
        return MIN_AV_HIGH_ANGLE
    else:
        return MIN_AV_TRANSITION
