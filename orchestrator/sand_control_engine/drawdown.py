"""
Sand Control Engine — Critical drawdown pressure for sanding.

References:
- Mohr-Coulomb failure criterion
- Kirsch (1898): Tangential stress at wellbore wall
- Plumb (1994), Hawkins & McConnell: Water weakening of UCS (~30% at full saturation)
- Penberthy & Shaughnessy: Sand Control (SPE Series)
"""
import math
from typing import Dict, Any, Optional


def calculate_critical_drawdown(
    ucs_psi: float,
    friction_angle_deg: float,
    reservoir_pressure_psi: float,
    overburden_stress_psi: float,
    poisson_ratio: float = 0.25,
    biot_coefficient: float = 1.0,
    sigma_H_psi: Optional[float] = None,
    sigma_h_psi: Optional[float] = None,
    wellbore_azimuth_deg: float = 0.0,
    water_saturation: float = 0.0,
    cohesion_psi: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate critical drawdown pressure for sanding using Mohr-Coulomb.

    Supports anisotropic horizontal stresses (Kirsch), water weakening,
    and explicit cohesion. Backward-compatible with isotropic k0 path.

    Args:
        ucs_psi: unconfined compressive strength (psi)
        friction_angle_deg: internal friction angle (degrees)
        reservoir_pressure_psi: pore pressure (psi)
        overburden_stress_psi: overburden stress (psi)
        poisson_ratio: Poisson's ratio (dimensionless)
        biot_coefficient: Biot's poroelastic coefficient (0-1)
        sigma_H_psi: max horizontal stress (psi, total). If None, use k0 estimate.
        sigma_h_psi: min horizontal stress (psi, total). If None, use k0 estimate.
        wellbore_azimuth_deg: wellbore azimuth relative to sigma_H (degrees)
        water_saturation: water saturation (0-1) for water weakening of UCS
        cohesion_psi: explicit cohesion (psi). If None, derived from UCS/friction.

    Returns:
        Dict with critical_drawdown, effective stresses, sanding_risk, anisotropy data
    """
    phi_rad = math.radians(friction_angle_deg)
    sin_phi = math.sin(phi_rad)
    cos_phi = math.cos(phi_rad)

    # Water weakening: reduce UCS with water saturation
    # Empirical: ~30% reduction at full saturation (Plumb 1994, Hawkins & McConnell)
    water_saturation = max(0.0, min(water_saturation, 1.0))
    water_weakening_factor = 1.0 - 0.3 * water_saturation
    ucs_wet = ucs_psi * water_weakening_factor

    # Derive cohesion from (wet) UCS if not explicitly provided
    if cohesion_psi is not None:
        C = cohesion_psi
    else:
        denom = 2.0 * cos_phi
        C = ucs_wet * (1.0 - sin_phi) / denom if denom > 0 else ucs_wet / 2.0

    # Effective vertical stress
    sigma_v_eff = overburden_stress_psi - biot_coefficient * reservoir_pressure_psi

    # Horizontal stresses: anisotropic if provided, else isotropic k0
    if sigma_H_psi is not None and sigma_h_psi is not None:
        sigma_H_eff = sigma_H_psi - biot_coefficient * reservoir_pressure_psi
        sigma_h_eff = sigma_h_psi - biot_coefficient * reservoir_pressure_psi
    else:
        k0 = poisson_ratio / (1.0 - poisson_ratio) if poisson_ratio < 1.0 else 1.0
        sigma_h_eff = k0 * sigma_v_eff
        sigma_H_eff = sigma_h_eff  # isotropic horizontal

    anisotropy_ratio = sigma_H_eff / sigma_h_eff if sigma_h_eff > 0 else 1.0

    # Kirsch tangential stress at wellbore wall
    theta_rad = math.radians(wellbore_azimuth_deg)
    sigma_theta_mean = 0.5 * (sigma_H_eff + sigma_h_eff)
    sigma_theta_dev = 0.5 * (sigma_H_eff - sigma_h_eff) * math.cos(2.0 * theta_rad)
    kirsch_sigma_theta = sigma_theta_mean - sigma_theta_dev

    # Critical drawdown: ΔP_crit = (UCS_wet + sigma_theta*(1-sin_phi)) / (1+sin_phi)
    if (1 + sin_phi) == 0:
        dp_crit = ucs_wet
    else:
        dp_crit = (ucs_wet + kirsch_sigma_theta * (1 - sin_phi)) / (1 + sin_phi)

    dp_crit = max(dp_crit, 0)

    # Sanding risk assessment
    if dp_crit < 200:
        risk = "Very High"
        recommendation = "Sand control required — OHGP or SAS recommended"
    elif dp_crit < 500:
        risk = "High"
        recommendation = "Sand control recommended — consider OHGP"
    elif dp_crit < 1000:
        risk = "Moderate"
        recommendation = "Monitor sand production — rate-restricted completion"
    elif dp_crit < 2000:
        risk = "Low"
        recommendation = "Oriented perforating may be sufficient"
    else:
        risk = "Very Low"
        recommendation = "Sand-free completion likely — no sand control needed"

    # FIX-SAND-001: dry (water_sat=0) and wet (water_sat=1.0) drawdown variants
    # kirsch_sigma_theta is independent of water saturation — only UCS term changes
    _denom = 1 + sin_phi
    dp_crit_dry = max((ucs_psi + kirsch_sigma_theta * (1 - sin_phi)) / _denom, 0) if _denom else ucs_psi
    dp_crit_wet = max((ucs_psi * 0.70 + kirsch_sigma_theta * (1 - sin_phi)) / _denom, 0) if _denom else ucs_psi * 0.70

    return {
        "critical_drawdown_psi": round(dp_crit, 0),
        "critical_drawdown_dry_psi": round(dp_crit_dry, 0),
        "critical_drawdown_wet_psi": round(dp_crit_wet, 0),
        "effective_overburden_psi": round(sigma_v_eff, 0),
        "effective_horizontal_psi": round(sigma_h_eff, 0),
        "sigma_H_eff_psi": round(sigma_H_eff, 0),
        "anisotropy_ratio": round(anisotropy_ratio, 3),
        "water_weakening_factor": round(water_weakening_factor, 3),
        "ucs_wet_psi": round(ucs_wet, 0),
        "kirsch_sigma_theta": round(kirsch_sigma_theta, 0),
        "cohesion_psi": round(C, 1),
        "sanding_risk": risk,
        "recommendation": recommendation,
        "ucs_psi": ucs_psi,
        "friction_angle_deg": friction_angle_deg
    }
