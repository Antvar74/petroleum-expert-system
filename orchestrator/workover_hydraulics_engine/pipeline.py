"""
Pipeline — orchestrates all workover hydraulics sub-calculations.
"""
from typing import Dict, Any

from .ct_geometry import calculate_ct_dimensions
from .ct_hydraulics import calculate_ct_pressure_loss
from .ct_forces import calculate_ct_buoyed_weight, calculate_ct_drag, calculate_snubbing_force
from .ct_reach import calculate_max_reach
from .ct_kill import calculate_workover_kill
from .ct_mechanics import calculate_ct_elongation, calculate_ct_fatigue


def calculate_full_workover(
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    ct_od: float,
    wall_thickness: float,
    ct_length: float,
    hole_id: float,
    tvd: float,
    inclination: float = 0.0,
    friction_factor: float = 0.25,
    wellhead_pressure: float = 0.0,
    reservoir_pressure: float = 0.0,
    yield_strength_psi: float = 80000.0,
) -> Dict[str, Any]:
    """
    Complete workover hydraulics analysis combining all calculations.

    Returns:
        Dict with summary, hydraulics, forces, reach, kill_data, elongation, alerts
    """
    dims = calculate_ct_dimensions(ct_od, wall_thickness)
    if "error" in dims:
        return {"summary": {}, "alerts": [dims["error"]]}

    ct_id = dims["ct_id_in"]
    weight_per_ft = dims["weight_per_ft_lb"]

    hydraulics = calculate_ct_pressure_loss(
        flow_rate, mud_weight, pv, yp,
        ct_od, ct_id, ct_length, hole_id, ct_length,
    )

    weight_data = calculate_ct_buoyed_weight(weight_per_ft, ct_length, mud_weight, inclination)

    drag_data = calculate_ct_drag(weight_data["buoyed_weight_lb"], inclination, friction_factor)

    snubbing = calculate_snubbing_force(
        wellhead_pressure, ct_od,
        weight_data["buoyed_weight_lb"], ct_length,
        weight_per_ft, mud_weight,
    )

    reach = calculate_max_reach(
        ct_od, ct_id, wall_thickness, weight_per_ft,
        mud_weight, inclination, friction_factor,
        wellhead_pressure, yield_strength_psi,
    )

    kill_data = calculate_workover_kill(reservoir_pressure, tvd, mud_weight)

    elongation = calculate_ct_elongation(
        ct_od=ct_od, ct_id=ct_id, ct_length=ct_length,
        weight_per_ft=weight_per_ft, mud_weight=mud_weight,
        delta_p_internal=hydraulics["pipe_loss_psi"],
        delta_t=0.0,
        wellhead_pressure=wellhead_pressure,
        annular_pressure=0.0,
    )

    alerts = []
    if snubbing["pipe_light"]:
        alerts.append(f"CT is pipe-light! Snubbing force: {snubbing['snubbing_force_lb']:.0f} lb. Use snubbing unit.")
    if hydraulics["total_loss_psi"] > 5000:
        alerts.append(f"High total pressure loss: {hydraulics['total_loss_psi']:.0f} psi — verify CT pressure rating")
    if ct_length > reach["max_reach_ft"]:
        alerts.append(f"CT length {ct_length:.0f} ft exceeds max reach {reach['max_reach_ft']:.0f} ft — risk of helical buckling")
    if kill_data["status"].startswith("UNDERBALANCED"):
        alerts.append(f"Well is underbalanced! Kill weight required: {kill_data['kill_weight_ppg']:.2f} ppg")
    if hydraulics["pipe_velocity_ftmin"] > 600:
        alerts.append(f"High pipe velocity {hydraulics['pipe_velocity_ftmin']:.0f} ft/min — erosion risk in CT")
    if drag_data["drag_force_lb"] > weight_data["buoyed_weight_lb"] * 0.5:
        alerts.append("Drag force exceeds 50% of buoyed weight — consider friction reducer")
    if abs(elongation.get("dL_total_ft", 0)) > 5.0:
        alerts.append(f"Significant CT elongation: {elongation['dL_total_ft']:.2f} ft — adjust depth tags")

    summary = {
        "total_pressure_loss_psi": hydraulics["total_loss_psi"],
        "pipe_loss_psi": hydraulics["pipe_loss_psi"],
        "annular_loss_psi": hydraulics["annular_loss_psi"],
        "buoyed_weight_lb": weight_data["buoyed_weight_lb"],
        "drag_force_lb": drag_data["drag_force_lb"],
        "snubbing_force_lb": snubbing["snubbing_force_lb"],
        "pipe_light": snubbing["pipe_light"],
        "max_reach_ft": reach["max_reach_ft"],
        "kill_weight_ppg": kill_data["kill_weight_ppg"],
        "limiting_factor": reach["limiting_factor"],
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "hydraulics": hydraulics,
        "ct_dimensions": dims,
        "weight_analysis": weight_data,
        "drag_analysis": drag_data,
        "snubbing": snubbing,
        "max_reach": reach,
        "kill_data": kill_data,
        "elongation": elongation,
        "parameters": {
            "flow_rate_gpm": flow_rate,
            "mud_weight_ppg": mud_weight,
            "pv_cp": pv,
            "yp_lb100ft2": yp,
            "ct_od_in": ct_od,
            "wall_thickness_in": wall_thickness,
            "ct_length_ft": ct_length,
            "hole_id_in": hole_id,
            "tvd_ft": tvd,
            "inclination_deg": inclination,
            "friction_factor": friction_factor,
            "wellhead_pressure_psi": wellhead_pressure,
            "reservoir_pressure_psi": reservoir_pressure,
            "yield_strength_psi": yield_strength_psi,
        },
        "alerts": alerts,
    }
