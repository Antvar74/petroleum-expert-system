"""Cementing Engine — backward-compatible facade.

Package split from monolithic cementing_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.cementing_engine import CementingEngine
"""
from .constants import CEMENT_CLASSES, DEFAULT_SPACER_DENSITY, DEFAULT_WASH_VOLUME_BBL_PER_1000FT, infer_cement_class
from .volumes import calculate_fluid_volumes, calculate_fluid_volumes_caliper
from .displacement import calculate_displacement_schedule
from .ecd import calculate_ecd_during_job
from .pressure import calculate_free_fall, calculate_utube_effect, calculate_bhp_schedule, calculate_lift_pressure
from .slurry import correct_slurry_properties_pt, estimate_bhct
from .risk import calculate_gas_migration_risk
from .design import optimize_spacer, design_centralizers
from .pipeline import calculate_full_cementing, generate_recommendations


class CementingEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Constants (re-exported as class attributes)
    CEMENT_CLASSES = CEMENT_CLASSES
    DEFAULT_SPACER_DENSITY = DEFAULT_SPACER_DENSITY
    DEFAULT_WASH_VOLUME_BBL_PER_1000FT = DEFAULT_WASH_VOLUME_BBL_PER_1000FT

    # constants
    _infer_cement_class = staticmethod(infer_cement_class)

    # volumes
    calculate_fluid_volumes = staticmethod(calculate_fluid_volumes)
    calculate_fluid_volumes_caliper = staticmethod(calculate_fluid_volumes_caliper)

    # displacement
    calculate_displacement_schedule = staticmethod(calculate_displacement_schedule)

    # ecd
    calculate_ecd_during_job = staticmethod(calculate_ecd_during_job)

    # pressure
    calculate_free_fall = staticmethod(calculate_free_fall)
    calculate_utube_effect = staticmethod(calculate_utube_effect)
    calculate_bhp_schedule = staticmethod(calculate_bhp_schedule)
    calculate_lift_pressure = staticmethod(calculate_lift_pressure)

    # slurry
    correct_slurry_properties_pt = staticmethod(correct_slurry_properties_pt)
    estimate_bhct = staticmethod(estimate_bhct)

    # risk
    calculate_gas_migration_risk = staticmethod(calculate_gas_migration_risk)

    # design
    optimize_spacer = staticmethod(optimize_spacer)
    design_centralizers = staticmethod(design_centralizers)

    # pipeline
    calculate_full_cementing = staticmethod(calculate_full_cementing)
    generate_recommendations = staticmethod(generate_recommendations)


__all__ = ["CementingEngine"]
