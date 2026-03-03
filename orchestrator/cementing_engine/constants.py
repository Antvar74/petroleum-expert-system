"""
Cementing Engine — constants and reference tables.

References:
- API Spec 10A: Cements and Materials for Well Cementing
- Nelson & Guillot: Well Cementing (2nd Edition, Schlumberger)
"""
from typing import Optional


# -------------------------------------------------------------------
# API 10A cement class reference table
# -------------------------------------------------------------------
CEMENT_CLASSES = {
    "A":  {"density_range": (15.0, 16.0), "depth_ft": 6000,  "use": "Surface / Conductor"},
    "B":  {"density_range": (15.0, 16.0), "depth_ft": 6000,  "use": "Surface / Conductor"},
    "C":  {"density_range": (14.0, 15.0), "depth_ft": 6000,  "use": "High early strength"},
    "G":  {"density_range": (15.6, 16.4), "depth_ft": 8000,  "use": "General purpose (most common)"},
    "H":  {"density_range": (16.0, 16.5), "depth_ft": 8000,  "use": "General purpose"},
}

# Typical spacer / wash densities
DEFAULT_SPACER_DENSITY = 10.0             # ppg (water-based spacer)
DEFAULT_WASH_VOLUME_BBL_PER_1000FT = 5.0  # rule of thumb


def infer_cement_class(density_ppg: float) -> Optional[str]:
    """
    Infer API 10A cement class from slurry density. Returns class letter or None.

    Non-overlapping classification per API Spec 10A (ordered by density, higher wins):
      C  : ≤ 15.0 ppg  (6,000 ft max)
      G  : 15.0–16.0 ppg, exclusive at 16.0  (8,000 ft max)
      H  : 16.0–16.5 ppg  (8,000 ft max)
      H+ : > 16.5 ppg  weighted cement, treated as H for depth check

    At exactly 16.0 ppg G and H overlap per API 10A; H is used (higher class).
    """
    if density_ppg <= 0:
        return None
    if density_ppg <= 15.0:
        return "C"
    if density_ppg < 16.0:
        return "G"
    if density_ppg <= 16.5:
        return "H"
    return "H"  # weighted/extended density — treat as H for depth check
