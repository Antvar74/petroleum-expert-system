"""
Completion Design Engine — full integrated pipeline.

Orchestrates all sub-modules into a single calculate_full_completion_design() call.
"""
from typing import Dict, Any

from .penetration   import calculate_penetration_depth
from .productivity  import calculate_productivity_ratio, optimize_perforation_design
from .underbalance  import calculate_underbalance
from .gun_selection import select_gun_configuration, select_gun_from_catalog  # noqa: F401
from .constants import GUN_CATALOG as _GUN_CATALOG
from .fracture      import (
    calculate_fracture_initiation,
    calculate_fracture_gradient,
    calculate_fracture_gradient_daines,
    calculate_fracture_gradient_matthews_kelly,
)
from .ipr     import calculate_ipr_vogel, calculate_ipr_fetkovich, calculate_ipr_darcy
from .vlp     import calculate_vlp_beggs_brill, calculate_nodal_analysis
from .advanced import calculate_crushed_zone_skin, calculate_horizontal_productivity

# Drainage radius default (ft) — 40-acre spacing → re ≈ 745 ft; use 660 ft (typical 20-acre)
_DEFAULT_DRAINAGE_RADIUS_FT = 660.0


def calculate_full_completion_design(
    casing_id_in: float,
    formation_permeability_md: float,
    formation_thickness_ft: float,
    reservoir_pressure_psi: float,
    wellbore_pressure_psi: float,
    depth_tvd_ft: float,
    overburden_stress_psi: float,
    pore_pressure_psi: float,
    sigma_min_psi: float,
    sigma_max_psi: float,
    tensile_strength_psi: float = 500.0,
    poisson_ratio: float = 0.25,
    penetration_berea_in: float = 12.0,
    effective_stress_psi: float = 3000.0,
    temperature_f: float = 200.0,
    completion_fluid: str = "brine",
    wellbore_radius_ft: float = 0.354,
    kv_kh_ratio: float = 0.5,
    tubing_od_in: float = 0.0,
    damage_radius_ft: float = 0.5,
    damage_permeability_md: float = 50.0,
    formation_type: str = "sandstone",
    # IPR defaults — single-phase oil (typical light/medium crude)
    Bo: float = 1.2,
    mu_oil_cp: float = 1.0,
    drainage_radius_ft: float = _DEFAULT_DRAINAGE_RADIUS_FT,
) -> Dict[str, Any]:
    """
    Complete integrated completion design analysis.

    Returns:
        Dict with penetration, gun selection, underbalance, fracture,
        productivity optimization, summary and alerts.
    """
    # 1. Penetration depth
    penetration = calculate_penetration_depth(
        penetration_berea_in=penetration_berea_in,
        effective_stress_psi=effective_stress_psi,
        temperature_f=temperature_f,
        completion_fluid=completion_fluid,
    )

    # 2. Gun selection
    gun = select_gun_configuration(
        casing_id_in=casing_id_in,
        tubing_od_in=tubing_od_in,
    )

    # 2a. P/T rating check — look up recommended gun OD in GUN_CATALOG
    if gun["recommended"]:
        rec_od = gun["recommended"]["od_in"]
        catalog_match = next(
            (g for g in _GUN_CATALOG if abs(g["od_in"] - rec_od) < 0.01), None
        )
        if catalog_match:
            p_pass = reservoir_pressure_psi <= catalog_match["max_pressure_psi"]
            t_pass = temperature_f <= catalog_match["max_temp_f"]
            gun["recommended"]["pt_check"] = {
                "bhp_psi": reservoir_pressure_psi,
                "bht_f": temperature_f,
                "gun_max_pressure_psi": catalog_match["max_pressure_psi"],
                "gun_max_temp_f": catalog_match["max_temp_f"],
                "pressure_pass": p_pass,
                "temp_pass": t_pass,
                "overall_pass": p_pass and t_pass,
            }

    # 3. Underbalance analysis
    underbalance = calculate_underbalance(
        reservoir_pressure_psi=reservoir_pressure_psi,
        wellbore_pressure_psi=wellbore_pressure_psi,
        formation_permeability_md=formation_permeability_md,
        formation_type=formation_type,
    )

    # 4. Fracture initiation
    fracture = calculate_fracture_initiation(
        sigma_min_psi=sigma_min_psi,
        sigma_max_psi=sigma_max_psi,
        tensile_strength_psi=tensile_strength_psi,
        pore_pressure_psi=pore_pressure_psi,
    )

    # 5. Fracture gradient (Eaton)
    frac_gradient = calculate_fracture_gradient(
        depth_tvd_ft=depth_tvd_ft,
        pore_pressure_psi=pore_pressure_psi,
        overburden_stress_psi=overburden_stress_psi,
        poisson_ratio=poisson_ratio,
    )

    # 6. Optimize perforation design
    optimization = optimize_perforation_design(
        casing_id_in=casing_id_in,
        formation_permeability_md=formation_permeability_md,
        formation_thickness_ft=formation_thickness_ft,
        reservoir_pressure_psi=reservoir_pressure_psi,
        wellbore_radius_ft=wellbore_radius_ft,
        kv_kh_ratio=kv_kh_ratio,
        penetration_berea_in=penetration_berea_in,
        effective_stress_psi=effective_stress_psi,
        temperature_f=temperature_f,
        damage_radius_ft=damage_radius_ft,
        damage_permeability_md=damage_permeability_md,
    )

    # 7. IPR — Darcy (single-phase oil, uses optimal skin from step 6)
    opt_skin = optimization["optimal_configuration"].get("skin_total", 0.0)
    ipr = calculate_ipr_darcy(
        permeability_md=formation_permeability_md,
        net_pay_ft=formation_thickness_ft,
        Bo=Bo,
        mu_oil_cp=mu_oil_cp,
        reservoir_pressure_psi=reservoir_pressure_psi,
        wellbore_radius_ft=wellbore_radius_ft,
        drainage_radius_ft=drainage_radius_ft,
        skin=opt_skin,
    )

    # Build alerts
    alerts = []
    if penetration["efficiency_pct"] < 70:
        alerts.append(f"Low penetration efficiency {penetration['efficiency_pct']}% — review correction factors")
    if underbalance["status"] != "Optimal":
        alerts.append(f"Underbalance: {underbalance['status']} — {underbalance['recommendation']}")
    opt_conf = optimization["optimal_configuration"]
    if opt_conf["productivity_ratio"] < 0.5:
        alerts.append(f"Low productivity ratio {opt_conf['productivity_ratio']:.2f} — consider stimulation")
    if gun["total_compatible_guns"] == 0:
        alerts.append("No compatible guns found for this casing size!")
    if frac_gradient["mud_weight_window_ppg"] < 1.0:
        alerts.append(f"Narrow mud weight window {frac_gradient['mud_weight_window_ppg']:.1f} ppg — risk of losses")

    # Summary
    summary = {
        "penetration_corrected_in": penetration["penetration_corrected_in"],
        "penetration_efficiency_pct": penetration["efficiency_pct"],
        "recommended_gun": gun["recommended"]["gun_size"] if gun["recommended"] else "None",
        "optimal_spf": opt_conf["spf"],
        "optimal_phasing_deg": opt_conf["phasing_deg"],
        "productivity_ratio": opt_conf["productivity_ratio"],
        "skin_total": opt_conf["skin_total"],
        "underbalance_psi": underbalance["underbalance_psi"],
        "underbalance_status": underbalance["status"],
        "fracture_gradient_ppg": frac_gradient["fracture_gradient_ppg"],
        "mud_weight_window_ppg": frac_gradient["mud_weight_window_ppg"],
        "breakdown_pressure_psi": fracture["breakdown_pressure_psi"],
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "penetration": penetration,
        "gun_selection": gun,
        "underbalance": underbalance,
        "fracture_initiation": fracture,
        "fracture_gradient": frac_gradient,
        "optimization": optimization,
        "ipr": ipr,
        "alerts": alerts,
    }
