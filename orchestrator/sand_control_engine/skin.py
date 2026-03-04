"""
Sand Control Engine — Completion skin factor.

References:
- Karakas & Tariq (1991): Semianalytical productivity models for perforated completions
- S_total = S_perf + S_gravel + S_damage
- Gravel-packed perforation: reduced effective permeability through gravel
"""
import math
from typing import Dict, Any


def calculate_skin_factor(
    perforation_length: float,
    perforation_diameter: float,
    gravel_permeability_md: float,
    formation_permeability_md: float,
    wellbore_radius: float,
    damaged_zone_radius: float = 0.0,
    damaged_zone_perm_md: float = 0.0
) -> Dict[str, Any]:
    """
    Calculate completion skin factor including gravel pack contribution.

    S_total = S_perf + S_gravel + S_damage

    Args:
        perforation_length: perforation tunnel length (inches). 0.0 for open hole.
        perforation_diameter: perforation tunnel diameter (inches)
        gravel_permeability_md: gravel pack permeability (mD)
        formation_permeability_md: formation permeability (mD)
        wellbore_radius: wellbore radius (ft)
        damaged_zone_radius: damaged zone extent (ft), 0 = no damage
        damaged_zone_perm_md: damaged zone permeability (mD)

    Returns:
        Dict with S_total and components (S_perf, S_gravel, S_damage)
    """
    if formation_permeability_md <= 0 or wellbore_radius <= 0:
        return {"error": "Invalid permeability or wellbore radius"}

    # Perforation tunnel converted to feet
    l_perf_ft = perforation_length / 12.0
    d_perf_ft = perforation_diameter / 12.0

    # Gravel-filled perforation skin
    s_gravel = 0.0
    if gravel_permeability_md > 0 and l_perf_ft > 0 and d_perf_ft > 0:
        r_perf = d_perf_ft / 2.0
        if r_perf > 0:
            s_gravel = (formation_permeability_md / gravel_permeability_md - 1.0) * \
                       math.log((wellbore_radius + l_perf_ft) / wellbore_radius)

    # Perforation pseudo-skin (simplified Karakas-Tariq 1991)
    # For open hole (perforation_length=0): S_perf = 0 (no perforation tunnel)
    s_perf = 0.0
    if l_perf_ft > 0:
        r_d = l_perf_ft / wellbore_radius
        if r_d > 0:
            s_perf = math.log(1.0 / r_d) if r_d < 1 else -math.log(r_d)

    # Damage skin
    s_damage = 0.0
    if damaged_zone_radius > wellbore_radius and damaged_zone_perm_md > 0:
        s_damage = (formation_permeability_md / damaged_zone_perm_md - 1.0) * \
                   math.log(damaged_zone_radius / wellbore_radius)

    s_total = s_perf + s_gravel + s_damage

    return {
        "skin_total": round(s_total, 2),
        "skin_perforation": round(s_perf, 2),
        "skin_gravel": round(s_gravel, 2),
        "skin_damage": round(s_damage, 2),
        "formation_perm_md": formation_permeability_md,
        "gravel_perm_md": gravel_permeability_md
    }
