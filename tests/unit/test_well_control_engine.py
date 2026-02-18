"""
Unit tests for WellControlEngine.
Tests: calculate_kill_sheet, generate_pressure_schedule, calculate_drillers_method,
       calculate_wait_and_weight, calculate_volumetric, calculate_bullhead, pre_record_kill_sheet.
"""
import math
import pytest
from orchestrator.well_control_engine import WellControlEngine


# ============================================================
# Standard test data
# ============================================================

def _standard_kill_params():
    """Standard gas kick parameters."""
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


def _standard_kill_sheet():
    """Pre-compute a kill sheet for method tests."""
    return WellControlEngine.calculate_kill_sheet(**_standard_kill_params())


# ============================================================
# calculate_kill_sheet (13 tests)
# ============================================================

class TestCalculateKillSheet:

    def test_kmw_gt_mw(self):
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        assert r["kill_mud_weight_ppg"] > 10.0

    def test_formation_pressure(self):
        """FP = MW × 0.052 × TVD + SIDPP → 10 × 0.052 × 10000 + 200 = 5400."""
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        expected = 10.0 * 0.052 * 10000 + 200
        assert abs(r["formation_pressure_psi"] - expected) < 1.0

    def test_icp_exact(self):
        """ICP = SIDPP + SCR."""
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        assert r["icp_psi"] == 200 + 800

    def test_fcp_exact(self):
        """FCP = SCR × (KMW / OMW)."""
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        kmw = r["kill_mud_weight_ppg"]
        expected_fcp = 800 * (kmw / 10.0)
        assert abs(r["fcp_psi"] - expected_fcp) < 1.0

    def test_maasp(self):
        """MAASP = (LOT - MW) × 0.052 × shoe_TVD → (14-10) × 0.052 × 5000 = 1040."""
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        expected = (14.0 - 10.0) * 0.052 * 5000
        assert abs(r["maasp_psi"] - expected) < 1.0

    def test_gas_influx_type(self):
        """SICP >> SIDPP suggests gas influx."""
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        assert "Gas" in r["influx_type"]

    def test_salt_water_influx(self):
        """SICP ≈ SIDPP suggests water/heavier influx."""
        params = _standard_kill_params()
        params["sicp"] = 210  # very close to SIDPP=200
        r = WellControlEngine.calculate_kill_sheet(**params)
        # Gradient should be higher, closer to salt water
        assert r["influx_gradient_psi_ft"] > 0.2

    def test_schedule_11_entries(self):
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        assert len(r["pressure_schedule"]) == 11

    def test_schedule_starts_icp_ends_fcp(self):
        r = WellControlEngine.calculate_kill_sheet(**_standard_kill_params())
        schedule = r["pressure_schedule"]
        assert schedule[0]["pressure_psi"] == r["icp_psi"]
        assert schedule[-1]["pressure_psi"] == r["fcp_psi"]

    def test_sicp_exceeds_maasp_alert(self):
        params = _standard_kill_params()
        params["sicp"] = 2000  # exceeds MAASP
        r = WellControlEngine.calculate_kill_sheet(**params)
        alerts = [a for a in r["alerts"] if "CRITICAL" in a and "SICP" in a]
        assert len(alerts) > 0

    def test_kmw_exceeds_lot_alert(self):
        params = _standard_kill_params()
        params["lot_emw"] = 10.2  # very low LOT
        params["sidpp"] = 500  # large kick
        r = WellControlEngine.calculate_kill_sheet(**params)
        alerts = [a for a in r["alerts"] if "CRITICAL" in a and "KMW" in a]
        assert len(alerts) > 0

    def test_tvd_zero_kmw_equals_mw(self):
        params = _standard_kill_params()
        params["depth_tvd"] = 0
        r = WellControlEngine.calculate_kill_sheet(**params)
        assert r["kill_mud_weight_ppg"] == 10.0

    def test_sidpp_zero_kmw_equals_mw(self):
        params = _standard_kill_params()
        params["sidpp"] = 0
        r = WellControlEngine.calculate_kill_sheet(**params)
        assert abs(r["kill_mud_weight_ppg"] - 10.0) < 0.01


# ============================================================
# generate_pressure_schedule (4 tests)
# ============================================================

class TestGeneratePressureSchedule:

    def test_zero_strokes_empty(self):
        r = WellControlEngine.generate_pressure_schedule(icp=1000, fcp=800, strokes_surface_to_bit=0)
        assert r == []

    def test_linear_decrease(self):
        r = WellControlEngine.generate_pressure_schedule(icp=1000, fcp=800, strokes_surface_to_bit=1800)
        assert r[0]["pressure_psi"] == 1000
        assert r[-1]["pressure_psi"] == 800
        # Constant decrement
        decrements = [r[i]["pressure_psi"] - r[i + 1]["pressure_psi"] for i in range(len(r) - 1)]
        for d in decrements:
            assert abs(d - decrements[0]) < 1.0

    def test_10_intervals_11_entries(self):
        r = WellControlEngine.generate_pressure_schedule(icp=1000, fcp=800, strokes_surface_to_bit=1800, intervals=10)
        assert len(r) == 11

    def test_percent_range(self):
        r = WellControlEngine.generate_pressure_schedule(icp=1000, fcp=800, strokes_surface_to_bit=1800)
        assert r[0]["percent_complete"] == 0
        assert r[-1]["percent_complete"] == 100


# ============================================================
# calculate_drillers_method (3 tests)
# ============================================================

class TestDrillersMethod:

    def test_structure(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_drillers_method(ks, scr_pressure=800)
        assert r["method"] == "Driller's Method"
        assert r["circulations"] == 2

    def test_first_circulation_dp_pressure(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_drillers_method(ks, scr_pressure=800)
        assert r["first_circulation"]["dp_pressure"] == ks["icp_psi"]

    def test_between_circulations_kmw(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_drillers_method(ks, scr_pressure=800)
        assert r["between_circulations"]["target_mw"] == ks["kill_mud_weight_ppg"]


# ============================================================
# calculate_wait_and_weight (3 tests)
# ============================================================

class TestWaitAndWeight:

    def test_structure(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_wait_and_weight(ks)
        assert r["method"] == "Wait and Weight"
        assert r["circulations"] == 1

    def test_pressure_schedule_present(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_wait_and_weight(ks)
        assert r["single_circulation"]["pressure_schedule"] is not None
        assert len(r["single_circulation"]["pressure_schedule"]) > 0

    def test_icp_fcp_positive(self):
        ks = _standard_kill_sheet()
        r = WellControlEngine.calculate_wait_and_weight(ks)
        assert r["single_circulation"]["icp"] > 0
        assert r["single_circulation"]["fcp"] > 0


# ============================================================
# calculate_volumetric (5 tests)
# ============================================================

class TestVolumetric:

    def test_structure(self):
        r = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        assert r["method"] == "Volumetric"
        assert "cycles" in r
        assert len(r["cycles"]) > 0

    def test_maasp_calculation(self):
        r = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        expected_maasp = (14.0 - 10.0) * 0.052 * 5000
        assert abs(r["initial_conditions"]["maasp_psi"] - expected_maasp) < 1.0

    def test_working_pressure(self):
        r = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000,
            safety_margin_psi=50
        )
        assert r["initial_conditions"]["working_pressure_psi"] == 250  # SICP + margin

    def test_cycles_capped_at_50(self):
        r = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=50000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        assert len(r["cycles"]) <= 50

    def test_mw_zero_volume_zero(self):
        r = WellControlEngine.calculate_volumetric(
            mud_weight=0, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        assert r["parameters"]["volume_per_cycle_bbl"] == 0


# ============================================================
# calculate_bullhead (4 tests)
# ============================================================

class TestBullhead:

    def test_structure(self):
        r = WellControlEngine.calculate_bullhead(
            mud_weight=10, kill_mud_weight=11, depth_tvd=10000,
            casing_shoe_tvd=5000, lot_emw=14.0,
            dp_capacity=0.018, depth_md=10000, formation_pressure=5720
        )
        assert r["method"] == "Bullhead"
        assert "shoe_integrity" in r

    def test_shoe_safe(self):
        """High LOT → shoe is safe."""
        r = WellControlEngine.calculate_bullhead(
            mud_weight=10, kill_mud_weight=11, depth_tvd=10000,
            casing_shoe_tvd=5000, lot_emw=16.0,
            dp_capacity=0.018, depth_md=10000, formation_pressure=5720
        )
        assert r["shoe_integrity"]["safe"] is True

    def test_shoe_unsafe(self):
        """Low LOT → shoe unsafe with warnings."""
        r = WellControlEngine.calculate_bullhead(
            mud_weight=10, kill_mud_weight=11, depth_tvd=10000,
            casing_shoe_tvd=5000, lot_emw=10.5,
            dp_capacity=0.018, depth_md=10000, formation_pressure=5720
        )
        assert r["shoe_integrity"]["safe"] is False
        assert len(r["warnings"]) > 0

    def test_pump_pressure_non_negative(self):
        r = WellControlEngine.calculate_bullhead(
            mud_weight=10, kill_mud_weight=11, depth_tvd=10000,
            casing_shoe_tvd=5000, lot_emw=14.0,
            dp_capacity=0.018, depth_md=10000, formation_pressure=5720
        )
        assert r["calculations"]["required_pump_pressure_psi"] >= 0


# ============================================================
# pre_record_kill_sheet (5 tests)
# ============================================================

class TestPreRecordKillSheet:

    def _standard_pre_record_params(self):
        return dict(
            well_name="TEST-WELL", depth_md=10000, depth_tvd=9500,
            original_mud_weight=10.0, casing_shoe_tvd=5000,
            casing_id=8.681, dp_od=5.0, dp_id=4.276, dp_length=9800,
            dc_od=6.5, dc_id=2.813, dc_length=200,
            scr_pressure=800, scr_rate=30, lot_emw=14.0,
            pump_output=0.1, hole_size=8.5
        )

    def test_status_pre_recorded(self):
        r = WellControlEngine.pre_record_kill_sheet(**self._standard_pre_record_params())
        assert r["status"] == "pre-recorded"

    def test_dp_capacity(self):
        """dp_capacity = ID² / 1029.4."""
        r = WellControlEngine.pre_record_kill_sheet(**self._standard_pre_record_params())
        expected = 4.276**2 / 1029.4
        assert abs(r["capacities_bbl_ft"]["dp_capacity"] - expected) < 0.0001

    def test_strokes_calculation(self):
        """strokes = volume / pump_output."""
        r = WellControlEngine.pre_record_kill_sheet(**self._standard_pre_record_params())
        dp_vol = r["volumes_bbl"]["dp_volume"]
        dc_vol = r["volumes_bbl"]["dc_volume"]
        expected_stk = (dp_vol + dc_vol) / 0.1
        assert abs(r["strokes"]["strokes_surface_to_bit"] - expected_stk) < 1.0

    def test_volumes_positive(self):
        r = WellControlEngine.pre_record_kill_sheet(**self._standard_pre_record_params())
        assert r["volumes_bbl"]["dp_volume"] > 0
        assert r["volumes_bbl"]["dc_volume"] > 0
        total = r["volumes_bbl"]["total_string_volume"] + r["volumes_bbl"]["total_annular_volume"]
        assert abs(r["volumes_bbl"]["total_well_volume"] - total) < 0.1

    def test_pump_output_zero(self):
        params = self._standard_pre_record_params()
        params["pump_output"] = 0
        r = WellControlEngine.pre_record_kill_sheet(**params)
        assert r["strokes"]["strokes_surface_to_bit"] == 0
        assert r["strokes"]["total_strokes"] == 0
