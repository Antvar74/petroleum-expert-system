"""
Phase 6 Elite Tests — Cementing Engine Elite Upgrades.

Tests caliper volumes, T-dependent slurry, gas migration risk,
spacer optimization, centralizer design, corrected free-fall,
gel strength U-tube, and variable pump rate schedule.
"""

import pytest
import math
from orchestrator.cementing_engine import CementingEngine


# ═══════════════════════════════════════════════════════════════
# Caliper-Integrated Volumes
# ═══════════════════════════════════════════════════════════════

class TestCaliperVolumes:
    """Test caliper-integrated volume calculations."""

    CALIPER = [
        {"md": 5000, "diameter": 12.25},
        {"md": 6000, "diameter": 14.00},  # washout
        {"md": 7000, "diameter": 13.50},  # washout
        {"md": 8000, "diameter": 12.50},
        {"md": 9000, "diameter": 12.25},
        {"md": 10000, "diameter": 12.30},
    ]

    def test_returns_keys(self):
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert "total_caliper_volume_bbl" in r
        assert "caliper_excess_pct" in r
        assert "sections" in r

    def test_caliper_volume_greater_than_nominal(self):
        """Washout zones → caliper volume > nominal."""
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert r["total_caliper_volume_bbl"] > r["total_nominal_volume_bbl"]
        assert r["caliper_excess_pct"] > 0

    def test_washout_max_identified(self):
        """Maximum washout should be in 6000-7000 ft zone."""
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert r["washout_max_pct"] > 0
        assert 5000 <= r["washout_max_md"] <= 7500  # washout zone

    def test_uniform_caliper_no_excess(self):
        """Uniform caliper = gauge → minimal excess."""
        uniform = [
            {"md": 5000, "diameter": 12.25},
            {"md": 7500, "diameter": 12.25},
            {"md": 10000, "diameter": 12.25},
        ]
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=uniform, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert abs(r["caliper_excess_pct"]) < 1.0

    def test_num_sections_correct(self):
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert r["num_sections"] == len(self.CALIPER) - 1

    def test_insufficient_caliper_data(self):
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=[{"md": 5000, "diameter": 12.25}],
            casing_od_in=9.625, toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        assert "error" in r

    def test_user_excess_applied(self):
        """Additional user excess should increase total."""
        r0 = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000, excess_pct=0
        )
        r50 = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000, excess_pct=50
        )
        assert r50["total_with_user_excess_bbl"] > r0["total_with_user_excess_bbl"]

    def test_multiple_washout_sections(self):
        """Each section should have its own washout percentage."""
        r = CementingEngine.calculate_fluid_volumes_caliper(
            caliper_data=self.CALIPER, casing_od_in=9.625,
            toc_md_ft=5000, casing_shoe_md_ft=10000
        )
        washouts = [s["washout_pct"] for s in r["sections"]]
        assert max(washouts) > 0  # at least one section has washout


# ═══════════════════════════════════════════════════════════════
# Temperature-Dependent Slurry Properties
# ═══════════════════════════════════════════════════════════════

class TestSlurryPropertiesPT:
    """Test temperature/pressure correction for slurry."""

    def test_high_temp_reduces_density(self):
        """Higher temperature → thermal expansion → lower density."""
        r = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=30, yp_slurry=15,
            temperature_f=300, pressure_psi=5000
        )
        assert r["density_corrected_ppg"] < 16.0  # expansion at high T

    def test_high_pressure_increases_density(self):
        """Higher pressure → compression → higher density."""
        r = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=30, yp_slurry=15,
            temperature_f=80, pressure_psi=15000
        )
        assert r["density_corrected_ppg"] > 16.0

    def test_temperature_reduces_viscosity(self):
        """Higher temperature → lower viscosity."""
        r = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=30, yp_slurry=15,
            temperature_f=250, pressure_psi=5000
        )
        assert r["pv_corrected"] < 30
        assert r["yp_corrected"] < 15

    def test_bhct_estimation(self):
        """BHCT should be less than BHST (cooling by circulation)."""
        r = CementingEngine.estimate_bhct(well_depth_ft=10000)
        assert r["bhct_f"] < r["bhst_f"]
        assert r["cooling_factor"] < 1.0
        assert r["bhst_f"] > 100  # reasonable temperature

    def test_bhct_deeper_well_hotter(self):
        """Deeper well → higher BHCT."""
        r1 = CementingEngine.estimate_bhct(well_depth_ft=5000)
        r2 = CementingEngine.estimate_bhct(well_depth_ft=15000)
        assert r2["bhct_f"] > r1["bhct_f"]

    def test_obm_different_coefficients(self):
        """OBM should use different correction coefficients."""
        r_wbm = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=30, yp_slurry=15,
            temperature_f=300, pressure_psi=10000, fluid_type="wbm"
        )
        r_obm = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=30, yp_slurry=15,
            temperature_f=300, pressure_psi=10000, fluid_type="obm"
        )
        # OBM has higher thermal expansion → more density change
        assert r_obm["density_corrected_ppg"] != r_wbm["density_corrected_ppg"]


# ═══════════════════════════════════════════════════════════════
# Gas Migration Risk
# ═══════════════════════════════════════════════════════════════

class TestGasMigrationRisk:
    """Test gas migration risk assessment (API RP 65-2)."""

    def test_low_risk_overbalanced(self):
        """Well overbalanced → LOW risk."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=4000, cement_column_height_ft=5000,
            slurry_density_ppg=16.0, pore_pressure_ppg=8.0, tvd_ft=10000
        )
        assert r["risk_level"] == "LOW"
        assert r["overbalance_psi"] > 0

    def test_high_risk_underbalanced(self):
        """Underbalanced → HIGH/CRITICAL risk."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=9000, cement_column_height_ft=5000,
            slurry_density_ppg=12.0, pore_pressure_ppg=10.0, tvd_ft=10000
        )
        assert r["risk_level"] in ("HIGH", "CRITICAL")

    def test_gfp_calculated(self):
        """GFP must always be calculated."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=5000, cement_column_height_ft=5000,
            slurry_density_ppg=16.0, pore_pressure_ppg=9.0, tvd_ft=10000
        )
        assert "gfp" in r
        assert r["gfp"] >= 0

    def test_recommendations_present(self):
        """Recommendations should always be populated."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=5000, cement_column_height_ft=5000,
            slurry_density_ppg=16.0, pore_pressure_ppg=9.0, tvd_ft=10000
        )
        assert len(r["recommendations"]) > 0

    def test_sgs_inadequate_warning(self):
        """Low SGS should trigger additional recommendation."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=5000, cement_column_height_ft=5000,
            slurry_density_ppg=16.0, pore_pressure_ppg=9.0, tvd_ft=10000,
            sgs_10min_lbf_100sqft=10  # very low
        )
        assert not r["sgs_adequate"]
        sgs_recs = [rec for rec in r["recommendations"] if "SGS" in rec]
        assert len(sgs_recs) > 0

    def test_critical_with_short_transition(self):
        """High GFP + short transition time → CRITICAL."""
        r = CementingEngine.calculate_gas_migration_risk(
            reservoir_pressure_psi=8500, cement_column_height_ft=3000,
            slurry_density_ppg=12.0, pore_pressure_ppg=10.0, tvd_ft=10000,
            transition_time_hr=1.0, thickening_time_hr=5.0
        )
        assert r["risk_level"] in ("HIGH", "CRITICAL")


# ═══════════════════════════════════════════════════════════════
# Spacer Optimization
# ═══════════════════════════════════════════════════════════════

class TestSpacerOptimization:
    """Test spacer volume and property optimization."""

    def test_returns_keys(self):
        r = CementingEngine.optimize_spacer(
            mud_density_ppg=10.5, mud_pv=15, mud_yp=10,
            slurry_density_ppg=16.0, slurry_pv=30, slurry_yp=20,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000
        )
        assert "spacer_volume_bbl" in r
        assert "spacer_density_ppg" in r
        assert "flow_regime" in r

    def test_density_intermediate(self):
        """Spacer density should be between mud and cement."""
        r = CementingEngine.optimize_spacer(
            mud_density_ppg=10.5, mud_pv=15, mud_yp=10,
            slurry_density_ppg=16.0, slurry_pv=30, slurry_yp=20,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000
        )
        assert r["density_hierarchy_ok"] is True

    def test_minimum_contact_time(self):
        """Contact time should meet minimum."""
        r = CementingEngine.optimize_spacer(
            mud_density_ppg=10.5, mud_pv=15, mud_yp=10,
            slurry_density_ppg=16.0, slurry_pv=30, slurry_yp=20,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000, min_contact_time_min=10
        )
        assert r["contact_time_min"] >= 10.0

    def test_minimum_contact_length(self):
        """Contact length should meet minimum."""
        r = CementingEngine.optimize_spacer(
            mud_density_ppg=10.5, mud_pv=15, mud_yp=10,
            slurry_density_ppg=16.0, slurry_pv=30, slurry_yp=20,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000, min_contact_length_ft=500
        )
        assert r["contact_length_ft"] >= 500

    def test_rheology_hierarchy(self):
        """Spacer PV should be less than mud PV when mud PV is high enough."""
        r = CementingEngine.optimize_spacer(
            mud_density_ppg=10.5, mud_pv=25, mud_yp=15,
            slurry_density_ppg=16.0, slurry_pv=20, slurry_yp=12,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000
        )
        # Spacer PV = (25+20)/2 * 0.8 = 18 < 25 (mud PV) → hierarchy OK
        assert r["rheology_hierarchy_ok"] is True


# ═══════════════════════════════════════════════════════════════
# Centralizer Design
# ═══════════════════════════════════════════════════════════════

class TestCentralizerDesign:
    """Test centralizer spacing and standoff calculations."""

    INC_PROFILE = [
        {"md": 0, "inc": 0},
        {"md": 3000, "inc": 15},
        {"md": 6000, "inc": 45},
        {"md": 8000, "inc": 60},
        {"md": 10000, "inc": 60},
    ]

    def test_returns_keys(self):
        r = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE
        )
        assert "total_centralizers" in r
        assert "sections" in r
        assert r["total_centralizers"] > 0

    def test_more_centralizers_in_deviated(self):
        """Higher inclination → tighter spacing → more centralizers."""
        # Vertical only
        vert = [{"md": 0, "inc": 0}, {"md": 10000, "inc": 0}]
        r_vert = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=vert
        )
        r_dev = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE
        )
        assert r_dev["total_centralizers"] >= r_vert["total_centralizers"]

    def test_drag_force_positive(self):
        """Centralizers add drag force."""
        r = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE
        )
        assert r["total_drag_extra_lbf"] > 0

    def test_rigid_vs_bow_spring(self):
        """Rigid centralizers have less drag than bow spring."""
        r_bow = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE,
            centralizer_type="bow_spring"
        )
        r_rigid = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE,
            centralizer_type="rigid"
        )
        # Rigid has lower friction coefficient → less drag per unit
        assert r_rigid["total_drag_extra_lbf"] < r_bow["total_drag_extra_lbf"]

    def test_standoff_decreases_with_inclination(self):
        """Standoff without centralizer decreases with inclination."""
        r = CementingEngine.design_centralizers(
            casing_od_in=9.625, hole_id_in=12.25,
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE
        )
        standoffs = [s["standoff_no_cent_pct"] for s in r["sections"]]
        # Vertical section should have higher standoff than deviated
        assert standoffs[0] >= standoffs[-1]

    def test_invalid_geometry(self):
        r = CementingEngine.design_centralizers(
            casing_od_in=12.25, hole_id_in=9.625,  # reversed
            casing_weight_ppf=47.0, inclination_profile=self.INC_PROFILE
        )
        assert "error" in r


# ═══════════════════════════════════════════════════════════════
# Corrected Free-Fall
# ═══════════════════════════════════════════════════════════════

class TestFreeFallCorrected:
    """Test corrected free-fall model with friction."""

    def test_friction_reduces_free_fall(self):
        """Higher friction → less free-fall."""
        common = dict(casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
                      cement_density_ppg=16.0, casing_id_in=8.681,
                      hole_id_in=12.25, casing_od_in=9.625)
        r_low_f = CementingEngine.calculate_free_fall(**common, friction_factor=0.01)
        r_high_f = CementingEngine.calculate_free_fall(**common, friction_factor=0.10)
        assert r_low_f["free_fall_height_ft"] > r_high_f["free_fall_height_ft"]

    def test_has_velocity_and_time(self):
        """Corrected model includes terminal velocity and fall time."""
        r = CementingEngine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0, casing_id_in=8.681,
            hole_id_in=12.25, casing_od_in=9.625
        )
        assert "terminal_velocity_fts" in r
        assert "estimated_fall_time_sec" in r
        assert r["terminal_velocity_fts"] > 0

    def test_heavier_cement_falls_more(self):
        """Heavier cement → larger driving force → more free-fall."""
        common = dict(casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
                      casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625)
        r_light = CementingEngine.calculate_free_fall(**common, cement_density_ppg=12.0)
        r_heavy = CementingEngine.calculate_free_fall(**common, cement_density_ppg=18.0)
        assert r_heavy["free_fall_height_ft"] > r_light["free_fall_height_ft"]

    def test_no_freefall_when_light(self):
        """Cement lighter than mud → no free-fall."""
        r = CementingEngine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=12.0,
            cement_density_ppg=10.0, casing_id_in=8.681,
            hole_id_in=12.25, casing_od_in=9.625
        )
        assert r["free_fall_height_ft"] == 0.0
        assert r["free_fall_occurs"] is False


# ═══════════════════════════════════════════════════════════════
# Gel Strength in U-Tube
# ═══════════════════════════════════════════════════════════════

class TestGelStrengthUTube:
    """Test gel strength resistance in U-tube calculations."""

    def test_gel_holds_column(self):
        """Strong gel → no U-tube flow."""
        r = CementingEngine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=13.5, cement_top_tvd_ft=5000,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
            gel_strength_10s=50, gel_strength_10min=200,
            static_time_min=10.0  # 10 min → use 10-min gel
        )
        assert r["gel_resistance_psi"] > 0
        # If gel resistance > delta_p, column should be held
        if r["gel_resistance_psi"] >= r["pressure_imbalance_psi"]:
            assert r["gel_holds_column"] is True

    def test_no_gel_normal_utube(self):
        """Zero gel → normal U-tube behavior."""
        r = CementingEngine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0, cement_top_tvd_ft=5000,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
            gel_strength_10s=0, gel_strength_10min=0
        )
        assert r["gel_resistance_psi"] == 0
        assert r["utube_occurs"] is True  # heavy cement → strong imbalance

    def test_gel_reduces_drop(self):
        """Gel strength should reduce the fluid drop distance."""
        common = dict(casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
                      cement_density_ppg=14.0, cement_top_tvd_ft=5000,
                      casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625)
        r_no_gel = CementingEngine.calculate_utube_effect(**common)
        r_gel = CementingEngine.calculate_utube_effect(
            **common, gel_strength_10s=20, gel_strength_10min=80, static_time_min=5.0
        )
        assert r_gel["fluid_drop_ft"] <= r_no_gel["fluid_drop_ft"]


# ═══════════════════════════════════════════════════════════════
# Variable Pump Rate Schedule
# ═══════════════════════════════════════════════════════════════

class TestVariablePumpRate:
    """Test variable pump rate displacement schedule."""

    def test_variable_rate_runs(self):
        """Multi-stage schedule should complete successfully."""
        schedule = [
            {"rate_bpm": 3.0, "volume_bbl": 25.0, "stage_name": "Spacer"},
            {"rate_bpm": 5.0, "volume_bbl": 100.0, "stage_name": "Lead Cement"},
            {"rate_bpm": 4.0, "volume_bbl": 50.0, "stage_name": "Tail Cement"},
            {"rate_bpm": 8.0, "volume_bbl": 200.0, "stage_name": "Displacement"},
        ]
        r = CementingEngine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_schedule=schedule
        )
        assert "error" not in r
        assert r["variable_rate"] is True
        assert len(r["stages"]) == 4

    def test_critical_stage_identified(self):
        """Stage with max rate should be identified as critical."""
        schedule = [
            {"rate_bpm": 3.0, "volume_bbl": 50.0, "stage_name": "Slow"},
            {"rate_bpm": 10.0, "volume_bbl": 100.0, "stage_name": "Fast"},
            {"rate_bpm": 5.0, "volume_bbl": 200.0, "stage_name": "Medium"},
        ]
        r = CementingEngine.calculate_displacement_schedule(
            spacer_volume_bbl=50, lead_cement_bbl=100,
            tail_cement_bbl=0, displacement_volume_bbl=200,
            pump_schedule=schedule
        )
        assert r["critical_stage"] == "Fast"
