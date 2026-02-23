"""
V&V: Torque & Drag engine against SPE 11380 (Johancsik et al. 1984).
Validates hookload predictions for tripping in/out against published benchmark.
"""
import pytest
from orchestrator.torque_drag_engine import TorqueDragEngine
from tests.validation.benchmark_data import JOHANCSIK_WELL
from tests.validation.conftest import assert_within_tolerance


class TestTorqueDragValidation:
    """Validate T&D engine against SPE 11380 benchmark data."""

    def _run_td(self, operation: str):
        bm = JOHANCSIK_WELL
        return TorqueDragEngine.compute_torque_drag(
            survey=bm["survey"],
            drillstring=bm["drillstring"],
            mud_weight=bm["mud_weight"],
            friction_cased=bm["friction_oh"],
            friction_open=bm["friction_oh"],
            wob=0,
            rpm=0,
            operation=operation,
        )

    def test_hookload_tripping_out_within_tolerance(self):
        """SPE 11380: Hookload tripping out must match within 15%."""
        result = self._run_td("trip_out")
        hookload = result["summary"]["surface_hookload_klb"]
        expected = JOHANCSIK_WELL["expected"]["hookload_trip_out_klb"]
        assert_within_tolerance(
            hookload,
            expected["value"],
            expected["tolerance_pct"],
            label=f"SPE 11380 Trip Out Hookload",
        )

    def test_hookload_tripping_in_within_tolerance(self):
        """SPE 11380: Hookload tripping in must match within 15%."""
        result = self._run_td("trip_in")
        hookload = result["summary"]["surface_hookload_klb"]
        expected = JOHANCSIK_WELL["expected"]["hookload_trip_in_klb"]
        assert_within_tolerance(
            hookload,
            expected["value"],
            expected["tolerance_pct"],
            label=f"SPE 11380 Trip In Hookload",
        )

    def test_buoyancy_factor_correct(self):
        """Buoyancy factor BF = 1 - MW/65.5 for steel drill pipe."""
        result = self._run_td("trip_out")
        bf = result["summary"]["buoyancy_factor"]
        expected_bf = 1.0 - JOHANCSIK_WELL["mud_weight"] / 65.5
        assert abs(bf - expected_bf) < 0.01, f"BF={bf}, expected={expected_bf:.4f}"

    def test_hookload_trip_out_greater_than_trip_in(self):
        """Physics check: trip-out hookload must exceed trip-in (friction opposes motion)."""
        result_out = self._run_td("trip_out")
        result_in = self._run_td("trip_in")
        hl_out = result_out["summary"]["surface_hookload_klb"]
        hl_in = result_in["summary"]["surface_hookload_klb"]
        assert hl_out > hl_in, (
            f"Trip-out hookload ({hl_out:.1f} klb) should exceed "
            f"trip-in ({hl_in:.1f} klb)"
        )

    def test_station_results_monotonic_depth(self):
        """Station results should be in monotonically increasing MD order."""
        result = self._run_td("trip_out")
        mds = [s["md"] for s in result["station_results"]]
        assert mds == sorted(mds), "Station MDs not in ascending order"

    def test_station_results_present(self):
        """Must return station-level results for survey intervals (N-1 for N stations)."""
        result = self._run_td("trip_out")
        # Engine computes per-interval results (between survey stations),
        # so count is N-1 for N survey stations.
        assert len(result["station_results"]) >= len(JOHANCSIK_WELL["survey"]) - 1
