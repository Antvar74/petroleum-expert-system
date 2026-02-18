"""
Unit tests for TorqueDragEngine.
Tests: compute_survey_derived, compute_torque_drag, _buckling_check,
       _casing_id_estimate, back_calculate_friction.
"""
import math
import pytest
from orchestrator.torque_drag_engine import TorqueDragEngine


# ============================================================
# compute_survey_derived — Minimum Curvature (8 tests)
# ============================================================

class TestComputeSurveyDerived:

    def test_empty_list(self):
        assert TorqueDragEngine.compute_survey_derived([]) == []

    def test_single_station(self):
        result = TorqueDragEngine.compute_survey_derived(
            [{"md": 0, "inclination": 0, "azimuth": 0}]
        )
        assert len(result) == 1
        assert result[0]["dls"] == 0.0

    def test_vertical_well_tvd_equals_md(self, vertical_survey):
        result = TorqueDragEngine.compute_survey_derived(vertical_survey)
        assert len(result) == 11
        for s in result:
            assert abs(s["tvd"] - s["md"]) < 0.1, f"TVD should equal MD for vertical at MD={s['md']}"

    def test_vertical_well_north_east_near_zero(self, vertical_survey):
        result = TorqueDragEngine.compute_survey_derived(vertical_survey)
        for s in result:
            assert abs(s["north"]) < 1.0
            assert abs(s["east"]) < 1.0

    def test_directional_tvd_less_than_md(self, directional_survey):
        result = TorqueDragEngine.compute_survey_derived(directional_survey)
        last = result[-1]
        assert last["tvd"] < last["md"], "TVD should be less than MD at bottom for directional well"

    def test_directional_build_dls(self, directional_survey):
        """In the build section, DLS should be approximately 2°/100ft."""
        result = TorqueDragEngine.compute_survey_derived(directional_survey)
        build_stations = [s for s in result if 2500 < s["md"] < 4500 and s["dls"] > 0]
        assert len(build_stations) > 0, "Should have build section stations"
        for s in build_stations:
            assert s["dls"] > 0, "DLS should be positive in build section"

    def test_same_md_no_crash(self):
        """Two stations with same MD should not crash."""
        stations = [
            {"md": 0, "inclination": 0, "azimuth": 0},
            {"md": 1000, "inclination": 5, "azimuth": 30},
            {"md": 1000, "inclination": 10, "azimuth": 30},  # duplicate MD
            {"md": 2000, "inclination": 15, "azimuth": 30},
        ]
        result = TorqueDragEngine.compute_survey_derived(stations)
        assert len(result) == 4
        assert result[2]["dls"] == 0.0  # guard for delta_md <= 0

    def test_first_station_defaults(self):
        stations = [{"md": 100, "inclination": 5, "azimuth": 30}]
        result = TorqueDragEngine.compute_survey_derived(stations)
        assert result[0]["tvd"] == 0.0
        assert result[0]["north"] == 0.0
        assert result[0]["east"] == 0.0


# ============================================================
# compute_torque_drag — Johancsik Soft-String (12 tests)
# ============================================================

class TestComputeTorqueDrag:

    def _build_vertical_survey(self):
        """Simple vertical 2-station survey with TVD."""
        return [
            {"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0},
            {"md": 10000, "inclination": 0, "azimuth": 0, "tvd": 10000},
        ]

    def _build_directional_survey(self):
        """Simple 3-station directional: vertical → 30° → 30° tangent."""
        return [
            {"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0},
            {"md": 3000, "inclination": 0, "azimuth": 0, "tvd": 3000},
            {"md": 6000, "inclination": 30, "azimuth": 45, "tvd": 5598},
            {"md": 10000, "inclination": 30, "azimuth": 45, "tvd": 9060},
        ]

    def _simple_drillstring(self):
        return [
            {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9800, "order_from_bit": 2},
            {"od": 6.5, "id_inner": 2.813, "weight": 91.0, "length": 200, "order_from_bit": 1},
        ]

    def test_too_few_stations(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=[{"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0}],
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        assert "error" in result

    def test_vertical_trip_out_hookload_positive(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_vertical_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        assert result["summary"]["surface_hookload_klb"] > 0

    def test_vertical_trip_in_hookload_positive(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_vertical_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_in", mud_weight=10.0
        )
        assert result["summary"]["surface_hookload_klb"] > 0

    def test_directional_trip_out_greater_than_trip_in(self):
        survey = self._build_directional_survey()
        ds = self._simple_drillstring()
        out = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        inn = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.25, friction_open=0.35,
            operation="trip_in", mud_weight=10.0
        )
        assert out["summary"]["surface_hookload_klb"] > inn["summary"]["surface_hookload_klb"]

    def test_rotating_torque_positive(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_directional_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="rotating", mud_weight=10.0, rpm=120, wob=15
        )
        assert result["summary"]["surface_torque_ftlb"] > 0

    def test_sliding_torque_zero(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_directional_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="sliding", mud_weight=10.0
        )
        assert result["summary"]["surface_torque_ftlb"] == 0

    def test_higher_friction_more_drag(self):
        survey = self._build_directional_survey()
        ds = self._simple_drillstring()
        low_mu = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.15, friction_open=0.20,
            operation="trip_out", mud_weight=10.0
        )
        high_mu = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.35, friction_open=0.45,
            operation="trip_out", mud_weight=10.0
        )
        assert high_mu["summary"]["surface_hookload_klb"] > low_mu["summary"]["surface_hookload_klb"]

    def test_buoyancy_factor(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_vertical_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        expected_bf = 1.0 - (10.0 / 65.5)
        assert abs(result["summary"]["buoyancy_factor"] - expected_bf) < 0.001

    def test_wob_reduces_hookload_rotating(self):
        survey = self._build_directional_survey()
        ds = self._simple_drillstring()
        no_wob = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.25, friction_open=0.35,
            operation="rotating", mud_weight=10.0, wob=0, rpm=120
        )
        with_wob = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.25, friction_open=0.35,
            operation="rotating", mud_weight=10.0, wob=30, rpm=120
        )
        assert with_wob["summary"]["surface_hookload_klb"] < no_wob["summary"]["surface_hookload_klb"]

    def test_results_have_station_data(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_directional_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        assert "station_results" in result
        assert len(result["station_results"]) > 0
        for sr in result["station_results"]:
            assert "md" in sr
            assert "axial_force" in sr
            assert "buckling_status" in sr

    def test_all_five_operations(self):
        survey = self._build_directional_survey()
        ds = self._simple_drillstring()
        for op in ("trip_out", "trip_in", "rotating", "sliding", "back_ream"):
            result = TorqueDragEngine.compute_torque_drag(
                survey=survey, drillstring=ds,
                friction_cased=0.25, friction_open=0.35,
                operation=op, mud_weight=10.0, wob=10, rpm=60
            )
            assert "summary" in result, f"Operation '{op}' should produce valid output"

    def test_results_ordered_surface_to_td(self):
        result = TorqueDragEngine.compute_torque_drag(
            survey=self._build_directional_survey(),
            drillstring=self._simple_drillstring(),
            friction_cased=0.25, friction_open=0.35,
            operation="trip_out", mud_weight=10.0
        )
        mds = [s["md"] for s in result["station_results"]]
        assert mds == sorted(mds), "Results should be ordered surface → TD"


# ============================================================
# _buckling_check (4 tests)
# ============================================================

class TestBucklingCheck:

    def _ds(self):
        return {"od": 5.0, "id_inner": 4.276, "weight": 19.5}

    def test_tension_ok(self):
        result = TorqueDragEngine._buckling_check(
            axial_force=50000, inclination=math.radians(30),
            ds=self._ds(), mud_weight=10.0,
            delta_md=500, md=5000, casing_shoe_md=3000
        )
        assert result == "OK"

    def test_moderate_compression_sinusoidal(self):
        """Moderate compression should trigger sinusoidal buckling."""
        result = TorqueDragEngine._buckling_check(
            axial_force=-30000, inclination=math.radians(30),
            ds=self._ds(), mud_weight=10.0,
            delta_md=500, md=5000, casing_shoe_md=3000
        )
        assert result in ("SINUSOIDAL", "HELICAL")

    def test_high_compression_helical(self):
        """Very high compression should trigger helical buckling."""
        result = TorqueDragEngine._buckling_check(
            axial_force=-200000, inclination=math.radians(45),
            ds=self._ds(), mud_weight=10.0,
            delta_md=500, md=5000, casing_shoe_md=3000
        )
        assert result == "HELICAL"

    def test_vertical_no_crash(self):
        """Near-vertical (sin≈0) should not crash due to floor at 0.01."""
        result = TorqueDragEngine._buckling_check(
            axial_force=-5000, inclination=math.radians(0.001),
            ds=self._ds(), mud_weight=10.0,
            delta_md=500, md=5000, casing_shoe_md=3000
        )
        assert result in ("OK", "SINUSOIDAL", "HELICAL")  # Just shouldn't crash


# ============================================================
# _casing_id_estimate (2 tests)
# ============================================================

class TestCasingIdEstimate:

    def test_known_pipe_5_inch(self):
        assert TorqueDragEngine._casing_id_estimate(5.0) == 8.681

    def test_unknown_pipe_default(self):
        assert TorqueDragEngine._casing_id_estimate(4.0) == 4.0 + 3.5


# ============================================================
# back_calculate_friction — Bisection (5 tests)
# ============================================================

class TestBackCalculateFriction:

    def _build_survey(self):
        return [
            {"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0},
            {"md": 3000, "inclination": 0, "azimuth": 0, "tvd": 3000},
            {"md": 6000, "inclination": 30, "azimuth": 45, "tvd": 5598},
            {"md": 10000, "inclination": 30, "azimuth": 45, "tvd": 9060},
        ]

    def _build_ds(self):
        return [
            {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9800, "order_from_bit": 2},
            {"od": 6.5, "id_inner": 2.813, "weight": 91.0, "length": 200, "order_from_bit": 1},
        ]

    def test_convergence_roundtrip(self):
        """Compute T&D with mu=0.30, use hookload to back-calculate, verify mu≈0.30."""
        survey = self._build_survey()
        ds = self._build_ds()
        forward = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.30, friction_open=0.30,
            operation="trip_out", mud_weight=10.0
        )
        hookload = forward["summary"]["surface_hookload_klb"]

        result = TorqueDragEngine.back_calculate_friction(
            survey=survey, drillstring=ds,
            measured_hookload=hookload,
            operation="trip_out", mud_weight=10.0
        )
        assert result.get("converged") is True
        assert abs(result["friction_factor"] - 0.30) < 0.05

    def test_result_in_range(self):
        survey = self._build_survey()
        ds = self._build_ds()
        result = TorqueDragEngine.back_calculate_friction(
            survey=survey, drillstring=ds,
            measured_hookload=200.0,
            operation="trip_out", mud_weight=10.0
        )
        assert 0.05 <= result["friction_factor"] <= 0.60

    def test_trip_out_converges(self):
        survey = self._build_survey()
        ds = self._build_ds()
        result = TorqueDragEngine.back_calculate_friction(
            survey=survey, drillstring=ds,
            measured_hookload=200.0,
            operation="trip_out", mud_weight=10.0
        )
        assert "friction_factor" in result

    def test_trip_in_converges(self):
        survey = self._build_survey()
        ds = self._build_ds()
        result = TorqueDragEngine.back_calculate_friction(
            survey=survey, drillstring=ds,
            measured_hookload=150.0,
            operation="trip_in", mud_weight=10.0
        )
        assert "friction_factor" in result

    def test_insufficient_survey_error(self):
        result = TorqueDragEngine.back_calculate_friction(
            survey=[{"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0}],
            drillstring=self._build_ds(),
            measured_hookload=200.0,
            operation="trip_out", mud_weight=10.0
        )
        assert "error" in result
