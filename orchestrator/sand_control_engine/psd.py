"""
Sand Control Engine — Particle Size Distribution (PSD) analysis.

References:
- Penberthy & Shaughnessy: Sand Control (SPE Series)
- Saucier (1974): Gravel sizing criteria (D_gravel = 5-6 × D50)
- Hazen uniformity coefficient: Cu = D60/D10
"""
import math
from typing import List, Dict, Any


def analyze_grain_distribution(
    sieve_sizes_mm: List[float],
    cumulative_passing_pct: List[float]
) -> Dict[str, Any]:
    """
    Analyze particle/grain size distribution from sieve analysis.

    Uses linear interpolation on cumulative passing curve to determine
    D10, D40, D50, D60, D90 and uniformity coefficient.

    Args:
        sieve_sizes_mm: sieve opening sizes in mm (descending order)
        cumulative_passing_pct: cumulative weight % passing each sieve

    Returns:
        Dict with D10, D40, D50, D60, D90, Cu, sorting description
    """
    if len(sieve_sizes_mm) < 3 or len(sieve_sizes_mm) != len(cumulative_passing_pct):
        return {"error": "Insufficient or mismatched sieve data"}

    # Ensure data is in descending sieve size order
    paired = sorted(zip(sieve_sizes_mm, cumulative_passing_pct), reverse=True)
    sizes = [p[0] for p in paired]
    passing = [p[1] for p in paired]

    def interpolate_d(target_pct: float) -> float:
        """Interpolate grain size at a given cumulative passing percentage."""
        for i in range(len(passing) - 1):
            if (passing[i] <= target_pct <= passing[i + 1]) or \
               (passing[i] >= target_pct >= passing[i + 1]):
                if passing[i + 1] == passing[i]:
                    return sizes[i]
                ratio = (target_pct - passing[i]) / (passing[i + 1] - passing[i])
                if sizes[i] > 0 and sizes[i + 1] > 0:
                    log_d = math.log10(sizes[i]) + ratio * (math.log10(sizes[i + 1]) - math.log10(sizes[i]))
                    return 10 ** log_d
                return sizes[i] + ratio * (sizes[i + 1] - sizes[i])
        # Extrapolate if outside range
        if target_pct <= min(passing):
            return max(sizes)
        return min(sizes)

    d10 = interpolate_d(10.0)
    d40 = interpolate_d(40.0)
    d50 = interpolate_d(50.0)
    d60 = interpolate_d(60.0)
    d90 = interpolate_d(90.0)

    cu = d60 / d10 if d10 > 0 else 0.0

    if cu < 2:
        sorting = "Very Well Sorted"
    elif cu < 3:
        sorting = "Well Sorted"
    elif cu < 5:
        sorting = "Moderately Sorted"
    elif cu < 10:
        sorting = "Poorly Sorted"
    else:
        sorting = "Very Poorly Sorted"

    return {
        "d10_mm": round(d10, 4),
        "d40_mm": round(d40, 4),
        "d50_mm": round(d50, 4),
        "d60_mm": round(d60, 4),
        "d90_mm": round(d90, 4),
        "uniformity_coefficient": round(cu, 2),
        "sorting": sorting,
        "sieve_count": len(sieve_sizes_mm)
    }


def select_gravel_size(
    d50_mm: float,
    d10_mm: float,
    d90_mm: float,
    uniformity_coefficient: float
) -> Dict[str, Any]:
    """
    Select optimal gravel size using Saucier criterion.

    Saucier (1974): D_gravel = 5-6 × D50 of formation sand.
    For poorly sorted sands (Cu > 5), use conservative (D50+D10)/2.

    Args:
        d50_mm: median grain size (mm)
        d10_mm: 10th percentile grain size (mm)
        d90_mm: 90th percentile grain size (mm)
        uniformity_coefficient: Cu = D60/D10

    Returns:
        Dict with recommended gravel size range and standard mesh sizes
    """
    if uniformity_coefficient > 5:
        reference_d = (d50_mm + d10_mm) / 2.0
    else:
        reference_d = d50_mm

    multiplier_low = 5.0
    multiplier_high = 6.0
    gravel_min_mm = reference_d * multiplier_low
    gravel_max_mm = reference_d * multiplier_high

    standard_packs = [
        {"name": "12/20", "min_mm": 0.85, "max_mm": 1.70},
        {"name": "16/30", "min_mm": 0.60, "max_mm": 1.18},
        {"name": "20/40", "min_mm": 0.425, "max_mm": 0.85},
        {"name": "40/60", "min_mm": 0.25, "max_mm": 0.425},
        {"name": "50/70", "min_mm": 0.212, "max_mm": 0.30},
    ]

    recommended_pack = "Custom"
    for pack in standard_packs:
        if pack["min_mm"] <= gravel_min_mm <= pack["max_mm"] or \
           pack["min_mm"] <= gravel_max_mm <= pack["max_mm"]:
            recommended_pack = pack["name"]
            break

    if recommended_pack == "Custom":
        target_mid = (gravel_min_mm + gravel_max_mm) / 2.0
        best_diff = float('inf')
        for pack in standard_packs:
            mid = (pack["min_mm"] + pack["max_mm"]) / 2.0
            diff = abs(mid - target_mid)
            if diff < best_diff:
                best_diff = diff
                recommended_pack = pack["name"]

    return {
        "gravel_min_mm": round(gravel_min_mm, 3),
        "gravel_max_mm": round(gravel_max_mm, 3),
        "recommended_pack": recommended_pack,
        "saucier_multiplier_low": multiplier_low,
        "saucier_multiplier_high": multiplier_high,
        "reference_d_mm": round(reference_d, 4),
        "criterion": "Saucier (1974)"
    }
