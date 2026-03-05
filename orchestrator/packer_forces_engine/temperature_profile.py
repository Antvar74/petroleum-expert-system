"""
Depth-varying temperature force calculation.

Uses a trapezoidal integration of the temperature difference profile
instead of a uniform average ΔT, which is more accurate for deviated
wells and production scenarios.

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Adams, A.J. & MacEachran, A. (1994): Impact on Casing Design of Thermal Expansion
"""
import math
from typing import Dict, Any, List

from .geometry import STEEL_E, STEEL_ALPHA


def calculate_temperature_force_profile(
    initial_t_profile: List[Dict[str, float]],
    production_t_profile: List[Dict[str, float]],
    tubing_od: float = 3.5,
    tubing_id: float = 2.992,
    youngs_modulus: float = STEEL_E,
    thermal_expansion: float = STEEL_ALPHA,
) -> Dict[str, Any]:
    """
    Calculate temperature force using depth-varying temperature profile
    instead of uniform delta-T.

    F_temp = E * A_s * alpha * integral(delta_T(z))dz / L

    The integral captures depth-varying temperature difference, which is
    more accurate than a single average delta-T for deviated wells and
    production scenarios.

    Args:
        initial_t_profile: list of {depth_ft, temperature_f} -- initial state
        production_t_profile: list of {depth_ft, temperature_f} -- final state
        tubing_od, tubing_id: tubing dimensions (in)
        youngs_modulus: Young's modulus (psi)
        thermal_expansion: thermal expansion coefficient (1/°F)

    Returns:
        Dict with force, delta-T profile, average delta-T, max delta-T.
    """
    if not initial_t_profile or not production_t_profile:
        return {"error": "Temperature profiles must be provided"}

    a_steel = math.pi * (tubing_od ** 2 - tubing_id ** 2) / 4.0

    delta_t_profile = []
    dt_integral = 0.0
    max_dt = -1e9
    min_dt = 1e9

    for i, prod_pt in enumerate(production_t_profile):
        depth = prod_pt.get("depth_ft", 0)
        t_prod = prod_pt.get("temperature_f", 0)

        # Linear interpolation in initial profile
        t_init = 0.0
        for j in range(len(initial_t_profile) - 1):
            d1 = initial_t_profile[j].get("depth_ft", 0)
            d2 = initial_t_profile[j + 1].get("depth_ft", 0)
            if d1 <= depth <= d2 and d2 > d1:
                frac = (depth - d1) / (d2 - d1)
                t1 = initial_t_profile[j].get("temperature_f", 0)
                t2 = initial_t_profile[j + 1].get("temperature_f", 0)
                t_init = t1 + frac * (t2 - t1)
                break
        else:
            if depth <= initial_t_profile[0].get("depth_ft", 0):
                t_init = initial_t_profile[0].get("temperature_f", 0)
            else:
                t_init = initial_t_profile[-1].get("temperature_f", 0)

        dt = t_prod - t_init
        delta_t_profile.append({
            "depth_ft": depth,
            "t_initial_f": round(t_init, 1),
            "t_production_f": round(t_prod, 1),
            "delta_t_f": round(dt, 1),
        })
        max_dt = max(max_dt, dt)
        min_dt = min(min_dt, dt)

        # Trapezoidal integration
        if i > 0:
            d_prev = production_t_profile[i - 1].get("depth_ft", 0)
            dt_prev = delta_t_profile[i - 1]["delta_t_f"]
            dz = (depth - d_prev) * 12.0  # inches
            dt_integral += 0.5 * (dt_prev + dt) * dz

    # Total tubing length
    total_length_ft = (
        production_t_profile[-1].get("depth_ft", 0) - production_t_profile[0].get("depth_ft", 0)
        if len(production_t_profile) >= 2 else 0.0
    )
    total_length_in = total_length_ft * 12.0
    delta_t_avg = dt_integral / total_length_in if total_length_in > 0 else 0.0

    # Force: F = -E * A_s * alpha * delta_T_avg (for anchored packer)
    force_temp = -youngs_modulus * a_steel * thermal_expansion * delta_t_avg

    # Free thermal expansion
    free_expansion_in = thermal_expansion * delta_t_avg * total_length_in

    return {
        "force_temperature_lbs": round(force_temp, 0),
        "delta_t_avg_f": round(delta_t_avg, 1),
        "delta_t_max_f": round(max_dt, 1),
        "delta_t_min_f": round(min_dt, 1),
        "free_expansion_in": round(free_expansion_in, 3),
        "tubing_length_ft": round(total_length_ft, 1),
        "delta_t_profile": delta_t_profile,
        "method": "Depth-varying temperature integral",
    }
