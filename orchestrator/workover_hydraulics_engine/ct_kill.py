"""
CT Kill — kill fluid weight calculation for workover operations.

Reference: IWCF/IADC well control principles; 0.052 psi/ft/ppg hydrostatic gradient
"""
from typing import Dict, Any


def calculate_workover_kill(
    reservoir_pressure: float,
    tvd: float,
    current_mud_weight: float,
    safety_margin_ppg: float = 0.3,
) -> Dict[str, Any]:
    """
    Calculate kill fluid requirements for workover operations.

    Kill weight = (P_reservoir / (0.052 × TVD)) + safety_margin

    Args:
        reservoir_pressure: formation/reservoir pressure (psi)
        tvd: true vertical depth (ft)
        current_mud_weight: current fluid weight (ppg)
        safety_margin_ppg: overbalance safety margin (ppg)

    Returns:
        Dict with kill_weight, hydrostatic, overbalance, status
    """
    if tvd <= 0:
        return {
            "kill_weight_ppg": current_mud_weight,
            "required_bhp_psi": reservoir_pressure,
            "current_bhp_psi": 0.0,
            "overbalance_psi": 0.0,
            "status": "Error: Zero TVD",
        }

    kill_weight = (reservoir_pressure / (0.052 * tvd)) + safety_margin_ppg
    current_bhp = 0.052 * current_mud_weight * tvd
    required_bhp = 0.052 * kill_weight * tvd
    # Overbalance = actual BHP vs reservoir — positive = overbalanced, negative = underbalanced
    overbalance = current_bhp - reservoir_pressure

    if current_bhp < reservoir_pressure:
        status = "UNDERBALANCED — Kill required"
    elif current_bhp >= reservoir_pressure and current_mud_weight < kill_weight:
        status = "Marginal — Weight up recommended"
    else:
        status = "Overbalanced"

    return {
        "kill_weight_ppg": round(kill_weight, 2),
        "required_bhp_psi": round(required_bhp, 0),
        "current_bhp_psi": round(current_bhp, 0),
        "reservoir_pressure_psi": reservoir_pressure,
        "overbalance_psi": round(overbalance, 0),
        "safety_margin_ppg": safety_margin_ppg,
        "status": status,
    }
