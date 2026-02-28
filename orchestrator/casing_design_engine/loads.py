"""
Casing Design — Burst, Collapse, and Tension Load Profiles

Calculates load profiles vs. depth for the three primary casing design
criteria: burst (internal > external), collapse (external > internal),
and tension (axial loads at surface).

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 7
"""
import math
from typing import Dict, Any


def calculate_burst_load(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    gas_gradient_psi_ft: float = 0.1,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Calculate burst load profile vs. depth.

    Design scenario: gas-to-surface (worst case for surface casing)
    - Internal pressure: gas column from TD to surface
    - External pressure (backup): mud/cement column outside

    Burst_load = P_internal - P_external at each depth

    Internal: P_int(z) = P_reservoir - gas_gradient * (TVD - z)
              P_reservoir = pore_pressure * 0.052 * TVD
    External: P_ext(z) = mud_weight * 0.052 * z  (above cement)
              P_ext(z) = cement_density * 0.052 * (z - cement_top) + ... (in cement)
    """
    if tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    # Reservoir pressure at TD
    p_reservoir = pore_pressure_ppg * 0.052 * tvd_ft

    profile = []
    step = tvd_ft / max(num_points - 1, 1)

    for i in range(num_points):
        depth = i * step

        # Internal pressure (gas to surface)
        p_internal = p_reservoir - gas_gradient_psi_ft * (tvd_ft - depth)
        p_internal = max(p_internal, 0.0)

        # External pressure (backup)
        if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
            p_external = mud_weight_ppg * 0.052 * depth
        else:
            # Above cement: mud; below cement top: cement
            p_external = (
                mud_weight_ppg * 0.052 * cement_top_tvd_ft
                + cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft)
            )

        burst_load = p_internal - p_external

        profile.append({
            "tvd_ft": round(depth, 0),
            "p_internal_psi": round(p_internal, 0),
            "p_external_psi": round(p_external, 0),
            "burst_load_psi": round(burst_load, 0),
        })

    max_burst = max(p["burst_load_psi"] for p in profile)
    max_burst_depth = next(p["tvd_ft"] for p in profile if p["burst_load_psi"] == max_burst)

    return {
        "profile": profile,
        "max_burst_load_psi": round(max_burst, 0),
        "max_burst_depth_ft": round(max_burst_depth, 0),
        "reservoir_pressure_psi": round(p_reservoir, 0),
        "scenario": "Gas to Surface",
    }


def calculate_collapse_load(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    evacuation_level_ft: float = 0.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Calculate collapse load profile vs. depth.

    Design scenario: full/partial evacuation
    - External pressure: mud/cement column
    - Internal pressure: empty or partially filled casing

    Collapse_load = P_external - P_internal at each depth
    """
    if tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    profile = []
    step = tvd_ft / max(num_points - 1, 1)

    # Resolve evacuation semantics:
    #   -1  → no evacuation (casing full of mud, collapse differential ≈ 0)
    #    0  → full evacuation (casing empty, worst-case collapse)
    #   >0  → partial evacuation (empty above that depth, fluid below)
    if evacuation_level_ft < 0:
        effective_evac = 0.0  # fluid level at surface = casing full of mud
    elif evacuation_level_ft == 0:
        effective_evac = tvd_ft  # fluid level at TD = casing empty
    else:
        effective_evac = evacuation_level_ft

    for i in range(num_points):
        depth = i * step

        # External pressure
        if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
            p_external = mud_weight_ppg * 0.052 * depth
        else:
            p_external = (
                mud_weight_ppg * 0.052 * cement_top_tvd_ft
                + cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft)
            )

        # Internal pressure (evacuation scenario)
        # fluid level = effective_evac: above it casing is empty, below it has mud
        if depth <= effective_evac:
            p_internal = 0.0  # empty above fluid level
        else:
            # Below fluid level: mud weight inside
            p_internal = mud_weight_ppg * 0.052 * (depth - effective_evac)

        collapse_load = p_external - p_internal

        profile.append({
            "tvd_ft": round(depth, 0),
            "p_external_psi": round(p_external, 0),
            "p_internal_psi": round(p_internal, 0),
            "collapse_load_psi": round(collapse_load, 0),
        })

    max_collapse = max(p["collapse_load_psi"] for p in profile)
    max_collapse_depth = next(p["tvd_ft"] for p in profile if p["collapse_load_psi"] == max_collapse)

    return {
        "profile": profile,
        "max_collapse_load_psi": round(max_collapse, 0),
        "max_collapse_depth_ft": round(max_collapse_depth, 0),
        "scenario": (
            "No Evacuation" if effective_evac <= 0
            else "Full Evacuation" if effective_evac >= tvd_ft
            else f"Partial Evacuation to {effective_evac:.0f} ft"
        ),
    }


def calculate_tension_load(
    casing_weight_ppf: float,
    casing_length_ft: float,
    mud_weight_ppg: float,
    casing_od_in: float,
    casing_id_in: float,
    buoyancy_applied: bool = True,
    shock_load: bool = True,
    bending_load_dls: float = 0.0,
    overpull_lbs: float = 50000.0,
) -> Dict[str, Any]:
    """
    Calculate tension load on casing string.

    Components:
    - Weight: W = weight_ppf * length (air weight)
    - Buoyancy factor: BF = 1 - MW/65.4 (steel density 65.4 ppg)
    - Shock load (Lubinski): F_shock = 3200 * W_ppf (for sudden stops)
    - Bending: F_bend = 63 * DLS * OD * W_ppf (API formula)
    - Overpull: additional pull for freeing stuck casing
    """
    # Air weight
    air_weight = casing_weight_ppf * casing_length_ft

    # Buoyancy
    bf = 1.0 - mud_weight_ppg / 65.4 if buoyancy_applied else 1.0
    buoyant_weight = air_weight * bf

    # Shock load (Lubinski approximation: 3200 * ppf)
    shock_lbs = 3200.0 * casing_weight_ppf if shock_load else 0.0

    # Bending load (from dogleg severity)
    bending_lbs = 63.0 * bending_load_dls * casing_od_in * casing_weight_ppf if bending_load_dls > 0 else 0.0

    # Total tension at surface
    total_tension = buoyant_weight + shock_lbs + bending_lbs + overpull_lbs

    # Cross-sectional area
    area_sq_in = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)

    # Axial stress
    axial_stress = total_tension / area_sq_in if area_sq_in > 0 else 0

    return {
        "air_weight_lbs": round(air_weight, 0),
        "buoyancy_factor": round(bf, 4),
        "buoyant_weight_lbs": round(buoyant_weight, 0),
        "shock_load_lbs": round(shock_lbs, 0),
        "bending_load_lbs": round(bending_lbs, 0),
        "overpull_lbs": round(overpull_lbs, 0),
        "total_tension_lbs": round(total_tension, 0),
        "axial_stress_psi": round(axial_stress, 0),
        "cross_section_area_sq_in": round(area_sq_in, 3),
    }
