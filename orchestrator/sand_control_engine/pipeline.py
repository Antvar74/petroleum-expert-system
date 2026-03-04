"""
Sand Control Engine — Full integrated analysis pipeline.

Orchestrates: PSD → gravel sizing → screen selection → critical drawdown
              → gravel volume → skin → completion type evaluation → alerts.

References:
- Penberthy & Shaughnessy: Sand Control (SPE Series)
- Saucier (1974): Gravel sizing criteria
- API RP 19C: Screen testing procedures
"""
from typing import List, Dict, Any, Optional

from .psd import analyze_grain_distribution, select_gravel_size
from .screen import select_screen_slot
from .drawdown import calculate_critical_drawdown
from .gravel_volume import calculate_gravel_volume
from .skin import calculate_skin_factor
from .completion_type import evaluate_completion_type


def calculate_full_sand_control(
    sieve_sizes_mm: List[float],
    cumulative_passing_pct: List[float],
    hole_id: float,
    screen_od: float,
    interval_length: float,
    ucs_psi: float,
    friction_angle_deg: float,
    reservoir_pressure_psi: float,
    overburden_stress_psi: float,
    formation_permeability_md: float,
    wellbore_radius_ft: float = 0.354,
    wellbore_type: str = "cased",
    gravel_permeability_md: float = 80000.0,
    pack_factor: float = 1.4,
    washout_factor: float = 1.1,
    sigma_H_psi: Optional[float] = None,
    sigma_h_psi: Optional[float] = None,
    wellbore_azimuth_deg: float = 0.0,
    water_saturation: float = 0.0,
    cohesion_psi: Optional[float] = None
) -> Dict[str, Any]:
    """
    Complete sand control analysis combining all sub-module calculations.

    Args:
        sieve_sizes_mm: sieve opening sizes (mm)
        cumulative_passing_pct: cumulative weight % passing each sieve
        hole_id: open hole ID (inches)
        screen_od: screen outer diameter (inches)
        interval_length: completion interval length (ft)
        ucs_psi: unconfined compressive strength (psi)
        friction_angle_deg: internal friction angle (degrees)
        reservoir_pressure_psi: reservoir / pore pressure (psi)
        overburden_stress_psi: overburden stress (psi)
        formation_permeability_md: formation permeability (mD)
        wellbore_radius_ft: wellbore radius (ft)
        wellbore_type: 'cased' or 'openhole'
        gravel_permeability_md: gravel pack permeability (mD)
        pack_factor: gravel overfill factor (1.3-1.5)
        washout_factor: hole enlargement factor (1.0 = gauge)
        sigma_H_psi: max horizontal stress (psi, total) — optional anisotropic
        sigma_h_psi: min horizontal stress (psi, total) — optional anisotropic
        wellbore_azimuth_deg: azimuth relative to sigma_H for Kirsch solution
        water_saturation: Sw (0-1) for water weakening of UCS
        cohesion_psi: explicit cohesion (psi), if None derived from UCS

    Returns:
        Dict with summary, psd, gravel, screen, drawdown, volume, skin,
        completion, parameters, alerts
    """
    # 1. PSD Analysis
    psd = analyze_grain_distribution(sieve_sizes_mm, cumulative_passing_pct)
    if "error" in psd:
        return {"summary": {}, "alerts": [psd["error"]]}

    # 2. Gravel selection (Saucier criterion)
    gravel = select_gravel_size(
        psd["d50_mm"], psd["d10_mm"], psd["d90_mm"],
        psd["uniformity_coefficient"]
    )

    # 3. Screen selection
    # Open hole: premium_mesh (direct contact with formation, finer slot needed)
    # Cased hole: wire_wrap (perforations provide primary sand barrier)
    screen_type = "premium_mesh" if wellbore_type == "openhole" else "wire_wrap"
    screen = select_screen_slot(psd["d10_mm"], psd["d50_mm"], screen_type=screen_type)

    # 4. Critical drawdown (Mohr-Coulomb with optional Kirsch + water weakening)
    drawdown = calculate_critical_drawdown(
        ucs_psi, friction_angle_deg,
        reservoir_pressure_psi, overburden_stress_psi,
        sigma_H_psi=sigma_H_psi,
        sigma_h_psi=sigma_h_psi,
        wellbore_azimuth_deg=wellbore_azimuth_deg,
        water_saturation=water_saturation,
        cohesion_psi=cohesion_psi
    )

    # 5. Gravel volume
    volume = calculate_gravel_volume(
        hole_id, screen_od, interval_length,
        pack_factor, washout_factor
    )

    # 6. Skin factor
    # Open hole: no perforation tunnel → S_perf = 0 (perforation_length = 0)
    # Cased hole: typical 12" perforation tunnel
    perf_length = 0.0 if wellbore_type == "openhole" else 12.0
    skin = calculate_skin_factor(
        perforation_length=perf_length,
        perforation_diameter=0.5,
        gravel_permeability_md=gravel_permeability_md,
        formation_permeability_md=formation_permeability_md,
        wellbore_radius=wellbore_radius_ft
    )

    # 7. Completion type evaluation
    completion = evaluate_completion_type(
        psd["d50_mm"], psd["uniformity_coefficient"],
        ucs_psi, reservoir_pressure_psi,
        formation_permeability_md, wellbore_type
    )

    # 8. Alerts
    alerts = []
    if psd["uniformity_coefficient"] > 10:
        alerts.append(f"Very poorly sorted sand (Cu={psd['uniformity_coefficient']:.1f}) — premium screen recommended")
    if drawdown["sanding_risk"] in ["Very High", "High"]:
        alerts.append(f"Sanding risk: {drawdown['sanding_risk']} — sand control required")
    if drawdown["critical_drawdown_psi"] < 200:
        alerts.append(f"Critical drawdown only {drawdown['critical_drawdown_psi']:.0f} psi — very weak formation")
    if skin["skin_total"] > 10:
        alerts.append(f"High completion skin {skin['skin_total']:.1f} — consider productivity optimization")
    if psd["d50_mm"] < 0.05:
        alerts.append("Very fine sand — consider frac-pack instead of conventional gravel pack")
    if volume.get("gravel_volume_bbl", 0) > 100:
        alerts.append(f"Large gravel volume required: {volume['gravel_volume_bbl']:.0f} bbl — verify logistics")

    summary = {
        "d50_mm": psd["d50_mm"],
        "uniformity_coefficient": psd["uniformity_coefficient"],
        "sorting": psd["sorting"],
        "recommended_gravel": gravel["recommended_pack"],
        "screen_slot_in": screen["recommended_standard_slot_in"],
        "screen_type": screen["screen_type"],
        "critical_drawdown_psi": drawdown["critical_drawdown_psi"],
        "sanding_risk": drawdown["sanding_risk"],
        "gravel_volume_bbl": volume.get("gravel_volume_bbl", 0),
        "skin_total": skin["skin_total"],
        "recommended_completion": completion["recommended"],
        "alerts": alerts
    }

    return {
        "summary": summary,
        "psd": psd,
        "gravel": gravel,
        "screen": screen,
        "drawdown": drawdown,
        "volume": volume,
        "skin": skin,
        "completion": completion,
        "parameters": {
            "hole_id_in": hole_id,
            "screen_od_in": screen_od,
            "interval_length_ft": interval_length,
            "ucs_psi": ucs_psi,
            "friction_angle_deg": friction_angle_deg,
            "reservoir_pressure_psi": reservoir_pressure_psi,
            "overburden_stress_psi": overburden_stress_psi,
            "formation_permeability_md": formation_permeability_md,
            "wellbore_type": wellbore_type,
            "pack_factor": pack_factor,
            "washout_factor": washout_factor
        },
        "alerts": alerts
    }
