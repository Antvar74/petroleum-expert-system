"""
Casing Design — Multi-Scenario Burst and Collapse Analysis

Five burst scenarios (gas-to-surface, displacement-to-gas, tubing leak,
injection, DST) and four collapse scenarios (full evacuation, partial
evacuation, cementing collapse, production depletion).

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
"""
from typing import Dict, Any


def calculate_burst_scenarios(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    gas_gradient_psi_ft: float = 0.1,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    tubing_pressure_psi: float = 0.0,
    injection_pressure_psi: float = 0.0,
    injection_fluid_gradient: float = 0.433,
    dst_pressure_psi: float = 0.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Multi-scenario burst analysis (API TR 5C3 / ISO 10400).

    Scenarios:
    1. Gas-to-surface — worst case for surface casing
    2. Displacement to gas — tubing full of gas, annulus with mud
    3. Tubing leak — tubing head pressure applied to casing
    4. Injection — injection pressure + fluid gradient
    5. DST — reservoir pressure at surface during drill stem test
    """
    if tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    p_reservoir = pore_pressure_ppg * 0.052 * tvd_ft

    scenarios = {}
    step = tvd_ft / max(num_points - 1, 1)

    # Helper: external pressure at depth
    def p_external(depth):
        if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
            return mud_weight_ppg * 0.052 * depth
        return (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft))

    # Scenario 1: Gas-to-surface
    profile_gts = []
    for i in range(num_points):
        d = i * step
        p_int = max(p_reservoir - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
        p_ext = p_external(d)
        profile_gts.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
    scenarios["gas_to_surface"] = {
        "profile": profile_gts,
        "max_burst_psi": max(p["burst_load_psi"] for p in profile_gts),
    }

    # Scenario 2: Displacement to gas
    profile_dtg = []
    for i in range(num_points):
        d = i * step
        p_int = max(p_reservoir - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
        p_ext = mud_weight_ppg * 0.052 * d  # annulus = mud (no cement backup)
        profile_dtg.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
    scenarios["displacement_to_gas"] = {
        "profile": profile_dtg,
        "max_burst_psi": max(p["burst_load_psi"] for p in profile_dtg),
    }

    # Scenario 3: Tubing leak
    p_tubing = tubing_pressure_psi if tubing_pressure_psi > 0 else 0.5 * p_reservoir
    profile_tl = []
    for i in range(num_points):
        d = i * step
        p_int = p_tubing + mud_weight_ppg * 0.052 * d
        p_ext = p_external(d)
        profile_tl.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
    scenarios["tubing_leak"] = {
        "profile": profile_tl,
        "max_burst_psi": max(p["burst_load_psi"] for p in profile_tl),
    }

    # Scenario 4: Injection
    p_inj = injection_pressure_psi if injection_pressure_psi > 0 else 0.0
    profile_inj = []
    for i in range(num_points):
        d = i * step
        p_int = p_inj + injection_fluid_gradient * d
        p_ext = p_external(d)
        profile_inj.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
    scenarios["injection"] = {
        "profile": profile_inj,
        "max_burst_psi": max(p["burst_load_psi"] for p in profile_inj),
    }

    # Scenario 5: DST
    p_dst = dst_pressure_psi if dst_pressure_psi > 0 else p_reservoir
    profile_dst = []
    for i in range(num_points):
        d = i * step
        p_int = max(p_dst - gas_gradient_psi_ft * (tvd_ft - d), 0.0)
        p_ext = p_external(d)
        profile_dst.append({"tvd_ft": round(d, 0), "burst_load_psi": round(p_int - p_ext, 0)})
    scenarios["dst"] = {
        "profile": profile_dst,
        "max_burst_psi": max(p["burst_load_psi"] for p in profile_dst),
    }

    # Governing scenario
    governing = max(scenarios.items(), key=lambda x: x[1]["max_burst_psi"])

    return {
        "scenarios": scenarios,
        "governing_scenario": governing[0],
        "governing_burst_psi": governing[1]["max_burst_psi"],
        "num_scenarios": len(scenarios),
    }


def calculate_collapse_scenarios(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    partial_evacuation_ft: float = 0.0,
    depleted_pressure_ppg: float = 0.0,
    cement_slurry_density_ppg: float = 16.5,
    internal_fluid_density_ppg: float = 0.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    """
    Multi-scenario collapse analysis.

    Scenarios:
    1. Full evacuation — worst case drilling
    2. Partial evacuation — fluid level drops to partial_evacuation_ft
    3. Cementing collapse — fresh cement outside, reduced inside
    4. Production collapse — reservoir depletion over life
    """
    if tvd_ft <= 0:
        return {"error": "TVD must be > 0"}

    scenarios = {}
    step = tvd_ft / max(num_points - 1, 1)

    # Resolve internal fluid density: 0 = use mud weight
    int_fluid_ppg = internal_fluid_density_ppg if internal_fluid_density_ppg > 0 else mud_weight_ppg

    # External pressure helper
    def p_external(depth):
        if depth <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
            return mud_weight_ppg * 0.052 * depth
        return (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                cement_density_ppg * 0.052 * (depth - cement_top_tvd_ft))

    # Scenario 1: Full evacuation
    profile_fe = []
    for i in range(num_points):
        d = i * step
        p_ext = p_external(d)
        p_int = 0.0  # empty
        profile_fe.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
    scenarios["full_evacuation"] = {
        "profile": profile_fe,
        "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_fe),
    }

    # Scenario 2: Partial evacuation
    evac_ft = partial_evacuation_ft if partial_evacuation_ft > 0 else tvd_ft * 0.5
    profile_pe = []
    for i in range(num_points):
        d = i * step
        p_ext = p_external(d)
        p_int = 0.0 if d <= evac_ft else int_fluid_ppg * 0.052 * (d - evac_ft)
        profile_pe.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
    scenarios["partial_evacuation"] = {
        "profile": profile_pe,
        "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_pe),
    }

    # Scenario 3: Cementing collapse
    profile_cc = []
    for i in range(num_points):
        d = i * step
        # External: fresh cement (heavier) outside casing during cementing
        if d <= cement_top_tvd_ft or cement_top_tvd_ft <= 0:
            p_ext_cc = mud_weight_ppg * 0.052 * d
        else:
            p_ext_cc = (mud_weight_ppg * 0.052 * cement_top_tvd_ft +
                        cement_slurry_density_ppg * 0.052 * (d - cement_top_tvd_ft))
        # Internal: reduced pressure (partial lost returns)
        p_int_cc = mud_weight_ppg * 0.052 * d * 0.85  # 85% of original MW
        profile_cc.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext_cc - p_int_cc, 0)})
    scenarios["cementing_collapse"] = {
        "profile": profile_cc,
        "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_cc),
    }

    # Scenario 4: Production collapse (depletion)
    depleted_ppg = depleted_pressure_ppg if depleted_pressure_ppg > 0 else pore_pressure_ppg * 0.5
    profile_pd = []
    for i in range(num_points):
        d = i * step
        p_ext = p_external(d)
        # Internal: depleted reservoir pressure gradient
        p_int = depleted_ppg * 0.052 * d
        profile_pd.append({"tvd_ft": round(d, 0), "collapse_load_psi": round(p_ext - p_int, 0)})
    scenarios["production_depletion"] = {
        "profile": profile_pd,
        "max_collapse_psi": max(p["collapse_load_psi"] for p in profile_pd),
    }

    governing = max(scenarios.items(), key=lambda x: x[1]["max_collapse_psi"])

    return {
        "scenarios": scenarios,
        "governing_scenario": governing[0],
        "governing_collapse_psi": governing[1]["max_collapse_psi"],
        "num_scenarios": len(scenarios),
    }
