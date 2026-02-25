"""Stabilizer placement optimization (node-based).

References:
- Mitchell (2003): Transfer Matrix analysis of BHA vibrations
"""
from typing import Dict, Any, List, Optional, Tuple

from .critical_speeds import calculate_critical_rpm_lateral_multi


def optimize_stabilizer_placement(
    bha_components: List[Dict[str, Any]],
    hole_diameter_in: float = 8.5,
    target_rpm_range: Optional[Tuple[float, float]] = None,
    mud_weight_ppg: float = 10.0,
    num_candidates: int = 5
) -> Dict[str, Any]:
    """
    Determine optimal stabilizer position to maximise separation between
    operating RPM range and BHA natural frequencies.

    Strategy: insert a virtual "stabilizer" (pinned constraint) at various
    candidate positions along the BHA and evaluate which position shifts
    the critical RPM farthest from the target operating window.

    Args:
        bha_components: list of BHA component dicts (same format as TMM)
        hole_diameter_in: hole / casing ID (in)
        target_rpm_range: (min_rpm, max_rpm) operating window
        mud_weight_ppg: mud weight (ppg)
        num_candidates: number of candidate positions to evaluate

    Returns:
        Dict with optimal_position, frequency_separation, evaluated candidates.
    """
    if not bha_components:
        return {"error": "No BHA components provided"}

    if target_rpm_range is None:
        target_rpm_range = (80, 160)

    rpm_low, rpm_high = target_rpm_range
    rpm_mid = (rpm_low + rpm_high) / 2.0

    # Total BHA length
    total_length_ft = sum(c.get("length_ft", 30.0) for c in bha_components)

    # Baseline critical RPM (no extra stabilizer)
    baseline = calculate_critical_rpm_lateral_multi(
        bha_components, mud_weight_ppg, hole_diameter_in
    )
    baseline_rpm = baseline.get("mode_1_critical_rpm", 120)

    # Generate candidate positions (evenly spaced along BHA)
    candidates = []
    for i in range(1, num_candidates + 1):
        pos_frac = i / (num_candidates + 1)
        pos_ft = total_length_ft * pos_frac

        # Split BHA at this position into two spans -> higher critical RPM
        # Approximate: shorter span -> higher critical RPM
        span_1 = pos_ft
        span_2 = total_length_ft - pos_ft

        # Critical RPM scales as 1/L^2 approximately
        if span_1 > 0 and span_2 > 0:
            # The governing mode is the longer span
            governing_span = max(span_1, span_2)
            # Approximate new critical RPM
            rpm_new = baseline_rpm * (total_length_ft / governing_span) ** 2
            rpm_new = min(rpm_new, 500)  # cap at reasonable value
        else:
            rpm_new = baseline_rpm

        # Separation from operating window
        if rpm_new < rpm_low:
            separation = rpm_low - rpm_new
        elif rpm_new > rpm_high:
            separation = rpm_new - rpm_high
        else:
            separation = 0  # Inside operating window = bad

        # Clearance / standoff
        avg_od = sum(c.get("od", 6.75) for c in bha_components) / len(bha_components)
        standoff = (hole_diameter_in - avg_od) / 2.0

        candidates.append({
            "position_ft": round(pos_ft, 1),
            "position_pct": round(pos_frac * 100, 1),
            "estimated_critical_rpm": round(rpm_new, 0),
            "separation_from_window_rpm": round(separation, 0),
            "span_1_ft": round(span_1, 1),
            "span_2_ft": round(span_2, 1),
        })

    # Select best: maximum separation
    best = max(candidates, key=lambda c: c["separation_from_window_rpm"])

    # Standoff calculation
    avg_od = sum(c.get("od", 6.75) for c in bha_components) / len(bha_components)
    standoff_pct = ((hole_diameter_in - avg_od) / (hole_diameter_in - avg_od)) * 100 if hole_diameter_in > avg_od else 0
    # Actual standoff pct with stabilizer (blade OD ~ hole_id - 0.125")
    stab_od = hole_diameter_in - 0.125
    standoff_with_stab = ((stab_od - avg_od) / (hole_diameter_in - avg_od)) * 100 if hole_diameter_in > avg_od else 0

    return {
        "optimal_position_ft": best["position_ft"],
        "optimal_position_pct": best["position_pct"],
        "estimated_critical_rpm_after": best["estimated_critical_rpm"],
        "baseline_critical_rpm": round(baseline_rpm, 0),
        "frequency_separation_rpm": best["separation_from_window_rpm"],
        "target_rpm_range": list(target_rpm_range),
        "standoff_pct": round(min(standoff_with_stab, 100), 1),
        "candidates": candidates,
        "total_bha_length_ft": round(total_length_ft, 1),
    }
