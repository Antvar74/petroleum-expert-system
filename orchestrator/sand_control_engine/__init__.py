"""Sand Control Engine — backward-compatible facade.

Package split from monolithic sand_control_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.sand_control_engine import SandControlEngine
"""
from .psd import analyze_grain_distribution, select_gravel_size
from .screen import select_screen_slot
from .drawdown import calculate_critical_drawdown
from .gravel_volume import calculate_gravel_volume
from .skin import calculate_skin_factor
from .completion_type import evaluate_completion_type
from .pipeline import calculate_full_sand_control


class SandControlEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Class-level constants (preserved from monolith)
    SIEVE_SIZES_MM = [4.75, 2.0, 0.85, 0.425, 0.25, 0.15, 0.075, 0.045]
    DEFAULT_PACK_FACTOR = 1.4

    analyze_grain_distribution = staticmethod(analyze_grain_distribution)
    select_gravel_size = staticmethod(select_gravel_size)
    select_screen_slot = staticmethod(select_screen_slot)
    calculate_critical_drawdown = staticmethod(calculate_critical_drawdown)
    calculate_gravel_volume = staticmethod(calculate_gravel_volume)
    calculate_skin_factor = staticmethod(calculate_skin_factor)
    evaluate_completion_type = staticmethod(evaluate_completion_type)
    calculate_full_sand_control = staticmethod(calculate_full_sand_control)
