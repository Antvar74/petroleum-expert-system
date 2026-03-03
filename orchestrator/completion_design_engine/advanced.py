"""
Completion Design Engine — advanced skin models and horizontal productivity.

References:
- Karakas & Tariq (1991): SPE 18247 — crushed zone skin (4th component)
- Joshi (1991): Horizontal Well Technology (PennWell)
"""
import math
from typing import Dict, Any


def calculate_crushed_zone_skin(
    formation_permeability_md: float,
    crushed_zone_permeability_md: float,
    crushed_zone_radius_in: float = 0.5,
    perforation_radius_in: float = 0.25,
) -> Dict[str, Any]:
    """
    Karakas-Tariq 4th skin component: damaged/crushed zone around perforation tunnel.

    S_cz = (k/k_cz - 1) × ln(r_cz / r_perf)

    The crushed zone forms from shaped-charge impact, reducing permeability
    by 50-90% within a thin zone (0.25-1.0 inches) around the tunnel.

    Args:
        formation_permeability_md: undamaged formation k (mD)
        crushed_zone_permeability_md: crushed zone k (mD), typically 10-50% of k
        crushed_zone_radius_in: radius of crushed zone from tunnel center (inches)
        perforation_radius_in: perforation tunnel radius (inches)

    Returns:
        Dict with S_cz, k_ratio, radii used
    """
    k    = formation_permeability_md
    k_cz = crushed_zone_permeability_md
    r_cz = crushed_zone_radius_in / 12.0   # ft
    r_p  = perforation_radius_in / 12.0    # ft

    if k_cz <= 0 or r_p <= 0 or r_cz <= r_p:
        return {"S_crushed_zone": 0.0, "k_ratio": 1.0,
                "note": "Invalid inputs — crushed zone skin set to 0"}

    k_ratio = k / k_cz
    if k_ratio <= 1.0:
        return {"S_crushed_zone": 0.0, "k_ratio": round(k_ratio, 3),
                "note": "No crushed zone damage"}

    S_cz = (k_ratio - 1.0) * math.log(r_cz / r_p)

    return {
        "S_crushed_zone": round(S_cz, 4),
        "k_ratio": round(k_ratio, 3),
        "k_formation_md": k,
        "k_crushed_zone_md": k_cz,
        "r_crushed_zone_in": crushed_zone_radius_in,
        "r_perforation_in": perforation_radius_in,
        "permeability_reduction_pct": round((1.0 - k_cz / k) * 100, 1),
    }


def calculate_horizontal_productivity(
    horizontal_length_ft: float,
    kh_md: float,
    kv_md: float,
    formation_thickness_ft: float,
    drainage_radius_ft: float = 660.0,
    wellbore_radius_ft: float = 0.354,
    reservoir_pressure_psi: float = 5000.0,
    Pwf_psi: float = 3000.0,
    Bo: float = 1.2,
    mu_oil_cp: float = 1.0,
    skin: float = 0.0,
) -> Dict[str, Any]:
    """
    Joshi (1991) horizontal well productivity model.

    q_h = kh × h × (Pr - Pwf) / [141.2 × Bo × mu ×
          (ln(a + sqrt(a² - (L/2)²))/(L/2) + (h/L)×ln(h/(2π×rw)))]

    a = (L/2) × [0.5 + sqrt(0.25 + (2re/L)^4)]^0.5

    Args:
        horizontal_length_ft: horizontal section length (ft)
        kh_md: horizontal permeability (mD)
        kv_md: vertical permeability (mD)
        formation_thickness_ft: net pay thickness (ft)
        drainage_radius_ft: drainage radius (ft)
        wellbore_radius_ft: wellbore radius (ft)
        reservoir_pressure_psi: reservoir pressure (psi)
        Pwf_psi: flowing BHP (psi)
        Bo: formation volume factor (RB/STB)
        mu_oil_cp: oil viscosity (cp)
        skin: total skin

    Returns:
        Dict with q_horizontal, PI, equivalent_vertical_wells, productivity_ratio
    """
    Lh  = horizontal_length_ft
    h   = formation_thickness_ft
    re  = drainage_radius_ft
    rw  = wellbore_radius_ft
    Pr  = reservoir_pressure_psi
    Pwf = Pwf_psi

    if Lh <= 0 or kh_md <= 0 or h <= 0 or Bo <= 0 or mu_oil_cp <= 0 or rw <= 0:
        return {"error": "Invalid input parameters",
                "q_horizontal_stbd": 0.0, "PI_horizontal": 0.0}

    kv_kh  = kv_md / kh_md if kh_md > 0 else 1.0
    beta   = math.sqrt(kh_md / kv_md) if kv_md > 0 else 1.0
    rw_eff = rw * (1.0 + beta) / (2.0 * beta) if beta > 0 else rw

    ratio_re_L = 2.0 * re / Lh if Lh > 0 else 10.0
    a_param    = (Lh / 2.0) * (0.5 + math.sqrt(0.25 + ratio_re_L ** 4)) ** 0.5

    inner_sqrt    = max(0.0, a_param ** 2 - (Lh / 2.0) ** 2)
    numerator_ln  = a_param + math.sqrt(inner_sqrt)
    denominator_ln = Lh / 2.0

    if denominator_ln <= 0 or numerator_ln <= 0:
        return {"error": "Invalid geometry",
                "q_horizontal_stbd": 0.0, "PI_horizontal": 0.0}

    term_h = math.log(numerator_ln / denominator_ln)
    term_v = (h / Lh) * math.log(h / (2.0 * math.pi * rw_eff)) if (Lh > 0 and rw_eff > 0 and h > 0) else 0.0

    total_denom = 141.2 * Bo * mu_oil_cp * (term_h + term_v + skin * h / Lh)
    if total_denom <= 0:
        total_denom = 1.0

    delta_P = Pr - Pwf
    q_h     = max(0.0, kh_md * h * delta_P / total_denom)
    PI_h    = kh_md * h / total_denom if total_denom > 0 else 0

    ln_re_rw = math.log(re / rw) + skin if (re > rw) else 7.0
    denom_v  = 141.2 * Bo * mu_oil_cp * ln_re_rw
    q_v      = kh_md * h * delta_P / denom_v if denom_v > 0 else 0
    PI_v     = kh_md * h / denom_v if denom_v > 0 else 0

    equiv_verticals   = q_h / q_v if q_v > 0 else 0.0
    productivity_ratio = q_h / q_v if q_v > 0 else 0.0

    return {
        "q_horizontal_stbd": round(q_h, 2),
        "q_vertical_stbd": round(q_v, 2),
        "PI_horizontal": round(PI_h, 4),
        "PI_vertical": round(PI_v, 4),
        "equivalent_vertical_wells": round(equiv_verticals, 2),
        "productivity_ratio_h_v": round(productivity_ratio, 3),
        "a_parameter_ft": round(a_param, 1),
        "beta_anisotropy": round(beta, 3),
        "kv_kh_ratio": round(kv_kh, 4),
        "horizontal_length_ft": round(Lh, 1),
        "method": "joshi_1991",
    }
