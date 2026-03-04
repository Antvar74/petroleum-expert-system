"""
Sand Control Engine — Completion type evaluation and recommendation.

Decision matrix comparing:
  - Open Hole Gravel Pack (OHGP)
  - Cased Hole Gravel Pack (CHGP)
  - Standalone Screen (SAS)
  - Frac-Pack

References:
- Penberthy & Shaughnessy: Sand Control (SPE Series)
- SPE 30115: Screen selection criteria
"""
from typing import Dict, Any


def evaluate_completion_type(
    d50_mm: float,
    uniformity_coefficient: float,
    ucs_psi: float,
    reservoir_pressure_psi: float,
    formation_permeability_md: float,
    wellbore_type: str = "cased"
) -> Dict[str, Any]:
    """
    Evaluate and recommend completion/sand control method.

    Decision matrix comparing OHGP, Cased-Hole GP, SAS, Frac-Pack.

    Args:
        d50_mm: median grain size (mm)
        uniformity_coefficient: Cu = D60/D10
        ucs_psi: unconfined compressive strength (psi)
        reservoir_pressure_psi: reservoir pressure (psi)
        formation_permeability_md: formation permeability (mD)
        wellbore_type: 'openhole' or 'cased'

    Returns:
        Dict with recommended method, alternatives, scoring
    """
    methods = []

    # --- Open Hole Gravel Pack (OHGP) ---
    ohgp_score = 0
    if wellbore_type == "openhole":
        ohgp_score += 3
    if d50_mm < 0.15:
        ohgp_score += 2
    if uniformity_coefficient < 5:
        ohgp_score += 2
    if formation_permeability_md > 500:
        ohgp_score += 2
    if ucs_psi < 500:
        ohgp_score += 1
    methods.append({"method": "Open Hole Gravel Pack (OHGP)", "score": ohgp_score,
                    "pro": "Best sand retention, low skin", "con": "Requires open hole"})

    # --- Cased Hole Gravel Pack (CHGP) ---
    chgp_score = 0
    if wellbore_type == "cased":
        chgp_score += 3
    if d50_mm < 0.20:
        chgp_score += 2
    if uniformity_coefficient < 5:
        chgp_score += 1
    if formation_permeability_md > 200:
        chgp_score += 2
    if ucs_psi < 1000:
        chgp_score += 1
    methods.append({"method": "Cased Hole Gravel Pack (CHGP)", "score": chgp_score,
                    "pro": "Works with cased completions", "con": "Higher skin than OHGP"})

    # --- Standalone Screen (SAS) ---
    sas_score = 0
    if uniformity_coefficient < 3:
        sas_score += 3
    if d50_mm > 0.15:
        sas_score += 2
    if formation_permeability_md > 1000:
        sas_score += 2
    if ucs_psi > 500:
        sas_score += 1
    methods.append({"method": "Standalone Screen (SAS)", "score": sas_score,
                    "pro": "Simple, cost-effective", "con": "Poor for fines, no gravel backup"})

    # --- Frac-Pack ---
    fp_score = 0
    if formation_permeability_md < 200:
        fp_score += 3
    if d50_mm < 0.10:
        fp_score += 2
    if ucs_psi < 300:
        fp_score += 2
    if reservoir_pressure_psi > 5000:
        fp_score += 1
    methods.append({"method": "Frac-Pack", "score": fp_score,
                    "pro": "Best for low-perm + sanding", "con": "Complex, expensive"})

    methods.sort(key=lambda m: m["score"], reverse=True)
    recommended = methods[0]["method"]

    return {
        "recommended": recommended,
        "methods": methods,
        "formation_d50_mm": d50_mm,
        "uniformity_coefficient": uniformity_coefficient,
        "ucs_psi": ucs_psi,
        "wellbore_type": wellbore_type
    }
