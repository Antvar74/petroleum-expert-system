"""
Cementing Engine — gas migration risk assessment.

References:
- API RP 65-2: Evaluating Zonal Isolation for Gas Migration
- Nelson & Guillot: Well Cementing Ch. 8 (Gas migration)
"""
from typing import Dict, Any, List


def calculate_gas_migration_risk(
    reservoir_pressure_psi: float,
    cement_column_height_ft: float,
    slurry_density_ppg: float,
    pore_pressure_ppg: float,
    tvd_ft: float,
    transition_time_hr: float = 2.0,
    thickening_time_hr: float = 5.0,
    sgs_10min_lbf_100sqft: float = 20.0,
) -> Dict[str, Any]:
    """
    Evaluate post-placement gas migration risk.

    Reference: API RP 65-2 (Gas Migration)
    - Gas Flow Potential (GFP) = (P_res - P_hydro_cement) / P_overbalance
    - Risk: HIGH if GFP > 1.0 AND transition_time < thickening_time
    """
    p_hydro_cement = slurry_density_ppg * 0.052 * cement_column_height_ft
    p_hydro_total = slurry_density_ppg * 0.052 * tvd_ft
    overbalance = p_hydro_total - reservoir_pressure_psi

    gfp = reservoir_pressure_psi / p_hydro_total if overbalance > 0 else 1.5

    transition_ratio = transition_time_hr / thickening_time_hr if thickening_time_hr > 0 else 999
    sgs_adequate = sgs_10min_lbf_100sqft >= 100  # API target: 500 lbf/100sqft ideal

    recommendations: List[str] = []
    if gfp >= 1.5 or (gfp >= 1.0 and transition_ratio < 0.5):
        risk_level = "CRITICAL"
        recommendations.append("Use gas-tight cement system with anti-gas additives")
        recommendations.append("Consider inner string cementing or staged cementing")
        recommendations.append("Apply external casing packer (ECP) across gas zone")
    elif gfp >= 1.0:
        risk_level = "HIGH"
        recommendations.append("Use cement with short transition time and high SGS development")
        recommendations.append("Maximize displacement efficiency (turbulent flow, spacer)")
    elif gfp >= 0.5:
        risk_level = "MODERATE"
        recommendations.append("Standard anti-gas cement additives recommended")
        recommendations.append("Ensure good mud removal and centralization")
    else:
        risk_level = "LOW"
        recommendations.append("Standard cementing practices adequate")

    if not sgs_adequate:
        recommendations.append("SGS too low — consider right-angle-set (RAS) cement system")

    return {
        "gfp": round(gfp, 3),
        "risk_level": risk_level,
        "overbalance_psi": round(overbalance, 0),
        "p_hydro_cement_psi": round(p_hydro_cement, 0),
        "reservoir_pressure_psi": round(reservoir_pressure_psi, 0),
        "transition_time_hr": transition_time_hr,
        "thickening_time_hr": thickening_time_hr,
        "transition_ratio": round(transition_ratio, 3),
        "sgs_adequate": sgs_adequate,
        "recommendations": recommendations,
    }
