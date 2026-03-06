"""
Petrophysics Engine — Permeability Estimation.

References:
- Timur, A. (1968): Permeability from Logs
- Coates, G.R. & Dumanoir, J.L. (1974): Permeability Estimation
"""
from typing import Dict, Any


def calculate_permeability_advanced(
    phi: float, sw_irr: float = 0.20, method: str = "timur",
) -> Dict[str, Any]:
    """
    Estimate permeability from porosity and irreducible water saturation.

    Methods:
    - Timur (1968): k = 8.58e4 * phi^4.4 / Sw_irr^2
    - Coates (1974): k = [(100*phi)^2 * (1-Sw_irr)/Sw_irr]^2 / 10000

    Args:
        phi: porosity (fractional)
        sw_irr: irreducible water saturation (fractional)
        method: "timur" or "coates"

    Returns:
        Dict with k_md, method, inputs
    """
    phi = max(0.01, min(phi, 0.50))
    sw_irr = max(0.05, min(sw_irr, 0.95))

    if method == "timur":
        k = 8.58e4 * (phi ** 4.4) / (sw_irr ** 2)
    elif method == "coates":
        k = ((100 * phi) ** 2 * (1 - sw_irr) / sw_irr) ** 2 / 10000
    else:
        return {"error": f"Unknown method: {method}"}

    return {
        "k_md": round(k, 2),
        "k_darcy": round(k / 1000, 4),
        "method": method,
        "phi": phi,
        "sw_irr": sw_irr,
        "quality": (
            "Excellent" if k > 1000 else
            "Good" if k > 100 else
            "Moderate" if k > 10 else
            "Poor" if k > 1 else
            "Tight"
        ),
    }
