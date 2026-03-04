"""
Sand Control Engine — Screen slot size selection.

References:
- API RP 19C: Procedures for Testing Sand Control Screens
- Penberthy & Shaughnessy: Sand Control (SPE Series)
  Wire wrap: slot ≈ 2×D10 (retains ~90% of formation sand)
  Premium mesh: slot ≈ D10 (retains ~95% — used for open hole)
"""
from typing import Dict, Any


def select_screen_slot(
    d10_mm: float,
    d50_mm: float,
    screen_type: str = "wire_wrap"
) -> Dict[str, Any]:
    """
    Select screen slot size based on grain size distribution.

    Wire wrap: slot ≈ 2 × D10 (retains 90% of formation sand)
    Premium mesh: slot ≈ D10 (retains 95% — recommended for open hole)

    Args:
        d10_mm: 10th percentile grain size (mm)
        d50_mm: 50th percentile grain size (mm)
        screen_type: 'wire_wrap' or 'premium_mesh'

    Returns:
        Dict with slot_size_mm, slot_size_inches, gauge, standard slot
    """
    if screen_type == "premium_mesh":
        slot_mm = d10_mm
    else:  # wire_wrap
        slot_mm = 2.0 * d10_mm

    slot_in = slot_mm / 25.4
    gauge = round(slot_in * 1000, 0)

    standard_slots = [0.006, 0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025, 0.030]
    closest_slot = min(standard_slots, key=lambda s: abs(s - slot_in))

    retention_estimate = 90.0 if screen_type == "wire_wrap" else 95.0

    return {
        "slot_size_mm": round(slot_mm, 3),
        "slot_size_in": round(slot_in, 4),
        "gauge_thou": gauge,
        "recommended_standard_slot_in": closest_slot,
        "screen_type": screen_type,
        "estimated_retention_pct": retention_estimate
    }
