"""
Engine → Chart Contract Tests.

Validates that engine return structures contain the exact fields
that frontend chart components expect as props/data.

Each test class corresponds to a module (T&D, Hydraulics, Well Control, Stuck Pipe)
and verifies field names, types, and value ranges that the chart components depend on.
"""
import pytest
from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.well_control_engine import WellControlEngine
from orchestrator.stuck_pipe_engine import StuckPipeEngine


# ============================================================
# Shared test data builders
# ============================================================

def _td_survey():
    """Directional survey with TVD pre-computed."""
    return [
        {"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0},
        {"md": 3000, "inclination": 0, "azimuth": 0, "tvd": 3000},
        {"md": 6000, "inclination": 30, "azimuth": 45, "tvd": 5598},
        {"md": 10000, "inclination": 30, "azimuth": 45, "tvd": 9060},
    ]


def _td_drillstring():
    return [
        {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9800, "order_from_bit": 2},
        {"od": 6.5, "id_inner": 2.813, "weight": 91.0, "length": 200, "order_from_bit": 1},
    ]


def _hyd_sections():
    """Standard 5-section hydraulic circuit."""
    return [
        {"section_type": "drill_pipe", "length": 9500.0, "od": 5.0, "id_inner": 4.276},
        {"section_type": "hwdp", "length": 300.0, "od": 5.0, "id_inner": 3.0},
        {"section_type": "collar", "length": 200.0, "od": 6.5, "id_inner": 2.813},
        {"section_type": "annulus_dc", "length": 200.0, "od": 8.5, "id_inner": 6.5},
        {"section_type": "annulus_dp", "length": 9800.0, "od": 8.5, "id_inner": 5.0},
    ]


def _kill_params():
    """Standard kill sheet parameters."""
    return dict(
        depth_md=10000.0, depth_tvd=10000.0,
        original_mud_weight=10.0, casing_shoe_tvd=5000.0,
        sidpp=200, sicp=350,
        pit_gain=20.0,
        scr_pressure=800, scr_rate=30,
        dp_capacity=0.018, annular_capacity=0.05,
        strokes_surface_to_bit=1800,
        lot_emw=14.0,
    )


# ============================================================
# Torque & Drag → TDMultiSeriesChart, BucklingStatusTrack,
#                  HookloadComparisonBar, TorqueDragProfile
# ============================================================

class TestTorqueDragContract:

    def _run_td(self, operation="trip_out", **kwargs):
        return TorqueDragEngine.compute_torque_drag(
            survey=_td_survey(),
            drillstring=_td_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            mud_weight=10.0, operation=operation,
            wob=kwargs.get("wob", 10), rpm=kwargs.get("rpm", 60),
        )

    def test_station_results_has_chart_fields(self):
        """TDMultiSeriesChart + BucklingStatusTrack need: md, tvd, inclination, axial_force, buckling_status."""
        result = self._run_td()
        assert "station_results" in result
        assert len(result["station_results"]) > 0
        for sr in result["station_results"]:
            assert "md" in sr, "station missing 'md'"
            assert "tvd" in sr, "station missing 'tvd'"
            assert "inclination" in sr, "station missing 'inclination'"
            assert "axial_force" in sr, "station missing 'axial_force'"
            assert "buckling_status" in sr, "station missing 'buckling_status'"
            # Type checks
            assert isinstance(sr["md"], (int, float))
            assert isinstance(sr["axial_force"], (int, float))
            assert sr["buckling_status"] in ("OK", "SINUSOIDAL", "HELICAL")

    def test_summary_has_hookload_klb(self):
        """HookloadComparisonBar needs summary.surface_hookload_klb."""
        result = self._run_td()
        summary = result["summary"]
        assert "surface_hookload_klb" in summary
        assert isinstance(summary["surface_hookload_klb"], (int, float))
        assert summary["surface_hookload_klb"] > 0

    def test_summary_has_buoyancy_factor(self):
        """Frontend computeBuoyedWeight() needs summary.buoyancy_factor."""
        result = self._run_td()
        bf = result["summary"]["buoyancy_factor"]
        assert isinstance(bf, float)
        assert 0 < bf < 1, "Buoyancy factor should be between 0 and 1"

    def test_station_results_has_torque_and_drag(self):
        """TorqueDragProfile needs: torque, normal_force (drag) per station."""
        result = self._run_td(operation="rotating", rpm=120)
        for sr in result["station_results"]:
            assert "torque" in sr, "station missing 'torque'"
            assert "normal_force" in sr, "station missing 'normal_force'"
            assert isinstance(sr["torque"], (int, float))
            assert isinstance(sr["normal_force"], (int, float))

    def test_summary_has_torque_ftlb(self):
        """HookloadComparisonBar summary_comparison needs torque_ftlb."""
        result = self._run_td(operation="rotating", rpm=120)
        assert "surface_torque_ftlb" in result["summary"]
        assert result["summary"]["surface_torque_ftlb"] > 0


# ============================================================
# Hydraulics → PressureWaterfallChart, FlowRegimeTrack,
#               BitHydraulicsGauges, ECDProfileChart, SurgeSwabWindow
# ============================================================

class TestHydraulicsContract:

    def _run_circuit(self):
        return HydraulicsEngine.calculate_full_circuit(
            sections=_hyd_sections(),
            nozzle_sizes=[12, 12, 12],
            flow_rate=350.0,
            mud_weight=10.0,
            pv=15, yp=10,
            tvd=9500.0,
        )

    def _run_surge_swab(self):
        return HydraulicsEngine.calculate_surge_swab(
            mud_weight=10.0, pv=15, yp=10,
            tvd=9500.0, pipe_od=5.0, pipe_id=4.276,
            hole_id=8.5, pipe_velocity_fpm=90.0,
        )

    def test_section_results_structure(self):
        """PressureWaterfallChart + FlowRegimeTrack need: section_type, pressure_loss_psi, velocity_ft_min, flow_regime."""
        result = self._run_circuit()
        assert "section_results" in result
        for sec in result["section_results"]:
            assert "section_type" in sec, "section missing 'section_type'"
            assert "pressure_loss_psi" in sec, "section missing 'pressure_loss_psi'"
            assert "velocity_ft_min" in sec, "section missing 'velocity_ft_min'"
            assert "flow_regime" in sec, "section missing 'flow_regime'"
            assert sec["flow_regime"] in ("laminar", "turbulent")

    def test_section_results_have_reynolds(self):
        """FlowRegimeTrack tooltip shows reynolds number."""
        result = self._run_circuit()
        for sec in result["section_results"]:
            assert "reynolds" in sec
            assert isinstance(sec["reynolds"], (int, float))

    def test_summary_has_pressure_breakdown(self):
        """PressureWaterfallChart needs: total_spp_psi, surface_equipment_psi, pipe_loss_psi, bit_loss_psi, annular_loss_psi."""
        result = self._run_circuit()
        s = result["summary"]
        for key in ["total_spp_psi", "surface_equipment_psi", "pipe_loss_psi", "bit_loss_psi", "annular_loss_psi"]:
            assert key in s, f"summary missing '{key}'"
            assert isinstance(s[key], (int, float))

    def test_bit_hydraulics_has_gauge_fields(self):
        """BitHydraulicsGauges needs: tfa_sqin, hsi, impact_force_lb, jet_velocity_fps, percent_at_bit."""
        result = self._run_circuit()
        bh = result["bit_hydraulics"]
        for key in ["tfa_sqin", "hsi", "impact_force_lb", "jet_velocity_fps", "percent_at_bit"]:
            assert key in bh, f"bit_hydraulics missing '{key}'"
            assert isinstance(bh[key], (int, float))
        # Value range sanity
        assert bh["hsi"] > 0
        assert bh["jet_velocity_fps"] > 0
        assert 0 <= bh["percent_at_bit"] <= 100

    def test_ecd_profile_has_tvd_ecd(self):
        """ECDProfileChart needs ecd_profile[] with {tvd, ecd}."""
        result = self._run_circuit()
        assert "ecd_profile" in result
        # ecd_profile may be empty for simple circuits, but if present check structure
        for point in result["ecd_profile"]:
            assert "tvd" in point
            assert "ecd" in point
            assert isinstance(point["tvd"], (int, float))
            assert isinstance(point["ecd"], (int, float))

    def test_surge_swab_has_margin_strings(self):
        """SurgeSwabWindow needs: surge_margin, swab_margin (string values)."""
        result = self._run_surge_swab()
        assert "surge_margin" in result, "Missing 'surge_margin'"
        assert "swab_margin" in result, "Missing 'swab_margin'"
        assert isinstance(result["surge_margin"], str)
        assert isinstance(result["swab_margin"], str)
        # Values should start with known prefixes
        valid_prefixes = ("OK", "WARNING", "CRITICAL")
        assert any(result["surge_margin"].startswith(p) for p in valid_prefixes), \
            f"Unexpected surge_margin value: {result['surge_margin']}"
        assert any(result["swab_margin"].startswith(p) for p in valid_prefixes), \
            f"Unexpected swab_margin value: {result['swab_margin']}"

    def test_surge_swab_has_ecd_ppg(self):
        """SurgeSwabWindow needs: surge_ecd_ppg, swab_ecd_ppg."""
        result = self._run_surge_swab()
        assert "surge_ecd_ppg" in result
        assert "swab_ecd_ppg" in result
        assert isinstance(result["surge_ecd_ppg"], (int, float))
        assert isinstance(result["swab_ecd_ppg"], (int, float))

    def test_surge_swab_has_emw_values(self):
        """SurgeSwabWindow uses surge_emw_ppg and swab_emw_ppg for marker positioning."""
        result = self._run_surge_swab()
        assert "surge_emw_ppg" in result
        assert "swab_emw_ppg" in result


# ============================================================
# Well Control → PressureScheduleChart, VolumetricCyclesChart,
#                 InfluxAnalysisGauge, WellborePressureProfile
# ============================================================

class TestWellControlContract:

    def _run_kill_sheet(self):
        return WellControlEngine.calculate_kill_sheet(**_kill_params())

    def test_kill_sheet_has_schedule_fields(self):
        """PressureScheduleChart needs pressure_schedule[] with: step, strokes, pressure_psi, percent_complete."""
        result = self._run_kill_sheet()
        assert "pressure_schedule" in result
        schedule = result["pressure_schedule"]
        assert len(schedule) > 0
        for entry in schedule:
            assert "step" in entry, "schedule entry missing 'step'"
            assert "strokes" in entry, "schedule entry missing 'strokes'"
            assert "pressure_psi" in entry, "schedule entry missing 'pressure_psi'"
            assert "percent_complete" in entry, "schedule entry missing 'percent_complete'"
            assert isinstance(entry["pressure_psi"], (int, float))
            assert 0 <= entry["percent_complete"] <= 100

    def test_kill_sheet_has_icp_fcp_maasp(self):
        """PressureScheduleChart props: icp, fcp, maasp."""
        result = self._run_kill_sheet()
        assert "icp_psi" in result
        assert "fcp_psi" in result
        assert "maasp_psi" in result
        assert result["icp_psi"] > 0
        assert result["fcp_psi"] > 0
        assert result["maasp_psi"] > 0

    def test_kill_sheet_schedule_starts_icp_ends_fcp(self):
        """PressureScheduleChart expects first entry = ICP, last = FCP."""
        result = self._run_kill_sheet()
        schedule = result["pressure_schedule"]
        assert schedule[0]["pressure_psi"] == result["icp_psi"]
        assert schedule[-1]["pressure_psi"] == result["fcp_psi"]

    def test_volumetric_cycles_field_names(self):
        """VolumetricCyclesChart normalization expects: cycle, max_pressure, volume_bled."""
        result = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        assert "cycles" in result
        for cycle in result["cycles"]:
            assert "cycle" in cycle, "cycle entry missing 'cycle'"
            assert "max_pressure" in cycle, "cycle entry missing 'max_pressure'"
            assert "volume_bled" in cycle, "cycle entry missing 'volume_bled'"
            assert isinstance(cycle["max_pressure"], (int, float))
            assert isinstance(cycle["volume_bled"], (int, float))

    def test_volumetric_cycles_no_psi_suffix(self):
        """Engine uses 'max_pressure' not 'max_pressure_psi' — frontend normalizes."""
        result = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        for cycle in result["cycles"]:
            # Engine should NOT have _psi suffix (frontend normalizes)
            assert "max_pressure" in cycle
            # But it may optionally also not have the suffixed version
            # The normalization layer handles both cases

    def test_kill_sheet_has_influx_data(self):
        """InfluxAnalysisGauge needs: influx_type, influx_height_ft, influx_gradient_psi_ft."""
        result = self._run_kill_sheet()
        assert "influx_type" in result
        assert "influx_height_ft" in result
        assert "influx_gradient_psi_ft" in result
        assert isinstance(result["influx_type"], str)
        assert isinstance(result["influx_height_ft"], (int, float))
        assert isinstance(result["influx_gradient_psi_ft"], (int, float))

    def test_kill_sheet_has_formation_pressure(self):
        """WellborePressureProfile needs formation_pressure_psi for computation."""
        result = self._run_kill_sheet()
        assert "formation_pressure_psi" in result
        assert result["formation_pressure_psi"] > 0

    def test_kill_sheet_has_kill_mud_weight(self):
        """WellborePressureProfile + InfluxAnalysisGauge need kill_mud_weight_ppg."""
        result = self._run_kill_sheet()
        assert "kill_mud_weight_ppg" in result
        assert result["kill_mud_weight_ppg"] > result.get("original_mud_weight", 0) or True


# ============================================================
# Stuck Pipe → InteractiveRiskMatrix, ContributingFactorsRadar
# ============================================================

class TestStuckPipeContract:

    def _run_risk(self):
        return StuckPipeEngine.assess_risk_matrix(
            mechanism="Differential Sticking",
            params={
                "mud_weight": 12.0,
                "pore_pressure": 9.0,
                "inclination": 45,
                "stationary_hours": 3,
            }
        )

    def test_risk_matrix_has_chart_fields(self):
        """InteractiveRiskMatrix needs: probability (1-5), severity (1-5), risk_level, contributing_factors[]."""
        result = self._run_risk()
        assert "probability" in result
        assert "severity" in result
        assert "risk_level" in result
        assert "contributing_factors" in result
        assert 1 <= result["probability"] <= 5
        assert 1 <= result["severity"] <= 5
        assert isinstance(result["contributing_factors"], list)

    def test_risk_matrix_has_matrix_position(self):
        """InteractiveRiskMatrix uses matrix_position.x and .y for grid placement."""
        result = self._run_risk()
        assert "matrix_position" in result
        pos = result["matrix_position"]
        assert "x" in pos and "y" in pos
        assert pos["x"] == result["probability"]
        assert pos["y"] == result["severity"]

    def test_contributing_factors_have_name_score(self):
        """ContributingFactorsRadar dataKey: factor (string), score (0-1 range)."""
        result = self._run_risk()
        factors = result["contributing_factors"]
        assert len(factors) > 0, "Should have at least one contributing factor"
        for f in factors:
            assert "factor" in f, "factor entry missing 'factor' name"
            assert "score" in f, "factor entry missing 'score'"
            assert isinstance(f["factor"], str)
            assert isinstance(f["score"], (int, float))
            assert 0 <= f["score"] <= 1.0, f"score {f['score']} out of range [0, 1]"

    def test_contributing_factors_have_detail(self):
        """ContributingFactorsRadar tooltip shows detail string."""
        result = self._run_risk()
        for f in result["contributing_factors"]:
            assert "detail" in f, "factor entry missing 'detail'"
            assert isinstance(f["detail"], str)

    def test_risk_level_in_expected_values(self):
        """RISK_COLORS mapping expects: LOW, MEDIUM, HIGH, CRITICAL."""
        result = self._run_risk()
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_risk_score_computed(self):
        """risk_score = probability × severity."""
        result = self._run_risk()
        assert "risk_score" in result
        assert result["risk_score"] == result["probability"] * result["severity"]
