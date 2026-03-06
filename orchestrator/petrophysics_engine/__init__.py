"""Petrophysics Engine — backward-compatible facade.

Package split from monolithic petrophysics_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.petrophysics_engine import PetrophysicsEngine
"""
from .constants import MNEMONIC_MAP, LITHOLOGY
from .las_parser import parse_las_file, parse_las_content
from .water_saturation import calculate_water_saturation_advanced
from .permeability import calculate_permeability_advanced
from .crossplots import generate_pickett_plot, crossplot_density_neutron
from .evaluation import run_full_evaluation


class PetrophysicsEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Reference data
    MNEMONIC_MAP = MNEMONIC_MAP
    LITHOLOGY = LITHOLOGY

    # LAS parsing
    parse_las_file = staticmethod(parse_las_file)
    parse_las_content = staticmethod(parse_las_content)

    # Water saturation
    calculate_water_saturation_advanced = staticmethod(calculate_water_saturation_advanced)

    # Permeability
    calculate_permeability_advanced = staticmethod(calculate_permeability_advanced)

    # Crossplots
    generate_pickett_plot = staticmethod(generate_pickett_plot)
    crossplot_density_neutron = staticmethod(crossplot_density_neutron)

    # Full evaluation
    run_full_evaluation = staticmethod(run_full_evaluation)
