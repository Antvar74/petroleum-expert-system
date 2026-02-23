"""
V&V: Well Control engine against standard kill sheet calculations (API RP 59).
Validates formation pressure, kill mud weight, and ICP calculations.
"""
import pytest
from orchestrator.well_control_engine import WellControlEngine
from tests.validation.benchmark_data import WELL_CONTROL_KILL_SHEET
from tests.validation.conftest import assert_within_tolerance


class TestWellControlKillSheetValidation:
    """Validate kill sheet calculations against standard formulas."""

    def _run_kill_sheet(self):
        bm = WELL_CONTROL_KILL_SHEET
        return WellControlEngine.calculate_kill_sheet(
            depth_md=bm["tvd"] + 500,  # slightly more than TVD
            depth_tvd=bm["tvd"],
            original_mud_weight=bm["original_mud_weight"],
            casing_shoe_tvd=5000,
            sidpp=bm["sidpp"],
            sicp=600,
            pit_gain=20,
            scr_pressure=bm["slow_pump_rate_psi"],
            scr_rate=30,
            dp_capacity=0.01776,
            annular_capacity=0.0505,
            strokes_surface_to_bit=1780,
            lot_emw=14.5,
        )

    def test_formation_pressure_calculation(self):
        """Pf = 0.052 * MW * TVD + SIDPP — standard formula."""
        result = self._run_kill_sheet()
        bm = WELL_CONTROL_KILL_SHEET
        expected = bm["expected"]["formation_pressure_psi"]
        assert_within_tolerance(
            result["formation_pressure_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API RP 59 Formation Pressure",
        )

    def test_kill_mud_weight(self):
        """KMW = Pf / (0.052 * TVD) — standard formula."""
        result = self._run_kill_sheet()
        bm = WELL_CONTROL_KILL_SHEET
        expected = bm["expected"]["kill_mud_weight_ppg"]
        assert_within_tolerance(
            result["kill_mud_weight_ppg"],
            expected["value"],
            expected["tolerance_pct"],
            label="API RP 59 Kill Mud Weight",
        )

    def test_icp_calculation(self):
        """ICP = SIDPP + SCR pressure — standard formula."""
        result = self._run_kill_sheet()
        bm = WELL_CONTROL_KILL_SHEET
        expected = bm["expected"]["icp_psi"]
        assert_within_tolerance(
            result["icp_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API RP 59 ICP",
        )

    def test_kill_mud_weight_greater_than_original(self):
        """Physics: kill MW must exceed original MW when there's a kick."""
        result = self._run_kill_sheet()
        bm = WELL_CONTROL_KILL_SHEET
        assert result["kill_mud_weight_ppg"] > bm["original_mud_weight"]

    def test_formation_pressure_matches_manual(self):
        """Manual: Pf = 0.052 * 10.0 * 10000 + 500 = 5700 psi."""
        result = self._run_kill_sheet()
        manual_pf = 0.052 * 10.0 * 10000 + 500
        assert abs(result["formation_pressure_psi"] - manual_pf) < 50
