"""
Petrophysics Engine — Water Saturation Models.

References:
- Archie, G.E. (1942): Formation Factor and Water Saturation
- Waxman, M.H. & Smits, L.J.M. (1968): Electrical Conductivities in Shaly Sands
- Clavier, C., Coates, G. & Dumanoir, J. (1984): Dual-Water Model
"""
import math
from typing import Dict, Any


def calculate_water_saturation_advanced(
    phi: float, rt: float, rw: float, vsh: float = 0.0, rsh: float = 2.0,
    a: float = 1.0, m: float = 2.0, n: float = 2.0,
    method: str = "auto",
) -> Dict[str, Any]:
    """
    Calculate water saturation with auto-model selection.

    Models:
    - Archie (1942): clean sands, Vsh < 0.15
    - Waxman-Smits (1968): moderate clay, 0.15 <= Vsh < 0.40
    - Dual-Water (Clavier 1984): high clay, Vsh >= 0.40

    Args:
        phi: total porosity (fractional, 0-1)
        rt: true resistivity (ohm-m)
        rw: formation water resistivity (ohm-m)
        vsh: volume of shale (fractional, 0-1)
        rsh: shale resistivity (ohm-m)
        a, m, n: Archie cementation parameters
        method: "auto", "archie", "waxman_smits", "dual_water"

    Returns:
        Dict with sw, model_used, details
    """
    # Validate inputs
    phi = max(0.01, min(phi, 0.50))
    rt = max(0.1, rt)
    rw = max(0.001, rw)
    vsh = max(0.0, min(vsh, 1.0))

    # Auto-select model
    if method == "auto":
        if vsh < 0.15:
            method = "archie"
        elif vsh < 0.40:
            method = "waxman_smits"
        else:
            method = "dual_water"

    if method == "archie":
        sw = _archie_sw(phi, rt, rw, a, m, n)
        return {"sw": sw, "model_used": "archie", "vsh": vsh,
                "details": "Clean sand model (Archie 1942)"}

    elif method == "waxman_smits":
        sw = _waxman_smits_sw(phi, rt, rw, vsh, rsh, a, m, n)
        return {"sw": sw, "model_used": "waxman_smits", "vsh": vsh,
                "details": "Shaly sand model (Waxman-Smits 1968)"}

    elif method == "dual_water":
        sw = _dual_water_sw(phi, rt, rw, vsh, rsh, a, m, n)
        return {"sw": sw, "model_used": "dual_water", "vsh": vsh,
                "details": "High-clay model (Clavier et al. 1984)"}

    else:
        return {"error": f"Unknown method: {method}"}


def _archie_sw(phi: float, rt: float, rw: float, a: float, m: float, n: float) -> float:
    """Archie (1942): Sw = [(a * Rw) / (Rt * phi^m)]^(1/n)"""
    sw = ((a * rw) / (rt * (phi ** m))) ** (1.0 / n)
    return max(0.0, min(sw, 1.0))


def _waxman_smits_sw(
    phi: float, rt: float, rw: float, vsh: float, rsh: float,
    a: float, m: float, n: float,
) -> float:
    """
    Waxman-Smits (1968): accounts for clay-bound water conductivity.

    Qv (CEC per unit pore volume) estimated from Vsh:
        Qv ≈ Vsh * rho_sh * CEC_sh / phi
    Simplified: Qv ≈ 0.6 * Vsh / phi (typical for Gulf Coast shales)

    1/Rt = Sw^n * phi^m / (a*Rw) + B*Qv*Sw^(n-1) * phi^m / a
    where B ≈ 4.6 * (1 - 0.6*exp(-0.77/Rw)) — equivalent conductance
    """
    qv = 0.6 * vsh / max(phi, 0.01)
    b_coeff = 4.6 * (1.0 - 0.6 * math.exp(-0.77 / max(rw, 0.001)))

    # Iterative solution: start with Archie as initial guess
    sw = _archie_sw(phi, rt, rw, a, m, n)

    for _ in range(20):
        # 1/Rt = Sw^n * phi^m/(a*Rw) + B*Qv*Sw^(n-1)*phi^m/a
        term1 = (sw ** n) * (phi ** m) / (a * rw)
        term2 = b_coeff * qv * (sw ** max(n - 1, 0.1)) * (phi ** m) / a
        rt_calc = 1.0 / max(term1 + term2, 1e-10)

        if abs(rt_calc - rt) < 0.01 * rt:
            break

        # Adjust Sw
        if rt_calc > rt:
            sw *= 1.02
        else:
            sw *= 0.98
        sw = max(0.01, min(sw, 1.0))

    return round(sw, 4)


def _dual_water_sw(
    phi: float, rt: float, rw: float, vsh: float, rsh: float,
    a: float, m: float, n: float,
) -> float:
    """
    Dual-Water Model (Clavier et al., 1984).

    Distinguishes bound water (Swb) from free water (Swf).
    phi_t = phi_e + Vsh * phi_sh
    Ct = (phi_t^m / a) * [Swt^n * Cw + (Swb - Swt*Swb) * Cwb]

    Simplified iterative approach.
    """
    phi_sh = 0.30  # typical shale porosity
    phi_t = phi + vsh * phi_sh * (1.0 - phi)
    phi_t = max(0.01, min(phi_t, 0.50))

    swb = vsh * phi_sh / phi_t  # bound water saturation
    swb = min(swb, 0.99)

    cw = 1.0 / max(rw, 0.001)
    cwb = 1.0 / max(rsh * 0.3, 0.01)  # bound water conductivity
    ct = 1.0 / max(rt, 0.1)

    # Solve for Swt: Ct = (phi_t^m / a) * Swt^n * [Cw + (Swb/Swt)*(Cwb - Cw)]
    swt = _archie_sw(phi_t, rt, rw, a, m, n)

    for _ in range(30):
        if swt < 0.01:
            swt = 0.01
        cw_eff = cw + (swb / max(swt, 0.01)) * (cwb - cw)
        cw_eff = max(cw_eff, cw * 0.5)
        ct_calc = (phi_t ** m / a) * (swt ** n) * cw_eff

        if abs(ct_calc - ct) < 0.005 * ct:
            break

        ratio = (ct / max(ct_calc, 1e-10)) ** (1.0 / n)
        swt = swt * ratio
        swt = max(0.01, min(swt, 1.0))

    # Free water saturation
    sw_free = max(swt - swb, 0.0)

    return round(swt, 4)
