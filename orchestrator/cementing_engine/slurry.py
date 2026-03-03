"""
Cementing Engine — temperature/pressure-dependent slurry properties.

References:
- API Spec 10A / 10B: Cement and slurry testing
- API RP 10B-2: BHCT correlation
"""
import math
from typing import Dict, Any


def correct_slurry_properties_pt(
    slurry_density_ppg: float,
    pv_slurry: float,
    yp_slurry: float,
    temperature_f: float,
    pressure_psi: float,
    ref_temperature_f: float = 80.0,
    ref_pressure_psi: float = 14.7,
    fluid_type: str = "wbm",
) -> Dict[str, Any]:
    """
    Correct slurry density and rheology for temperature and pressure.

    Reference: API Spec 10A/10B, API RP 10B-2
    - Density: rho(P,T) = rho_0 * [1 + Cp*(P-P0)] / [1 + Ct*(T-T0)]
    - Viscosity: PV(T) = PV_ref * exp(-alpha*(T-T_ref))
    """
    if fluid_type.lower() == "obm":
        Cp = 5.0e-6   # /psi
        Ct = 3.5e-4   # /°F
        alpha = 0.015
    else:
        Cp = 3.0e-6   # /psi
        Ct = 2.0e-4   # /°F
        alpha = 0.012

    dP = pressure_psi - ref_pressure_psi
    dT = temperature_f - ref_temperature_f

    rho_corrected = max(slurry_density_ppg * (1.0 + Cp * dP) / (1.0 + Ct * dT), 1.0)

    temp_factor = math.exp(-alpha * dT)
    pv_corrected = max(pv_slurry * temp_factor, 0.5)
    yp_corrected = max(yp_slurry * temp_factor, 0.1)

    return {
        "density_corrected_ppg": round(rho_corrected, 2),
        "pv_corrected": round(pv_corrected, 1),
        "yp_corrected": round(yp_corrected, 1),
        "density_change_ppg": round(rho_corrected - slurry_density_ppg, 3),
        "temperature_f": temperature_f,
        "pressure_psi": pressure_psi,
        "temp_factor": round(temp_factor, 4),
    }


def estimate_bhct(
    well_depth_ft: float,
    surface_temperature_f: float = 70.0,
    geothermal_gradient_f_per_100ft: float = 1.2,
    circulation_time_hrs: float = 4.0,
) -> Dict[str, Any]:
    """
    Estimate Bottom Hole Circulating Temperature (BHCT).

    Correlation: API RP 10B-2 — BHCT < BHST due to cooling by circulation.
    BHST = T_surface + gradient * depth
    BHCT = BHST * cooling_factor (typ 0.60–0.85 depending on circ time)
    """
    bhst = surface_temperature_f + geothermal_gradient_f_per_100ft * well_depth_ft / 100.0

    # Empirical: f = 0.85 - 0.03 * ln(t_hrs + 1)
    cooling_factor = 0.85 - 0.03 * math.log(max(circulation_time_hrs, 0.1) + 1.0)
    cooling_factor = max(min(cooling_factor, 0.95), 0.55)

    bhct = surface_temperature_f + (bhst - surface_temperature_f) * cooling_factor

    return {
        "bhst_f": round(bhst, 1),
        "bhct_f": round(bhct, 1),
        "cooling_factor": round(cooling_factor, 3),
        "surface_temperature_f": surface_temperature_f,
        "geothermal_gradient_f_per_100ft": geothermal_gradient_f_per_100ft,
    }
