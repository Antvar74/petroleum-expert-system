"""Casing Design Engine -- backward-compatible facade.

Package split from monolithic casing_design_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.casing_design_engine import CasingDesignEngine
"""
from .constants import CASING_GRADES, CASING_CATALOG, DEFAULT_SF
from .loads import calculate_burst_load, calculate_collapse_load, calculate_tension_load
from .ratings import calculate_burst_rating, calculate_collapse_rating, derate_for_temperature
from .corrections import calculate_biaxial_correction, calculate_triaxial_vme
from .grade_selection import select_casing_grade, lookup_casing_catalog, design_combination_string
from .safety_factors import calculate_safety_factors
from .scenarios import calculate_burst_scenarios, calculate_collapse_scenarios
from .running_loads import calculate_running_loads
from .wear import apply_wear_allowance
from .pipeline import calculate_full_casing_design, generate_recommendations


class CasingDesignEngine:
    """Backward-compatible facade -- delegates all methods to submodules."""

    # Constants (re-exported as class attributes)
    CASING_GRADES = CASING_GRADES
    CASING_CATALOG = CASING_CATALOG
    DEFAULT_SF = DEFAULT_SF

    # loads
    calculate_burst_load = staticmethod(calculate_burst_load)
    calculate_collapse_load = staticmethod(calculate_collapse_load)
    calculate_tension_load = staticmethod(calculate_tension_load)

    # ratings
    calculate_burst_rating = staticmethod(calculate_burst_rating)
    calculate_collapse_rating = staticmethod(calculate_collapse_rating)
    derate_for_temperature = staticmethod(derate_for_temperature)

    # corrections
    calculate_biaxial_correction = staticmethod(calculate_biaxial_correction)
    calculate_triaxial_vme = staticmethod(calculate_triaxial_vme)

    # grade selection
    select_casing_grade = staticmethod(select_casing_grade)
    lookup_casing_catalog = staticmethod(lookup_casing_catalog)
    design_combination_string = staticmethod(design_combination_string)

    # safety factors
    calculate_safety_factors = staticmethod(calculate_safety_factors)

    # scenarios
    calculate_burst_scenarios = staticmethod(calculate_burst_scenarios)
    calculate_collapse_scenarios = staticmethod(calculate_collapse_scenarios)

    # running loads
    calculate_running_loads = staticmethod(calculate_running_loads)

    # wear
    apply_wear_allowance = staticmethod(apply_wear_allowance)

    # pipeline
    calculate_full_casing_design = staticmethod(calculate_full_casing_design)
    generate_recommendations = staticmethod(generate_recommendations)


__all__ = ["CasingDesignEngine"]
