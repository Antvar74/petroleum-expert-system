"""
Phase 4 Elite Tests — Cross-Engine Integration.

Covers:
- Differential sticking force (ECD → Stuck Pipe) (8 tests)
- T&D with ECD profile (variable buoyancy) (10 tests)
- Pack-off early warning (Cleanup → Stuck Pipe) (7 tests)
"""

import pytest
import math
from orchestrator.stuck_pipe_engine import StuckPipeEngine
from orchestrator.torque_drag_engine import TorqueDragEngine


# ═══════════════════════════════════════════════════════════════
# Differential Sticking Force
# ═══════════════════════════════════════════════════════════════

class TestDifferentialStickingForce:
    """Test differential sticking force calculations (ECD → stuck pipe)."""

    def test_overbalanced_positive_force(self):
        """Overbalanced condition should produce positive sticking force."""
        r = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0, tvd_ft=10000
        )
        assert r["sticking_force_lbs"] > 0
        assert r["differential_pressure_psi"] > 0

    def test_underbalanced_no_risk(self):
        """Underbalanced condition should show NONE risk."""
        r = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=9.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0, tvd_ft=10000
        )
        assert r["risk_level"] == "NONE"
        assert r["sticking_force_lbs"] == 0.0

    def test_high_overbalance_high_risk(self):
        """Very high overbalance → HIGH or CRITICAL risk."""
        r = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=16.0, pore_pressure_ppg=9.0,
            contact_length_ft=100, pipe_od_in=5.0, tvd_ft=15000
        )
        assert r["risk_level"] in ("HIGH", "CRITICAL")

    def test_contact_area_positive(self):
        """Contact area must be positive for overbalanced case."""
        r = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0, tvd_ft=10000
        )
        assert r["contact_area_sqin"] > 0
        assert r["contact_width_in"] > 0

    def test_longer_contact_more_force(self):
        """Longer contact length → greater sticking force."""
        r1 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=20, pipe_od_in=5.0, tvd_ft=10000
        )
        r2 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=60, pipe_od_in=5.0, tvd_ft=10000
        )
        assert r2["sticking_force_lbs"] > r1["sticking_force_lbs"]

    def test_thicker_cake_more_area(self):
        """Thicker filter cake → larger contact area."""
        r1 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0,
            filter_cake_thickness_in=0.125, tvd_ft=10000
        )
        r2 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0,
            filter_cake_thickness_in=0.5, tvd_ft=10000
        )
        assert r2["contact_area_sqin"] > r1["contact_area_sqin"]

    def test_pull_free_vs_sticking_force(self):
        """Pull-free force should be sticking_force × friction coefficient."""
        r = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0,
            friction_coefficient_cake=0.15, tvd_ft=10000
        )
        expected_pull = r["sticking_force_lbs"] * 0.15
        assert abs(r["pull_free_force_lbs"] - expected_pull) < 100  # rounding tolerance

    def test_deeper_well_more_pressure(self):
        """Deeper well → higher differential pressure for same overbalance."""
        r1 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0, tvd_ft=5000
        )
        r2 = StuckPipeEngine.calculate_differential_sticking_force(
            ecd_ppg=13.0, pore_pressure_ppg=10.0,
            contact_length_ft=30, pipe_od_in=5.0, tvd_ft=15000
        )
        assert r2["differential_pressure_psi"] > r1["differential_pressure_psi"]


# ═══════════════════════════════════════════════════════════════
# Torque & Drag with ECD Profile
# ═══════════════════════════════════════════════════════════════

class TestTorqueDragWithECD:
    """Test T&D with ECD profile for variable buoyancy."""

    SURVEY = [
        {"md": 0, "inclination": 0, "azimuth": 0},
        {"md": 2000, "inclination": 0, "azimuth": 0},
        {"md": 5000, "inclination": 30, "azimuth": 90},
        {"md": 8000, "inclination": 60, "azimuth": 90},
        {"md": 10000, "inclination": 60, "azimuth": 90},
    ]
    DRILLSTRING = [
        {"od": 6.75, "id_inner": 2.8125, "weight": 90.0, "length": 600, "order_from_bit": 0},
        {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9400, "order_from_bit": 1},
    ]

    ECD_PROFILE = [
        {"tvd": 1000, "ecd": 12.1},
        {"tvd": 3000, "ecd": 12.3},
        {"tvd": 5000, "ecd": 12.5},
        {"tvd": 7000, "ecd": 12.8},
        {"tvd": 9000, "ecd": 13.2},
    ]

    def test_no_ecd_baseline(self):
        """Without ECD profile, should work normally."""
        r = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        assert "error" not in r
        assert r["summary"]["surface_hookload_klb"] > 0

    def test_with_ecd_runs(self):
        """With ECD profile, should still complete successfully."""
        r = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=self.ECD_PROFILE
        )
        assert "error" not in r
        assert r["summary"]["surface_hookload_klb"] > 0

    def test_ecd_changes_hookload(self):
        """ECD profile (heavier fluid) should reduce hookload vs constant MW."""
        r_no = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        r_ecd = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=self.ECD_PROFILE
        )
        # ECD is higher than MW → more buoyancy → lower hookload
        assert r_ecd["summary"]["surface_hookload_klb"] < r_no["summary"]["surface_hookload_klb"]

    def test_ecd_trip_in(self):
        """ECD profile with trip_in also works."""
        r = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_in", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=self.ECD_PROFILE
        )
        assert "error" not in r

    def test_ecd_rotating(self):
        """ECD profile with rotating operation works."""
        r = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="rotating", mud_weight=12.0,
            wob=30, rpm=120,
            casing_shoe_md=5000,
            ecd_profile=self.ECD_PROFILE
        )
        assert "error" not in r
        assert r["summary"]["surface_torque_ftlb"] > 0

    def test_empty_ecd_profile_uses_mw(self):
        """Empty ECD profile should fall back to constant mud_weight."""
        r_no = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        r_empty = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=[]
        )
        # Empty profile → same as no profile → same hookload
        assert abs(r_no["summary"]["surface_hookload_klb"] - r_empty["summary"]["surface_hookload_klb"]) < 0.1

    def test_uniform_ecd_matches_mw(self):
        """Uniform ECD profile = constant MW → should give identical hookload."""
        uniform_ecd = [{"tvd": d, "ecd": 12.0} for d in range(0, 10001, 2000)]
        r_no = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        r_uni = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=uniform_ecd
        )
        # Should be very close (same MW everywhere)
        assert abs(r_no["summary"]["surface_hookload_klb"] - r_uni["summary"]["surface_hookload_klb"]) < 1.0

    def test_higher_ecd_more_buoyancy(self):
        """Higher ECD → more buoyancy → lower string weight in hole."""
        high_ecd = [{"tvd": d, "ecd": 16.0} for d in range(0, 10001, 2000)]
        r_low = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        r_high = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=high_ecd
        )
        # 16 ppg ECD → much more buoyancy → lighter string
        assert r_high["summary"]["surface_hookload_klb"] < r_low["summary"]["surface_hookload_klb"]

    def test_station_count_unchanged(self):
        """Number of station results should be same with or without ECD."""
        r_no = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000
        )
        r_ecd = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=self.ECD_PROFILE
        )
        assert len(r_no["station_results"]) == len(r_ecd["station_results"])

    def test_single_point_ecd_profile(self):
        """Single-point ECD profile should fall back to constant MW."""
        single = [{"tvd": 5000, "ecd": 13.0}]
        r = TorqueDragEngine.compute_torque_drag(
            self.SURVEY, self.DRILLSTRING,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=5000,
            ecd_profile=single
        )
        # Single point → use_ecd_buoyancy=False → uses mud_weight
        assert "error" not in r


# ═══════════════════════════════════════════════════════════════
# Pack-Off Early Warning
# ═══════════════════════════════════════════════════════════════

class TestPackoffRisk:
    """Test pack-off/bridge risk assessment from cleanup indicators."""

    def test_good_cleaning_low_risk(self):
        """Good HCI and low cuttings → LOW risk."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.9, cuttings_concentration_pct=2.0,
            inclination=10, annular_velocity_ftmin=180
        )
        assert r["risk_level"] == "LOW"

    def test_poor_hci_elevates_risk(self):
        """HCI < 0.5 → should elevate risk significantly."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.4, cuttings_concentration_pct=3.0,
            inclination=45, annular_velocity_ftmin=150
        )
        assert r["packoff_probability"] >= 2
        assert len(r["risk_factors"]) > 0

    def test_high_cuttings_elevates_risk(self):
        """High cuttings concentration (>7%) → HIGH risk factor."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.65, cuttings_concentration_pct=8.0,
            inclination=70, annular_velocity_ftmin=100
        )
        assert r["risk_level"] in ("MODERATE", "HIGH")

    def test_hci_and_cuttings_combined(self):
        """Bad HCI + high cuttings → HIGH risk."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.4, cuttings_concentration_pct=9.0,
            inclination=75, annular_velocity_ftmin=80
        )
        assert r["risk_level"] == "HIGH"

    def test_risk_factors_populated(self):
        """Risk factors list should have entries for bad conditions."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.4, cuttings_concentration_pct=8.0,
            inclination=70, annular_velocity_ftmin=80
        )
        # Should have at least 3 factors: poor HCI, high cuttings, high angle
        assert len(r["risk_factors"]) >= 3

    def test_recommendation_present(self):
        """Result must always have a recommendation."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.9, cuttings_concentration_pct=1.0
        )
        assert len(r["recommendation"]) > 0

    def test_risk_matrix_compatible(self):
        """Output uses probability × severity compatible with risk matrix."""
        r = StuckPipeEngine.assess_packoff_risk(
            hci=0.6, cuttings_concentration_pct=5.0,
            inclination=50, annular_velocity_ftmin=120
        )
        assert 1 <= r["packoff_probability"] <= 5
        assert r["severity"] == 3  # Pack-Off severity = 3
        assert r["risk_score"] == r["packoff_probability"] * r["severity"]
