"""
Hole Cleaning Index (HCI) — Luo et al. (1992).

Accounts for annular velocity, pipe rotation, fluid rheology, and mud density.
All four factors are applied regardless of inclination (conservative approach).

References:
- Luo, Y., Bern, P.A., & Chambers, B.D. (1992):
  "Flow-Rate Predictions for Cleaning Deviated Wells" SPE 23884
- API RP 13D
"""
from .constants import get_min_annular_velocity


def calculate_hole_cleaning_index(
    annular_velocity: float,
    rpm: float,
    inclination: float,
    mud_weight: float,
    cutting_density: float,
    pv: float,
    yp: float,
) -> float:
    """
    Hole Cleaning Index (HCI) based on Luo et al. (1992) — SPE 23884.

    HCI = velocity_ratio × rpm_factor × rheo_factor × density_factor

    All four factors are applied at every inclination for conservative evaluation.

    Components (per KB §2.7):
      velocity_ratio = V_ann / V_min       (capped at 1.5)
      rpm_factor     = 0.7 + 0.3 × min(RPM / 120, 1.0)
      rheo_factor    = 0.6 + 0.4 × min(YP / 15, 1.0)
      density_factor = 0.8 + 0.2 × min(MW / 10, 1.0)

    Interpretation:
      > 0.90  Excellent
      0.70–0.90  Good
      0.50–0.70  Fair — increase AV or RPM
      < 0.50  Poor — immediate action required

    Args:
        annular_velocity: annular velocity (ft/min)
        rpm: drillstring rotation (RPM)
        inclination: wellbore inclination (degrees)
        mud_weight: mud density (ppg)
        cutting_density: cutting density (ppg)  [unused, kept for backward compat]
        pv: plastic viscosity (cP)  [unused, kept for backward compat]
        yp: yield point (lb/100ft²)

    Returns:
        HCI (dimensionless)
    """
    va_min = get_min_annular_velocity(inclination)

    if va_min <= 0:
        return 0.0

    # Velocity ratio — capped at 1.5 per Luo (1992)
    velocity_ratio = min(annular_velocity / va_min, 1.5)

    # RPM factor: 0.7 (no rotation) to 1.0 (≥120 RPM)
    rpm_factor = 0.7 + 0.3 * min(rpm / 120.0, 1.0)

    # Rheology factor: 0.6 (low YP) to 1.0 (YP ≥ 15)
    rheo_factor = 0.6 + 0.4 * min(yp / 15.0, 1.0)

    # Density factor: 0.8 (light mud) to 1.0 (MW ≥ 10 ppg)
    density_factor = 0.8 + 0.2 * min(mud_weight / 10.0, 1.0)

    hci = velocity_ratio * rpm_factor * rheo_factor * density_factor
    return round(hci, 3)
