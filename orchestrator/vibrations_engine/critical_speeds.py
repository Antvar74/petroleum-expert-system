"""Critical RPM calculations -- axial, lateral, and multi-component TMM.

References:
- Paslay & Dawson (1984): Drillstring lateral vibrations and whirl
- Mitchell (2003): Transfer Matrix analysis of BHA vibrations
"""
import math
from typing import Dict, Any, List, Optional

# Shared steel constants
STEEL_E = 30e6         # Young's modulus (psi)
STEEL_DENSITY = 490.0  # lb/ft^3 (steel density)
GRAVITY = 32.174       # ft/s^2


def calculate_critical_rpm_axial(
    bha_length_ft: float,
    bha_od_in: float,
    bha_id_in: float,
    bha_weight_lbft: float,
    mud_weight_ppg: float = 10.0
) -> Dict[str, Any]:
    """
    Calculate critical RPM for axial vibrations (bit bounce).

    Natural frequency: fn = (1 / 2L) * sqrt(E / rho)
    Critical RPM = fn * 60

    For BHA with buoyancy: rho_eff = rho_steel * (1 - MW/65.5)

    Args:
        bha_length_ft: BHA length (ft)
        bha_od_in: BHA outer diameter (inches)
        bha_id_in: BHA inner diameter (inches)
        bha_weight_lbft: BHA weight per foot (lb/ft)
        mud_weight_ppg: mud weight (ppg)

    Returns:
        Dict with critical RPM, natural frequency, harmonics
    """
    if bha_length_ft <= 0:
        return {"error": "BHA length must be > 0"}

    e = STEEL_E
    rho_steel = STEEL_DENSITY

    # Buoyancy factor
    bf = 1.0 - (mud_weight_ppg / 65.5)
    rho_eff = rho_steel * bf  # effective density lb/ft^3

    # Convert to consistent units (psi and slugs/ft^3)
    # E in psi = lbf/in^2, rho in lb/ft^3 -> need lbm/in^3
    rho_in3 = rho_eff / 1728.0  # lb/in^3
    # Speed of sound in steel: c = sqrt(E/rho) where rho in lb/in^3 and E in lb/in^2
    # But need consistent: E (lb/in^2), rho (lbm/in^3), g=386.4 in/s^2
    g_in = 386.4  # in/s^2
    c_steel = math.sqrt(e * g_in / rho_in3) if rho_in3 > 0 else 16000 * 12  # in/s

    # BHA length in inches
    l_in = bha_length_ft * 12.0

    # Natural frequency (1st mode)
    fn_1 = c_steel / (2.0 * l_in)  # Hz

    # Critical RPM
    rpm_critical_1 = fn_1 * 60.0

    # Harmonics (2nd and 3rd mode)
    fn_2 = 2 * fn_1
    fn_3 = 3 * fn_1
    rpm_critical_2 = fn_2 * 60.0
    rpm_critical_3 = fn_3 * 60.0

    # Safe operating bands
    safe_bands = []
    if rpm_critical_1 > 40:
        safe_bands.append({"min_rpm": 0, "max_rpm": round(rpm_critical_1 * 0.85)})
    if rpm_critical_2 - rpm_critical_1 > 20:
        safe_bands.append({
            "min_rpm": round(rpm_critical_1 * 1.15),
            "max_rpm": round(rpm_critical_2 * 0.85)
        })

    return {
        "critical_rpm_1st": round(rpm_critical_1, 0),
        "critical_rpm_2nd": round(rpm_critical_2, 0),
        "critical_rpm_3rd": round(rpm_critical_3, 0),
        "natural_freq_hz_1st": round(fn_1, 2),
        "natural_freq_hz_2nd": round(fn_2, 2),
        "buoyancy_factor": round(bf, 4),
        "safe_operating_bands": safe_bands,
        "mode": "Axial (Bit Bounce)",
    }


def calculate_critical_rpm_lateral(
    bha_length_ft: float,
    bha_od_in: float,
    bha_id_in: float,
    bha_weight_lbft: float,
    hole_diameter_in: float,
    mud_weight_ppg: float = 10.0,
    inclination_deg: float = 0.0,
    stabilizer_spacing_ft: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate critical RPM for lateral vibrations (whirl).
    Paslay & Dawson (1984):

    RPM_crit = 4760 / (L * sqrt(BF * w / (E * I)))

    Where L in ft, w in lb/ft, E in psi, I in in^4.

    Forward whirl occurs below critical RPM.
    Backward whirl occurs at and above critical RPM.

    Args:
        bha_length_ft: BHA length between stabilizers (ft)
        bha_od_in: BHA outer diameter (inches)
        bha_id_in: BHA inner diameter (inches)
        bha_weight_lbft: BHA weight per foot (lb/ft)
        hole_diameter_in: hole/casing inner diameter (inches)
        mud_weight_ppg: mud weight (ppg)
        inclination_deg: wellbore inclination (degrees)

    Returns:
        Dict with critical RPM, whirl type prediction, clearance
    """
    if bha_length_ft <= 0:
        return {"error": "BHA length must be > 0"}

    e = STEEL_E
    bf = 1.0 - (mud_weight_ppg / 65.5)

    # Moment of inertia
    i_moment = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 64.0

    # Buoyed weight per foot
    w_buoyed = bha_weight_lbft * bf

    if w_buoyed <= 0 or i_moment <= 0:
        return {"error": "Invalid BHA parameters"}

    # Determine span length for lateral calculation
    if stabilizer_spacing_ft is not None and stabilizer_spacing_ft > 0:
        span_ft = stabilizer_spacing_ft
        span_source = "user"
    else:
        span_ft = min(bha_length_ft, 90.0)
        span_source = "estimated"

    # Lateral critical RPM -- Euler-Bernoulli pinned-pinned 1st mode:
    # omega_n = (pi/L_in)^2 * sqrt(E*I*g / w_lbin)   [rad/s]
    # N_crit  = omega_n * 60 / (2*pi)
    #         = (30*pi / L_in^2) * sqrt(E*I*g / w_lbin)
    g_in = 386.4  # in/s^2, gravitational constant for lbm->slug conversion
    l_in = span_ft * 12.0
    w_lbin = w_buoyed / 12.0  # lb/ft -> lb/in
    numerator = 30.0 * math.pi * math.sqrt(e * i_moment * g_in / w_lbin)
    rpm_critical = numerator / (l_in ** 2) if l_in > 0 else 999

    # Radial clearance
    clearance = (hole_diameter_in - bha_od_in) / 2.0

    # Whirl severity factor (increases with clearance and inclination)
    inc_factor = 1.0 + 0.5 * math.sin(math.radians(inclination_deg))
    whirl_severity = clearance * inc_factor

    return {
        "critical_rpm": round(rpm_critical, 0),
        "mode": "Lateral (Whirl)",
        "span_used_ft": round(span_ft, 1),
        "span_source": span_source,
        "radial_clearance_in": round(clearance, 3),
        "buoyed_weight_lbft": round(w_buoyed, 2),
        "moment_of_inertia_in4": round(i_moment, 2),
        "whirl_severity_factor": round(whirl_severity, 3),
        "prediction": "Forward Whirl risk below critical RPM" if rpm_critical > 60 else "High whirl risk",
    }


def calculate_critical_rpm_lateral_multi(
    bha_components: List[Dict[str, Any]],
    mud_weight_ppg: float = 10.0,
    hole_diameter_in: float = 8.5,
    boundary_conditions: str = "pinned-pinned"
) -> Dict[str, Any]:
    """
    Multi-component BHA lateral critical RPM via Transfer Matrix Method (TMM).

    Each BHA component is modelled as a Euler-Bernoulli beam segment with
    its own EI, linear mass, and length. A 4x4 field transfer matrix is
    built per segment, and the product T = T_n * ... * T_1 is evaluated.
    Critical frequencies are found by scanning for sign changes of the
    appropriate determinant boundary condition.

    Args:
        bha_components: list of dicts, each with:
            - type (str): 'collar', 'stabilizer', 'motor', 'mwd', 'lwd', 'hwdp', 'jar', 'crossover'
            - od (float): outer diameter (in)
            - id_inner (float): inner diameter (in)
            - length_ft (float): segment length (ft)
            - weight_ppf (float): weight per foot (lb/ft)
        mud_weight_ppg: mud weight (ppg)
        hole_diameter_in: hole / casing ID (in)
        boundary_conditions: 'pinned-pinned' | 'fixed-pinned' | 'fixed-free'

    Returns:
        Dict with mode frequencies, critical RPMs (1st-3rd), component details.
    """
    if not bha_components:
        return {"error": "No BHA components provided"}

    e = STEEL_E
    rho_steel = STEEL_DENSITY
    bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)

    # Pre-compute per-component properties
    segments = []
    total_length_ft = 0.0
    for comp in bha_components:
        od = comp.get("od", 6.75)
        id_in = comp.get("id_inner", 2.813)
        l_ft = comp.get("length_ft", 30.0)
        w_ppf = comp.get("weight_ppf", 80.0)

        i_moment = math.pi * (od ** 4 - id_in ** 4) / 64.0  # in^4
        a_steel = math.pi * (od ** 2 - id_in ** 2) / 4.0    # in^2
        w_buoyed = w_ppf * bf  # lb/ft buoyed
        mass_per_in = (w_ppf / 386.4) / 12.0  # slug / in (mass per inch length)

        segments.append({
            "type": comp.get("type", "collar"),
            "od": od,
            "id_inner": id_in,
            "length_in": l_ft * 12.0,
            "length_ft": l_ft,
            "EI": e * i_moment,          # lb*in^2
            "mass_per_in": mass_per_in,   # slug/in
            "w_buoyed_ppf": w_buoyed,
            "i_moment_in4": i_moment,
            "a_steel_in2": a_steel,
        })
        total_length_ft += l_ft

    if total_length_ft <= 0:
        return {"error": "Total BHA length must be > 0"}

    # --- TMM frequency sweep ---
    # For pinned-pinned: boundary is y=0, M=0 at both ends.
    # State vector [y, theta, M, V]. After transfer: T * [0, theta_0, 0, V_0]
    # Requirement: y_end = 0 and M_end = 0.
    # From state vector output: y_end = T[0][1]*theta_0 + T[0][3]*V_0 = 0
    #                            M_end = T[2][1]*theta_0 + T[2][3]*V_0 = 0
    # Non-trivial solution: det([[T01,T03],[T21,T23]]) = 0

    def _transfer_matrix_product(omega: float) -> List[List[float]]:
        """Build product of transfer matrices for all segments at angular freq omega."""
        # 4x4 identity
        T = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

        for seg in segments:
            L = seg["length_in"]
            ei = seg["EI"]
            m_per_in = seg["mass_per_in"]

            if L <= 0 or ei <= 0:
                continue

            # lambda^4 = m*omega^2/EI
            lam4 = m_per_in * omega ** 2 / ei if ei > 0 else 0
            if lam4 <= 0:
                # Zero frequency: rigid body transfer
                F = [[1, L, 0, 0], [0, 1, 0, 0], [0, 0, 1, L], [0, 0, 0, 1]]
            else:
                lam = lam4 ** 0.25
                lL = lam * L

                # Prevent overflow for very large lL
                if lL > 20:
                    lL = 20.0

                c = math.cos(lL)
                s = math.sin(lL)
                ch = math.cosh(lL)
                sh = math.sinh(lL)

                # Field transfer matrix (Euler-Bernoulli beam vibration)
                # [y, theta, M, V] transfer
                a11 = 0.5 * (c + ch)
                a12 = 0.5 * (s / lam + sh / lam) if lam > 0 else L
                a13 = 0.5 * (-c + ch) / (lam ** 2) if lam > 0 else 0
                a14 = 0.5 * (-s + sh) / (lam ** 3) if lam > 0 else 0

                a21 = 0.5 * (-lam * s + lam * sh)
                a22 = 0.5 * (c + ch)
                a23 = 0.5 * (s + sh) / lam if lam > 0 else 0
                a24 = 0.5 * (-c + ch) / (lam ** 2) if lam > 0 else 0

                a31 = 0.5 * (-lam ** 2 * c - lam ** 2 * ch) if lam > 0 else 0
                a32 = 0.5 * (-lam * s + lam * sh)
                a33 = 0.5 * (c + ch)
                a34 = 0.5 * (s / lam + sh / lam) if lam > 0 else L

                a41_base = 0.5 * (lam ** 3 * s - lam ** 3 * sh) if lam > 0 else 0
                a42 = 0.5 * (-lam ** 2 * c - lam ** 2 * ch) if lam > 0 else 0
                a43 = 0.5 * (-lam * s + lam * sh)
                a44 = 0.5 * (c + ch)

                # Adjust signs for EI*M convention
                F = [
                    [a11,          a12,          a13 / ei if ei > 0 else 0,  a14 / ei if ei > 0 else 0],
                    [a21,          a22,          a23 / ei if ei > 0 else 0,  a24 / ei if ei > 0 else 0],
                    [a31 * ei,     a32 * ei,     a33,                         a34],
                    [a41_base * ei, a42 * ei,    a43,                         a44],
                ]

            # Matrix multiply T = F * T
            T_new = [[0.0] * 4 for _ in range(4)]
            for i in range(4):
                for j in range(4):
                    for k in range(4):
                        T_new[i][j] += F[i][k] * T[k][j]
            T = T_new

        return T

    def _boundary_det(omega: float) -> float:
        """Determinant of boundary condition sub-matrix."""
        T = _transfer_matrix_product(omega)
        if boundary_conditions == "pinned-pinned":
            # y=0,M=0 at start; y=0,M=0 at end
            # Free variables: theta_0, V_0 (indices 1,3)
            return T[0][1] * T[2][3] - T[0][3] * T[2][1]
        elif boundary_conditions == "fixed-pinned":
            # y=0,theta=0 at start; y=0,M=0 at end
            return T[0][2] * T[2][3] - T[0][3] * T[2][2]
        else:  # fixed-free
            # y=0,theta=0 at start; M=0,V=0 at end
            return T[2][2] * T[3][3] - T[2][3] * T[3][2]

    # Frequency scan: 0.1 to 200 rad/s in 500 steps
    omega_max = 200.0
    n_scan = 500
    d_omega = omega_max / n_scan
    modes = []
    prev_val = _boundary_det(0.1)
    for i in range(1, n_scan + 1):
        omega = 0.1 + i * d_omega
        val = _boundary_det(omega)
        if prev_val * val < 0 and len(modes) < 5:
            # Sign change -- bisect to refine
            lo, hi = omega - d_omega, omega
            for _ in range(30):
                mid = (lo + hi) / 2.0
                mv = _boundary_det(mid)
                if mv * _boundary_det(lo) < 0:
                    hi = mid
                else:
                    lo = mid
            omega_root = (lo + hi) / 2.0
            freq_hz = omega_root / (2.0 * math.pi)
            rpm_crit = freq_hz * 60.0
            if rpm_crit > 5:  # Filter out numerical noise
                modes.append({
                    "mode_number": len(modes) + 1,
                    "natural_freq_hz": round(freq_hz, 3),
                    "critical_rpm": round(rpm_crit, 1),
                    "omega_rad_s": round(omega_root, 4),
                })
        prev_val = val

    # Fallback: if TMM found no modes, use weighted Paslay-Dawson
    if not modes:
        total_ei = sum(s["EI"] for s in segments)
        total_w = sum(s["w_buoyed_ppf"] for s in segments)
        avg_ei = total_ei / len(segments)
        avg_w = total_w / len(segments) if total_w > 0 else 1.0
        rpm_pd = 4760.0 / (total_length_ft * math.sqrt(avg_w / avg_ei)) if avg_ei > 0 else 120.0
        modes = [
            {"mode_number": 1, "natural_freq_hz": round(rpm_pd / 60.0, 3),
             "critical_rpm": round(rpm_pd, 1), "omega_rad_s": round(rpm_pd / 60.0 * 2 * math.pi, 4)},
            {"mode_number": 2, "natural_freq_hz": round(rpm_pd * 2 / 60.0, 3),
             "critical_rpm": round(rpm_pd * 2, 1), "omega_rad_s": round(rpm_pd * 2 / 60.0 * 2 * math.pi, 4)},
        ]

    # Component summary table
    comp_table = []
    for seg in segments:
        comp_table.append({
            "type": seg["type"],
            "od_in": seg["od"],
            "id_in": seg["id_inner"],
            "length_ft": seg["length_ft"],
            "EI_lb_in2": round(seg["EI"], 0),
            "buoyed_weight_ppf": round(seg["w_buoyed_ppf"], 2),
        })

    return {
        "modes": modes,
        "mode_1_critical_rpm": modes[0]["critical_rpm"] if modes else 0,
        "mode_2_critical_rpm": modes[1]["critical_rpm"] if len(modes) > 1 else 0,
        "mode_3_critical_rpm": modes[2]["critical_rpm"] if len(modes) > 2 else 0,
        "num_modes_found": len(modes),
        "total_bha_length_ft": round(total_length_ft, 1),
        "boundary_conditions": boundary_conditions,
        "components": comp_table,
        "method": "Transfer Matrix Method (TMM)",
    }
