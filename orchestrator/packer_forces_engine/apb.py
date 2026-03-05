"""
Annular Pressure Buildup (APB) — calculation and mitigation for trapped annuli.

Critical for HPHT and subsea wells where annuli are sealed.

References:
- Adams, A.J. & MacEachran, A. (1994): Impact on Casing Design of Thermal Expansion
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
"""
import math
from typing import Dict, Any

from .geometry import STEEL_E


def calculate_apb(
    annular_fluid_type: str = "WBM",
    delta_t_avg: float = 100.0,
    annular_volume_bbl: float = 200.0,
    casing_od: float = 9.625,
    casing_id: float = 8.681,
    tubing_od: float = 3.5,
    tubing_id: float = 2.992,
    annular_length_ft: float = 10000.0,
    initial_pressure_psi: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate Annular Pressure Buildup (APB) for trapped annulus.

    APB = alpha_f * delta_T * V / (C_f * V + C_casing + C_tubing)

    Where:
        alpha_f = thermal expansion coefficient of fluid
        C_f = fluid compressibility
        C_casing = casing compliance (radial expansion capacity)
        C_tubing = tubing compliance (radial compression capacity)

    Args:
        annular_fluid_type: 'WBM', 'OBM', 'brine', 'completion_fluid'
        delta_t_avg: average temperature increase (deg F)
        annular_volume_bbl: total annular volume (bbl)
        casing_od, casing_id: casing dimensions (in)
        tubing_od, tubing_id: tubing dimensions (in)
        annular_length_ft: length of sealed annulus (ft)
        initial_pressure_psi: initial trapped pressure (psi)

    Returns:
        Dict with APB pressure, SF checks, mitigation recommendations.
    """
    fluid_props = {
        "WBM":              {"alpha": 2.0e-4, "C_f": 3.0e-6},
        "OBM":              {"alpha": 3.5e-4, "C_f": 5.0e-6},
        "brine":            {"alpha": 2.5e-4, "C_f": 3.2e-6},
        "completion_fluid": {"alpha": 2.8e-4, "C_f": 4.0e-6},
    }
    props = fluid_props.get(annular_fluid_type, fluid_props["WBM"])
    alpha_f = props["alpha"]  # 1/°F
    c_f = props["C_f"]        # 1/psi

    # Volume in cubic inches (1 bbl = 9702 in³)
    v_ann_in3 = annular_volume_bbl * 9702.0

    # Casing compliance: dV/dP for casing expanding outward
    casing_wall = (casing_od - casing_id) / 2.0
    c_casing = (math.pi * casing_id ** 2 * (annular_length_ft * 12.0) / (2.0 * STEEL_E * casing_wall)
                if casing_wall > 0 else 0.0)

    # Tubing compliance: dV/dP for tubing compressing inward
    tubing_wall = (tubing_od - tubing_id) / 2.0
    c_tubing = (math.pi * tubing_od ** 2 * (annular_length_ft * 12.0) / (2.0 * STEEL_E * tubing_wall)
                if tubing_wall > 0 else 0.0)

    denominator = c_f * v_ann_in3 + c_casing + c_tubing
    apb_psi = alpha_f * delta_t_avg * v_ann_in3 / denominator if denominator > 0 else 0.0

    total_pressure = initial_pressure_psi + apb_psi

    # Safety factor checks (simplified burst/collapse ratings)
    casing_burst_approx = 0.875 * 2 * 80000 * casing_wall / casing_od if casing_od > 0 else 99999
    casing_burst_sf = casing_burst_approx / total_pressure if total_pressure > 0 else 99.0

    tubing_collapse_approx = 2 * 80000 * tubing_wall / tubing_od if tubing_od > 0 else 99999
    tubing_collapse_sf = tubing_collapse_approx / total_pressure if total_pressure > 0 else 99.0

    mitigation_needed = total_pressure > 0.8 * casing_burst_approx
    recommendations = []
    if mitigation_needed:
        recommendations.append("Consider nitrogen-foamed spacer to reduce APB")
        recommendations.append("Evaluate crushable foam inserts for annular volume compensation")
        recommendations.append("Consider rupture disk or pressure relief sub")

    return {
        "apb_psi": round(apb_psi, 0),
        "total_annular_pressure_psi": round(total_pressure, 0),
        "casing_burst_sf": round(casing_burst_sf, 2),
        "tubing_collapse_sf": round(tubing_collapse_sf, 2),
        "thermal_expansion_coeff": alpha_f,
        "fluid_compressibility": c_f,
        "casing_compliance_in3_psi": round(c_casing, 4),
        "tubing_compliance_in3_psi": round(c_tubing, 4),
        "annular_fluid_type": annular_fluid_type,
        "delta_t_avg_f": delta_t_avg,
        "mitigation_needed": mitigation_needed,
        "recommendations": recommendations,
    }


def calculate_apb_mitigation(
    apb_psi: float,
    foam_volume_pct: float = 0.0,
    crushable_spacer_vol_bbl: float = 0.0,
    annular_volume_bbl: float = 200.0,
    fluid_compressibility: float = 3.0e-6,
) -> Dict[str, Any]:
    """
    Calculate APB after mitigation measures (foam, crushable spacers).

    Nitrogen foam increases effective compressibility of annular fluid.
    Crushable spacers provide additional compliance volume.

    Args:
        apb_psi: original APB pressure (psi)
        foam_volume_pct: percentage of annular volume filled with foam (0-50%)
        crushable_spacer_vol_bbl: volume of crushable spacer (bbl)
        annular_volume_bbl: total annular volume (bbl)
        fluid_compressibility: base fluid compressibility (1/psi)

    Returns:
        Dict with mitigated APB, reduction percentage.
    """
    if apb_psi <= 0:
        return {
            "apb_original_psi": 0,
            "apb_mitigated_psi": 0,
            "reduction_pct": 0,
            "foam_reduction_factor": 1.0,
            "crush_reduction_factor": 1.0,
        }

    # Foam effect: nitrogen compressibility ~100x higher than liquid
    foam_frac = min(0.50, max(0.0, foam_volume_pct / 100.0))
    c_foam = 1.0e-4  # 1/psi (nitrogen at typical downhole conditions)
    c_effective = (1.0 - foam_frac) * fluid_compressibility + foam_frac * c_foam
    foam_reduction_factor = fluid_compressibility / c_effective if c_effective > 0 else 1.0

    # Crushable spacer: provides additional compliance
    v_ann = annular_volume_bbl * 9702.0
    v_crush = crushable_spacer_vol_bbl * 9702.0
    crush_factor = v_ann / (v_ann + v_crush) if (v_ann + v_crush) > 0 else 1.0

    apb_mitigated = apb_psi * foam_reduction_factor * crush_factor
    reduction_pct = (1.0 - apb_mitigated / apb_psi) * 100 if apb_psi > 0 else 0.0

    return {
        "apb_original_psi": round(apb_psi, 0),
        "apb_mitigated_psi": round(apb_mitigated, 0),
        "reduction_pct": round(reduction_pct, 1),
        "foam_reduction_factor": round(foam_reduction_factor, 4),
        "crush_reduction_factor": round(crush_factor, 4),
        "effective_compressibility": round(c_effective, 8),
        "foam_volume_pct": foam_volume_pct,
        "crushable_spacer_bbl": crushable_spacer_vol_bbl,
    }
