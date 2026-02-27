"""Stick-slip (torsional vibration) severity calculation.

References:
- Jansen & van den Steen (1995): Active damping of stick-slip vibrations
- Bowden & Tabor (1950): Friction and Lubrication of Solids (Stribeck curve)
"""
import math
from typing import Dict, Any, List, Optional


def _stribeck_friction(friction_factor: float, surface_rpm: float) -> float:
    """Apply Stribeck friction curve.

    mu_eff = mu_d + (mu_s - mu_d) * exp(-(omega/omega_s)^2)

    Where:
        mu_s = friction_factor (static, user input)
        mu_d = 0.6 * mu_s (dynamic, ~60% of static per Bowden & Tabor 1950)
        omega_s = 5.0 rad/s (Stribeck transition velocity)
    """
    mu_s = friction_factor
    mu_d = 0.6 * mu_s
    omega = surface_rpm * 2.0 * math.pi / 60.0
    omega_s = 5.0  # Stribeck transition velocity (rad/s)
    return mu_d + (mu_s - mu_d) * math.exp(-(omega / omega_s) ** 2)


def _viscous_damping_factor(
    surface_rpm: float,
    mud_weight_ppg: float,
    pv_cp: Optional[float],
    hole_diameter_in: float,
    bha_od_in: float,
    bha_length_ft: float,
) -> float:
    """Compute viscous damping reduction factor (0 < D <= 1).

    Based on annular viscous drag torque opposing torsional oscillations.
    Higher RPM + higher viscosity + smaller clearance = more damping.

    Reference: Jansen & van den Steen (1995), eq. 12-14.
    """
    # Approximate PV from mud weight when not provided (heuristic, not a published
    # correlation — users should supply actual PV for accurate damping estimates)
    pv = pv_cp if pv_cp is not None else mud_weight_ppg * 2.5
    omega = surface_rpm * 2.0 * math.pi / 60.0
    clearance_in = max(0.25, (hole_diameter_in - bha_od_in) / 2.0)
    c_visc = (pv / 100.0) * (bha_length_ft / 300.0) / (clearance_in / 0.875)
    c_visc *= 0.003
    return 1.0 / (1.0 + c_visc * omega)


def calculate_stick_slip_severity(
    surface_rpm: float,
    wob_klb: float,
    torque_ftlb: float,
    bit_diameter_in: float,
    bha_length_ft: float,
    bha_od_in: float,
    bha_id_in: float,
    mud_weight_ppg: float = 10.0,
    friction_factor: float = 0.25,
    pv_cp: Optional[float] = None,
    hole_diameter_in: float = 8.5,
    total_depth_ft: Optional[float] = None,
    dp_od_in: float = 5.0,
    dp_id_in: float = 4.276,
    bha_components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Calculate stick-slip severity index.

    Torsional stiffness is computed in priority order:
    1. **bha_components** (detailed drillstring table): iterates over every
       component and sums flexibility in series:
         1/K_eq = Σ (L_i / (G × J_i))
    2. **total_depth_ft** (wellbore sections): models BHA + DP as two
       springs in series.
    3. **BHA-only** fallback: uses bha_length_ft alone.

    Severity = delta_omega / omega_surface
    Where delta_omega = 2 * (T_friction / K_eq) * omega_surface

    Classification:
    - < 0.5: Mild (normal drilling)
    - 0.5-1.0: Moderate (monitoring needed)
    - 1.0-1.5: Severe (adjust parameters)
    - > 1.5: Critical (bit stalling likely)

    Args:
        surface_rpm: surface rotary speed (RPM)
        wob_klb: weight on bit (klbs)
        torque_ftlb: surface torque (ft-lbs)
        bit_diameter_in: bit diameter (inches)
        bha_length_ft: BHA length (ft)
        bha_od_in: BHA OD (inches)
        bha_id_in: BHA ID (inches)
        mud_weight_ppg: mud weight (ppg)
        friction_factor: bit-formation friction coefficient
        total_depth_ft: total measured depth (ft). When provided, DP section
            is modeled as a torsional spring in series with BHA.
        dp_od_in: drill pipe OD (inches), used when total_depth_ft provided
        dp_id_in: drill pipe ID (inches), used when total_depth_ft provided
        bha_components: detailed drillstring component list from BHA Editor.
            Each dict: {od, id_inner, length_ft, weight_ppf, type}.
            When provided, overrides total_depth_ft for stiffness calculation.

    Returns:
        Dict with severity index, classification, recommendations
    """
    if surface_rpm <= 0:
        return {"error": "RPM must be > 0"}

    # Stribeck-adjusted friction at operating RPM
    mu_eff = _stribeck_friction(friction_factor, surface_rpm)

    # Friction torque at bit (ft-lbs)
    r_bit_ft = bit_diameter_in / (2.0 * 12.0)
    wob_lbs = wob_klb * 1000.0
    t_friction = mu_eff * wob_lbs * r_bit_ft * 2.0 / 3.0

    # Torsional stiffness — G = E / (2(1+nu)) ~ 11.5e6 psi for steel
    g_shear = 11.5e6  # psi

    # Priority 1: Multi-component model from bha_components (BHA Editor table)
    if bha_components and len(bha_components) > 0:
        # Sum flexibility in series: 1/K_eq = Σ (L_i / (G × J_i))
        flex_sum = 0.0
        for comp in bha_components:
            od = comp.get("od", bha_od_in)
            id_in = comp.get("id_inner", bha_id_in)
            length_ft = comp.get("length_ft", 0)
            if length_ft <= 0:
                continue
            j_i = math.pi * (od ** 4 - id_in ** 4) / 32.0  # in^4
            if j_i <= 0:
                continue
            length_in = length_ft * 12.0
            flex_sum += length_in / (g_shear * j_i)
        k_torsion = 1.0 / flex_sum if flex_sum > 0 else 1e6

    # Priority 2: Two-section model from total_depth_ft (Wellbore Sections)
    elif total_depth_ft is not None and total_depth_ft > bha_length_ft:
        j_bha = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 32.0
        bha_length_in = bha_length_ft * 12.0
        k_bha = g_shear * j_bha / bha_length_in if bha_length_in > 0 else 1e6

        dp_length_ft = total_depth_ft - bha_length_ft
        dp_length_in = dp_length_ft * 12.0
        j_dp = math.pi * (dp_od_in ** 4 - dp_id_in ** 4) / 32.0
        k_dp = g_shear * j_dp / dp_length_in if dp_length_in > 0 else 1e6
        k_torsion = (k_bha * k_dp) / (k_bha + k_dp)

    # Priority 3: BHA-only fallback
    else:
        j_bha = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 32.0
        bha_length_in = bha_length_ft * 12.0
        k_torsion = g_shear * j_bha / bha_length_in if bha_length_in > 0 else 1e6

    # Angular displacement (radians)
    t_friction_inlb = t_friction * 12.0  # convert to in-lb
    delta_theta = t_friction_inlb / k_torsion if k_torsion > 0 else 0

    # Severity = 2 * delta_theta (peak-to-peak torsional oscillation amplitude)
    # Factor 2 accounts for full oscillation cycle per Jansen & van den Steen (1995)
    severity = 2.0 * delta_theta
    severity_undamped = severity

    # Viscous damping reduction
    d_factor = _viscous_damping_factor(
        surface_rpm, mud_weight_ppg, pv_cp,
        hole_diameter_in, bha_od_in, bha_length_ft,
    )
    severity = severity_undamped * d_factor

    # Min/Max RPM at bit (using damped severity)
    rpm_min_bit = max(0, surface_rpm * (1.0 - severity / 2.0))
    rpm_max_bit = surface_rpm * (1.0 + severity / 2.0)

    # Classification
    if severity < 0.5:
        classification = "Mild"
        color = "green"
        recommendation = "Normal drilling — no action needed"
    elif severity < 1.0:
        classification = "Moderate"
        color = "yellow"
        recommendation = "Monitor closely — consider increasing RPM or reducing WOB"
    elif severity < 1.5:
        classification = "Severe"
        color = "orange"
        recommendation = "Increase RPM to >120, reduce WOB, consider anti-stall tool"
    else:
        classification = "Critical"
        color = "red"
        recommendation = "Bit stalling likely — significantly reduce WOB and increase RPM"

    return {
        "severity_index": round(severity, 3),
        "severity_undamped": round(severity_undamped, 3),
        "classification": classification,
        "color": color,
        "rpm_min_at_bit": round(rpm_min_bit, 0),
        "rpm_max_at_bit": round(rpm_max_bit, 0),
        "surface_rpm": surface_rpm,
        "friction_torque_ftlb": round(t_friction, 0),
        "torsional_stiffness_inlb_rad": round(k_torsion, 0),
        "angular_displacement_deg": round(math.degrees(delta_theta), 2),
        "stribeck_friction_factor": round(mu_eff, 4),
        "damping_factor": round(d_factor, 4),
        "recommendation": recommendation,
    }
