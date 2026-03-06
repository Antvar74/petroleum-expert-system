"""
Hydraulics Engine — Surge & Swab Pressure Calculation.

References:
- Bourgoyne et al., Applied Drilling Engineering (SPE Textbook)
- Burkhardt, J.A. (1961): Wellbore Pressure Surges Produced by Pipe Movement
"""
import math
from typing import Dict, Any

from .rheology import pressure_loss_bingham


def calculate_surge_swab(
    mud_weight: float,
    pv: float,
    yp: float,
    tvd: float,
    pipe_od: float,
    pipe_id: float,
    hole_id: float,
    pipe_velocity_fpm: float,
    pipe_open: bool = True
) -> Dict[str, Any]:
    """
    Calculate surge and swab pressures (Bourgoyne model).

    Parameters:
    - pipe_velocity_fpm: tripping speed in ft/min (positive = running in / surge)
    - pipe_open: True if pipe is open-ended, False if closed
    """
    if tvd <= 0 or hole_id <= pipe_od:
        return {"error": "Invalid geometry"}

    # Clinging constant (Burkhardt)
    d_ratio = pipe_od / hole_id
    k_c = 0.45  # default clinging constant
    if d_ratio < 0.3:
        k_c = 0.3
    elif d_ratio > 0.7:
        k_c = 0.6

    # Effective velocity in annulus
    annular_area = math.pi / 4.0 * (hole_id**2 - pipe_od**2)
    pipe_displacement = math.pi / 4.0 * pipe_od**2

    if pipe_open:
        # Open pipe: fluid flows through pipe and annulus
        pipe_area_inner = math.pi / 4.0 * pipe_id**2
        flow_area = annular_area + pipe_area_inner
        v_eff = abs(pipe_velocity_fpm) * pipe_displacement / annular_area * k_c
    else:
        # Closed pipe: all displacement goes to annulus
        v_eff = abs(pipe_velocity_fpm) * pipe_displacement / annular_area

    # Calculate annular pressure loss at this effective velocity
    # Using Bingham model for annular flow
    d_eff = hole_id - pipe_od
    if d_eff <= 0:
        return {"error": "Zero annular gap"}

    # Equivalent flow rate
    q_equiv = v_eff * (hole_id**2 - pipe_od**2) / 24.5

    if q_equiv > 0:
        result = pressure_loss_bingham(
            flow_rate=q_equiv,
            mud_weight=mud_weight,
            pv=pv, yp=yp,
            length=tvd,  # approximate — full string length
            od=hole_id,
            id_inner=pipe_od,
            is_annular=True
        )
        surge_pressure = result["pressure_loss_psi"]
    else:
        surge_pressure = 0.0

    # Convert to EMW
    surge_emw = surge_pressure / (0.052 * tvd) if tvd > 0 else 0
    swab_emw = surge_emw  # magnitude is same, direction differs

    surge_ecd = mud_weight + surge_emw
    swab_ecd = mud_weight - swab_emw

    # Safety margins
    surge_margin = "OK"
    swab_margin = "OK"

    if surge_emw > 0.5:
        surge_margin = "WARNING — Risk of losses"
    if surge_emw > 1.0:
        surge_margin = "CRITICAL — Likely fracturing"

    if swab_emw > 0.3:
        swab_margin = "WARNING — Risk of kick/influx"
    if swab_emw > 0.5:
        swab_margin = "CRITICAL — Likely swabbing in formation fluid"

    return {
        "surge_pressure_psi": round(surge_pressure, 0),
        "swab_pressure_psi": round(surge_pressure, 0),
        "surge_emw_ppg": round(surge_emw, 2),
        "swab_emw_ppg": round(swab_emw, 2),
        "surge_ecd_ppg": round(surge_ecd, 2),
        "swab_ecd_ppg": round(swab_ecd, 2),
        "effective_velocity_fpm": round(v_eff, 1),
        "clinging_constant": k_c,
        "pipe_velocity_fpm": abs(pipe_velocity_fpm),
        "pipe_status": "open" if pipe_open else "closed",
        "surge_margin": surge_margin,
        "swab_margin": swab_margin
    }
