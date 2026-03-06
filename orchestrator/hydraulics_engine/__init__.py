"""Hydraulics Engine — backward-compatible facade.

Package split from monolithic hydraulics_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.hydraulics_engine import HydraulicsEngine
"""
from .pt_corrections import correct_density_pt, correct_viscosity_pt, calculate_temperature_profile
from .rheology import (
    pressure_loss_bingham,
    pressure_loss_power_law,
    fit_herschel_bulkley,
    pressure_loss_herschel_bulkley,
)
from .bit_hydraulics import calculate_bit_hydraulics, CD
from .ecd import calculate_ecd_dynamic, calculate_bha_pressure_breakdown, generate_pressure_waterfall
from .full_circuit import calculate_full_circuit
from .surge_swab import calculate_surge_swab


class HydraulicsEngine:
    """Backward-compatible facade — delegates all methods to sub-modules."""

    # Discharge coefficient
    CD = CD

    # P/T corrections
    correct_density_pt = staticmethod(correct_density_pt)
    correct_viscosity_pt = staticmethod(correct_viscosity_pt)
    calculate_temperature_profile = staticmethod(calculate_temperature_profile)

    # Rheological models
    pressure_loss_bingham = staticmethod(pressure_loss_bingham)
    pressure_loss_power_law = staticmethod(pressure_loss_power_law)
    fit_herschel_bulkley = staticmethod(fit_herschel_bulkley)
    pressure_loss_herschel_bulkley = staticmethod(pressure_loss_herschel_bulkley)

    # Bit hydraulics
    calculate_bit_hydraulics = staticmethod(calculate_bit_hydraulics)

    # ECD & BHA
    calculate_ecd_dynamic = staticmethod(calculate_ecd_dynamic)
    calculate_bha_pressure_breakdown = staticmethod(calculate_bha_pressure_breakdown)
    generate_pressure_waterfall = staticmethod(generate_pressure_waterfall)

    # Full circuit
    calculate_full_circuit = staticmethod(calculate_full_circuit)

    # Surge & Swab
    calculate_surge_swab = staticmethod(calculate_surge_swab)

    @staticmethod
    def _zero_result():
        from .rheology import _zero_result
        return _zero_result()
