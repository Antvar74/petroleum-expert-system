"""
Casing Design — Biaxial Correction and Triaxial VME Stress Check

Biaxial correction reduces collapse resistance under axial tension
(API 5C3 ellipse). Triaxial Von Mises Equivalent (VME) stress check
evaluates combined loading against yield strength.

References:
- API TR 5C3 (ISO 10400): Technical Report on Equations and Calculations
  for Casing, Tubing, and Line Pipe
- Von Mises yield criterion for combined stress states
- NORSOK D-010: Well Integrity in Drilling and Well Operations
"""
import math
from typing import Dict, Any


def calculate_biaxial_correction(
    collapse_rating_psi: float,
    axial_stress_psi: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    """
    Reduce collapse resistance due to axial tension (API 5C3 ellipse).

    The presence of axial tension reduces the casing's ability to resist
    external pressure (collapse). The API 5C3 biaxial approach uses:

    Yp_effective = Yp * sqrt(1 - 0.75*(Sa/Yp)^2) - 0.5*(Sa/Yp)*Yp

    where Sa = axial stress (positive = tension).
    Then recalculate collapse with Yp_effective.
    """
    if yield_strength_psi <= 0:
        return {"error": "Yield strength must be > 0"}

    sa_ratio = axial_stress_psi / yield_strength_psi

    # Limit ratio to practical range
    sa_ratio = max(min(sa_ratio, 0.99), -0.99)

    # Effective yield strength under biaxial loading
    yp_eff = yield_strength_psi * (
        math.sqrt(1.0 - 0.75 * sa_ratio ** 2) - 0.5 * sa_ratio
    )
    yp_eff = max(yp_eff, 0.0)

    # Reduction factor
    reduction_factor = yp_eff / yield_strength_psi if yield_strength_psi > 0 else 1.0

    # Corrected collapse
    corrected_collapse = collapse_rating_psi * reduction_factor

    return {
        "original_collapse_psi": round(collapse_rating_psi, 0),
        "corrected_collapse_psi": round(corrected_collapse, 0),
        "reduction_factor": round(reduction_factor, 4),
        "effective_yield_psi": round(yp_eff, 0),
        "axial_stress_psi": round(axial_stress_psi, 0),
        "stress_ratio": round(sa_ratio, 4),
    }


def calculate_biaxial_profile(
    collapse_profile: list,
    collapse_rating_psi: float,
    casing_weight_ppf: float,
    casing_length_ft: float,
    casing_od_in: float,
    casing_id_in: float,
    mud_weight_ppg: float,
    yield_strength_psi: float,
    overpull_lbs: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate depth-varying biaxial correction.

    At each depth, the axial tension is the buoyed weight of pipe below
    that point (plus overpull at surface). The biaxial correction factor
    varies with depth because tension decreases toward the shoe.

    References:
    - API TR 5C3 (ISO 10400): Biaxial yield criterion
    """
    area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)
    if area <= 0 or yield_strength_psi <= 0:
        return {"error": "Invalid dimensions or yield strength"}

    bf = 1.0 - mud_weight_ppg / 65.4

    profile = []
    for point in collapse_profile:
        depth = point.get("tvd_ft", 0)
        collapse_load = point.get("collapse_load_psi", 0)

        # Tension at this depth: buoyed weight of pipe below
        remaining_length = max(casing_length_ft - depth, 0)
        tension_at_depth = casing_weight_ppf * remaining_length * bf
        # Add overpull only at surface
        if depth == 0:
            tension_at_depth += overpull_lbs

        axial_stress = tension_at_depth / area
        sa_ratio = axial_stress / yield_strength_psi
        sa_ratio = max(min(sa_ratio, 0.99), -0.99)

        # Effective yield under biaxial loading
        yp_eff = yield_strength_psi * (
            math.sqrt(1.0 - 0.75 * sa_ratio ** 2) - 0.5 * sa_ratio
        )
        yp_eff = max(yp_eff, 0.0)
        reduction_factor = yp_eff / yield_strength_psi

        # Corrected collapse rating at this depth
        corrected_collapse = collapse_rating_psi * reduction_factor

        # SF at this depth
        sf = corrected_collapse / collapse_load if collapse_load > 0 else 99.0

        profile.append({
            "tvd_ft": round(depth, 0),
            "collapse_load_psi": round(collapse_load, 0),
            "tension_at_depth_lbs": round(tension_at_depth, 0),
            "axial_stress_psi": round(axial_stress, 0),
            "reduction_factor": round(reduction_factor, 4),
            "corrected_collapse_psi": round(corrected_collapse, 0),
            "sf_collapse_biaxial": round(min(sf, 99.0), 2),
        })

    # Find worst case (minimum SF)
    if profile:
        worst = min(profile, key=lambda p: p["sf_collapse_biaxial"])
        min_sf = worst["sf_collapse_biaxial"]
        min_sf_depth = worst["tvd_ft"]
    else:
        min_sf = 99.0
        min_sf_depth = 0

    return {
        "profile": profile,
        "min_sf_collapse_biaxial": min_sf,
        "min_sf_depth_ft": min_sf_depth,
        "num_points": len(profile),
    }


def calculate_triaxial_vme(
    axial_stress_psi: float,
    hoop_stress_psi: float,
    radial_stress_psi: float = 0.0,
    shear_stress_psi: float = 0.0,
    yield_strength_psi: float = 80000.0,
    safety_factor: float = 1.25,
) -> Dict[str, Any]:
    """
    Triaxial Von Mises Equivalent stress check.

    sigma_vme = sqrt(
        (sigma_a - sigma_h)^2 +
        (sigma_h - sigma_r)^2 +
        (sigma_r - sigma_a)^2 +
        6 * tau^2
    ) / sqrt(2)

    Pass if: sigma_vme < Yp / SF
    """
    sa = axial_stress_psi
    sh = hoop_stress_psi
    sr = radial_stress_psi
    tau = shear_stress_psi

    vme = math.sqrt(
        ((sa - sh) ** 2 + (sh - sr) ** 2 + (sr - sa) ** 2 + 6 * tau ** 2) / 2.0
    )

    allowable = yield_strength_psi / safety_factor
    utilization = vme / allowable if allowable > 0 else 999
    passes = vme < allowable

    status = "PASS" if passes else "FAIL"
    if utilization > 0.9 and passes:
        status = "MARGINAL"

    return {
        "vme_stress_psi": round(vme, 0),
        "allowable_psi": round(allowable, 0),
        "utilization_pct": round(utilization * 100, 1),
        "passes": passes,
        "status": status,
        "yield_strength_psi": yield_strength_psi,
        "safety_factor": safety_factor,
        "stress_components": {
            "axial_psi": round(sa, 0),
            "hoop_psi": round(sh, 0),
            "radial_psi": round(sr, 0),
            "shear_psi": round(tau, 0),
        },
    }


def calculate_hoop_stress_lame(
    od_in: float,
    id_in: float,
    p_internal_psi: float,
    p_external_psi: float,
) -> Dict[str, Any]:
    """
    Lame thick-walled cylinder hoop stress at inner and outer wall.

    sigma_h(r) = (Pi*ri^2 - Po*ro^2)/(ro^2-ri^2) + ri^2*ro^2*(Pi-Po)/(r^2*(ro^2-ri^2))

    At inner wall (r=ri): maximum magnitude for collapse
    At outer wall (r=ro): maximum magnitude for burst

    References:
    - Timoshenko: Theory of Elasticity, thick cylinder analysis
    - API TR 5C3 Annex B: Stress analysis of casing
    """
    ro = od_in / 2.0
    ri = id_in / 2.0

    if ro <= ri or ri <= 0:
        return {"error": "Invalid dimensions: OD must be > ID > 0"}

    ro2 = ro ** 2
    ri2 = ri ** 2
    diff = ro2 - ri2

    # Hoop stress at inner wall (r = ri)
    hoop_inner = (p_internal_psi * ri2 - p_external_psi * ro2) / diff + \
                 ri2 * ro2 * (p_internal_psi - p_external_psi) / (ri2 * diff)

    # Hoop stress at outer wall (r = ro)
    hoop_outer = (p_internal_psi * ri2 - p_external_psi * ro2) / diff + \
                 ri2 * ro2 * (p_internal_psi - p_external_psi) / (ro2 * diff)

    # Radial stress at inner wall = -P_internal, at outer wall = -P_external
    radial_inner = -p_internal_psi
    radial_outer = -p_external_psi

    return {
        "hoop_inner_psi": round(hoop_inner, 0),
        "hoop_outer_psi": round(hoop_outer, 0),
        "radial_inner_psi": round(radial_inner, 0),
        "radial_outer_psi": round(radial_outer, 0),
    }
