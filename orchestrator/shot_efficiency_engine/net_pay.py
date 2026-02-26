"""Net pay interval identification from processed log data."""
from typing import Dict, Any, List


def identify_net_pay_intervals(
    log_data: List[Dict],
    phi_cutoff: float = 0.08,
    sw_cutoff: float = 0.60,
    vsh_cutoff: float = 0.40,
    min_thickness_ft: float = 2.0
) -> Dict[str, Any]:
    """
    Identify net-pay intervals from processed log data.

    A depth point passes: phi > phi_min, Sw < Sw_max, Vsh < Vsh_max.
    Contiguous passing points grouped into intervals.
    Intervals thinner than min_thickness_ft are discarded.

    Args:
        log_data: list of dicts with md, phi, sw, vsh
        phi_cutoff: minimum porosity (v/v)
        sw_cutoff: maximum water saturation (v/v)
        vsh_cutoff: maximum shale volume (v/v)
        min_thickness_ft: minimum interval thickness (ft)

    Returns:
        Dict with intervals list and summary statistics
    """
    if not log_data:
        return {
            "intervals": [], "interval_count": 0, "total_net_pay_ft": 0.0,
            "gross_pay_ft": 0.0, "net_to_gross": 0.0,
        }

    # Tag each point
    tagged = []
    for pt in log_data:
        passes = (
            pt.get("phi", 0) > phi_cutoff
            and pt.get("sw", 1) < sw_cutoff
            and pt.get("vsh", 1) < vsh_cutoff
        )
        tagged.append({**pt, "is_net_pay": passes})

    # Group contiguous passing points
    intervals = []
    current_group = []

    for pt in tagged:
        if pt["is_net_pay"]:
            current_group.append(pt)
        else:
            if current_group:
                intervals.append(current_group)
                current_group = []
    if current_group:
        intervals.append(current_group)

    # Build interval summaries
    result_intervals = []
    total_net = 0.0

    for grp in intervals:
        top_md = grp[0]["md"]
        base_md = grp[-1]["md"]
        thickness = base_md - top_md
        if len(grp) == 1:
            thickness = 0.5  # single-point: assume 0.5 ft spacing

        if thickness < min_thickness_ft:
            continue

        avg_phi = sum(p["phi"] for p in grp) / len(grp)
        avg_sw = sum(p["sw"] for p in grp) / len(grp)
        avg_vsh = sum(p["vsh"] for p in grp) / len(grp)

        result_intervals.append({
            "top_md": round(top_md, 1),
            "base_md": round(base_md, 1),
            "thickness_ft": round(thickness, 1),
            "avg_phi": round(avg_phi, 4),
            "avg_sw": round(avg_sw, 4),
            "avg_vsh": round(avg_vsh, 4),
            "is_net_pay": True,
            "point_count": len(grp),
        })
        total_net += thickness

    gross_pay = log_data[-1]["md"] - log_data[0]["md"]

    return {
        "intervals": result_intervals,
        "interval_count": len(result_intervals),
        "total_net_pay_ft": round(total_net, 1),
        "gross_pay_ft": round(gross_pay, 1),
        "net_to_gross": round(total_net / gross_pay, 4) if gross_pay > 0 else 0.0,
        "cutoffs_used": {
            "phi_min": phi_cutoff, "sw_max": sw_cutoff,
            "vsh_max": vsh_cutoff, "min_thickness_ft": min_thickness_ft,
        },
    }
