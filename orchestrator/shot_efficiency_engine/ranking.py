"""Interval scoring and ranking for perforation optimization."""
from typing import Dict, Any, List, Optional


def rank_intervals(
    intervals: List[Dict],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Score and rank candidate perforation intervals.

    score = w_phi * phi_norm + w_sw * (1-sw_norm) + w_thick * thick_norm
            + w_skin * (1/(1+|skin|)) [+ w_kh * kh_norm if available]

    Default weights: phi=0.30, sw=0.25, thickness=0.20, skin=0.10, kh=0.15

    Args:
        intervals: list of interval dicts with avg_phi, avg_sw, thickness_ft, skin_total
                   optionally: k_md, kh_md (from permeability estimation)
        weights: optional dict overriding default weights

    Returns:
        Dict with ranked list and best interval
    """
    if not intervals:
        return {"ranked": [], "best": None}

    has_kh = any("kh_md_ft" in iv or "k_md" in iv for iv in intervals)

    if has_kh:
        w = weights or {"phi": 0.25, "sw": 0.20, "thickness": 0.15, "skin": 0.10, "kh": 0.30}
    else:
        w = weights or {"phi": 0.35, "sw": 0.25, "thickness": 0.25, "skin": 0.15}

    phis = [iv["avg_phi"] for iv in intervals]
    sws = [iv["avg_sw"] for iv in intervals]
    thicks = [iv["thickness_ft"] for iv in intervals]

    def _norm(val, lo, hi):
        return (val - lo) / (hi - lo) if hi != lo else 1.0

    phi_lo, phi_hi = min(phis), max(phis)
    sw_lo, sw_hi = min(sws), max(sws)
    th_lo, th_hi = min(thicks), max(thicks)

    kh_lo, kh_hi = 0.0, 1.0
    if has_kh:
        kh_values = [iv.get("kh_md_ft", iv.get("k_md", 0) * iv.get("thickness_ft", 1)) for iv in intervals]
        kh_lo = min(kh_values) if kh_values else 0.0
        kh_hi = max(kh_values) if kh_values else 1.0

    scored = []
    for iv in intervals:
        phi_n = _norm(iv["avg_phi"], phi_lo, phi_hi)
        sw_n = _norm(iv["avg_sw"], sw_lo, sw_hi)
        th_n = _norm(iv["thickness_ft"], th_lo, th_hi)
        sk_factor = 1.0 / (1.0 + abs(iv.get("skin_total", 0.0)))

        score = (w.get("phi", 0.35) * phi_n + w.get("sw", 0.25) * (1.0 - sw_n)
                 + w.get("thickness", 0.25) * th_n + w.get("skin", 0.15) * sk_factor)

        if has_kh and "kh" in w:
            kh_val = iv.get("kh_md_ft", iv.get("k_md", 0) * iv.get("thickness_ft", 1))
            kh_n = _norm(kh_val, kh_lo, kh_hi)
            score += w["kh"] * kh_n

        scored.append({**iv, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    for idx, item in enumerate(scored):
        item["rank"] = idx + 1

    return {"ranked": scored, "best": scored[0] if scored else None, "weights_used": w}
