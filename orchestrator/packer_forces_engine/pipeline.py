"""
Pipeline — orchestrates all packer forces sub-calculations.

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Mitchell, R. & Samuel, R. (2009): How Good Is the Thin Shell Approximation
"""
import math
from typing import Dict, Any

from .geometry import calculate_tubing_areas, STEEL_ALPHA, STEEL_DENSITY_PPG
from .forces import (
    calculate_piston_force,
    calculate_ballooning_force,
    calculate_temperature_force,
    calculate_tubing_movement,
)
from .buckling import calculate_helical_buckling_load


def calculate_total_packer_force(
    tubing_od: float,
    tubing_id: float,
    tubing_weight: float,
    tubing_length: float,
    seal_bore_id: float,
    initial_tubing_pressure: float,
    final_tubing_pressure: float,
    initial_annulus_pressure: float,
    final_annulus_pressure: float,
    initial_temperature: float,
    final_temperature: float,
    packer_depth_tvd: float,
    mud_weight_tubing: float = 8.34,
    mud_weight_annulus: float = 8.34,
    poisson_ratio: float = 0.30,
    thermal_expansion: float = STEEL_ALPHA,
) -> Dict[str, Any]:
    """
    Complete packer force analysis — combines all effects.

    Calculates piston, ballooning, and temperature force components,
    tubing movements, and performs buckling check.

    Args:
        tubing_od: tubing outer diameter (in)
        tubing_id: tubing inner diameter (in)
        tubing_weight: air weight per foot (lb/ft)
        tubing_length: tubing length (ft)
        seal_bore_id: packer seal bore inner diameter (in)
        initial_tubing_pressure: surface tubing pressure before operation (psi)
        final_tubing_pressure: surface tubing pressure after operation (psi)
        initial_annulus_pressure: surface annulus pressure before operation (psi)
        final_annulus_pressure: surface annulus pressure after operation (psi)
        initial_temperature: average tubing temperature before (°F)
        final_temperature: average tubing temperature after (°F)
        packer_depth_tvd: packer true vertical depth (ft)
        mud_weight_tubing: tubing fluid density (ppg)
        mud_weight_annulus: annulus fluid density (ppg)
        poisson_ratio: Poisson's ratio (default 0.30)
        thermal_expansion: thermal expansion coefficient (1/°F)

    Returns:
        Dict with summary, force_components, movements, parameters, alerts.
    """
    # Areas
    areas = calculate_tubing_areas(tubing_od, tubing_id)
    ao = areas["ao_in2"]
    ai = areas["ai_in2"]
    a_steel = areas["as_in2"]

    seal_area = math.pi * (seal_bore_id / 2.0) ** 2

    # Hydrostatic pressures at packer (P_surface + 0.052 × MW × TVD)
    p_below_initial = initial_tubing_pressure + 0.052 * mud_weight_tubing * packer_depth_tvd
    p_below_final = final_tubing_pressure + 0.052 * mud_weight_tubing * packer_depth_tvd
    p_above_initial = initial_annulus_pressure + 0.052 * mud_weight_annulus * packer_depth_tvd
    p_above_final = final_annulus_pressure + 0.052 * mud_weight_annulus * packer_depth_tvd

    # 1. Piston force (change from initial to final)
    f_piston_initial = calculate_piston_force(p_below_initial, p_above_initial, seal_area, ao, ai)
    f_piston_final = calculate_piston_force(p_below_final, p_above_final, seal_area, ao, ai)
    delta_f_piston = f_piston_final - f_piston_initial

    # 2. Ballooning force
    delta_pi = final_tubing_pressure - initial_tubing_pressure
    delta_po = final_annulus_pressure - initial_annulus_pressure
    f_ballooning = calculate_ballooning_force(delta_pi, delta_po, ai, ao, poisson_ratio)

    # 3. Temperature force
    # Scale ΔT by depth fraction: packer at shallower depth experiences less thermal stress
    # (average temperature change from surface to packer < change from surface to TD)
    depth_ratio = min(packer_depth_tvd / tubing_length, 1.0) if tubing_length > 0 else 1.0
    delta_t = (final_temperature - initial_temperature) * depth_ratio
    f_temperature = calculate_temperature_force(delta_t, a_steel, thermal_expansion=thermal_expansion)

    # Total force change
    total_force = delta_f_piston + f_ballooning + f_temperature

    # Movements (if packer allows motion)
    dl_piston = calculate_tubing_movement(delta_f_piston, tubing_length, a_steel)
    dl_balloon = calculate_tubing_movement(f_ballooning, tubing_length, a_steel)
    dl_temp_free = -thermal_expansion * delta_t * tubing_length * 12.0  # free thermal expansion (inches)
    dl_total = dl_piston + dl_balloon + dl_temp_free

    # Buckling check
    # Effective buoyancy factor: accounts for different internal (tubing) and external (annulus) fluid densities
    # BF_eff = 1 - (MW_ann*Ao - MW_tub*Ai) / (steel_density*As)   [Archimedes hollow tube]
    bf_eff = 1.0 - (mud_weight_annulus * ao - mud_weight_tubing * ai) / (STEEL_DENSITY_PPG * a_steel)
    buoyed_weight = tubing_weight * max(bf_eff, 0.01)
    f_buckling_critical = calculate_helical_buckling_load(
        tubing_od, tubing_id, buoyed_weight, seal_bore_id
    )

    buckling_status = "OK"
    if total_force < 0 and abs(total_force) > f_buckling_critical:
        buckling_status = "Helical Buckling"
    elif total_force < 0 and abs(total_force) > f_buckling_critical * 0.5:
        buckling_status = "Sinusoidal Buckling"

    # Alerts
    alerts = []
    if buckling_status != "OK":
        alerts.append(
            f"{buckling_status} predicted — compressive force {abs(total_force):.0f} lbs "
            f"exceeds critical {f_buckling_critical:.0f} lbs"
        )
    if abs(dl_total) > 6.0:
        alerts.append(f"Large tubing movement {dl_total:.2f} inches — verify seal stroke length")
    if total_force > 0 and total_force > 0.6 * 80000 * a_steel:  # 80 ksi yield approx
        alerts.append(f"High tension {total_force:.0f} lbs — verify tubing connection rating")
    if delta_t > 100:
        alerts.append(f"Large temperature change ΔT={delta_t:.0f}°F — significant thermal effects")

    summary = {
        "total_force_lbs": round(total_force, 0),
        "force_direction": "Tension" if total_force > 0 else "Compression",
        "piston_force_lbs": round(delta_f_piston, 0),
        "ballooning_force_lbs": round(f_ballooning, 0),
        "temperature_force_lbs": round(f_temperature, 0),
        "total_movement_inches": round(dl_total, 3),
        "movement_piston_in": round(dl_piston, 3),
        "movement_balloon_in": round(dl_balloon, 3),
        "movement_thermal_in": round(dl_temp_free, 3),
        "buckling_status": buckling_status,
        "buckling_critical_load_lbs": round(f_buckling_critical, 0),
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "force_components": {
            "piston": round(delta_f_piston, 0),
            "ballooning": round(f_ballooning, 0),
            "temperature": round(f_temperature, 0),
            "total": round(total_force, 0),
        },
        "movements": {
            "piston_in": round(dl_piston, 3),
            "ballooning_in": round(dl_balloon, 3),
            "thermal_in": round(dl_temp_free, 3),
            "total_in": round(dl_total, 3),
        },
        "parameters": {
            "tubing_od_in": tubing_od,
            "tubing_id_in": tubing_id,
            "tubing_weight_lbft": tubing_weight,
            "tubing_length_ft": tubing_length,
            "seal_bore_id_in": seal_bore_id,
            "packer_depth_tvd_ft": packer_depth_tvd,
            "delta_t_f": delta_t,
            "delta_pi_psi": delta_pi,
            "delta_po_psi": delta_po,
        },
        "alerts": alerts,
    }
