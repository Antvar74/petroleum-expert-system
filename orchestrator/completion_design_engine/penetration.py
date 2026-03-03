"""
Completion Design Engine — perforation penetration depth corrections.

Reference: API RP 19B: Evaluation of Well Perforators (Berea correction factors)
"""
from typing import Dict, Any


def calculate_penetration_depth(
    penetration_berea_in: float,
    effective_stress_psi: float = 0.0,
    temperature_f: float = 200.0,
    completion_fluid: str = "brine",
    cement_strength_psi: float = 3000.0,
    casing_thickness_in: float = 0.50,
) -> Dict[str, Any]:
    """
    Calculate corrected perforation penetration depth per API RP 19B.

    P_corrected = P_berea × CF_stress × CF_temp × CF_fluid × CF_cement × CF_casing

    Args:
        penetration_berea_in: penetration in Berea sandstone (inches) from gun spec
        effective_stress_psi: net confining stress (overburden - pore pressure)
        temperature_f: bottomhole temperature (°F)
        completion_fluid: type of fluid ("brine", "oil_based", "acid", "completion")
        cement_strength_psi: compressive strength of cement (psi)
        casing_thickness_in: casing wall thickness (inches)

    Returns:
        Dict with corrected penetration, correction factors, entry hole
    """
    # CF_stress: Higher stress reduces penetration (API RP 19B Section 5)
    if effective_stress_psi <= 0:
        cf_stress = 1.0
    elif effective_stress_psi < 3000:
        cf_stress = 1.0 - 0.05 * (effective_stress_psi / 3000)
    elif effective_stress_psi < 10000:
        cf_stress = 0.95 - 0.20 * ((effective_stress_psi - 3000) / 7000)
    else:
        cf_stress = max(0.60, 0.75 - 0.15 * ((effective_stress_psi - 10000) / 10000))

    # CF_temp: Temperature affects shaped charge jet
    if temperature_f < 200:
        cf_temp = 1.02
    elif temperature_f < 350:
        cf_temp = 1.02 - 0.07 * ((temperature_f - 200) / 150)
    elif temperature_f < 500:
        cf_temp = 0.95 - 0.10 * ((temperature_f - 350) / 150)
    else:
        cf_temp = max(0.80, 0.85 - 0.05 * ((temperature_f - 500) / 200))

    # CF_fluid: Completion fluid viscosity/density affects tunnel cleanup
    fluid_factors = {
        "brine": 0.95, "acid": 1.00, "oil_based": 0.80,
        "completion": 0.90, "water": 0.95, "diesel": 0.75,
    }
    cf_fluid = fluid_factors.get(completion_fluid.lower(), 0.90)

    # CF_cement: Higher cement strength slightly restricts penetration
    if cement_strength_psi < 2000:
        cf_cement = 1.0
    elif cement_strength_psi < 5000:
        cf_cement = 1.0 - 0.03 * ((cement_strength_psi - 2000) / 3000)
    else:
        cf_cement = max(0.93, 0.97 - 0.04 * ((cement_strength_psi - 5000) / 5000))

    # CF_casing: Thicker casing absorbs more jet energy
    if casing_thickness_in < 0.3:
        cf_casing = 1.0
    elif casing_thickness_in < 0.6:
        cf_casing = 1.0 - 0.05 * ((casing_thickness_in - 0.3) / 0.3)
    else:
        cf_casing = max(0.90, 0.95 - 0.05 * ((casing_thickness_in - 0.6) / 0.4))

    # Total correction
    cf_total = cf_stress * cf_temp * cf_fluid * cf_cement * cf_casing
    penetration_corrected = penetration_berea_in * cf_total

    # Entry hole estimate (roughly 10% of Berea penetration length)
    entry_hole_berea = penetration_berea_in * 0.10
    entry_hole_corrected = entry_hole_berea * cf_stress * cf_cement

    return {
        "penetration_berea_in": round(penetration_berea_in, 2),
        "penetration_corrected_in": round(penetration_corrected, 2),
        "penetration_corrected_ft": round(penetration_corrected / 12, 3),
        "entry_hole_corrected_in": round(entry_hole_corrected, 3),
        "correction_factors": {
            "cf_stress": round(cf_stress, 3),
            "cf_temperature": round(cf_temp, 3),
            "cf_fluid": round(cf_fluid, 3),
            "cf_cement": round(cf_cement, 3),
            "cf_casing": round(cf_casing, 3),
            "cf_total": round(cf_total, 3),
        },
        "efficiency_pct": round(cf_total * 100, 1),
    }
