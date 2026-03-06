"""
Hydraulics Engine — Pressure/Temperature Corrections.

References:
- API RP 13D: Rheology and Hydraulics of Oil-Well Drilling Fluids
"""
import math
from typing import Dict, Any, List


def correct_density_pt(
    rho_surface: float, pressure: float, temperature: float,
    fluid_type: str = "wbm",
    p_ref: float = 14.7, t_ref: float = 70.0
) -> Dict[str, Any]:
    """
    Correct mud density for pressure and temperature effects.

    rho(P,T) = rho_0 * [1 + Cp*(P - P0)] * [1 / (1 + Ct*(T - T0))]

    Parameters:
    - rho_surface: surface mud density (ppg)
    - pressure: local pressure (psi)
    - temperature: local temperature (°F)
    - fluid_type: 'wbm' (water-based) or 'obm' (oil-based)
    - p_ref, t_ref: reference conditions (default: atmospheric, 70°F)

    Returns:
    - rho_corrected: corrected density (ppg)
    - pressure_effect, temperature_effect: individual contributions
    """
    if rho_surface <= 0:
        return {"rho_corrected": 0.0, "pressure_effect_ppg": 0.0,
                "temperature_effect_ppg": 0.0, "fluid_type": fluid_type}

    # Compressibility and thermal expansion coefficients (API RP 13D)
    if fluid_type.lower() == "obm":
        cp = 5.0e-6   # compressibility (/psi) — OBM more compressible
        ct = 3.5e-4   # thermal expansion (/°F) — OBM expands more
    else:
        cp = 3.0e-6   # compressibility (/psi) — WBM
        ct = 2.0e-4   # thermal expansion (/°F) — WBM

    # Density correction
    pressure_factor = 1.0 + cp * (pressure - p_ref)
    temp_factor = 1.0 + ct * (temperature - t_ref)
    temp_factor = max(temp_factor, 0.5)  # Guard against extreme cooling

    rho_corrected = rho_surface * pressure_factor / temp_factor

    return {
        "rho_corrected": round(rho_corrected, 4),
        "pressure_effect_ppg": round(rho_surface * (pressure_factor - 1.0), 4),
        "temperature_effect_ppg": round(rho_surface * (1.0 - 1.0 / temp_factor), 4),
        "fluid_type": fluid_type
    }


def correct_viscosity_pt(
    pv_surface: float, temperature: float,
    t_ref: float = 120.0, alpha: float = 0.015
) -> Dict[str, Any]:
    """
    Correct plastic viscosity for temperature using Arrhenius-type model.

    PV(T) = PV_ref * exp(-alpha * (T - T_ref))

    Parameters:
    - pv_surface: PV at reference temperature (cP)
    - temperature: local temperature (°F)
    - t_ref: reference temperature (°F), default 120°F
    - alpha: temperature sensitivity coefficient (1/°F)

    Returns:
    - pv_corrected: corrected PV (cP)
    - correction_factor: multiplicative factor applied
    """
    if pv_surface <= 0:
        return {"pv_corrected": 0.0, "correction_factor": 1.0,
                "temperature_f": temperature}

    delta_t = temperature - t_ref
    factor = math.exp(-alpha * delta_t)
    factor = max(0.2, min(factor, 5.0))  # Physical bounds

    return {
        "pv_corrected": round(pv_surface * factor, 2),
        "correction_factor": round(factor, 4),
        "temperature_f": temperature
    }


def calculate_temperature_profile(
    t_surface: float, gradient: float, depths: List[float]
) -> List[Dict[str, Any]]:
    """
    Calculate temperature at each depth using a linear geothermal gradient.

    T(z) = T_surface + gradient * z

    Parameters:
    - t_surface: surface/mudline temperature (°F)
    - gradient: geothermal gradient (°F per ft, typical 1.0-1.5 per 100ft → 0.01-0.015)
    - depths: list of TVDs (ft)

    Returns:
    - list of {depth, temperature} dicts
    """
    return [
        {"depth_ft": round(d, 1),
         "temperature_f": round(t_surface + gradient * d, 2)}
        for d in depths
    ]
