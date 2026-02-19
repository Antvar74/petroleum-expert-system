"""
Unit tests for WellboreCleanupEngine.
Tests: annular_velocity, slip_velocity, ctr, minimum_flow_rate,
       hole_cleaning_index, sweep_pill, cuttings_concentration, full_cleanup.
"""
import math
import pytest
from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine


# ============================================================
# calculate_annular_velocity (5 tests)
# ============================================================

class TestAnnularVelocity:

    def test_standard_case(self):
        """8.5" hole, 5" pipe, 500 gpm → ~226 ft/min."""
        va = WellboreCleanupEngine.calculate_annular_velocity(500, 8.5, 5.0)
        assert 200 < va < 260

    def test_zero_flow_rate(self):
        va = WellboreCleanupEngine.calculate_annular_velocity(0, 8.5, 5.0)
        assert va == 0.0

    def test_pipe_equals_hole(self):
        va = WellboreCleanupEngine.calculate_annular_velocity(500, 5.0, 5.0)
        assert va == 0.0

    def test_larger_annulus_lower_velocity(self):
        """Larger hole → larger annulus → lower velocity at same flow rate."""
        va_small = WellboreCleanupEngine.calculate_annular_velocity(500, 8.5, 5.0)
        va_large = WellboreCleanupEngine.calculate_annular_velocity(500, 12.25, 5.0)
        assert va_small > va_large

    def test_higher_flow_higher_velocity(self):
        va_low = WellboreCleanupEngine.calculate_annular_velocity(300, 8.5, 5.0)
        va_high = WellboreCleanupEngine.calculate_annular_velocity(600, 8.5, 5.0)
        assert va_high > va_low


# ============================================================
# calculate_slip_velocity (4 tests)
# ============================================================

class TestSlipVelocity:

    def test_standard_cuttings(self):
        """Standard sandstone cuttings in 10 ppg mud."""
        vs = WellboreCleanupEngine.calculate_slip_velocity(10.0, 15, 10, 0.25, 21.0)
        assert vs > 0

    def test_zero_cutting_size(self):
        vs = WellboreCleanupEngine.calculate_slip_velocity(10.0, 15, 10, 0.0, 21.0)
        assert vs == 0.0

    def test_heavier_mud_lower_slip(self):
        """Heavier mud reduces density difference → lower slip velocity."""
        vs_light = WellboreCleanupEngine.calculate_slip_velocity(8.0, 15, 10, 0.25, 21.0)
        vs_heavy = WellboreCleanupEngine.calculate_slip_velocity(14.0, 15, 10, 0.25, 21.0)
        assert vs_light > vs_heavy

    def test_equal_density_zero_slip(self):
        """If cutting density = mud weight, no slip."""
        vs = WellboreCleanupEngine.calculate_slip_velocity(21.0, 15, 10, 0.25, 21.0)
        assert vs == 0.0


# ============================================================
# calculate_ctr (3 tests)
# ============================================================

class TestCTR:

    def test_good_transport(self):
        """Va=200, Vs=50 → CTR=0.75 (good)."""
        ctr = WellboreCleanupEngine.calculate_ctr(200, 50)
        assert abs(ctr - 0.75) < 0.01

    def test_zero_velocity(self):
        ctr = WellboreCleanupEngine.calculate_ctr(0, 50)
        assert ctr == 0.0

    def test_slip_exceeds_annular(self):
        """If Vs > Va, CTR is clamped to 0."""
        ctr = WellboreCleanupEngine.calculate_ctr(50, 100)
        assert ctr == 0.0


# ============================================================
# calculate_minimum_flow_rate (3 tests)
# ============================================================

class TestMinimumFlowRate:

    def test_vertical_minimum(self):
        """Vertical (0°) requires ~120 ft/min minimum."""
        q_min = WellboreCleanupEngine.calculate_minimum_flow_rate(8.5, 5.0, 0)
        assert q_min > 0

    def test_high_angle_higher_minimum(self):
        """High-angle section needs higher minimum flow rate."""
        q_vert = WellboreCleanupEngine.calculate_minimum_flow_rate(8.5, 5.0, 0)
        q_high = WellboreCleanupEngine.calculate_minimum_flow_rate(8.5, 5.0, 75)
        assert q_high > q_vert

    def test_pipe_equals_hole(self):
        q_min = WellboreCleanupEngine.calculate_minimum_flow_rate(5.0, 5.0, 0)
        assert q_min == 0.0


# ============================================================
# calculate_hole_cleaning_index (4 tests)
# ============================================================

class TestHCI:

    def test_good_cleaning(self):
        """Adequate velocity → HCI > 1.0."""
        hci = WellboreCleanupEngine.calculate_hole_cleaning_index(
            150, 120, 0, 10.0, 21.0, 15, 10
        )
        assert hci >= 1.0

    def test_poor_cleaning(self):
        """Low velocity → HCI < 0.7."""
        hci = WellboreCleanupEngine.calculate_hole_cleaning_index(
            60, 0, 0, 10.0, 21.0, 15, 10
        )
        assert hci < 0.7

    def test_rpm_improves_cleaning(self):
        """Rotation should improve HCI in deviated wells."""
        hci_no_rpm = WellboreCleanupEngine.calculate_hole_cleaning_index(
            130, 0, 60, 10.0, 21.0, 15, 10
        )
        hci_with_rpm = WellboreCleanupEngine.calculate_hole_cleaning_index(
            130, 120, 60, 10.0, 21.0, 15, 10
        )
        assert hci_with_rpm > hci_no_rpm

    def test_returns_float(self):
        hci = WellboreCleanupEngine.calculate_hole_cleaning_index(
            150, 0, 0, 10.0, 21.0, 15, 10
        )
        assert isinstance(hci, float)


# ============================================================
# design_sweep_pill (2 tests)
# ============================================================

class TestSweepPill:

    def test_standard_pill(self):
        sweep = WellboreCleanupEngine.design_sweep_pill(
            annular_volume_per_ft=0.045, annular_length=1000, mud_weight=10.0
        )
        assert sweep["pill_volume_bbl"] > 0
        assert sweep["pill_weight_ppg"] > 10.0
        assert sweep["pill_length_ft"] > 0

    def test_zero_annular_volume(self):
        sweep = WellboreCleanupEngine.design_sweep_pill(
            annular_volume_per_ft=0.0, annular_length=1000, mud_weight=10.0
        )
        assert sweep["pill_volume_bbl"] == 0.0


# ============================================================
# calculate_cuttings_concentration (3 tests)
# ============================================================

class TestCuttingsConcentration:

    def test_normal_concentration(self):
        cc = WellboreCleanupEngine.calculate_cuttings_concentration(
            rop=60, hole_id=8.5, pipe_od=5.0, flow_rate=500, transport_velocity=150
        )
        assert 0 < cc < 10

    def test_zero_transport_velocity(self):
        cc = WellboreCleanupEngine.calculate_cuttings_concentration(
            rop=60, hole_id=8.5, pipe_od=5.0, flow_rate=500, transport_velocity=0
        )
        assert cc == 100.0

    def test_zero_flow_rate(self):
        cc = WellboreCleanupEngine.calculate_cuttings_concentration(
            rop=60, hole_id=8.5, pipe_od=5.0, flow_rate=0, transport_velocity=150
        )
        assert cc == 100.0


# ============================================================
# calculate_full_cleanup (6 tests)
# ============================================================

class TestFullCleanup:

    def test_returns_required_keys(self):
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=500, mud_weight=10.0, pv=15, yp=10,
            hole_id=8.5, pipe_od=5.0, inclination=0
        )
        assert "summary" in result
        assert "sweep_pill" in result
        assert "parameters" in result
        assert "alerts" in result

    def test_summary_contains_metrics(self):
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=500, mud_weight=10.0, pv=15, yp=10,
            hole_id=8.5, pipe_od=5.0, inclination=0
        )
        summary = result["summary"]
        assert "annular_velocity_ftmin" in summary
        assert "cuttings_transport_ratio" in summary
        assert "hole_cleaning_index" in summary
        assert "cleaning_quality" in summary

    def test_good_cleaning_no_critical_alerts(self):
        """High flow rate, vertical → should be good cleaning."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=700, mud_weight=12.0, pv=20, yp=15,
            hole_id=8.5, pipe_od=5.0, inclination=0, rpm=120
        )
        assert result["summary"]["cleaning_quality"] == "Good"

    def test_low_flow_generates_alerts(self):
        """Very low flow rate should generate alerts."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=100, mud_weight=10.0, pv=15, yp=10,
            hole_id=8.5, pipe_od=5.0, inclination=0
        )
        assert len(result["alerts"]) > 0

    def test_high_angle_no_rotation_alert(self):
        """High angle with no rotation should trigger alert."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=500, mud_weight=10.0, pv=15, yp=10,
            hole_id=8.5, pipe_od=5.0, inclination=60, rpm=0
        )
        rotation_alerts = [a for a in result["alerts"] if "rotation" in a.lower()]
        assert len(rotation_alerts) > 0

    def test_physical_invariants(self):
        """Transport velocity = annular velocity - slip velocity."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=500, mud_weight=10.0, pv=15, yp=10,
            hole_id=8.5, pipe_od=5.0, inclination=30
        )
        s = result["summary"]
        expected_vt = s["annular_velocity_ftmin"] - s["slip_velocity_ftmin"]
        assert abs(s["transport_velocity_ftmin"] - expected_vt) < 0.2
