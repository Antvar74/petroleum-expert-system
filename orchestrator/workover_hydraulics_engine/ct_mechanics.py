"""
CT Mechanics — CT elongation (4-component Lubinski model) and fatigue life (Miner's rule).

References:
- Lubinski (1977): Coiled Tubing elongation calculations
- API RP 5C7: Coiled Tubing fatigue methodology
"""
import math
from typing import Dict, Any, List, Optional


def calculate_ct_elongation(
    ct_od: float,
    ct_id: float,
    ct_length: float,
    weight_per_ft: float,
    mud_weight: float,
    delta_p_internal: float = 0.0,
    delta_t: float = 0.0,
    wellhead_pressure: float = 0.0,
    annular_pressure: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate CT elongation/shortening from four physical mechanisms.

    Components:
    1. Weight (Hooke's triangular load): dL_weight = W × L / (2 × E × A_s)
    2. Temperature: dL_temp = alpha × delta_T × L
    3. Ballooning (Poisson effect): dL_balloon = -2ν × (Pi×Ai - Po×Ao) × L / (E × A_s)
    4. Bourdon (internal pressure end force): dL_bourdon = delta_P × Ai × L / (E × A_s)

    Args:
        ct_od: CT outer diameter (inches)
        ct_id: CT inner diameter (inches)
        ct_length: CT length in hole (ft)
        weight_per_ft: CT weight (lb/ft)
        mud_weight: fluid density (ppg) — for buoyancy
        delta_p_internal: differential internal pressure above hydrostatic (psi)
        delta_t: average temperature change from surface condition (°F, positive = hotter)
        wellhead_pressure: surface treating pressure (psi)
        annular_pressure: annular surface pressure (psi)

    Returns:
        Dict with individual elongation components and total (ft)
    """
    if ct_od <= 0 or ct_id <= 0 or ct_length <= 0:
        return {
            "dL_weight_ft": 0.0, "dL_temperature_ft": 0.0,
            "dL_ballooning_ft": 0.0, "dL_bourdon_ft": 0.0,
            "dL_total_ft": 0.0, "depth_correction_ft": 0.0,
        }

    E = 30e6        # Young's modulus, psi
    alpha = 6.9e-6  # Thermal expansion coefficient, 1/°F
    nu = 0.30       # Poisson's ratio

    A_o = math.pi / 4.0 * ct_od ** 2
    A_i = math.pi / 4.0 * ct_id ** 2
    A_s = A_o - A_i

    if A_s <= 0:
        return {
            "dL_weight_ft": 0.0, "dL_temperature_ft": 0.0,
            "dL_ballooning_ft": 0.0, "dL_bourdon_ft": 0.0,
            "dL_total_ft": 0.0, "depth_correction_ft": 0.0,
        }

    bf = max(1.0 - (mud_weight / 65.5), 0.0)
    W_buoyed = weight_per_ft * bf * ct_length

    L_in = ct_length * 12.0  # ft → inches

    # 1. Weight elongation (triangular load, CG at L/2)
    dL_weight_ft = (W_buoyed * L_in / (2.0 * E * A_s)) / 12.0

    # 2. Temperature elongation
    dL_temp_ft = alpha * delta_t * ct_length

    # 3. Ballooning (Poisson shortening)
    Pi = wellhead_pressure + delta_p_internal
    Po = annular_pressure
    dL_balloon_ft = (-2.0 * nu * (Pi * A_i - Po * A_o) * L_in / (E * A_s)) / 12.0

    # 4. Bourdon effect (pressure end-force)
    delta_P_net = Pi - Po
    dL_bourdon_ft = (delta_P_net * A_i * L_in / (E * A_s)) / 12.0

    dL_total_ft = dL_weight_ft + dL_temp_ft + dL_balloon_ft + dL_bourdon_ft

    return {
        "dL_weight_ft": round(dL_weight_ft, 4),
        "dL_temperature_ft": round(dL_temp_ft, 4),
        "dL_ballooning_ft": round(dL_balloon_ft, 4),
        "dL_bourdon_ft": round(dL_bourdon_ft, 4),
        "dL_total_ft": round(dL_total_ft, 4),
        "depth_correction_ft": round(-dL_total_ft, 4),
        "ct_length_ft": ct_length,
        "metal_area_in2": round(A_s, 4),
        "buoyed_weight_lb": round(W_buoyed, 0),
    }


def calculate_ct_fatigue(
    ct_od: float,
    wall_thickness: float,
    reel_diameter: float,
    internal_pressure: float = 0.0,
    yield_strength_psi: float = 80000.0,
    trips_history: Optional[List[Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Calculate CT fatigue life based on bending/pressure strains and Miner's rule.

    Based on API RP 5C7 low-cycle fatigue methodology:
    1. Bending strain on reel: eps_bend = OD / (2 × R_reel)
    2. Pressure strain: eps_pressure = P × ID / (2 × wall × E)
    3. Total strain: eps_total = eps_bend + eps_pressure
    4. Cycles to failure: N_f = C / eps_total^m  (S-N curve parameters)
    5. Miner's rule: D = Σ(n_i / N_f_i), failure at D ≥ 1.0

    Args:
        ct_od: CT outer diameter (inches)
        wall_thickness: CT wall thickness (inches)
        reel_diameter: guide arch / reel core diameter (inches, typical 72"–120")
        internal_pressure: treating pressure during bending (psi)
        yield_strength_psi: CT yield strength (psi)
        trips_history: list of {pressure_psi, cycles} for accumulated damage

    Returns:
        Dict with strain components, cycles to failure, remaining life
    """
    ct_id = ct_od - 2.0 * wall_thickness
    if ct_od <= 0 or wall_thickness <= 0 or ct_id <= 0 or reel_diameter <= 0:
        return {
            "error": "Invalid CT or reel dimensions",
            "strain_bending_pct": 0.0, "strain_pressure_pct": 0.0,
            "strain_total_pct": 0.0, "cycles_to_failure": 0,
            "remaining_life_pct": 0.0,
        }

    E = 30e6  # psi

    # 1. Bending strain
    eps_bending = ct_od / (2.0 * (reel_diameter / 2.0))

    # 2. Pressure strain (hoop → axial via Poisson)
    eps_pressure = (internal_pressure * ct_id / (2.0 * wall_thickness * E)) if internal_pressure > 0 else 0.0

    eps_total = eps_bending + eps_pressure

    # S-N curve parameters (API RP 5C7)
    m = 2.5
    if yield_strength_psi >= 110000:
        C = 0.020
    elif yield_strength_psi >= 90000:
        C = 0.028
    else:
        C = 0.038  # CT-80 baseline

    N_f = max(int(C / (eps_total ** m)), 1) if eps_total > 0 else 999999

    # Miner's rule — accumulated damage
    damage_accumulated = 0.0
    damage_breakdown = []

    if trips_history:
        for entry in trips_history:
            p_hist = entry.get("pressure_psi", 0.0)
            n_cycles = entry.get("cycles", 0)
            eps_p_hist = (p_hist * ct_id / (2.0 * wall_thickness * E)) if p_hist > 0 else 0.0
            eps_hist = eps_bending + eps_p_hist
            if eps_hist > 0:
                N_f_hist = max(C / (eps_hist ** m), 1.0)
                damage_i = n_cycles / N_f_hist
            else:
                N_f_hist = 999999
                damage_i = 0.0
            damage_accumulated += damage_i
            damage_breakdown.append({
                "pressure_psi": p_hist,
                "cycles": n_cycles,
                "strain_pct": round(eps_hist * 100, 4),
                "Nf": int(max(N_f_hist, 1)) if eps_hist > 0 else 999999,
                "damage_fraction": round(damage_i, 6),
            })

    remaining_life_pct = max((1.0 - damage_accumulated) * 100.0, 0.0)
    remaining_cycles = int(N_f * (1.0 - damage_accumulated)) if N_f > 0 and damage_accumulated < 1.0 else 0

    return {
        "strain_bending_pct": round(eps_bending * 100, 4),
        "strain_pressure_pct": round(eps_pressure * 100, 4),
        "strain_total_pct": round(eps_total * 100, 4),
        "cycles_to_failure": N_f,
        "remaining_life_pct": round(remaining_life_pct, 2),
        "remaining_cycles_at_current_pressure": remaining_cycles,
        "damage_accumulated": round(damage_accumulated, 6),
        "damage_breakdown": damage_breakdown,
        "sn_parameters": {
            "C": C,
            "m": m,
            "grade_class": "CT-80" if yield_strength_psi < 90000 else "CT-90+",
        },
        "reel_diameter_in": reel_diameter,
        "internal_pressure_psi": internal_pressure,
    }
