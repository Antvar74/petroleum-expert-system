"""
Completion Design Engine — VLP (Beggs & Brill 1973) + Nodal Analysis.

References:
- Beggs & Brill (1973): Two-Phase Flow in Pipes (U. Tulsa)
- Nodal analysis: pressure matching at bottomhole node
"""
import math
from typing import Dict, Any, List, Optional, Tuple


def calculate_vlp_beggs_brill(
    tubing_id_in: float,
    well_depth_ft: float,
    wellhead_pressure_psi: float,
    oil_rate_stbd: float,
    water_cut: float = 0.0,
    glr_scf_stb: float = 500.0,
    oil_api: float = 35.0,
    gas_sg: float = 0.65,
    water_sg: float = 1.07,
    surface_temp_f: float = 100.0,
    bht_f: float = 200.0,
    num_points: int = 20,
    inclination_deg: float = 0.0,
) -> Dict[str, Any]:
    """
    Simplified Beggs & Brill (1973) VLP for multiphase tubing flow.

    Calculates Pwf required at bottom for a given wellhead pressure and rate.
    dP/dz = (dP/dz)_gravity + (dP/dz)_friction

    Args:
        tubing_id_in: tubing inner diameter (inches)
        well_depth_ft: measured depth of tubing (ft)
        wellhead_pressure_psi: flowing wellhead pressure (psi)
        oil_rate_stbd: oil rate (STB/d)
        water_cut: water fraction (0-1)
        glr_scf_stb: gas-liquid ratio (scf/STB)
        oil_api: oil API gravity
        gas_sg: gas specific gravity (air=1)
        water_sg: water specific gravity
        surface_temp_f: surface temperature (°F)
        bht_f: bottomhole temperature (°F)
        num_points: number of depth increments
        inclination_deg: well inclination from vertical (degrees)

    Returns:
        Dict with Pwf required, pressure profile, flow regime
    """
    d   = tubing_id_in / 12.0   # feet
    A   = math.pi * d ** 2 / 4.0
    L   = well_depth_ft
    Pwh = wellhead_pressure_psi

    if d <= 0 or L <= 0 or oil_rate_stbd < 0:
        return {"error": "Invalid tubing geometry or rate", "Pwf_required_psi": 0.0}

    gamma_o     = 141.5 / (131.5 + oil_api)
    rho_oil_sc  = gamma_o * 62.4  # lb/ft³ at SC

    if oil_rate_stbd == 0:
        rho_water    = water_sg * 62.4
        rho_liq      = rho_oil_sc * (1.0 - water_cut) + rho_water * water_cut
        hydrostatic  = rho_liq * L * math.cos(math.radians(inclination_deg)) / 144.0
        return {
            "Pwf_required_psi": round(Pwh + hydrostatic, 1),
            "pressure_profile": [],
            "dominant_flow_regime": "static",
            "method": "beggs_brill_simplified",
        }

    q_liquid_stbd = oil_rate_stbd / (1.0 - water_cut) if water_cut < 1.0 else oil_rate_stbd
    q_oil   = oil_rate_stbd
    q_water = q_liquid_stbd * water_cut

    dL        = L / max(num_points, 2)
    P         = Pwh
    cos_theta = math.cos(math.radians(inclination_deg))

    profile: List[Dict[str, Any]] = [{"depth_ft": 0.0, "pressure_psi": round(P, 1)}]
    regime_counts: Dict[str, int] = {"segregated": 0, "intermittent": 0, "distributed": 0, "transition": 0}

    for i in range(1, num_points + 1):
        depth   = i * dL
        T_local = surface_temp_f + (bht_f - surface_temp_f) * (depth / L)
        T_R     = T_local + 460.0

        Rs  = gas_sg * ((P / 18.2 + 1.4) * 10 ** (0.0125 * oil_api - 0.00091 * T_local)) ** 1.2048
        Rs  = min(Rs, glr_scf_stb)
        free_gas_glr = max(0.0, glr_scf_stb - Rs)

        Bo  = 0.972 + 0.000147 * (Rs * (gas_sg / gamma_o) ** 0.5 + 1.25 * T_local) ** 1.175
        Bo  = max(1.0, Bo)

        Ppc = 677 + 15 * gas_sg - 37.5 * gas_sg ** 2
        Tpc = 168 + 325 * gas_sg - 12.5 * gas_sg ** 2
        Ppr = P / Ppc if Ppc > 0 else 1.0
        Tpr = T_R / Tpc if Tpc > 0 else 1.5
        Z   = 1.0 - 3.52 * Ppr / (10 ** (0.9813 * Tpr)) + 0.274 * Ppr ** 2 / (10 ** (0.8157 * Tpr))
        Z   = max(0.3, min(Z, 1.5))

        v_sl = (5.615 * q_oil * Bo + 5.615 * q_water * 1.0) / (86400.0 * A)
        Bg   = 0.0283 * Z * T_R / P if P > 0 else 0.05
        v_sg = (q_oil * free_gas_glr * Bg) / (86400.0 * A)
        v_m  = max(v_sl + v_sg, 0.001)

        lambda_L = max(0.01, min(v_sl / v_m, 1.0))
        N_FR     = v_m ** 2 / (32.174 * d) if d > 0 else 0

        L1 = 316 * lambda_L ** 0.302
        L2 = 0.0009252 * lambda_L ** (-2.4684)
        L3 = 0.10 * lambda_L ** (-1.4516)
        L4 = 0.5  * lambda_L ** (-6.738)

        if lambda_L < 0.01 and N_FR < L1:
            pattern = "segregated"
        elif lambda_L >= 0.01 and N_FR < L2:
            pattern = "segregated"
        elif lambda_L >= 0.01 and L2 <= N_FR <= L3:
            pattern = "transition"
        elif (0.01 <= lambda_L < 0.4 and L3 < N_FR <= L1) or (lambda_L >= 0.4 and L3 < N_FR <= L4):
            pattern = "intermittent"
        else:
            pattern = "distributed"

        regime_counts[pattern] = regime_counts.get(pattern, 0) + 1

        if pattern == "segregated":
            a_bb, b_bb, c_bb = 0.980, 0.4846, 0.0868
        elif pattern == "intermittent":
            a_bb, b_bb, c_bb = 0.845, 0.5351, 0.0173
        elif pattern == "distributed":
            a_bb, b_bb, c_bb = 1.065, 0.5824, 0.0609
        else:
            a_bb, b_bb, c_bb = 0.920, 0.5100, 0.0500

        HL_0 = a_bb * lambda_L ** b_bb / (N_FR ** c_bb) if N_FR > 0 else lambda_L
        HL_0 = max(lambda_L, min(HL_0, 1.0))

        inc_rad  = math.radians(inclination_deg)
        NLv      = 1.938 * v_sl * (rho_oil_sc / (72.0 * max(0.001, 72.0 - 60.0))) ** 0.25
        C_factor = max(0.0, (1.0 - lambda_L) * math.log(
            max(1e-6, 0.011 * NLv ** 0.5 * lambda_L ** 0.2 * HL_0 ** 0.8)))
        psi_factor = 1.0 + C_factor * (math.sin(1.8 * inc_rad) - 0.333 * math.sin(1.8 * inc_rad) ** 3)
        HL = max(0.01, min(HL_0 * psi_factor, 1.0))

        rho_l = rho_oil_sc * (1.0 - water_cut) + water_sg * 62.4 * water_cut
        rho_g = gas_sg * 28.97 * P / (10.73 * T_R * Z) if (T_R * Z) > 0 else 0.1
        rho_m = rho_l * HL + rho_g * (1.0 - HL)

        dp_dz_grav = rho_m * cos_theta / 144.0

        Re_ns = 1488.0 * rho_m * v_m * d / max(0.01, 1.0)
        f_ns  = 0.0056 + 0.5 / Re_ns ** 0.32 if Re_ns > 0 else 0.01

        y_factor = lambda_L / (HL ** 2) if HL > 0 else 1.0
        if 1.0 < y_factor < 1.2:
            s_factor = math.log(2.2 * y_factor - 1.2)
        elif y_factor >= 1.2 and math.log(y_factor) != 0:
            lny = math.log(y_factor)
            s_factor = lny / (-0.0523 + 3.182 * lny - 0.8725 * lny ** 2 + 0.01853 * lny ** 4)
        else:
            s_factor = 0.0

        f_tp = f_ns * math.exp(s_factor)
        dp_dz_fric = f_tp * rho_m * v_m ** 2 / (2.0 * 32.174 * d * 144.0) if d > 0 else 0.0

        P = max(0.0, P + (dp_dz_grav + dp_dz_fric) * dL)
        profile.append({"depth_ft": round(depth, 1), "pressure_psi": round(P, 1)})

    dominant = max(regime_counts, key=regime_counts.get)

    return {
        "Pwf_required_psi": round(P, 1),
        "wellhead_pressure_psi": round(Pwh, 1),
        "pressure_profile": profile,
        "dominant_flow_regime": dominant,
        "flow_regime_distribution": regime_counts,
        "method": "beggs_brill_simplified",
        "parameters": {
            "tubing_id_in": tubing_id_in,
            "well_depth_ft": well_depth_ft,
            "oil_rate_stbd": oil_rate_stbd,
            "water_cut": water_cut,
            "glr_scf_stb": glr_scf_stb,
            "oil_api": oil_api,
        },
    }


def calculate_vlp_curve(
    tubing_id_in: float,
    well_depth_ft: float,
    wellhead_pressure_psi: float,
    q_max_stbd: float,
    water_cut: float = 0.0,
    glr_scf_stb: float = 500.0,
    oil_api: float = 35.0,
    gas_sg: float = 0.65,
    water_sg: float = 1.07,
    surface_temp_f: float = 100.0,
    bht_f: float = 200.0,
    num_rate_points: int = 20,
    inclination_deg: float = 0.0,
) -> Dict[str, Any]:
    """
    Build full VLP curve (Pwf vs q) using Beggs & Brill (1973).

    Calls calculate_vlp_beggs_brill() at each rate point from 0 to q_max.
    The characteristic J-shape arises from hydrostatic dominance at low rates
    and friction dominance at high rates.

    Args:
        tubing_id_in: tubing inner diameter (inches)
        well_depth_ft: tubing setting depth, measured depth (ft)
        wellhead_pressure_psi: flowing wellhead pressure (psi)
        q_max_stbd: maximum rate for curve (usually 1.1 × AOF) (STB/d)
        num_rate_points: number of q points on curve

    Returns:
        Dict with q_stbd[], Pwf_psi[], static BHP, dominant_regime, method
    """
    if q_max_stbd <= 0 or tubing_id_in <= 0 or well_depth_ft <= 0:
        return {"error": "Invalid inputs", "q_stbd": [], "Pwf_psi": []}

    # q=0: purely hydrostatic (single-phase liquid column)
    static_result = calculate_vlp_beggs_brill(
        tubing_id_in=tubing_id_in,
        well_depth_ft=well_depth_ft,
        wellhead_pressure_psi=wellhead_pressure_psi,
        oil_rate_stbd=0.0,
        water_cut=water_cut,
        glr_scf_stb=glr_scf_stb,
        oil_api=oil_api,
        gas_sg=gas_sg,
        water_sg=water_sg,
        surface_temp_f=surface_temp_f,
        bht_f=bht_f,
        num_points=3,
        inclination_deg=inclination_deg,
    )
    q_stbd: List[float] = [0.0]
    Pwf_psi: List[float] = [static_result.get("Pwf_required_psi", 0.0)]

    for i in range(1, num_rate_points + 1):
        q = q_max_stbd * i / num_rate_points
        res = calculate_vlp_beggs_brill(
            tubing_id_in=tubing_id_in,
            well_depth_ft=well_depth_ft,
            wellhead_pressure_psi=wellhead_pressure_psi,
            oil_rate_stbd=q,
            water_cut=water_cut,
            glr_scf_stb=glr_scf_stb,
            oil_api=oil_api,
            gas_sg=gas_sg,
            water_sg=water_sg,
            surface_temp_f=surface_temp_f,
            bht_f=bht_f,
            num_points=5,  # fewer internal steps for speed in curve-building mode
            inclination_deg=inclination_deg,
        )
        q_stbd.append(round(q, 1))
        Pwf_psi.append(res.get("Pwf_required_psi", 0.0))

    return {
        "q_stbd": q_stbd,
        "Pwf_psi": Pwf_psi,
        "q_max_stbd": round(q_max_stbd, 1),
        "static_bhp_psi": round(Pwf_psi[0], 1),
        "wellhead_pressure_psi": wellhead_pressure_psi,
        "method": "beggs_brill_1973",
    }


def calculate_nodal_analysis(
    ipr_Pwf: List[float],
    ipr_q: List[float],
    vlp_q_range: List[float],
    vlp_Pwf: List[float],
) -> Dict[str, Any]:
    """
    Find operating point at IPR-VLP intersection (nodal analysis at BH node).

    Interpolates both curves and finds intersection point.

    Args:
        ipr_Pwf: IPR Pwf values (psi), decreasing order
        ipr_q: IPR flow rates (STB/d), increasing with decreasing Pwf
        vlp_q_range: VLP flow rates (STB/d)
        vlp_Pwf: VLP Pwf required at each rate (psi)

    Returns:
        Dict with operating_point_q, operating_point_Pwf, stable flag
    """
    if not ipr_Pwf or not ipr_q or not vlp_q_range or not vlp_Pwf:
        return {"error": "Empty curve data",
                "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

    if len(ipr_Pwf) != len(ipr_q) or len(vlp_q_range) != len(vlp_Pwf):
        return {"error": "Curve arrays must have equal length",
                "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

    ipr_pairs = sorted(zip(ipr_q, ipr_Pwf), key=lambda x: x[0])
    vlp_pairs = sorted(zip(vlp_q_range, vlp_Pwf), key=lambda x: x[0])

    def _interp(pairs: List[Tuple[float, float]], q_val: float) -> Optional[float]:
        if not pairs:
            return None
        if q_val <= pairs[0][0]:
            return pairs[0][1]
        if q_val >= pairs[-1][0]:
            return pairs[-1][1]
        for j in range(len(pairs) - 1):
            q1, p1 = pairs[j]
            q2, p2 = pairs[j + 1]
            if q1 <= q_val <= q2:
                if q2 == q1:
                    return p1
                return p1 + (p2 - p1) * (q_val - q1) / (q2 - q1)
        return pairs[-1][1]

    q_min = max(ipr_pairs[0][0], vlp_pairs[0][0])
    q_max = min(ipr_pairs[-1][0], vlp_pairs[-1][0])

    if q_max <= q_min:
        return {"error": "No overlapping rate range",
                "operating_point_q": 0.0, "operating_point_Pwf": 0.0, "stable": False}

    best_q   = 0.0
    best_Pwf = 0.0
    best_diff = 1e12
    num_scan  = 200

    for i in range(num_scan + 1):
        q = q_min + (q_max - q_min) * i / num_scan
        Pwf_ipr = _interp(ipr_pairs, q)
        Pwf_vlp = _interp(vlp_pairs, q)
        if Pwf_ipr is None or Pwf_vlp is None:
            continue
        diff = abs(Pwf_ipr - Pwf_vlp)
        if diff < best_diff:
            best_diff = diff
            best_q    = q
            best_Pwf  = (Pwf_ipr + Pwf_vlp) / 2.0

    dq = max(1.0, best_q * 0.01)
    Pwf_ipr_lo = _interp(ipr_pairs, best_q - dq)
    Pwf_ipr_hi = _interp(ipr_pairs, best_q + dq)
    Pwf_vlp_lo = _interp(vlp_pairs, best_q - dq)
    Pwf_vlp_hi = _interp(vlp_pairs, best_q + dq)

    stable = True
    if all(v is not None for v in [Pwf_ipr_lo, Pwf_ipr_hi, Pwf_vlp_lo, Pwf_vlp_hi]):
        slope_ipr = (Pwf_ipr_hi - Pwf_ipr_lo) / (2 * dq) if dq > 0 else 0  # type: ignore[operator]
        slope_vlp = (Pwf_vlp_hi - Pwf_vlp_lo) / (2 * dq) if dq > 0 else 0  # type: ignore[operator]
        stable = slope_vlp > slope_ipr

    return {
        "operating_point_q": round(best_q, 2),
        "operating_point_Pwf_psi": round(best_Pwf, 1),
        "intersection_error_psi": round(best_diff, 2),
        "stable": stable,
        "q_range_min": round(q_min, 2),
        "q_range_max": round(q_max, 2),
    }
