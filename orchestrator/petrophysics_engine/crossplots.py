"""
Petrophysics Engine — Crossplot Generation.

- Pickett plot (log10(Rt) vs log10(phi)) with iso-Sw lines
- Density-Neutron crossplot with lithology lines

References:
- Archie, G.E. (1942): Formation Factor and Water Saturation
"""
import math
from typing import Dict, Any, List

from .constants import LITHOLOGY


def generate_pickett_plot(
    log_data: List[Dict], rw: float = 0.05,
    a: float = 1.0, m: float = 2.0, n: float = 2.0,
) -> Dict[str, Any]:
    """
    Generate Pickett plot data (log10(Rt) vs log10(phi)).

    Includes iso-Sw lines for Sw = 0.2, 0.4, 0.6, 0.8, 1.0.

    Args:
        log_data: list of dicts with phi, rt, and optionally sw
        rw: formation water resistivity
        a, m, n: Archie parameters

    Returns:
        Dict with points, iso_sw_lines, regression
    """
    points = []
    for entry in log_data:
        phi = entry.get("phi", 0)
        rt = entry.get("rt", 0)
        if phi > 0.01 and rt > 0.1:
            points.append({
                "phi": phi,
                "rt": rt,
                "log_phi": round(math.log10(phi), 4),
                "log_rt": round(math.log10(rt), 4),
                "sw": entry.get("sw"),
            })

    # Generate iso-Sw lines
    iso_sw_lines = {}
    phi_range = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    for sw in [0.20, 0.40, 0.60, 0.80, 1.00]:
        line_points = []
        for phi in phi_range:
            # Rt = a * Rw / (phi^m * Sw^n)
            rt_val = a * rw / ((phi ** m) * (sw ** n))
            line_points.append({
                "log_phi": round(math.log10(phi), 4),
                "log_rt": round(math.log10(rt_val), 4),
            })
        iso_sw_lines[f"Sw={sw:.0%}"] = line_points

    # Simple linear regression on log-log for m estimation
    regression = {}
    if len(points) >= 3:
        x = [p["log_phi"] for p in points]
        y = [p["log_rt"] for p in points]
        n_pts = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi ** 2 for xi in x)
        denom = n_pts * sum_xx - sum_x ** 2
        if abs(denom) > 1e-10:
            slope = (n_pts * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n_pts
            regression = {
                "slope": round(slope, 3),
                "intercept": round(intercept, 3),
                "estimated_m": round(-slope, 3),
                "note": "Slope of Pickett plot ≈ -m (cementation exponent)",
            }

    return {
        "points": points,
        "iso_sw_lines": iso_sw_lines,
        "regression": regression,
    }


def crossplot_density_neutron(
    log_data: List[Dict],
    rho_fluid: float = 1.0,
) -> Dict[str, Any]:
    """
    Generate Density-Neutron crossplot data with lithology lines.

    Args:
        log_data: list of dicts with rhob, nphi
        rho_fluid: fluid density (g/cc), default 1.0 for water

    Returns:
        Dict with data_points, lithology_lines, gas_flag zones
    """
    points = []
    for entry in log_data:
        rhob = entry.get("rhob", 0)
        nphi = entry.get("nphi", 0)
        if 1.5 < rhob < 3.2 and -0.05 < nphi < 0.60:
            # Compute density porosity
            rho_ma = 2.65  # assume sandstone
            phi_d = (rho_ma - rhob) / (rho_ma - rho_fluid)
            phi_d = max(0, min(phi_d, 0.50))

            # Gas flag: neutron reads low, density reads high porosity
            gas_flag = nphi < phi_d - 0.04

            points.append({
                "rhob": round(rhob, 4),
                "nphi": round(nphi, 4),
                "phi_density": round(phi_d, 4),
                "gas_flag": gas_flag,
                "md": entry.get("md"),
            })

    # Lithology lines (matrix → fluid point)
    lithology_lines = {}
    for lith, params in LITHOLOGY.items():
        lithology_lines[lith] = {
            "matrix_point": {"rhob": params["rho_ma"], "nphi": params["nphi_ma"]},
            "fluid_point": {"rhob": rho_fluid, "nphi": 1.0},
            "line": [
                {"rhob": params["rho_ma"], "nphi": params["nphi_ma"]},
                {"rhob": round(params["rho_ma"] * 0.6 + rho_fluid * 0.4, 3),
                 "nphi": round(params["nphi_ma"] * 0.6 + 0.4, 3)},
            ],
        }

    return {
        "points": points,
        "lithology_lines": lithology_lines,
        "gas_count": sum(1 for p in points if p["gas_flag"]),
        "total_points": len(points),
    }
