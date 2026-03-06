"""
Petrophysics Engine — Full Petrophysical Evaluation Pipeline.

Runs complete log evaluation: Vsh → porosity → Sw → permeability → net pay.
"""
import math
from typing import Dict, Any, List, Optional

from .water_saturation import calculate_water_saturation_advanced
from .permeability import calculate_permeability_advanced


def run_full_evaluation(
    log_data: List[Dict],
    archie_params: Optional[Dict] = None,
    matrix_params: Optional[Dict] = None,
    cutoffs: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run complete petrophysical evaluation on log data.

    Computes Vsh, porosity, Sw (auto-model), permeability, net pay for each depth.

    Args:
        log_data: list of dicts with md, gr, rhob, nphi, rt (+ optional dt)
        archie_params: {a, m, n, rw}
        matrix_params: {rho_matrix, rho_fluid, gr_clean, gr_shale}
        cutoffs: {phi_min, sw_max, vsh_max}

    Returns:
        Dict with evaluated_data, summary, net_pay_intervals
    """
    ap = archie_params or {"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05}
    mp = matrix_params or {"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120}
    co = cutoffs or {"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40}

    evaluated = []
    for entry in log_data:
        md = entry.get("md", 0)
        gr = entry.get("gr")
        rhob = entry.get("rhob")
        nphi = entry.get("nphi")
        rt = entry.get("rt")

        if gr is None or rhob is None or nphi is None or rt is None:
            continue

        # Vshale (linear)
        gr_range = mp["gr_shale"] - mp["gr_clean"]
        vsh = (gr - mp["gr_clean"]) / max(gr_range, 1) if gr_range > 0 else 0
        vsh = max(0.0, min(vsh, 1.0))

        # Porosity (density-neutron RMS crossplot)
        phi_d = (mp["rho_matrix"] - rhob) / (mp["rho_matrix"] - mp["rho_fluid"])
        phi_d = max(0.0, min(phi_d, 0.50))
        phi = math.sqrt((phi_d ** 2 + nphi ** 2) / 2)
        phi = max(0.0, min(phi, 0.50))

        # Effective porosity
        phi_e = phi * (1.0 - vsh)
        phi_e = max(0.0, phi_e)

        # Water saturation (auto-model)
        sw_result = calculate_water_saturation_advanced(
            phi=max(phi_e, 0.01), rt=rt, rw=ap["rw"], vsh=vsh,
            rsh=2.0, a=ap["a"], m=ap["m"], n=ap["n"],
        )
        sw = sw_result.get("sw", 1.0)

        # Permeability
        sw_irr = min(sw, 0.50)
        perm = calculate_permeability_advanced(phi_e, sw_irr, "timur")

        # Net pay flag
        is_pay = phi_e >= co["phi_min"] and sw <= co["sw_max"] and vsh <= co["vsh_max"]

        evaluated.append({
            "md": md,
            "gr": gr, "rhob": rhob, "nphi": nphi, "rt": rt,
            "vsh": round(vsh, 4),
            "phi_total": round(phi, 4),
            "phi_effective": round(phi_e, 4),
            "sw": round(sw, 4),
            "sw_model": sw_result.get("model_used", "archie"),
            "k_md": perm.get("k_md", 0),
            "is_pay": is_pay,
            "hc_saturation": round(1.0 - sw, 4),
        })

    # Identify net pay intervals
    intervals = _identify_intervals(evaluated, co)

    # Auto-detect sample spacing from data (default 0.5 ft if < 2 points)
    if len(evaluated) >= 2:
        spacing = abs(evaluated[1]["md"] - evaluated[0]["md"])
        spacing = max(spacing, 0.1)  # guard against zero
    else:
        spacing = 0.5

    # Summary statistics
    pay_points = [e for e in evaluated if e["is_pay"]]
    summary = {
        "total_points": len(evaluated),
        "pay_points": len(pay_points),
        "net_pay_ft": round(len(pay_points) * spacing, 1) if pay_points else 0,
        "avg_phi_pay": round(sum(p["phi_effective"] for p in pay_points) / len(pay_points), 4) if pay_points else 0,
        "avg_sw_pay": round(sum(p["sw"] for p in pay_points) / len(pay_points), 4) if pay_points else 0,
        "avg_perm_pay": round(sum(p["k_md"] for p in pay_points) / len(pay_points), 2) if pay_points else 0,
    }

    return {
        "evaluated_data": evaluated,
        "summary": summary,
        "intervals": intervals,
    }


def _identify_intervals(evaluated: List[Dict], cutoffs: Dict) -> List[Dict]:
    """Group consecutive pay points into intervals."""
    intervals = []
    current = None

    for pt in evaluated:
        if pt["is_pay"]:
            if current is None:
                current = {
                    "top_md": pt["md"],
                    "base_md": pt["md"],
                    "points": [pt],
                }
            else:
                current["base_md"] = pt["md"]
                current["points"].append(pt)
        else:
            if current is not None:
                thickness = current["base_md"] - current["top_md"]
                if thickness >= cutoffs.get("min_thickness_ft", 0):
                    pts = current["points"]
                    intervals.append({
                        "top_md": current["top_md"],
                        "base_md": current["base_md"],
                        "thickness_ft": round(thickness, 1),
                        "avg_phi": round(sum(p["phi_effective"] for p in pts) / len(pts), 4),
                        "avg_sw": round(sum(p["sw"] for p in pts) / len(pts), 4),
                        "avg_perm_md": round(sum(p["k_md"] for p in pts) / len(pts), 2),
                    })
                current = None

    # Close last interval
    if current is not None:
        thickness = current["base_md"] - current["top_md"]
        pts = current["points"]
        if thickness >= cutoffs.get("min_thickness_ft", 0):
            intervals.append({
                "top_md": current["top_md"],
                "base_md": current["base_md"],
                "thickness_ft": round(thickness, 1),
                "avg_phi": round(sum(p["phi_effective"] for p in pts) / len(pts), 4),
                "avg_sw": round(sum(p["sw"] for p in pts) / len(pts), 4),
                "avg_perm_md": round(sum(p["k_md"] for p in pts) / len(pts), 2),
            })

    return intervals
