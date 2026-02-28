"""Full integrated shot-efficiency analysis pipeline."""
import math
from typing import Dict, Any, List, Optional

from .petrophysics import (
    calculate_porosity,
    calculate_vshale,
    calculate_water_saturation,
    calculate_sw_simandoux,
    calculate_sw_indonesia,
    calculate_sw_auto,
    calculate_porosity_sonic,
)
from .permeability import (
    calculate_permeability_timur,
    calculate_permeability_coates,
    classify_hydrocarbon_type,
)
from .skin import calculate_skin_factor
from .net_pay import identify_net_pay_intervals
from .ranking import rank_intervals
from .log_parser import parse_log_data


def calculate_full_shot_efficiency(
    log_entries: List[Dict],
    archie_params: Optional[Dict[str, float]] = None,
    matrix_params: Optional[Dict[str, float]] = None,
    cutoffs: Optional[Dict[str, float]] = None,
    perf_params: Optional[Dict[str, Any]] = None,
    reservoir_params: Optional[Dict[str, float]] = None,
    sw_model: str = "auto",
    rsh: float = 5.0,
    estimate_permeability: bool = False,
    sw_irreducible: float = 0.25
) -> Dict[str, Any]:
    """
    Full integrated shot-efficiency analysis pipeline.

    1. Parse and validate log data
    2. Compute porosity, Sw (auto/archie/simandoux/indonesia), Vshale per point
    3. Optionally estimate permeability (Timur) and compute kh
    4. Identify net pay intervals
    5. Calculate Karakas-Tariq skin per interval
    6. Classify HC type per interval
    7. Rank intervals by composite score (with kh if available)
    8. Compile summary with alerts

    Args:
        log_entries: raw log measurements
        archie_params: {a, m, n, rw}
        matrix_params: {rho_matrix, rho_fluid, gr_clean, gr_shale}
        cutoffs: {phi_min, sw_max, vsh_max, min_thickness_ft}
        perf_params: {spf, phasing_deg, perf_length_in, tunnel_radius_in}
        reservoir_params: {k_h, kv_kh, wellbore_radius_ft}
        sw_model: "auto", "archie", "simandoux", "indonesia" (default auto)
        rsh: shale resistivity for shaly-sand models (ohm-m)
        estimate_permeability: if True, estimate k from Timur and include kh in ranking
        sw_irreducible: irreducible Sw for permeability estimation (v/v)

    Returns:
        Dict with processed_logs, intervals, rankings, summary, alerts
    """
    # Resolve defaults
    ap = archie_params or {}
    a, m, n, rw = ap.get("a", 1.0), ap.get("m", 2.0), ap.get("n", 2.0), ap.get("rw", 0.05)

    mp = matrix_params or {}
    rho_matrix = mp.get("rho_matrix", 2.65)
    rho_fluid = mp.get("rho_fluid", 1.0)
    gr_clean = mp.get("gr_clean", 20.0)
    gr_shale = mp.get("gr_shale", 120.0)

    co = cutoffs or {}
    phi_min = co.get("phi_min", 0.08)
    sw_max = co.get("sw_max", 0.60)
    vsh_max = co.get("vsh_max", 0.40)
    min_thick = co.get("min_thickness_ft", 2.0)

    pp = perf_params or {}
    spf = pp.get("spf", 4)
    phasing_deg = pp.get("phasing_deg", 90)
    perf_length_in = pp.get("perf_length_in", 12.0)
    tunnel_radius_in = pp.get("tunnel_radius_in", 0.20)

    rp = reservoir_params or {}
    kv_kh = rp.get("kv_kh", 0.5)
    wellbore_radius_ft = rp.get("wellbore_radius_ft", 0.354)

    # Step 1: Parse logs
    parsed = parse_log_data(log_entries)
    if "error" in parsed:
        return {"summary": {}, "alerts": [parsed["error"]]}

    accepted = parsed["accepted"]
    if not accepted:
        return {"summary": {}, "alerts": ["No valid log points after parsing"], "parsing": parsed}

    # Step 2: Compute petrophysics with selected Sw model
    processed = []
    for pt in accepted:
        por = calculate_porosity(pt["rhob"], pt["nphi"], rho_matrix, rho_fluid)
        vsh_res = calculate_vshale(pt["gr"], gr_clean, gr_shale)
        phi_val = por.get("phi", 0.0)
        vsh_val = vsh_res.get("vsh", 1.0)

        # Sw model selection
        if sw_model == "auto":
            sw_res = calculate_sw_auto(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
        elif sw_model == "simandoux":
            sw_res = calculate_sw_simandoux(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
        elif sw_model == "indonesia":
            sw_res = calculate_sw_indonesia(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
        else:
            sw_res = calculate_water_saturation(pt["rt"], phi_val, rw, a, m, n)

        row = {
            "md": pt["md"], "gr": pt["gr"], "rhob": pt["rhob"],
            "nphi": pt["nphi"], "rt": pt["rt"],
            "phi": phi_val,
            "phi_density": por.get("phi_density", 0.0),
            "phi_neutron": por.get("phi_neutron", 0.0),
            "sw": sw_res.get("sw", 1.0),
            "hydrocarbon_saturation": sw_res.get("hydrocarbon_saturation", 0.0),
            "sw_class": sw_res.get("classification", ""),
            "sw_model": sw_res.get("method", "archie"),
            "vsh": vsh_val,
            "igr": vsh_res.get("igr", 1.0),
        }

        # Permeability estimation
        if estimate_permeability and phi_val > 0 and sw_irreducible > 0:
            k_res = calculate_permeability_timur(phi_val, sw_irreducible)
            row["k_md"] = k_res.get("k_md", 0.0)

        # HC type classification
        hc_res = classify_hydrocarbon_type(
            por.get("phi_density", 0.0), por.get("phi_neutron", 0.0),
            pt["rt"], 0.0, sw_res.get("sw", 1.0), 0.7
        )
        row["hc_type"] = hc_res.get("type", "water")

        processed.append(row)

    # Step 3: Identify net pay
    net_pay = identify_net_pay_intervals(processed, phi_min, sw_max, vsh_max, min_thick)
    intervals = net_pay["intervals"]

    # Step 4: Calculate skin per interval + add kh if permeability estimated
    for iv in intervals:
        skin_res = calculate_skin_factor(
            perf_length_in=perf_length_in,
            perf_radius_in=tunnel_radius_in,
            wellbore_radius_ft=wellbore_radius_ft,
            spf=spf, phasing_deg=phasing_deg,
            h_perf_ft=iv["thickness_ft"],
            kv_kh=kv_kh,
        )
        iv["skin_total"] = skin_res["s_total"]
        iv["skin_components"] = {"s_p": skin_res["s_p"], "s_v": skin_res["s_v"], "s_wb": skin_res["s_wb"]}

        # Aggregate kh per interval
        if estimate_permeability:
            interval_pts = [p for p in processed
                            if iv["top_md"] <= p["md"] <= iv["base_md"] and "k_md" in p]
            if interval_pts:
                avg_k = sum(p["k_md"] for p in interval_pts) / len(interval_pts)
                iv["k_md"] = round(avg_k, 3)
                iv["kh_md_ft"] = round(avg_k * iv["thickness_ft"], 1)

    # Step 5: Rank
    ranking = rank_intervals(intervals)

    # Step 6: Alerts & summary
    alerts = []
    if parsed["rejected_count"] > 0:
        alerts.append(f"{parsed['rejected_count']} log point(s) rejected during parsing")
    if net_pay["interval_count"] == 0:
        alerts.append("No net-pay intervals identified -- review cutoffs")
    if net_pay["total_net_pay_ft"] < 5.0 and net_pay["interval_count"] > 0:
        alerts.append(f"Thin total net pay ({net_pay['total_net_pay_ft']:.1f} ft)")

    best = ranking.get("best")
    if best:
        if best.get("skin_total", 0) > 10:
            alerts.append(f"High skin ({best['skin_total']:.1f}) on best interval -- consider stimulation")
        if best.get("avg_sw", 1) > 0.50:
            alerts.append(f"Best interval Sw={best['avg_sw']:.2f} -- risk of early water production")

    avg_phi_all = sum(p["phi"] for p in processed) / len(processed)
    avg_sw_all = sum(p["sw"] for p in processed) / len(processed)
    avg_vsh_all = sum(p["vsh"] for p in processed) / len(processed)

    summary = {
        "total_log_points": len(processed),
        "rejected_points": parsed["rejected_count"],
        "avg_porosity": round(avg_phi_all, 4),
        "avg_sw": round(avg_sw_all, 4),
        "avg_vsh": round(avg_vsh_all, 4),
        "net_pay_intervals_count": net_pay["interval_count"],
        "total_net_pay_ft": net_pay["total_net_pay_ft"],
        "sw_model_used": sw_model,
        "permeability_estimated": estimate_permeability,
        "best_interval": {
            "top_md": best["top_md"], "base_md": best["base_md"],
            "thickness_ft": best["thickness_ft"], "avg_phi": best["avg_phi"],
            "avg_sw": best["avg_sw"], "score": best["score"],
            "skin_total": best.get("skin_total", 0),
        } if best else None,
        "perf_config": {"spf": spf, "phasing_deg": phasing_deg, "perf_length_in": perf_length_in},
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "processed_logs": processed,
        "net_pay": net_pay,
        "intervals_with_skin": intervals,
        "rankings": ranking,
        "parameters": {
            "archie": {"a": a, "m": m, "n": n, "rw": rw},
            "matrix": {"rho_matrix": rho_matrix, "rho_fluid": rho_fluid, "gr_clean": gr_clean, "gr_shale": gr_shale},
            "cutoffs": {"phi_min": phi_min, "sw_max": sw_max, "vsh_max": vsh_max, "min_thickness_ft": min_thick},
            "perforation": {"spf": spf, "phasing_deg": phasing_deg, "perf_length_in": perf_length_in, "tunnel_radius_in": tunnel_radius_in},
            "reservoir": {"kv_kh": kv_kh, "wellbore_radius_ft": wellbore_radius_ft},
            "sw_model": sw_model,
            "rsh": rsh,
            "estimate_permeability": estimate_permeability,
            "sw_irreducible": sw_irreducible,
        },
        "alerts": alerts,
    }
