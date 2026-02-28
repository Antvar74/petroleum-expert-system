"""Petrophysical calculations: porosity, Vshale, water saturation models."""
import math
from typing import Dict, Any


def calculate_porosity(
    rhob: float,
    nphi: float,
    rho_matrix: float = 2.65,
    rho_fluid: float = 1.0,
    gas_correction: bool = False,
    rho_gas: float = 0.2
) -> Dict[str, Any]:
    """
    Density-neutron crossplot porosity.

    phi = sqrt((phi_D^2 + phi_N^2) / 2)
    where phi_D = (rho_ma - rhob) / (rho_ma - rho_fl)

    When gas_correction is enabled and a DN crossover is detected
    (phi_density > phi_neutron), the density porosity is recalculated
    using a lighter effective fluid density (rho_gas) to account for
    gas in the invaded zone, and the RMS combination is recomputed.

    Args:
        rhob: bulk density (g/cc)
        nphi: neutron porosity (v/v fraction)
        rho_matrix: matrix density (g/cc), default 2.65 sandstone
        rho_fluid: fluid density (g/cc), default 1.0
        gas_correction: if True, apply gas correction when DN crossover
            is detected (default False)
        rho_gas: gas density (g/cc) for invaded-zone correction,
            default 0.2 (methane at reservoir conditions)

    Returns:
        Dict with phi, phi_density, phi_neutron, method.
        When gas correction is applied the dict also includes
        phi_density_gas_corrected and gas_flag.
    """
    denom = rho_matrix - rho_fluid
    if denom == 0:
        return {"error": "Matrix and fluid densities are equal"}

    phi_d = (rho_matrix - rhob) / denom
    phi_n = nphi

    # Gas correction: DN crossover indicates gas presence
    if gas_correction and phi_d > phi_n:
        # Recalculate density porosity with gas density as effective fluid
        rho_fluid_eff = rho_gas
        denom_gas = rho_matrix - rho_fluid_eff
        if denom_gas == 0:
            return {"error": "Matrix and gas densities are equal"}
        phi_d_gas = (rho_matrix - rhob) / denom_gas
        phi = math.sqrt((phi_d_gas ** 2 + phi_n ** 2) / 2.0)
        phi = max(0.0, min(phi, 0.50))
        return {
            "phi": round(phi, 4),
            "phi_density": round(phi_d, 4),
            "phi_density_gas_corrected": round(phi_d_gas, 4),
            "phi_neutron": round(phi_n, 4),
            "method": "density_neutron_rms_crossplot_gas_corrected",
            "gas_flag": True,
        }

    # RMS crossplot
    phi = math.sqrt((phi_d ** 2 + phi_n ** 2) / 2.0)

    # Clamp to physically reasonable range
    phi = max(0.0, min(phi, 0.50))

    return {
        "phi": round(phi, 4),
        "phi_density": round(phi_d, 4),
        "phi_neutron": round(phi_n, 4),
        "method": "density_neutron_rms_crossplot",
    }


def calculate_vshale(
    gr_value: float,
    gr_clean: float = 20.0,
    gr_shale: float = 120.0,
    method: str = "larionov_tertiary"
) -> Dict[str, Any]:
    """
    Volume of shale from gamma ray.

    Linear (IGR): Vsh = (GR - GR_clean) / (GR_shale - GR_clean)
    Larionov Tertiary: Vsh = 0.083 * (2^(3.7 * IGR) - 1)
    Clavier (1971): Vsh = 1.7 - sqrt(3.38 - (IGR + 0.7)^2)

    Args:
        gr_value: gamma ray reading (API)
        gr_clean: clean-sand GR baseline (API)
        gr_shale: pure-shale GR baseline (API)
        method: "linear", "larionov_tertiary", or "clavier"

    Returns:
        Dict with vsh, igr, method used
    """
    denom = gr_shale - gr_clean
    if denom <= 0:
        return {"error": "GR_shale must be greater than GR_clean"}

    igr = (gr_value - gr_clean) / denom
    igr = max(0.0, min(igr, 1.0))

    if method == "linear":
        vsh = igr
    elif method == "clavier":
        # Clavier (1971) correction
        vsh = 1.7 - math.sqrt(3.38 - (igr + 0.7) ** 2)
    else:
        # Larionov Tertiary correction
        vsh = 0.083 * (2.0 ** (3.7 * igr) - 1.0)

    vsh = max(0.0, min(vsh, 1.0))

    return {
        "vsh": round(vsh, 4),
        "igr": round(igr, 4),
        "method": method,
    }


def calculate_water_saturation(
    rt: float,
    porosity: float,
    rw: float = 0.05,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0
) -> Dict[str, Any]:
    """
    Archie (1942) water saturation.

    Sw^n = (a * Rw) / (Rt * phi^m)
    Sw   = ((a * Rw) / (Rt * phi^m))^(1/n)

    Args:
        rt: true (deep) resistivity (ohm-m)
        porosity: total porosity (v/v fraction)
        rw: formation water resistivity (ohm-m)
        a: tortuosity factor (default 1.0)
        m: cementation exponent (default 2.0)
        n: saturation exponent (default 2.0)

    Returns:
        Dict with sw, hydrocarbon_saturation, classification
    """
    if porosity <= 0 or rt <= 0:
        return {"sw": 1.0, "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

    numerator = a * rw
    denominator = rt * (porosity ** m)
    if denominator <= 0:
        sw = 1.0
    else:
        sw = (numerator / denominator) ** (1.0 / n)

    sw = max(0.0, min(sw, 1.0))
    sh = 1.0 - sw

    if sw > 0.80:
        classification = "Water"
    elif sw > 0.60:
        classification = "Water with residual HC"
    elif sw > 0.40:
        classification = "Transition"
    elif sw > 0.20:
        classification = "Hydrocarbon"
    else:
        classification = "Hydrocarbon (high saturation)"

    return {
        "sw": round(sw, 4),
        "hydrocarbon_saturation": round(sh, 4),
        "classification": classification,
    }


def calculate_sw_simandoux(
    rt: float,
    porosity: float,
    rw: float = 0.05,
    vsh: float = 0.0,
    rsh: float = 5.0,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0
) -> Dict[str, Any]:
    """
    Simandoux (1963) shaly-sand water saturation model.

    1/Rt = Sw^n * phi^m / (a * Rw) + Vsh * Sw / Rsh

    Solves quadratic for Sw (linearized for n=2):
    Rearranged: (phi^m/(a*Rw))*Sw^2 + (Vsh/Rsh)*Sw - 1/Rt = 0

    Args:
        rt: true resistivity (ohm-m)
        porosity: total porosity (v/v)
        rw: water resistivity (ohm-m)
        vsh: volume of shale (v/v)
        rsh: shale resistivity (ohm-m)
        a, m, n: Archie parameters

    Returns:
        Dict with sw, method, comparison with Archie
    """
    if porosity <= 0 or rt <= 0 or rw <= 0:
        return {"sw": 1.0, "method": "simandoux",
                "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

    # Quadratic coefficients (for n~2): A*Sw^2 + B*Sw + C = 0
    A_coeff = (porosity ** m) / (a * rw)
    B_coeff = vsh / rsh if rsh > 0 else 0.0
    C_coeff = -1.0 / rt

    # Solve quadratic: Sw = (-B + sqrt(B^2 - 4AC)) / (2A)
    discriminant = B_coeff ** 2 - 4.0 * A_coeff * C_coeff
    if discriminant < 0 or A_coeff <= 0:
        sw = 1.0
    else:
        sw = (-B_coeff + math.sqrt(discriminant)) / (2.0 * A_coeff)

    sw = max(0.0, min(sw, 1.0))

    # Archie comparison
    sw_archie = ((a * rw) / (rt * porosity ** m)) ** (1.0 / n)
    sw_archie = max(0.0, min(sw_archie, 1.0))

    if sw > 0.80:
        classification = "Water"
    elif sw > 0.60:
        classification = "Water with residual HC"
    elif sw > 0.40:
        classification = "Transition"
    elif sw > 0.20:
        classification = "Hydrocarbon"
    else:
        classification = "Hydrocarbon (high saturation)"

    return {
        "sw": round(sw, 4),
        "hydrocarbon_saturation": round(1.0 - sw, 4),
        "classification": classification,
        "sw_archie": round(sw_archie, 4),
        "sw_difference": round(sw - sw_archie, 4),
        "vsh_used": round(vsh, 4),
        "method": "simandoux",
    }


def calculate_sw_indonesia(
    rt: float,
    porosity: float,
    rw: float = 0.05,
    vsh: float = 0.0,
    rsh: float = 5.0,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0
) -> Dict[str, Any]:
    """
    Indonesia / Poupon-Leveaux (1971) shaly-sand Sw model.

    1/sqrt(Rt) = sqrt(phi^m/(a*Rw)) * Sw^(n/2) + Vsh^(1-Vsh/2)/sqrt(Rsh) * Sw

    Better for high-Vsh formations (>30%). Iterative solution.

    Args:
        rt: true resistivity (ohm-m)
        porosity: total porosity (v/v)
        rw: water resistivity (ohm-m)
        vsh: volume of shale (v/v)
        rsh: shale resistivity (ohm-m)
        a, m, n: Archie parameters

    Returns:
        Dict with sw, method, iterations
    """
    if porosity <= 0 or rt <= 0 or rw <= 0:
        return {"sw": 1.0, "method": "indonesia",
                "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

    # Target: 1/sqrt(Rt)
    target = 1.0 / math.sqrt(rt)

    # Clean-sand term coefficient
    clean_coeff = math.sqrt(porosity ** m / (a * rw))
    # Shale term coefficient
    vsh_exp = max(0.0, 1.0 - vsh / 2.0)
    shale_coeff = (vsh ** vsh_exp) / math.sqrt(rsh) if rsh > 0 else 0.0

    # Iterative: F(Sw) = clean_coeff * Sw^(n/2) + shale_coeff * Sw - target = 0
    # Newton-Raphson
    sw = 0.5  # initial guess
    for iteration in range(20):
        f = clean_coeff * sw ** (n / 2.0) + shale_coeff * sw - target
        df = clean_coeff * (n / 2.0) * sw ** (n / 2.0 - 1.0) + shale_coeff if sw > 0 else shale_coeff + 1.0
        if abs(df) < 1e-15:
            break
        sw_new = sw - f / df
        sw_new = max(0.01, min(sw_new, 1.0))
        if abs(sw_new - sw) < 1e-6:
            sw = sw_new
            break
        sw = sw_new

    sw = max(0.0, min(sw, 1.0))

    # Archie comparison
    sw_archie = ((a * rw) / (rt * porosity ** m)) ** (1.0 / n)
    sw_archie = max(0.0, min(sw_archie, 1.0))

    if sw > 0.80:
        classification = "Water"
    elif sw > 0.60:
        classification = "Water with residual HC"
    elif sw > 0.40:
        classification = "Transition"
    elif sw > 0.20:
        classification = "Hydrocarbon"
    else:
        classification = "Hydrocarbon (high saturation)"

    return {
        "sw": round(sw, 4),
        "hydrocarbon_saturation": round(1.0 - sw, 4),
        "classification": classification,
        "sw_archie": round(sw_archie, 4),
        "sw_difference": round(sw - sw_archie, 4),
        "vsh_used": round(vsh, 4),
        "method": "indonesia",
    }


def calculate_sw_auto(
    rt: float,
    porosity: float,
    rw: float = 0.05,
    vsh: float = 0.0,
    rsh: float = 5.0,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0
) -> Dict[str, Any]:
    """
    Auto-select Sw model based on Vsh content.

    - Vsh < 0.15: Archie (clean sand)
    - 0.15 <= Vsh < 0.40: Simandoux
    - Vsh >= 0.40: Indonesia (Poupon-Leveaux)

    Returns:
        Dict with sw, method selected, selection_reason
    """
    if vsh < 0.15:
        result = calculate_water_saturation(rt, porosity, rw, a, m, n)
        result["method"] = "archie"
        result["selection_reason"] = f"Vsh={vsh:.3f} < 0.15 \u2192 clean sand (Archie)"
    elif vsh < 0.40:
        result = calculate_sw_simandoux(rt, porosity, rw, vsh, rsh, a, m, n)
        result["selection_reason"] = f"0.15 <= Vsh={vsh:.3f} < 0.40 \u2192 moderately shaly (Simandoux)"
    else:
        result = calculate_sw_indonesia(rt, porosity, rw, vsh, rsh, a, m, n)
        result["selection_reason"] = f"Vsh={vsh:.3f} >= 0.40 \u2192 highly shaly (Indonesia)"

    return result


def calculate_porosity_sonic(
    dt_log: float,
    dt_matrix: float = 55.5,
    dt_fluid: float = 189.0,
    method: str = "raymer"
) -> Dict[str, Any]:
    """
    Sonic porosity from compressional slowness log.

    Wyllie: phi = (DT_log - DT_ma) / (DT_fl - DT_ma)
    Raymer-Hunt-Gardner: phi = 0.625 * (DT_log - DT_ma) / DT_log

    Typical DT_matrix values:
    - Sandstone: 55.5 us/ft
    - Limestone: 47.5 us/ft
    - Dolomite: 43.5 us/ft

    Args:
        dt_log: interval transit time from log (us/ft)
        dt_matrix: matrix transit time (us/ft)
        dt_fluid: fluid transit time (us/ft), ~189 freshwater
        method: "wyllie" or "raymer" (default)

    Returns:
        Dict with phi_sonic, method used
    """
    if dt_log <= 0 or dt_matrix <= 0:
        return {"phi_sonic": 0.0, "method": method,
                "note": "Invalid DT values"}

    if method.lower() == "wyllie":
        denom = dt_fluid - dt_matrix
        if denom <= 0:
            return {"phi_sonic": 0.0, "method": "wyllie",
                    "note": "DT_fluid must be > DT_matrix"}
        phi = (dt_log - dt_matrix) / denom
    else:
        # Raymer-Hunt-Gardner (empirical, preferred)
        if dt_log <= 0:
            phi = 0.0
        else:
            phi = 0.625 * (dt_log - dt_matrix) / dt_log

    phi = max(0.0, min(phi, 0.50))

    return {
        "phi_sonic": round(phi, 4),
        "dt_log": dt_log,
        "dt_matrix": dt_matrix,
        "dt_fluid": dt_fluid,
        "method": f"sonic_{method.lower()}",
    }
