"""
Torque & Drag Engine — Friction Back-Calculation.

Bisection method to find the friction factor that matches
a measured surface hookload.

References:
- Applied Drilling Engineering (Bourgoyne et al.)
"""
from typing import List, Dict, Any

from .soft_string import compute_torque_drag


def back_calculate_friction(
    survey: List[Dict[str, Any]],
    drillstring: List[Dict[str, Any]],
    measured_hookload: float,
    operation: str,
    mud_weight: float,
    wob: float = 0.0,
    casing_shoe_md: float = 0.0,
    tolerance: float = 0.5
) -> Dict[str, Any]:
    """
    Back-calculate friction factor using bisection method.
    Finds the friction factor that matches the measured hookload.

    Parameters:
    - measured_hookload: measured surface hookload in klb
    - tolerance: acceptable error in klb
    Returns: dict with calculated friction factor and iterations
    """
    mu_low = 0.05
    mu_high = 0.60
    max_iter = 50

    calc_hookload = 0.0
    error = 0.0
    mu_mid = 0.0

    for iteration in range(max_iter):
        mu_mid = (mu_low + mu_high) / 2.0

        result = compute_torque_drag(
            survey=survey,
            drillstring=drillstring,
            friction_cased=mu_mid,
            friction_open=mu_mid,
            operation=operation,
            mud_weight=mud_weight,
            wob=wob,
            casing_shoe_md=casing_shoe_md
        )

        if "error" in result:
            return {"error": result["error"]}

        calc_hookload = result["summary"]["surface_hookload_klb"]
        error = calc_hookload - measured_hookload

        if abs(error) < tolerance:
            return {
                "friction_factor": round(mu_mid, 4),
                "calculated_hookload_klb": round(calc_hookload, 1),
                "measured_hookload_klb": measured_hookload,
                "error_klb": round(error, 2),
                "iterations": iteration + 1,
                "converged": True
            }

        if operation in ("trip_out", "back_ream", "rotating"):
            # Higher friction -> higher hookload
            if calc_hookload > measured_hookload:
                mu_high = mu_mid
            else:
                mu_low = mu_mid
        else:
            # trip_in, sliding: higher friction -> lower hookload
            if calc_hookload < measured_hookload:
                mu_high = mu_mid
            else:
                mu_low = mu_mid

    return {
        "friction_factor": round(mu_mid, 4),
        "calculated_hookload_klb": round(calc_hookload, 1),
        "measured_hookload_klb": measured_hookload,
        "error_klb": round(error, 2),
        "iterations": max_iter,
        "converged": False
    }
