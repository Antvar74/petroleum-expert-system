"""
Completion Design Engine — fracture initiation and gradient calculations.

References:
- Haimson & Fairhurst (1967): Hydraulic fracture initiation pressure
- Eaton (1969): Fracture gradient from Poisson's ratio
- Daines (1982): Modified fracture gradient with superimposed tectonic stress
- Matthews & Kelly (1967): Effective stress ratio Ki method
"""
import math
from typing import Dict, Any, List


def _classify_stress_regime(sigma_h: float, sigma_H: float, sigma_v: float) -> str:
    """
    Anderson (1951) stress regime classification.

    Normal:      σ_v ≥ σ_H ≥ σ_h  → gravity-dominated, normal faulting
    Strike-slip: σ_H ≥ σ_v ≥ σ_h  → one horizontal dominant
    Reverse:     σ_H ≥ σ_h ≥ σ_v  → compressional, thrust faulting
    """
    if sigma_v >= sigma_H >= sigma_h:
        return "Normal"
    elif sigma_H >= sigma_v >= sigma_h:
        return "Strike-Slip"
    elif sigma_H >= sigma_h >= sigma_v:
        return "Reverse"
    else:
        return "Transitional"


def calculate_fracture_initiation(
    sigma_min_psi: float,
    sigma_max_psi: float,
    tensile_strength_psi: float,
    pore_pressure_psi: float,
    biot_coefficient: float = 1.0,
    overburden_stress_psi: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate hydraulic fracture initiation pressure.
    Haimson & Fairhurst (1967):

    P_frac = 3σ_min - σ_max + T - α × P_pore

    Args:
        sigma_min_psi: minimum horizontal stress (psi)
        sigma_max_psi: maximum horizontal stress (psi)
        tensile_strength_psi: rock tensile strength (psi)
        pore_pressure_psi: formation pore pressure (psi)
        biot_coefficient: Biot poroelastic coefficient (0-1)
        overburden_stress_psi: vertical/overburden stress (psi); enables regime classification

    Returns:
        Dict with fracture initiation pressure, breakdown pressure, margins, stress_regime
    """
    p_breakdown = (3.0 * sigma_min_psi - sigma_max_psi
                   + tensile_strength_psi
                   - biot_coefficient * pore_pressure_psi)
    p_reopen  = 3.0 * sigma_min_psi - sigma_max_psi - biot_coefficient * pore_pressure_psi
    p_closure = sigma_min_psi
    p_isip    = sigma_min_psi * 1.02
    net_pressure = p_breakdown - p_closure
    stress_ratio = sigma_max_psi / sigma_min_psi if sigma_min_psi > 0 else 1.0

    if stress_ratio > 1.1:
        orientation = "Fractura ⊥ σ_min — transversal en pozo horizontal"
    else:
        orientation = "Esfuerzos casi isotrópicos — dirección de fractura incierta"

    # Anderson (1951) stress regime classification
    if overburden_stress_psi > 0:
        regime = _classify_stress_regime(sigma_min_psi, sigma_max_psi, overburden_stress_psi)
    else:
        regime = "Unknown (overburden not provided)"

    return {
        "breakdown_pressure_psi": round(p_breakdown, 1),
        "reopening_pressure_psi": round(p_reopen, 1),
        "closure_pressure_psi": round(p_closure, 1),
        "isip_estimate_psi": round(p_isip, 1),
        "net_pressure_psi": round(net_pressure, 1),
        "tensile_strength_psi": round(tensile_strength_psi, 1),
        "stress_ratio": round(stress_ratio, 3),
        "fracture_orientation": orientation,
        "stress_regime": regime,
        "stresses": {
            "sigma_min_psi": round(sigma_min_psi, 1),
            "sigma_max_psi": round(sigma_max_psi, 1),
            "overburden_psi": round(overburden_stress_psi, 1),
            "pore_pressure_psi": round(pore_pressure_psi, 1),
        },
    }


def calculate_fracture_gradient(
    depth_tvd_ft: float,
    pore_pressure_psi: float,
    overburden_stress_psi: float,
    poisson_ratio: float = 0.25,
    tectonic_stress_psi: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate fracture gradient using Eaton's method (1969).

    FG = (ν/(1-ν)) × (σ_ob - P_p)/D + P_p/D + σ_tect/D

    Args:
        depth_tvd_ft: true vertical depth (ft)
        pore_pressure_psi: pore pressure at TVD (psi)
        overburden_stress_psi: overburden stress at TVD (psi)
        poisson_ratio: Poisson's ratio of formation
        tectonic_stress_psi: additional tectonic stress component (psi)

    Returns:
        Dict with fracture gradient, equivalent pressures, profile data
    """
    if depth_tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    nu = poisson_ratio
    stress_ratio = nu / (1.0 - nu)
    matrix_stress = stress_ratio * (overburden_stress_psi - pore_pressure_psi)
    frac_pressure = pore_pressure_psi + matrix_stress + tectonic_stress_psi

    frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
    frac_gradient_ppg    = frac_gradient_psi_ft / 0.052
    pore_gradient_ppg    = (pore_pressure_psi / depth_tvd_ft) / 0.052
    overburden_gradient_ppg = (overburden_stress_psi / depth_tvd_ft) / 0.052
    window_ppg = frac_gradient_ppg - pore_gradient_ppg

    # Depth profile (every 1000 ft)
    profile: List[Dict[str, Any]] = []
    for d in range(1000, int(depth_tvd_ft) + 1, 1000):
        d_ratio = d / depth_tvd_ft
        p_pore_d  = pore_pressure_psi * d_ratio
        sigma_ob_d = overburden_stress_psi * d_ratio
        frac_p_d  = p_pore_d + stress_ratio * (sigma_ob_d - p_pore_d) + tectonic_stress_psi * d_ratio
        profile.append({
            "depth_ft": d,
            "pore_pressure_ppg": round((p_pore_d / d) / 0.052, 2),
            "fracture_gradient_ppg": round((frac_p_d / d) / 0.052, 2),
            "overburden_ppg": round((sigma_ob_d / d) / 0.052, 2),
        })
    profile.append({
        "depth_ft": round(depth_tvd_ft),
        "pore_pressure_ppg": round(pore_gradient_ppg, 2),
        "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
        "overburden_ppg": round(overburden_gradient_ppg, 2),
    })

    return {
        "fracture_pressure_psi": round(frac_pressure, 1),
        "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
        "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
        "pore_gradient_ppg": round(pore_gradient_ppg, 2),
        "overburden_gradient_ppg": round(overburden_gradient_ppg, 2),
        "mud_weight_window_ppg": round(window_ppg, 2),
        "stress_ratio_nu": round(stress_ratio, 4),
        "poisson_ratio": poisson_ratio,
        "depth_profile": profile,
    }


def calculate_fracture_gradient_daines(
    depth_tvd_ft: float,
    pore_pressure_psi: float,
    overburden_stress_psi: float,
    poisson_ratio: float = 0.25,
    tectonic_stress_psi: float = 0.0,
    superimposed_tectonic_psi: float = 0.0,
) -> Dict[str, Any]:
    """
    Daines (1982) fracture gradient with explicit tectonic stress correction.

    Fg = (nu/(1-nu)) × (sigma_ob - Pp)/D + Pp/D + sigma_tec/D + sigma_super/D

    Args:
        depth_tvd_ft: true vertical depth (ft)
        pore_pressure_psi: pore pressure (psi)
        overburden_stress_psi: overburden stress (psi)
        poisson_ratio: Poisson's ratio
        tectonic_stress_psi: primary tectonic stress (psi)
        superimposed_tectonic_psi: superimposed tectonic stress from LOT calibration (psi)

    Returns:
        Dict with fracture gradient, comparison with Eaton
    """
    if depth_tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    nu = poisson_ratio
    stress_ratio = nu / (1.0 - nu)
    matrix_stress = stress_ratio * (overburden_stress_psi - pore_pressure_psi)
    frac_pressure = pore_pressure_psi + matrix_stress + tectonic_stress_psi + superimposed_tectonic_psi

    frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
    frac_gradient_ppg    = frac_gradient_psi_ft / 0.052

    frac_eaton = pore_pressure_psi + matrix_stress + tectonic_stress_psi
    eaton_ppg  = (frac_eaton / depth_tvd_ft) / 0.052

    return {
        "fracture_pressure_psi": round(frac_pressure, 1),
        "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
        "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
        "eaton_baseline_ppg": round(eaton_ppg, 2),
        "tectonic_correction_ppg": round(frac_gradient_ppg - eaton_ppg, 2),
        "superimposed_tectonic_psi": round(superimposed_tectonic_psi, 1),
        "poisson_ratio": poisson_ratio,
        "method": "daines_1982",
    }


def calculate_fracture_gradient_matthews_kelly(
    depth_tvd_ft: float,
    pore_pressure_psi: float,
    overburden_stress_psi: float,
    Ki: float = 0.0,
    depth_normal_psi_ft: float = 0.465,
) -> Dict[str, Any]:
    """
    Matthews & Kelly (1967) fracture gradient using effective stress ratio Ki.

    Fg = Ki × (sigma_ob - Pp)/D + Pp/D

    Ki is empirically determined per geological province from LOT data.
    If Ki=0, it is estimated from depth (Gulf Coast correlation).

    Args:
        depth_tvd_ft: true vertical depth (ft)
        pore_pressure_psi: pore pressure (psi)
        overburden_stress_psi: overburden stress (psi)
        Ki: effective stress coefficient (0.3-0.9 typical). 0 = auto-estimate.
        depth_normal_psi_ft: normal pore pressure gradient (psi/ft)

    Returns:
        Dict with fracture gradient, Ki used
    """
    if depth_tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    if Ki <= 0:
        depth_equiv = depth_tvd_ft * depth_normal_psi_ft / max(0.001, pore_pressure_psi / depth_tvd_ft)
        if depth_equiv < 4000:
            Ki = 0.40 + 0.10 * (depth_equiv / 4000)
        elif depth_equiv < 10000:
            Ki = 0.50 + 0.20 * ((depth_equiv - 4000) / 6000)
        else:
            Ki = 0.70 + 0.15 * min(1.0, (depth_equiv - 10000) / 10000)
        Ki = max(0.3, min(Ki, 0.95))

    sigma_eff = overburden_stress_psi - pore_pressure_psi
    frac_pressure = Ki * sigma_eff + pore_pressure_psi

    frac_gradient_psi_ft = frac_pressure / depth_tvd_ft
    frac_gradient_ppg    = frac_gradient_psi_ft / 0.052

    return {
        "fracture_pressure_psi": round(frac_pressure, 1),
        "fracture_gradient_psi_ft": round(frac_gradient_psi_ft, 4),
        "fracture_gradient_ppg": round(frac_gradient_ppg, 2),
        "Ki_used": round(Ki, 4),
        "effective_stress_psi": round(sigma_eff, 1),
        "method": "matthews_kelly_1967",
    }
