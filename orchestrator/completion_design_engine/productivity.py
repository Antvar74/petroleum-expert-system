"""
Completion Design Engine — perforation productivity (Karakas & Tariq 1991).

Reference: Karakas & Tariq (1991) SPE 18247 — Semi-analytical productivity
model for perforated completions. Table 1 phasing constants, Table 2 vertical
flow skin constants.
"""
import math
from typing import Dict, Any

from .penetration import calculate_penetration_depth


def calculate_productivity_ratio(
    formation_permeability_md: float,
    perforation_length_in: float,
    perforation_radius_in: float,
    wellbore_radius_ft: float,
    spf: int,
    phasing_deg: int,
    formation_thickness_ft: float,
    kv_kh_ratio: float = 1.0,
    damage_radius_ft: float = 0.0,
    damage_permeability_md: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate productivity ratio using Karakas & Tariq (1991) model.

    S_total = S_p + S_v + S_wb + S_d
    PR = ln(re/rw) / (ln(re/rw) + S_total)

    K&T phasing constants (Table 1) govern S_p and S_wb.
    K&T vertical flow skin constants (Table 2) govern S_v — they are NOT
    phasing-dependent: a1=2.091, a2=0.0453, b1=5.1313, b2=1.8672.

    Args:
        formation_permeability_md: horizontal permeability (mD)
        perforation_length_in: total perforation tunnel length (inches)
        perforation_radius_in: perforation tunnel radius (inches)
        wellbore_radius_ft: wellbore radius (ft)
        spf: shots per foot
        phasing_deg: gun phasing (degrees: 0, 60, 90, 120, 180, 360)
        formation_thickness_ft: net pay thickness (ft)
        kv_kh_ratio: vertical to horizontal permeability ratio
        damage_radius_ft: extent of damaged zone (ft) (0 = no damage)
        damage_permeability_md: permeability of damaged zone (mD)

    Returns:
        Dict with skin components, total skin, PR
    """
    r_w = wellbore_radius_ft
    l_p = perforation_length_in / 12.0   # convert to feet
    r_p = perforation_radius_in / 12.0   # convert to feet
    h = formation_thickness_ft
    k_h = formation_permeability_md
    k_v = k_h * kv_kh_ratio

    # Effective perforation spacing (feet between shots along wellbore)
    h_perf_ft = 1.0 / spf if spf > 0 else h

    # Phasing-dependent constants (K&T 1991 Table 1)
    # α_θ: plane-flow effective-wellbore term; c1, c2: wellbore pseudo-skin
    phasing_data = {
        0:   {"a_theta": -2.091, "b_theta": 0.0453, "c1": 1.6e-1,  "c2": 2.675},
        60:  {"a_theta": -2.025, "b_theta": 0.0943, "c1": 2.6e-2,  "c2": 4.532},
        90:  {"a_theta": -1.905, "b_theta": 0.1038, "c1": 6.6e-3,  "c2": 5.320},
        120: {"a_theta": -1.898, "b_theta": 0.1023, "c1": 1.6e-3,  "c2": 6.155},
        180: {"a_theta": -2.018, "b_theta": 0.0634, "c1": 2.3e-2,  "c2": 3.550},
        360: {"a_theta": -2.091, "b_theta": 0.0453, "c1": 1.6e-1,  "c2": 2.675},
    }
    p = phasing_data.get(phasing_deg, phasing_data[90])

    # S_p: Plane-flow pseudo-skin (phasing-dependent via α_θ)
    r_eff_w = r_w * math.exp(p["a_theta"])   # effective wellbore radius
    if l_p > 0 and r_eff_w > 0:
        s_p = math.log(r_eff_w / (r_w + l_p)) if (r_w + l_p) > r_eff_w else 0.0
    else:
        s_p = 0.0

    # S_v: Vertical pseudo-skin (convergence to perforation tunnels)
    # Uses K&T Table 2 constants — NOT phasing-dependent:
    #   S_v = 10^(a1 + a2·log10(r_pD)) × h_D^(b1 + b2·log10(r_pD))
    # K&T Table 2: a1=2.091, a2=0.0453, b1=5.1313, b2=1.8672
    if l_p > 0 and k_v > 0 and h_perf_ft > 0:
        h_d = h_perf_ft * math.sqrt(k_h / k_v) / l_p           # dimensionless spacing
        r_pd = r_p / (h_perf_ft * (1.0 + math.sqrt(k_v / k_h)))  # dimensionless perf radius

        if h_d > 0 and r_pd > 0:
            # K&T vertical flow skin constants (Table 2, SPE 18247)
            a1, a2 = 2.091, 0.0453
            b1, b2 = 5.1313, 1.8672
            log_rpd = math.log10(max(r_pd, 1e-9))
            sv_exp   = a1 + a2 * log_rpd         # exponent of 10
            hd_exp   = b1 + b2 * log_rpd         # exponent of h_d
            s_v = (10.0 ** sv_exp) * (h_d ** hd_exp)
            s_v = max(0.0, min(s_v, 100.0))       # physical cap
        else:
            s_v = 0.0
    else:
        s_v = 0.0

    # S_wb: Wellbore pseudo-skin (phasing-dependent via c1, c2)
    c1 = p["c1"]
    c2 = p["c2"]
    if r_p > 0 and r_w > 0:
        r_wD = r_p / r_w
        s_wb = c1 * math.exp(c2 * r_wD) if r_wD < 1.0 else c1
        s_wb = min(s_wb, 5.0)
    else:
        s_wb = 0.0

    # S_d: Damage skin (Hawkins formula)
    if damage_radius_ft > 0 and damage_permeability_md > 0 and damage_permeability_md < k_h:
        s_d = (k_h / damage_permeability_md - 1.0) * math.log(damage_radius_ft / r_w)
        s_d = max(0.0, s_d)
    else:
        s_d = 0.0

    s_total = s_p + s_v + s_wb + s_d

    # Productivity Ratio: PR = ln(re/rw) / (ln(re/rw) + S_total)
    # Assume drainage radius ~ 660 ft (40-acre spacing)
    r_e = 660.0
    ln_re_rw = math.log(r_e / r_w) if r_w > 0 else 7.0
    pr = ln_re_rw / (ln_re_rw + s_total) if (ln_re_rw + s_total) > 0 else 0.0

    # Classification
    if pr >= 0.90:
        quality = "Excellent"
    elif pr >= 0.75:
        quality = "Good"
    elif pr >= 0.50:
        quality = "Fair"
    else:
        quality = "Poor"

    return {
        "skin_components": {
            "s_perforation": round(s_p, 3),
            "s_vertical":    round(s_v, 3),
            "s_wellbore":    round(s_wb, 4),
            "s_damage":      round(s_d, 3),
        },
        "skin_total":       round(s_total, 3),
        "productivity_ratio": round(pr, 4),
        "productivity_pct": round(pr * 100, 1),
        "quality": quality,
        "parameters_used": {
            "spf": spf, "phasing_deg": phasing_deg,
            "perf_length_in": round(perforation_length_in, 2),
            "perf_radius_in": round(perforation_radius_in, 3),
            "kv_kh": kv_kh_ratio,
        },
    }


def optimize_perforation_design(
    casing_id_in: float,
    formation_permeability_md: float,
    formation_thickness_ft: float,
    reservoir_pressure_psi: float,
    wellbore_radius_ft: float = 0.354,
    kv_kh_ratio: float = 0.5,
    penetration_berea_in: float = 12.0,
    effective_stress_psi: float = 3000.0,
    temperature_f: float = 200.0,
    damage_radius_ft: float = 0.5,
    damage_permeability_md: float = 50.0,
) -> Dict[str, Any]:
    """
    Optimize SPF and phasing combination for maximum productivity.

    Tests 25 configurations (5 SPF × 5 phasing) and ranks by PR.
    Each configuration independently evaluates K&T full skin model.

    Args:
        All standard completion parameters.

    Returns:
        Dict with ranked configurations, optimal selection, sensitivity data
    """
    # Corrected penetration for this gun/well combination
    pen = calculate_penetration_depth(
        penetration_berea_in=penetration_berea_in,
        effective_stress_psi=effective_stress_psi,
        temperature_f=temperature_f,
    )
    corrected_pen_in = pen["penetration_corrected_in"]

    spf_options    = [2, 4, 6, 8, 12]
    phasing_options = [0, 60, 90, 120, 180]

    results = []
    for spf in spf_options:
        for phasing in phasing_options:
            pr_result = calculate_productivity_ratio(
                formation_permeability_md=formation_permeability_md,
                perforation_length_in=corrected_pen_in,
                perforation_radius_in=corrected_pen_in * 0.04,  # ~4% of tunnel length
                wellbore_radius_ft=wellbore_radius_ft,
                spf=spf,
                phasing_deg=phasing,
                formation_thickness_ft=formation_thickness_ft,
                kv_kh_ratio=kv_kh_ratio,
                damage_radius_ft=damage_radius_ft,
                damage_permeability_md=damage_permeability_md,
            )
            results.append({
                "spf": spf,
                "phasing_deg": phasing,
                "productivity_ratio": pr_result["productivity_ratio"],
                "productivity_pct": pr_result["productivity_pct"],
                "skin_total": pr_result["skin_total"],
                "skin_components": pr_result["skin_components"],
                "quality": pr_result["quality"],
            })

    # Sort by PR descending
    results.sort(key=lambda r: r["productivity_ratio"], reverse=True)

    optimal = results[0]
    top_5   = results[:5]

    # SPF sensitivity (fix phasing at optimal)
    spf_sensitivity = [
        {"spf": r["spf"], "productivity_ratio": r["productivity_ratio"], "skin_total": r["skin_total"]}
        for r in results if r["phasing_deg"] == optimal["phasing_deg"]
    ]

    # Phasing sensitivity (fix SPF at optimal)
    phasing_sensitivity = [
        {"phasing_deg": r["phasing_deg"], "productivity_ratio": r["productivity_ratio"], "skin_total": r["skin_total"]}
        for r in results if r["spf"] == optimal["spf"]
    ]

    return {
        "optimal_configuration": optimal,
        "top_5_configurations": top_5,
        "penetration_corrected_in": corrected_pen_in,
        "spf_sensitivity": spf_sensitivity,
        "phasing_sensitivity": phasing_sensitivity,
        "total_configurations_tested": len(results),
    }
