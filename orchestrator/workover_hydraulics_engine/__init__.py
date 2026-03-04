"""Workover Hydraulics Engine — backward-compatible facade.

Package split from monolithic workover_hydraulics_engine.py.
All existing imports continue to work unchanged.
"""
from .ct_geometry import calculate_ct_dimensions, STEEL_DENSITY, STEEL_WEIGHT_WATER, GRAVITY
from .ct_hydraulics import calculate_ct_pressure_loss
from .ct_forces import calculate_ct_buoyed_weight, calculate_ct_drag, calculate_snubbing_force
from .ct_reach import calculate_max_reach
from .ct_kill import calculate_workover_kill
from .ct_mechanics import calculate_ct_elongation, calculate_ct_fatigue
from .pipeline import calculate_full_workover


class WorkoverHydraulicsEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    STEEL_DENSITY = STEEL_DENSITY
    STEEL_WEIGHT_WATER = STEEL_WEIGHT_WATER
    GRAVITY = GRAVITY

    calculate_ct_dimensions = staticmethod(calculate_ct_dimensions)
    calculate_ct_pressure_loss = staticmethod(calculate_ct_pressure_loss)
    calculate_ct_buoyed_weight = staticmethod(calculate_ct_buoyed_weight)
    calculate_ct_drag = staticmethod(calculate_ct_drag)
    calculate_snubbing_force = staticmethod(calculate_snubbing_force)
    calculate_max_reach = staticmethod(calculate_max_reach)
    calculate_workover_kill = staticmethod(calculate_workover_kill)
    calculate_ct_elongation = staticmethod(calculate_ct_elongation)
    calculate_ct_fatigue = staticmethod(calculate_ct_fatigue)
    calculate_full_workover = staticmethod(calculate_full_workover)
