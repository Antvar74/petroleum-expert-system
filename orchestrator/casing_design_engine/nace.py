"""
NACE MR0175 / ISO 15156 — Sour Service Material Validation

Validates casing grade selection against H2S environment requirements.
Reference: NACE MR0175/ISO 15156-2, Table A.2
"""
from typing import Dict, Any

# NACE MR0175 compliant grades (max hardness 22 HRC for SSC resistance)
NACE_COMPLIANT_GRADES = {
    "J55": {"compliant": True, "max_hardness_hrc": 22, "note": "Low strength, inherently resistant"},
    "K55": {"compliant": True, "max_hardness_hrc": 22, "note": "Low strength, inherently resistant"},
    "L80": {"compliant": True, "max_hardness_hrc": 22, "note": "NACE grade, restricted chemistry"},
    "C90": {"compliant": True, "max_hardness_hrc": 25.4, "note": "NACE grade per ISO 15156-2 Table A.2"},
    "T95": {"compliant": True, "max_hardness_hrc": 25.4, "note": "NACE grade per ISO 15156-2 Table A.2"},
    "C110": {"compliant": True, "max_hardness_hrc": 30, "note": "NACE grade, CRA requirements may apply"},
    "N80": {"compliant": False, "max_hardness_hrc": None, "note": "Not NACE compliant — exceeds hardness limits"},
    "P110": {"compliant": False, "max_hardness_hrc": None, "note": "Not NACE compliant — yield > 95 ksi"},
    "Q125": {"compliant": False, "max_hardness_hrc": None, "note": "Not NACE compliant — yield > 95 ksi"},
}

# NACE threshold: H2S partial pressure > 0.05 psi triggers sour service requirements
SOUR_SERVICE_THRESHOLD_PSI = 0.05


def check_nace_compliance(
    grade: str,
    h2s_psi: float = 0.0,
    co2_psi: float = 0.0,
    temperature_f: float = 200.0,
) -> Dict[str, Any]:
    """
    Check if casing grade is compliant with NACE MR0175/ISO 15156.

    Parameters:
        grade: API 5CT grade code
        h2s_psi: H2S partial pressure (psi)
        co2_psi: CO2 partial pressure (psi) — for corrosion severity
        temperature_f: Service temperature

    Returns:
        Dict with compliant (bool), grade, environment classification, notes
    """
    if h2s_psi < SOUR_SERVICE_THRESHOLD_PSI:
        return {
            "compliant": True,
            "grade": grade,
            "environment": "Sweet (non-sour)",
            "h2s_psi": h2s_psi,
            "note": f"H2S ({h2s_psi:.3f} psi) below NACE threshold ({SOUR_SERVICE_THRESHOLD_PSI} psi)",
        }

    if h2s_psi >= 10:
        severity = "Very Severe"
    elif h2s_psi >= 1.0:
        severity = "Severe"
    else:
        severity = "Mild Sour"

    grade_info = NACE_COMPLIANT_GRADES.get(grade.upper(), {
        "compliant": False, "max_hardness_hrc": None,
        "note": f"Unknown grade '{grade}' — assume non-compliant",
    })

    return {
        "compliant": grade_info["compliant"],
        "grade": grade,
        "environment": severity,
        "h2s_psi": h2s_psi,
        "co2_psi": co2_psi,
        "max_hardness_hrc": grade_info.get("max_hardness_hrc"),
        "note": grade_info["note"],
        "recommendation": (
            None if grade_info["compliant"]
            else f"Replace {grade} with L80, C90, or T95 for sour service"
        ),
    }
