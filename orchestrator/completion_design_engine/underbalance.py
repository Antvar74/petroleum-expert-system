"""
Completion Design Engine — underbalance analysis for perforating.

Reference: API RP 19B; industry guidelines for underbalance pressure windows.
"""
from typing import Dict, Any


def calculate_underbalance(
    reservoir_pressure_psi: float,
    wellbore_pressure_psi: float,
    formation_permeability_md: float,
    formation_type: str = "sandstone",
) -> Dict[str, Any]:
    """
    Calculate underbalance for perforating and evaluate adequacy.

    ΔP_ub = P_reservoir - P_wellbore  (positive = underbalanced)

    Args:
        reservoir_pressure_psi: formation/reservoir pressure (psi)
        wellbore_pressure_psi: wellbore pressure at perforation depth (psi)
        formation_permeability_md: formation permeability (mD)
        formation_type: "sandstone", "carbonate", "shale"

    Returns:
        Dict with underbalance, status, recommended range
    """
    delta_p = reservoir_pressure_psi - wellbore_pressure_psi
    is_underbalanced = delta_p > 0

    # Recommended underbalance ranges (industry guidelines, psi)
    recommendations = {
        "sandstone": {
            "high_perm": (200, 500),    # >100 mD
            "med_perm":  (500, 1500),   # 10-100 mD
            "low_perm":  (1500, 3000),  # <10 mD
        },
        "carbonate": {
            "high_perm": (100, 300),
            "med_perm":  (300, 1000),
            "low_perm":  (1000, 2000),
        },
        "shale": {
            "high_perm": (500, 1000),
            "med_perm":  (1000, 2000),
            "low_perm":  (2000, 5000),
        },
    }

    rock = recommendations.get(formation_type.lower(), recommendations["sandstone"])
    if formation_permeability_md > 100:
        rec_range  = rock["high_perm"]
        perm_class = "High (>100 mD)"
    elif formation_permeability_md > 10:
        rec_range  = rock["med_perm"]
        perm_class = "Medium (10-100 mD)"
    else:
        rec_range  = rock["low_perm"]
        perm_class = "Low (<10 mD)"

    if not is_underbalanced:
        status = "Overbalanced"
        recommendation = "Switch to underbalanced perforating for better cleanup"
    elif delta_p < rec_range[0]:
        status = "Insufficient Underbalance"
        recommendation = f"Increase underbalance to {rec_range[0]}-{rec_range[1]} psi"
    elif delta_p <= rec_range[1]:
        status = "Optimal"
        recommendation = "Underbalance within recommended range"
    else:
        status = "Excessive Underbalance"
        recommendation = f"Risk of sand influx/formation failure. Reduce to {rec_range[1]} psi max"

    return {
        "underbalance_psi": round(delta_p, 1),
        "is_underbalanced": is_underbalanced,
        "overbalance_psi": round(-delta_p, 1) if not is_underbalanced else 0,
        "status": status,
        "recommended_range_psi": list(rec_range),
        "permeability_class": perm_class,
        "formation_type": formation_type,
        "recommendation": recommendation,
    }
