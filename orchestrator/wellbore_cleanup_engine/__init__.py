"""Wellbore Cleanup Engine — backward-compatible facade.

Package split from monolithic wellbore_cleanup_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine
"""
from .constants import (
    GRAVITY,
    WATER_DENSITY,
    MIN_AV_VERTICAL,
    MIN_AV_HIGH_ANGLE,
    MIN_AV_TRANSITION,
    get_min_annular_velocity,
)
from .annular import calculate_annular_velocity, calculate_minimum_flow_rate
from .slip_velocity import calculate_slip_velocity, calculate_slip_velocity_larsen
from .transport import calculate_ctr, calculate_transport_velocity, calculate_cuttings_concentration
from .hci import calculate_hole_cleaning_index
from .sweep import design_sweep_pill
from .ecd import calculate_cuttings_ecd_contribution
from .pipeline import calculate_full_cleanup


class WellboreCleanupEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Physical constants
    GRAVITY = GRAVITY
    WATER_DENSITY = WATER_DENSITY

    # Recommended minimums (API RP 13D)
    MIN_AV_VERTICAL = MIN_AV_VERTICAL
    MIN_AV_HIGH_ANGLE = MIN_AV_HIGH_ANGLE
    MIN_AV_TRANSITION = MIN_AV_TRANSITION

    calculate_annular_velocity = staticmethod(calculate_annular_velocity)
    calculate_slip_velocity = staticmethod(calculate_slip_velocity)
    calculate_slip_velocity_larsen = staticmethod(calculate_slip_velocity_larsen)
    calculate_ctr = staticmethod(calculate_ctr)
    calculate_transport_velocity = staticmethod(calculate_transport_velocity)
    calculate_minimum_flow_rate = staticmethod(calculate_minimum_flow_rate)
    calculate_hole_cleaning_index = staticmethod(calculate_hole_cleaning_index)
    design_sweep_pill = staticmethod(design_sweep_pill)
    calculate_cuttings_concentration = staticmethod(calculate_cuttings_concentration)
    calculate_cuttings_ecd_contribution = staticmethod(calculate_cuttings_ecd_contribution)
    calculate_full_cleanup = staticmethod(calculate_full_cleanup)
