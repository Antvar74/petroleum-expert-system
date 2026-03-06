"""
Hydraulics Engine — Bit Hydraulics.

TFA, pressure drop, HSI, impact force, jet velocity.

References:
- Bourgoyne et al., Applied Drilling Engineering (SPE Textbook)
"""
import math
from typing import Dict, Any, List

# Discharge coefficient for bit nozzles
CD = 0.95


def calculate_bit_hydraulics(
    flow_rate: float,
    mud_weight: float,
    nozzle_sizes: List[float],
    total_system_loss: float = 0.0
) -> Dict[str, Any]:
    """
    Calculate bit hydraulics: TFA, pressure drop, HSI, impact force, jet velocity.

    Parameters:
    - nozzle_sizes: list of nozzle sizes in 32nds of an inch
    - total_system_loss: total pressure loss in the system excluding bit (psi)
    """
    if not nozzle_sizes or flow_rate <= 0:
        return {"error": "Missing nozzle data or flow rate"}

    # Total Flow Area
    tfa = 0.0
    for noz in nozzle_sizes:
        d_inches = noz / 32.0
        tfa += math.pi / 4.0 * d_inches**2

    if tfa <= 0:
        return {"error": "Zero TFA"}

    # Bit pressure drop: dP = 8.311e-5 * MW * Q² / (Cd² * TFA²)
    dp_bit = 8.311e-5 * mud_weight * flow_rate**2 / (CD**2 * tfa**2)

    # Nozzle velocity: Vn = Q / (3.117 * TFA)
    vn = flow_rate / (3.117 * tfa)

    # Hydraulic horsepower at bit
    hhp_bit = dp_bit * flow_rate / 1714.0

    # Bit diameter estimate (largest nozzle ring)
    max_noz = max(nozzle_sizes) / 32.0
    bit_area = math.pi / 4.0 * (max_noz * 4)**2  # rough estimate

    # HSI = HHP / bit_area (use standard bit sizes)
    # Common bit diameters based on nozzle count
    bit_diameters = {3: 8.5, 4: 8.5, 5: 12.25, 6: 12.25, 7: 17.5}
    n_noz = len(nozzle_sizes)
    bit_dia = bit_diameters.get(n_noz, 8.5)
    bit_area_actual = math.pi / 4.0 * bit_dia**2
    hsi = hhp_bit / bit_area_actual

    # Impact force: Fi = 0.01823 * Cd * Q * sqrt(MW * dP_bit)
    impact_force = 0.01823 * CD * flow_rate * math.sqrt(mud_weight * dp_bit)

    # Percent pressure at bit
    total_pressure = dp_bit + total_system_loss
    pct_at_bit = (dp_bit / total_pressure * 100.0) if total_pressure > 0 else 0

    return {
        "tfa_sqin": round(tfa, 4),
        "pressure_drop_psi": round(dp_bit, 0),
        "jet_velocity_fps": round(vn, 0),
        "hhp_bit": round(hhp_bit, 1),
        "hsi": round(hsi, 2),
        "impact_force_lb": round(impact_force, 0),
        "nozzle_count": n_noz,
        "nozzle_sizes_32nds": nozzle_sizes,
        "percent_at_bit": round(pct_at_bit, 1),
        "bit_diameter_assumed": bit_dia
    }
