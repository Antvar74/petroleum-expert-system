"""Unit tests for TransientFlowEngine — kick migration, kill circulation, surge/swab."""
import pytest
from orchestrator.transient_flow_engine import TransientFlowEngine


class TestZFactor:
    """Test standalone DAK Z-factor calculation."""

    def test_z_factor_at_standard_conditions(self):
        """Z should be ~1.0 at low pressure."""
        z = TransientFlowEngine._z_factor_dak(14.7, 60.0, 0.65)
        assert 0.95 <= z <= 1.05

    def test_z_factor_at_high_pressure(self):
        """Z should be less than 1 at moderate pressure."""
        z = TransientFlowEngine._z_factor_dak(3000, 200.0, 0.65)
        assert 0.5 < z < 1.0

    def test_z_factor_zero_pressure(self):
        """Should return 1.0 for non-physical inputs."""
        z = TransientFlowEngine._z_factor_dak(0, 200.0, 0.65)
        assert z == 1.0


class TestKickMigration:
    """Test gas kick migration simulation."""

    def test_gas_kick_rises_over_time(self):
        """Gas kick should migrate upward, increasing casing pressure."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=60,
        )
        assert len(result["time_series"]) > 1
        # Casing pressure should increase as gas migrates up
        first_cp = result["time_series"][0]["casing_pressure_psi"]
        last_cp = result["time_series"][-1]["casing_pressure_psi"]
        assert last_cp >= first_cp

    def test_kick_migration_respects_z_factor(self):
        """Gas volume should expand as it moves to lower pressure zones."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=60,
        )
        first_vol = result["time_series"][0]["kick_volume_bbl"]
        last_vol = result["time_series"][-1]["kick_volume_bbl"]
        assert last_vol >= first_vol

    def test_kick_top_moves_upward(self):
        """Kick top TVD should decrease over time."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=60,
        )
        first_top = result["time_series"][0]["kick_top_tvd"]
        last_top = result["time_series"][-1]["kick_top_tvd"]
        assert last_top < first_top

    def test_time_series_has_z_factor(self):
        """Each time step should include Z-factor."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=10,
        )
        for point in result["time_series"]:
            assert "z_factor" in point
            assert 0.05 <= point["z_factor"] <= 3.0

    def test_max_casing_pressure_reported(self):
        """Result should include max casing pressure."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=30,
        )
        assert "max_casing_pressure" in result
        assert result["max_casing_pressure"] >= 350  # At least initial SICP

    def test_surface_arrival_detected(self):
        """Gas should eventually reach surface in extended simulation."""
        result = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=5000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=600,
            migration_rate_ft_hr=2000.0,
        )
        assert result["surface_arrival_min"] is not None
        assert result["surface_arrival_min"] > 0


class TestKillCirculation:
    """Test kill circulation simulation."""

    def test_drillers_method_icp(self):
        """Driller's method should start at ICP = SIDPP + SCR."""
        result = TransientFlowEngine.simulate_kill_circulation(
            well_depth_tvd=10000, mud_weight=10.0, kill_mud_weight=11.0,
            sidpp=200, scr=400, strokes_to_bit=1000, strokes_bit_to_surface=2000,
            method="drillers",
        )
        assert "drill_pipe_pressure" in result
        assert "casing_pressure" in result
        icp = result["drill_pipe_pressure"][0]["pressure_psi"]
        assert icp == pytest.approx(200 + 400, rel=0.05)

    def test_drillers_method_fcp(self):
        """FCP should be SCR * (KMW / OMW)."""
        result = TransientFlowEngine.simulate_kill_circulation(
            well_depth_tvd=10000, mud_weight=10.0, kill_mud_weight=11.0,
            sidpp=200, scr=400, strokes_to_bit=1000, strokes_bit_to_surface=2000,
            method="drillers",
        )
        assert result["fcp"] == pytest.approx(400 * (11.0 / 10.0), rel=0.01)

    def test_drillers_method_has_multiple_points(self):
        """Should produce enough data points for charting."""
        result = TransientFlowEngine.simulate_kill_circulation(
            well_depth_tvd=10000, mud_weight=10.0, kill_mud_weight=11.0,
            sidpp=200, scr=400, strokes_to_bit=1000, strokes_bit_to_surface=2000,
            method="drillers",
        )
        assert len(result["drill_pipe_pressure"]) > 10

    def test_wait_weight_method(self):
        """Wait-and-Weight should show ICP→FCP transition in one circulation."""
        result = TransientFlowEngine.simulate_kill_circulation(
            well_depth_tvd=10000, mud_weight=10.0, kill_mud_weight=11.0,
            sidpp=200, scr=400, strokes_to_bit=1000, strokes_bit_to_surface=2000,
            method="wait_weight",
        )
        # ICP at start
        assert result["drill_pipe_pressure"][0]["pressure_psi"] == pytest.approx(600, rel=0.05)
        # DPP should decrease to FCP
        last_dpp = result["drill_pipe_pressure"][-1]["pressure_psi"]
        assert last_dpp == pytest.approx(result["fcp"], rel=0.05)

    def test_kill_result_contains_summary(self):
        """Result should include ICP, FCP, total strokes."""
        result = TransientFlowEngine.simulate_kill_circulation(
            well_depth_tvd=10000, mud_weight=10.0, kill_mud_weight=11.0,
            sidpp=200, scr=400, strokes_to_bit=1000, strokes_bit_to_surface=2000,
        )
        assert "icp" in result
        assert "fcp" in result
        assert "total_strokes" in result
        assert result["total_strokes"] > 0


class TestSurgeSwab:
    """Test surge/swab transient estimation."""

    def test_surge_produces_positive_delta_p(self):
        """Running in (surge) should produce positive pressure increase."""
        result = TransientFlowEngine.estimate_surge_swab(
            trip_speed_ft_min=90, pipe_od=5.0, hole_id=8.5,
            mud_weight=10.0, pv=15, yp=10, pipe_length_ft=10000,
            is_surge=True,
        )
        assert result["delta_p_psi"] > 0
        assert result["ecd_ppg"] > 10.0
        assert result["type"] == "surge"

    def test_swab_reduces_ecd(self):
        """Pulling out (swab) should reduce ECD below mud weight."""
        result = TransientFlowEngine.estimate_surge_swab(
            trip_speed_ft_min=90, pipe_od=5.0, hole_id=8.5,
            mud_weight=10.0, pv=15, yp=10, pipe_length_ft=10000,
            is_surge=False,
        )
        assert result["ecd_ppg"] < 10.0
        assert result["type"] == "swab"

    def test_higher_speed_more_pressure(self):
        """Faster tripping should produce more surge pressure."""
        slow = TransientFlowEngine.estimate_surge_swab(
            trip_speed_ft_min=30, pipe_od=5.0, hole_id=8.5,
            mud_weight=10.0, pv=15, yp=10, pipe_length_ft=10000,
        )
        fast = TransientFlowEngine.estimate_surge_swab(
            trip_speed_ft_min=120, pipe_od=5.0, hole_id=8.5,
            mud_weight=10.0, pv=15, yp=10, pipe_length_ft=10000,
        )
        assert fast["delta_p_psi"] > slow["delta_p_psi"]

    def test_clinging_factor_included(self):
        """Result should include Burkhardt clinging factor."""
        result = TransientFlowEngine.estimate_surge_swab(
            trip_speed_ft_min=90, pipe_od=5.0, hole_id=8.5,
            mud_weight=10.0, pv=15, yp=10, pipe_length_ft=10000,
        )
        assert "clinging_factor" in result
        assert 0 < result["clinging_factor"] < 1
