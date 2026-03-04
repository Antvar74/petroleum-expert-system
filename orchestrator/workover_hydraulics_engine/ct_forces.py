"""
CT Forces — buoyed weight, drag, and snubbing force calculations.

References:
- Bourgoyne et al.: Applied Drilling Engineering (1986)
- ICoTA Coiled Tubing Manual
"""
import math
from typing import Dict, Any

from .ct_geometry import STEEL_WEIGHT_WATER


def calculate_ct_buoyed_weight(
    weight_per_ft: float,
    length: float,
    mud_weight: float,
    inclination: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate buoyed CT string weight considering inclination.

    Args:
        weight_per_ft: CT weight (lb/ft)
        length: CT length in hole (ft)
        mud_weight: fluid density (ppg)
        inclination: average inclination (degrees)

    Returns:
        Dict with air_weight, buoyancy_factor, buoyed_weight, axial_component
    """
    if length <= 0 or weight_per_ft <= 0:
        return {
            "air_weight_lb": 0.0,
            "buoyancy_factor": 1.0,
            "buoyed_weight_lb": 0.0,
            "axial_component_lb": 0.0,
        }

    bf = max(1.0 - (mud_weight / STEEL_WEIGHT_WATER), 0.0)
    air_weight = weight_per_ft * length
    buoyed_weight = air_weight * bf
    axial_component = buoyed_weight * math.cos(math.radians(inclination))

    return {
        "air_weight_lb": round(air_weight, 0),
        "buoyancy_factor": round(bf, 4),
        "buoyed_weight_lb": round(buoyed_weight, 0),
        "axial_component_lb": round(axial_component, 0),
    }


def calculate_ct_drag(
    buoyed_weight: float,
    inclination: float,
    friction_factor: float = 0.25,
) -> Dict[str, Any]:
    """
    Calculate CT drag force in wellbore.

    F_drag = mu × W_buoyed × sin(incl)

    Args:
        buoyed_weight: buoyed CT weight (lb)
        inclination: average inclination (degrees)
        friction_factor: wellbore friction coefficient (0.15–0.40)

    Returns:
        Dict with drag_force, normal_force, friction_factor
    """
    incl_rad = math.radians(inclination)
    normal_force = buoyed_weight * math.sin(incl_rad)
    drag_force = friction_factor * normal_force

    return {
        "drag_force_lb": round(drag_force, 0),
        "normal_force_lb": round(normal_force, 0),
        "friction_factor": friction_factor,
    }


def calculate_snubbing_force(
    wellhead_pressure: float,
    ct_od: float,
    buoyed_weight: float,
    ct_length_in_hole: float,
    weight_per_ft: float,
    mud_weight: float,
) -> Dict[str, Any]:
    """
    Calculate snubbing force for CT operations under pressure.

    F_snub = P_wellhead × A_pipe - W_buoyed
    Light point: when F_snub = 0 (pipe weight = pressure force)

    Args:
        wellhead_pressure: surface pressure (psi)
        ct_od: CT outer diameter (inches)
        buoyed_weight: total buoyed weight in hole (lb)
        ct_length_in_hole: CT length in hole (ft)
        weight_per_ft: CT weight (lb/ft)
        mud_weight: fluid density (ppg)

    Returns:
        Dict with snubbing_force, pipe_light status, light_heavy_point
    """
    pipe_area = math.pi / 4.0 * ct_od ** 2
    pressure_force = wellhead_pressure * pipe_area
    snubbing_force = pressure_force - buoyed_weight
    pipe_light = snubbing_force > 0

    bf = 1.0 - (mud_weight / STEEL_WEIGHT_WATER)
    buoyed_weight_per_ft = weight_per_ft * max(bf, 0.01)
    light_heavy_depth = (pressure_force / buoyed_weight_per_ft) if buoyed_weight_per_ft > 0 else 0.0

    return {
        "snubbing_force_lb": round(snubbing_force, 0),
        "pressure_force_lb": round(pressure_force, 0),
        "buoyed_weight_lb": round(buoyed_weight, 0),
        "pipe_light": pipe_light,
        "light_heavy_depth_ft": round(light_heavy_depth, 0),
        "wellhead_pressure_psi": wellhead_pressure,
    }
