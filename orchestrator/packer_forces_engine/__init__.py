"""Packer Forces Engine — backward-compatible facade.

Package split from monolithic packer_forces_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.packer_forces_engine import PackerForcesEngine
"""
from .geometry import calculate_tubing_areas, STEEL_E, STEEL_POISSON, STEEL_ALPHA
from .forces import (
    calculate_piston_force,
    calculate_ballooning_force,
    calculate_temperature_force,
    calculate_buckling_force,
    calculate_tubing_movement,
)
from .buckling import calculate_helical_buckling_load, calculate_buckling_length
from .apb import calculate_apb, calculate_apb_mitigation
from .packer_type import calculate_packer_force_by_type
from .temperature_profile import calculate_temperature_force_profile
from .landing import calculate_landing_conditions
from .pipeline import calculate_total_packer_force


class PackerForcesEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Steel properties (class-level constants for backward compatibility)
    STEEL_E = STEEL_E
    STEEL_POISSON = STEEL_POISSON
    STEEL_ALPHA = STEEL_ALPHA

    calculate_tubing_areas = staticmethod(calculate_tubing_areas)
    calculate_piston_force = staticmethod(calculate_piston_force)
    calculate_ballooning_force = staticmethod(calculate_ballooning_force)
    calculate_temperature_force = staticmethod(calculate_temperature_force)
    calculate_buckling_force = staticmethod(calculate_buckling_force)
    calculate_tubing_movement = staticmethod(calculate_tubing_movement)
    calculate_helical_buckling_load = staticmethod(calculate_helical_buckling_load)
    calculate_total_packer_force = staticmethod(calculate_total_packer_force)
    calculate_apb = staticmethod(calculate_apb)
    calculate_apb_mitigation = staticmethod(calculate_apb_mitigation)
    calculate_packer_force_by_type = staticmethod(calculate_packer_force_by_type)
    calculate_temperature_force_profile = staticmethod(calculate_temperature_force_profile)
    calculate_buckling_length = staticmethod(calculate_buckling_length)
    calculate_landing_conditions = staticmethod(calculate_landing_conditions)
