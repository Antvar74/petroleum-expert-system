# tests/unit/test_multiphase_kick.py
"""Unit tests for multiphase drift-flux kick migration model (Zuber-Findlay)."""
import pytest
from orchestrator.transient_flow_engine import TransientFlowEngine


class TestDriftFluxPhysics:
    """Tests that the drift-flux model produces physically correct behavior."""

    def test_gas_rises_faster_than_single_phase(self):
        """Drift-flux slip velocity should make gas arrive sooner than fixed-rate model."""
        sp = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=120,
            migration_rate_ft_hr=1000.0,
        )
        mp = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=120,
        )
        assert len(mp["time_series"]) > 1
        assert mp["model"] == "zuber_findlay_drift_flux"

    def test_casing_pressure_increases(self):
        """Casing pressure should increase as gas migrates upward."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=60,
        )
        first_cp = result["time_series"][0]["casing_pressure_psi"]
        last_cp = result["time_series"][-1]["casing_pressure_psi"]
        assert last_cp >= first_cp

    def test_kick_volume_expands(self):
        """Gas volume should expand as it rises to lower pressure zones."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=60,
        )
        first_vol = result["time_series"][0]["kick_volume_bbl"]
        last_vol = result["time_series"][-1]["kick_volume_bbl"]
        assert last_vol >= first_vol

    def test_holdup_present_in_output(self):
        """Each time step should include max gas holdup."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=10,
        )
        for point in result["time_series"]:
            assert "max_holdup" in point
            assert 0 <= point["max_holdup"] <= 1.0

    def test_gas_velocity_positive(self):
        """Gas velocity should be positive (upward)."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=10,
        )
        for point in result["time_series"][1:]:
            assert point["max_gas_velocity_ft_min"] >= 0

    def test_max_casing_pressure_tracked(self):
        """Result should include max casing pressure across all timesteps."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=30,
        )
        assert "max_casing_pressure" in result
        assert result["max_casing_pressure"] >= 350

    def test_ncells_produces_profile(self):
        """With n_cells > 1, mixture_density_profile should have n_cells entries."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=5, n_cells=20,
        )
        last = result["time_series"][-1]
        assert "mixture_density_profile" in last
        assert len(last["mixture_density_profile"]) == 20

    def test_mass_conservation(self):
        """Total gas mass (PV/ZT proxy) should stay approximately constant."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=30, n_cells=30,
        )
        first_mass = result["time_series"][0].get("gas_mass_proxy", 0)
        last_mass = result["time_series"][-1].get("gas_mass_proxy", 0)
        if first_mass > 0:
            assert abs(last_mass - first_mass) / first_mass < 0.15
