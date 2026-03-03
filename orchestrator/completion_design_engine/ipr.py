"""
Completion Design Engine — Inflow Performance Relationship (IPR) models.

References:
- Vogel (1968): Inflow Performance of Solution-Gas Drive Wells (JPT)
- Fetkovich (1973): Isochronal Testing of Oil Wells (SPE 4529)
- Darcy (1856): steady-state radial flow
"""
import math
from typing import Dict, Any, List


def calculate_ipr_vogel(
    reservoir_pressure_psi: float,
    bubble_point_psi: float,
    productivity_index_above_pb: float,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Vogel (1968) IPR for solution-gas drive wells (oil below bubble point).

    q/q_max = 1 - 0.2*(Pwf/Pr) - 0.8*(Pwf/Pr)^2

    If Pr > Pb: composite IPR — Darcy above Pb, Vogel below.

    Args:
        reservoir_pressure_psi: average reservoir pressure (psi)
        bubble_point_psi: bubble point pressure (psi)
        productivity_index_above_pb: PI above bubble point (STB/d/psi)
        num_points: number of IPR curve points

    Returns:
        Dict with Pwf[], q[], AOF, q_at_pb, composite flag
    """
    Pr = reservoir_pressure_psi
    Pb = bubble_point_psi
    PI = productivity_index_above_pb

    if Pr <= 0 or PI <= 0:
        return {"error": "Reservoir pressure and PI must be > 0",
                "Pwf_psi": [], "q_oil_stbd": [], "AOF_stbd": 0.0}

    is_composite = Pr > Pb

    if is_composite:
        q_b     = PI * (Pr - Pb)
        q_v_max = q_b + PI * Pb / 1.8
        AOF     = q_v_max
    else:
        q_b     = 0.0
        q_v_max = PI * Pr / 1.8
        AOF     = q_v_max

    Pwf_list: List[float] = []
    q_list:   List[float] = []
    step = Pr / max(num_points, 2)
    for i in range(num_points + 1):
        Pwf = max(0.0, Pr - i * step)

        if is_composite and Pwf >= Pb:
            q = PI * (Pr - Pwf)
        else:
            if is_composite:
                ratio = Pwf / Pb if Pb > 0 else 0.0
                q = q_b + (q_v_max - q_b) * (1.0 - 0.2 * ratio - 0.8 * ratio ** 2)
            else:
                ratio = Pwf / Pr if Pr > 0 else 0.0
                q = q_v_max * (1.0 - 0.2 * ratio - 0.8 * ratio ** 2)

        Pwf_list.append(round(Pwf, 1))
        q_list.append(round(max(0.0, q), 2))

    return {
        "Pwf_psi": Pwf_list,
        "q_oil_stbd": q_list,
        "AOF_stbd": round(AOF, 2),
        "q_at_bubble_point_stbd": round(q_b, 2),
        "reservoir_pressure_psi": round(Pr, 1),
        "bubble_point_psi": round(Pb, 1),
        "productivity_index": round(PI, 4),
        "is_composite": is_composite,
        "method": "vogel_composite" if is_composite else "vogel_pure",
    }


def calculate_ipr_fetkovich(
    reservoir_pressure_psi: float,
    C_coefficient: float,
    n_exponent: float = 0.8,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Fetkovich (1973) IPR for gas and gas-condensate wells.

    q = C × (Pr² - Pwf²)^n

    Args:
        reservoir_pressure_psi: average reservoir pressure (psi)
        C_coefficient: back-pressure coefficient (Mscf/d/psi^2n)
        n_exponent: deliverability exponent (0.5-1.0)
        num_points: number of IPR curve points

    Returns:
        Dict with Pwf[], q_gas[], AOF
    """
    Pr = reservoir_pressure_psi
    C  = C_coefficient
    n  = max(0.5, min(n_exponent, 1.0))

    if Pr <= 0 or C <= 0:
        return {"error": "Reservoir pressure and C must be > 0",
                "Pwf_psi": [], "q_gas_mscfd": [], "AOF_mscfd": 0.0}

    AOF = C * (Pr ** 2) ** n

    Pwf_list: List[float] = []
    q_list:   List[float] = []
    step = Pr / max(num_points, 2)
    for i in range(num_points + 1):
        Pwf = max(0.0, Pr - i * step)
        delta_p2 = max(0.0, Pr ** 2 - Pwf ** 2)
        q = C * delta_p2 ** n
        Pwf_list.append(round(Pwf, 1))
        q_list.append(round(q, 2))

    return {
        "Pwf_psi": Pwf_list,
        "q_gas_mscfd": q_list,
        "AOF_mscfd": round(AOF, 2),
        "reservoir_pressure_psi": round(Pr, 1),
        "C_coefficient": C,
        "n_exponent": round(n, 3),
        "method": "fetkovich",
    }


def calculate_ipr_darcy(
    permeability_md: float,
    net_pay_ft: float,
    Bo: float,
    mu_oil_cp: float,
    reservoir_pressure_psi: float,
    wellbore_radius_ft: float = 0.354,
    drainage_radius_ft: float = 660.0,
    skin: float = 0.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Darcy straight-line IPR for single-phase oil above bubble point.

    q = kh(Pr-Pwf) / [141.2 × Bo × mu × (ln(re/rw) + S)]

    Args:
        permeability_md: formation permeability (mD)
        net_pay_ft: net formation thickness (ft)
        Bo: oil formation volume factor (RB/STB)
        mu_oil_cp: oil viscosity (cp)
        reservoir_pressure_psi: reservoir pressure (psi)
        wellbore_radius_ft: wellbore radius (ft)
        drainage_radius_ft: drainage radius (ft)
        skin: total skin factor
        num_points: number of IPR curve points

    Returns:
        Dict with Pwf[], q[], PI, AOF
    """
    k  = permeability_md
    h  = net_pay_ft
    Pr = reservoir_pressure_psi
    rw = wellbore_radius_ft
    re = drainage_radius_ft

    if k <= 0 or h <= 0 or Bo <= 0 or mu_oil_cp <= 0 or Pr <= 0 or rw <= 0 or re <= rw:
        return {"error": "Invalid input parameters",
                "Pwf_psi": [], "q_oil_stbd": [], "PI_stbd_psi": 0.0, "AOF_stbd": 0.0}

    ln_term = math.log(re / rw) + skin
    if ln_term <= 0:
        ln_term = 0.1   # guard for very negative skin

    PI  = k * h / (141.2 * Bo * mu_oil_cp * ln_term)
    AOF = PI * Pr

    Pwf_list: List[float] = []
    q_list:   List[float] = []
    step = Pr / max(num_points, 2)
    for i in range(num_points + 1):
        Pwf = max(0.0, Pr - i * step)
        q   = PI * (Pr - Pwf)
        Pwf_list.append(round(Pwf, 1))
        q_list.append(round(max(0.0, q), 2))

    return {
        "Pwf_psi": Pwf_list,
        "q_oil_stbd": q_list,
        "PI_stbd_psi": round(PI, 4),
        "AOF_stbd": round(AOF, 2),
        "reservoir_pressure_psi": round(Pr, 1),
        "permeability_md": k,
        "net_pay_ft": h,
        "skin": round(skin, 2),
        "method": "darcy_linear",
    }
