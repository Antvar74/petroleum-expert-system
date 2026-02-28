"""Vibrations & Stability Engine -- backward-compatible facade.

Package split from monolithic vibrations_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.vibrations_engine import VibrationsEngine
"""
from .critical_speeds import (
    calculate_critical_rpm_axial,
    calculate_critical_rpm_lateral,
    calculate_critical_rpm_lateral_multi,
    STEEL_E,
    STEEL_DENSITY,
    GRAVITY,
)
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
from .stability import (
    calculate_stability_index,
    generate_vibration_map,
    calculate_vibration_map_3d,
)
from .bit_excitation import calculate_bit_excitation, check_resonance
from .stabilizers import optimize_stabilizer_placement
from .fatigue import calculate_fatigue_damage
from .pipeline import calculate_full_vibration_analysis
from .fea import run_fea_analysis, generate_campbell_diagram


class VibrationsEngine:
    """Backward-compatible facade -- delegates all methods to submodules."""

    # Steel properties (re-exported as class attributes)
    STEEL_E = STEEL_E
    STEEL_DENSITY = STEEL_DENSITY
    GRAVITY = GRAVITY

    # critical_speeds
    calculate_critical_rpm_axial = staticmethod(calculate_critical_rpm_axial)
    calculate_critical_rpm_lateral = staticmethod(calculate_critical_rpm_lateral)
    calculate_critical_rpm_lateral_multi = staticmethod(calculate_critical_rpm_lateral_multi)

    # stick_slip
    calculate_stick_slip_severity = staticmethod(calculate_stick_slip_severity)

    # mse
    calculate_mse = staticmethod(calculate_mse)

    # stability
    calculate_stability_index = staticmethod(calculate_stability_index)
    generate_vibration_map = staticmethod(generate_vibration_map)
    calculate_vibration_map_3d = staticmethod(calculate_vibration_map_3d)

    # bit_excitation
    calculate_bit_excitation = staticmethod(calculate_bit_excitation)
    check_resonance = staticmethod(check_resonance)

    # stabilizers
    optimize_stabilizer_placement = staticmethod(optimize_stabilizer_placement)

    # fatigue
    calculate_fatigue_damage = staticmethod(calculate_fatigue_damage)

    # pipeline
    calculate_full_vibration_analysis = staticmethod(calculate_full_vibration_analysis)

    # fea
    run_fea_analysis = staticmethod(run_fea_analysis)
    generate_campbell_diagram = staticmethod(generate_campbell_diagram)
