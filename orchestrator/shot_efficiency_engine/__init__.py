"""Shot Efficiency Engine -- backward-compatible facade.

Package split from monolithic shot_efficiency_engine.py.
All existing imports continue to work unchanged.
"""
from .petrophysics import (
    calculate_porosity,
    calculate_vshale,
    calculate_water_saturation,
    calculate_sw_simandoux,
    calculate_sw_indonesia,
    calculate_sw_auto,
    calculate_porosity_sonic,
)
from .permeability import (
    calculate_permeability_timur,
    calculate_permeability_coates,
    classify_hydrocarbon_type,
)
from .skin import calculate_skin_factor, PHASING_DATA
from .net_pay import identify_net_pay_intervals
from .ranking import rank_intervals
from .log_parser import parse_log_data, parse_las_file
from .pipeline import calculate_full_shot_efficiency


class ShotEfficiencyEngine:
    """Backward-compatible facade -- delegates all methods to submodules."""

    PHASING_DATA = PHASING_DATA

    calculate_porosity = staticmethod(calculate_porosity)
    calculate_vshale = staticmethod(calculate_vshale)
    calculate_water_saturation = staticmethod(calculate_water_saturation)
    calculate_sw_simandoux = staticmethod(calculate_sw_simandoux)
    calculate_sw_indonesia = staticmethod(calculate_sw_indonesia)
    calculate_sw_auto = staticmethod(calculate_sw_auto)
    calculate_porosity_sonic = staticmethod(calculate_porosity_sonic)
    calculate_permeability_timur = staticmethod(calculate_permeability_timur)
    calculate_permeability_coates = staticmethod(calculate_permeability_coates)
    classify_hydrocarbon_type = staticmethod(classify_hydrocarbon_type)
    calculate_skin_factor = staticmethod(calculate_skin_factor)
    identify_net_pay_intervals = staticmethod(identify_net_pay_intervals)
    rank_intervals = staticmethod(rank_intervals)
    parse_log_data = staticmethod(parse_log_data)
    parse_las_file = staticmethod(parse_las_file)
    calculate_full_shot_efficiency = staticmethod(calculate_full_shot_efficiency)
