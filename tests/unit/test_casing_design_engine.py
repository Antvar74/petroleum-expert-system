"""
Unit tests for CasingDesignEngine -- casing design calculations.

Covers burst/collapse/tension loads, API 5C3 collapse rating (4 zones),
Barlow burst, biaxial correction, triaxial VME, grade selection,
safety factor verification, and full master method integration.
"""
import math
import pytest
from orchestrator.casing_design_engine import CasingDesignEngine


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def engine():
    """Return CasingDesignEngine class (all static methods)."""
    return CasingDesignEngine


@pytest.fixture
def typical_casing():
    """Standard 9-5/8" 47 ppf casing."""
    return dict(
        casing_od_in=9.625,
        casing_id_in=8.681,
        wall_thickness_in=0.472,
        casing_weight_ppf=47.0,
    )


@pytest.fixture
def typical_well():
    return dict(
        tvd_ft=9500.0,
        mud_weight_ppg=10.5,
        pore_pressure_ppg=9.0,
    )


# ===========================================================================
# 1. BURST LOAD
# ===========================================================================
class TestBurstLoad:
    def test_profile_has_points(self, engine, typical_well):
        result = engine.calculate_burst_load(**typical_well, num_points=20)
        assert len(result["profile"]) == 20

    def test_max_burst_positive(self, engine, typical_well):
        result = engine.calculate_burst_load(**typical_well)
        assert result["max_burst_load_psi"] > 0

    def test_max_burst_at_surface(self, engine, typical_well):
        """Gas-to-surface scenario: max burst is at surface (depth = 0)."""
        result = engine.calculate_burst_load(**typical_well)
        assert result["max_burst_depth_ft"] == 0

    def test_reservoir_pressure_consistent(self, engine, typical_well):
        result = engine.calculate_burst_load(**typical_well)
        expected_p_res = 9.0 * 0.052 * 9500
        assert result["reservoir_pressure_psi"] == pytest.approx(expected_p_res, abs=1)

    def test_zero_tvd_error(self, engine):
        result = engine.calculate_burst_load(tvd_ft=0, mud_weight_ppg=10.0, pore_pressure_ppg=9.0)
        assert "error" in result

    def test_higher_pore_pressure_higher_burst(self, engine):
        low = engine.calculate_burst_load(tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=9.0)
        high = engine.calculate_burst_load(tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=14.0)
        assert high["max_burst_load_psi"] > low["max_burst_load_psi"]


# ===========================================================================
# 2. COLLAPSE LOAD
# ===========================================================================
class TestCollapseLoad:
    def test_profile_has_points(self, engine, typical_well):
        result = engine.calculate_collapse_load(**typical_well, num_points=15)
        assert len(result["profile"]) == 15

    def test_max_collapse_positive_with_evacuation(self, engine, typical_well):
        """Full evacuation (evacuation_level = TVD) yields positive collapse."""
        result = engine.calculate_collapse_load(
            **typical_well, evacuation_level_ft=typical_well["tvd_ft"])
        assert result["max_collapse_load_psi"] > 0

    def test_full_evacuation_max_at_bottom(self, engine, typical_well):
        """Full evacuation: max collapse load at TD (deepest point)."""
        result = engine.calculate_collapse_load(
            **typical_well, evacuation_level_ft=typical_well["tvd_ft"])
        assert result["max_collapse_depth_ft"] == pytest.approx(typical_well["tvd_ft"], abs=1)

    def test_heavier_mud_higher_collapse(self, engine):
        """With full evacuation, heavier external mud → higher collapse load."""
        light = engine.calculate_collapse_load(
            tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=9.0,
            evacuation_level_ft=10000)
        heavy = engine.calculate_collapse_load(
            tvd_ft=10000, mud_weight_ppg=14.0, pore_pressure_ppg=9.0,
            evacuation_level_ft=10000)
        assert heavy["max_collapse_load_psi"] > light["max_collapse_load_psi"]

    def test_zero_tvd_error(self, engine):
        result = engine.calculate_collapse_load(tvd_ft=0, mud_weight_ppg=10.0, pore_pressure_ppg=9.0)
        assert "error" in result

    def test_partial_evacuation_scenario_label(self, engine, typical_well):
        result = engine.calculate_collapse_load(**typical_well, evacuation_level_ft=3000.0)
        assert "Partial" in result["scenario"]

    def test_full_evacuation_default_produces_max_collapse(self, engine):
        """evacuation_level_ft=TVD should produce max collapse = MW * 0.052 * TVD at shoe."""
        result = engine.calculate_collapse_load(
            tvd_ft=11000, mud_weight_ppg=14.0, pore_pressure_ppg=12.0,
            evacuation_level_ft=11000,
        )
        expected_max = 14.0 * 0.052 * 11000  # 8008 psi
        assert result["max_collapse_load_psi"] == pytest.approx(expected_max, rel=0.05)

    def test_zero_evacuation_is_full_evacuation(self, engine):
        """evacuation_level_ft=0 means full evacuation (casing empty), max collapse = MW*0.052*TVD."""
        result = engine.calculate_collapse_load(
            tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=9.0,
            evacuation_level_ft=0.0,
            cement_top_tvd_ft=0.0,
        )
        # Full evacuation with no cement: collapse at shoe = MW * 0.052 * TVD
        expected = 10.0 * 0.052 * 10000  # 5200 psi
        assert result["max_collapse_load_psi"] == pytest.approx(expected, rel=0.02)

    def test_full_evacuation_scenario_label(self, engine, typical_well):
        """Full evacuation (evac=0 or evac=TVD) should be labeled 'Full Evacuation'."""
        result = engine.calculate_collapse_load(
            **typical_well, evacuation_level_ft=0)
        assert "Full" in result["scenario"]


# ===========================================================================
# 3. TENSION LOAD
# ===========================================================================
class TestTensionLoad:
    def test_air_weight_correct(self, engine, typical_casing):
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert result["air_weight_lbs"] == pytest.approx(470000, abs=1)

    def test_buoyancy_factor_formula(self, engine, typical_casing):
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
        )
        expected_bf = 1.0 - 10.0 / 65.4
        assert result["buoyancy_factor"] == pytest.approx(expected_bf, abs=0.001)

    def test_buoyant_weight_less_than_air(self, engine, typical_casing):
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert result["buoyant_weight_lbs"] < result["air_weight_lbs"]

    def test_shock_load_lubinski(self, engine, typical_casing):
        """Lubinski shock: F = 3200 * ppf."""
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
            shock_load=True,
        )
        assert result["shock_load_lbs"] == pytest.approx(3200.0 * 47.0, abs=1)

    def test_no_shock_when_disabled(self, engine, typical_casing):
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
            shock_load=False,
        )
        assert result["shock_load_lbs"] == 0.0

    def test_bending_increases_tension(self, engine, typical_casing):
        no_bend = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
            bending_load_dls=0.0,
        )
        with_bend = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
            bending_load_dls=5.0,
        )
        assert with_bend["total_tension_lbs"] > no_bend["total_tension_lbs"]

    def test_cross_section_area(self, engine, typical_casing):
        result = engine.calculate_tension_load(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.0, casing_od_in=9.625, casing_id_in=8.681,
        )
        expected_area = math.pi / 4.0 * (9.625**2 - 8.681**2)
        assert result["cross_section_area_sq_in"] == pytest.approx(expected_area, abs=0.01)


# ===========================================================================
# 4. BURST RATING (BARLOW)
# ===========================================================================
class TestBurstRating:
    def test_barlow_formula(self, engine):
        """P_burst = 0.875 * 2 * Yp * t / OD"""
        result = engine.calculate_burst_rating(
            casing_od_in=9.625, wall_thickness_in=0.472, yield_strength_psi=80000,
        )
        expected = 0.875 * 2 * 80000 * 0.472 / 9.625
        assert result["burst_rating_psi"] == pytest.approx(expected, abs=1)

    def test_higher_yield_higher_rating(self, engine):
        low = engine.calculate_burst_rating(9.625, 0.472, 55000)
        high = engine.calculate_burst_rating(9.625, 0.472, 110000)
        assert high["burst_rating_psi"] > low["burst_rating_psi"]

    def test_thicker_wall_higher_rating(self, engine):
        thin = engine.calculate_burst_rating(9.625, 0.312, 80000)
        thick = engine.calculate_burst_rating(9.625, 0.625, 80000)
        assert thick["burst_rating_psi"] > thin["burst_rating_psi"]

    def test_invalid_zero_od(self, engine):
        result = engine.calculate_burst_rating(0.0, 0.472, 80000)
        assert "error" in result

    def test_dt_ratio(self, engine):
        result = engine.calculate_burst_rating(9.625, 0.472, 80000)
        assert result["dt_ratio"] == pytest.approx(9.625 / 0.472, abs=0.01)


# ===========================================================================
# 5. COLLAPSE RATING (API 5C3 — 4 ZONES)
# ===========================================================================
class TestCollapseRating:
    def test_positive_rating(self, engine):
        result = engine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert result["collapse_rating_psi"] > 0

    def test_zone_assignment(self, engine):
        result = engine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert result["collapse_zone"] in ("Yield", "Plastic", "Transition", "Elastic")

    def test_boundaries_ordered(self, engine):
        result = engine.calculate_collapse_rating(9.625, 0.472, 80000)
        b = result["boundaries"]
        assert b["yield_plastic"] <= b["plastic_transition"] <= b["transition_elastic"]

    def test_higher_yield_higher_collapse(self, engine):
        low = engine.calculate_collapse_rating(9.625, 0.472, 55000)
        high = engine.calculate_collapse_rating(9.625, 0.472, 110000)
        assert high["collapse_rating_psi"] >= low["collapse_rating_psi"]

    def test_very_thin_wall_high_dt(self, engine):
        """Very thin wall (very high D/t) should NOT be in Yield zone."""
        result = engine.calculate_collapse_rating(9.625, 0.150, 80000)
        # D/t ~ 64, should be Transition or Elastic
        assert result["collapse_zone"] in ("Transition", "Elastic")
        assert result["dt_ratio"] > 50

    def test_invalid_dimensions(self, engine):
        result = engine.calculate_collapse_rating(0.0, 0.472, 80000)
        assert "error" in result


# ===========================================================================
# 6. BIAXIAL CORRECTION (API 5C3 ELLIPSE)
# ===========================================================================
class TestBiaxialCorrection:
    def test_no_axial_no_reduction(self, engine):
        result = engine.calculate_biaxial_correction(5000, 0, 80000)
        assert result["reduction_factor"] == pytest.approx(1.0, abs=0.001)
        assert result["corrected_collapse_psi"] == pytest.approx(5000, abs=1)

    def test_tension_reduces_collapse(self, engine):
        result = engine.calculate_biaxial_correction(5000, 40000, 80000)
        assert result["corrected_collapse_psi"] < 5000
        assert result["reduction_factor"] < 1.0

    def test_more_tension_more_reduction(self, engine):
        low_t = engine.calculate_biaxial_correction(5000, 20000, 80000)
        high_t = engine.calculate_biaxial_correction(5000, 60000, 80000)
        assert high_t["reduction_factor"] < low_t["reduction_factor"]

    def test_stress_ratio_clamped(self, engine):
        """Stress ratio should be clamped to [-0.99, 0.99]."""
        result = engine.calculate_biaxial_correction(5000, 90000, 80000)
        assert result["stress_ratio"] <= 0.99

    def test_zero_yield_error(self, engine):
        result = engine.calculate_biaxial_correction(5000, 1000, 0)
        assert "error" in result


# ===========================================================================
# 7. TRIAXIAL VME STRESS
# ===========================================================================
class TestTriaxialVME:
    def test_low_stress_passes(self, engine):
        result = engine.calculate_triaxial_vme(
            axial_stress_psi=10000, hoop_stress_psi=5000,
            yield_strength_psi=80000,
        )
        assert result["passes"] is True
        assert result["status"] == "PASS"

    def test_high_stress_fails(self, engine):
        result = engine.calculate_triaxial_vme(
            axial_stress_psi=70000, hoop_stress_psi=60000,
            yield_strength_psi=80000,
        )
        assert result["passes"] is False
        assert result["status"] == "FAIL"

    def test_marginal_status(self, engine):
        """High utilization (>90%) but still passing → MARGINAL."""
        # Target: VME ~ 0.92 * allowable
        # allowable = 80000/1.25 = 64000; need VME ~ 59000
        result = engine.calculate_triaxial_vme(
            axial_stress_psi=55000, hoop_stress_psi=0,
            yield_strength_psi=80000, safety_factor=1.25,
        )
        # VME ≈ 55000 for uniaxial, allowable = 64000, util = 85.9% → PASS
        # Need higher. Try axial=60000:
        result2 = engine.calculate_triaxial_vme(
            axial_stress_psi=60000, hoop_stress_psi=0,
            yield_strength_psi=80000, safety_factor=1.25,
        )
        # VME = 60000, allowable = 64000, util = 93.75% → MARGINAL
        assert result2["status"] == "MARGINAL"

    def test_utilization_percentage(self, engine):
        result = engine.calculate_triaxial_vme(
            axial_stress_psi=30000, hoop_stress_psi=0,
            yield_strength_psi=80000, safety_factor=1.0,
        )
        # VME = 30000, allowable = 80000, util = 37.5%
        assert result["utilization_pct"] == pytest.approx(37.5, abs=0.5)

    def test_stress_components_returned(self, engine):
        result = engine.calculate_triaxial_vme(
            axial_stress_psi=10000, hoop_stress_psi=5000,
            radial_stress_psi=1000, shear_stress_psi=500,
        )
        assert result["stress_components"]["axial_psi"] == 10000
        assert result["stress_components"]["shear_psi"] == 500


# ===========================================================================
# 8. GRADE SELECTION
# ===========================================================================
class TestGradeSelection:
    def test_selects_grade(self, engine, typical_casing):
        result = engine.select_casing_grade(
            required_burst_psi=3000, required_collapse_psi=3000,
            required_tension_lbs=500000,
            casing_od_in=9.625, wall_thickness_in=0.472,
        )
        assert result["selected_grade"] != "None"
        assert "None" not in result["selected_grade"]

    def test_selects_cheapest_that_passes(self, engine, typical_casing):
        """Should select lowest-yield grade that satisfies all criteria."""
        result = engine.select_casing_grade(
            required_burst_psi=2000, required_collapse_psi=2000,
            required_tension_lbs=200000,
            casing_od_in=9.625, wall_thickness_in=0.472,
        )
        selected = result["selected_details"]
        assert selected is not None
        # Verify it passes all
        assert selected["passes_all"] is True

    def test_all_candidates_listed(self, engine, typical_casing):
        result = engine.select_casing_grade(
            required_burst_psi=3000, required_collapse_psi=3000,
            required_tension_lbs=500000,
            casing_od_in=9.625, wall_thickness_in=0.472,
        )
        assert len(result["all_candidates"]) == len(CasingDesignEngine.CASING_GRADES)

    def test_extreme_loads_no_grade(self, engine, typical_casing):
        """Loads too high for any grade → no selection."""
        result = engine.select_casing_grade(
            required_burst_psi=50000, required_collapse_psi=50000,
            required_tension_lbs=50000000,
            casing_od_in=9.625, wall_thickness_in=0.472,
        )
        assert "None" in result["selected_grade"]

    def test_invalid_dimensions(self, engine):
        result = engine.select_casing_grade(
            required_burst_psi=3000, required_collapse_psi=3000,
            required_tension_lbs=500000,
            casing_od_in=0, wall_thickness_in=0.472,
        )
        assert "error" in result


# ===========================================================================
# 9. SAFETY FACTORS
# ===========================================================================
class TestSafetyFactors:
    def test_all_pass(self, engine):
        result = engine.calculate_safety_factors(
            burst_load_psi=3000, burst_rating_psi=5000,
            collapse_load_psi=3000, collapse_rating_psi=5000,
            tension_load_lbs=500000, tension_rating_lbs=1500000,
        )
        assert result["all_pass"] is True
        assert result["overall_status"] == "ALL PASS"

    def test_burst_failure(self, engine):
        result = engine.calculate_safety_factors(
            burst_load_psi=5000, burst_rating_psi=3000,
            collapse_load_psi=1000, collapse_rating_psi=5000,
            tension_load_lbs=100000, tension_rating_lbs=1500000,
        )
        assert result["all_pass"] is False
        assert result["results"]["burst"]["status"] == "FAIL"

    def test_governing_criterion(self, engine):
        result = engine.calculate_safety_factors(
            burst_load_psi=4000, burst_rating_psi=5000,   # SF=1.25
            collapse_load_psi=4500, collapse_rating_psi=5000,  # SF=1.11
            tension_load_lbs=800000, tension_rating_lbs=1000000,  # SF=1.25
        )
        assert result["governing_criterion"] == "collapse"

    def test_margin_percentage(self, engine):
        result = engine.calculate_safety_factors(
            burst_load_psi=1000, burst_rating_psi=2200,
            collapse_load_psi=1000, collapse_rating_psi=2000,
            tension_load_lbs=100000, tension_rating_lbs=320000,
            sf_burst_min=1.1, sf_collapse_min=1.0, sf_tension_min=1.6,
        )
        # Burst SF = 2.2, min=1.1 → margin = (2.2/1.1 - 1)*100 = 100%
        assert result["results"]["burst"]["margin_pct"] == pytest.approx(100.0, abs=0.5)


# ===========================================================================
# 10. FULL CASING DESIGN (MASTER METHOD)
# ===========================================================================
class TestFullCasingDesign:
    def test_all_sections_present(self, engine):
        result = engine.calculate_full_casing_design()
        expected_keys = {
            "burst_load", "collapse_load", "tension_load",
            "burst_rating", "collapse_rating", "biaxial_correction",
            "biaxial_depth_profile", "triaxial_vme", "grade_selection",
            "safety_factors", "sf_vs_depth", "summary",
            "burst_scenarios", "collapse_scenarios", "tension_scenarios",
            "connection", "temperature_derating",
        }
        assert expected_keys.issubset(result.keys())

    def test_multi_scenario_burst_present(self, engine):
        result = engine.calculate_full_casing_design()
        assert result["burst_scenarios"]["num_scenarios"] == 5
        assert result["summary"]["governing_burst_scenario"] != ""

    def test_multi_scenario_collapse_present(self, engine):
        result = engine.calculate_full_casing_design()
        assert result["collapse_scenarios"]["num_scenarios"] == 4
        assert result["summary"]["governing_collapse_scenario"] != ""

    def test_collapse_uses_full_evacuation_by_default(self, engine):
        """Default behavior: full evacuation produces realistic collapse load."""
        result = engine.calculate_full_casing_design(
            tvd_ft=11000, mud_weight_ppg=14.0, pore_pressure_ppg=12.0,
            cement_top_tvd_ft=0.0,
        )
        assert result["summary"]["max_collapse_load_psi"] > 5000

    def test_sf_collapse_not_absurdly_high(self, engine):
        """SF collapse should be reasonable (< 10), not 17+ like the bug produced."""
        result = engine.calculate_full_casing_design(
            tvd_ft=11000, mud_weight_ppg=14.0, pore_pressure_ppg=12.0,
        )
        assert result["summary"]["sf_collapse"] < 10.0

    def test_tension_scenarios_separated(self, engine):
        result = engine.calculate_full_casing_design()
        ts = result["tension_scenarios"]
        assert "running" in ts
        assert "stuck_pipe" in ts
        assert ts["running"]["shock_load_lbs"] > 0
        assert ts["running"]["overpull_lbs"] == 0
        assert ts["stuck_pipe"]["shock_load_lbs"] == 0
        assert ts["stuck_pipe"]["overpull_lbs"] > 0

    def test_biaxial_depth_profile_present(self, engine):
        result = engine.calculate_full_casing_design()
        bdp = result["biaxial_depth_profile"]
        assert bdp["num_points"] > 0
        assert len(bdp["profile"]) > 0
        first = bdp["profile"][0]["reduction_factor"]
        last = bdp["profile"][-1]["reduction_factor"]
        assert last >= first  # Less tension at shoe -> less derating -> higher factor

    def test_connection_verification_present(self, engine):
        result = engine.calculate_full_casing_design()
        assert "connection" in result
        assert result["connection"]["connection_type"] in ("STC", "LTC", "BTC", "PREMIUM")

    def test_sf_vs_depth_present(self, engine):
        result = engine.calculate_full_casing_design()
        assert "sf_vs_depth" in result
        assert result["sf_vs_depth"]["num_points"] > 0

    def test_sf_sanity_alert_on_unrealistic_values(self, engine):
        """If any SF > 10, an alert should be generated."""
        result = engine.calculate_full_casing_design(
            tvd_ft=1000, mud_weight_ppg=8.6, pore_pressure_ppg=8.6,
        )
        sf_alerts = [a for a in result["summary"]["alerts"] if "unusually high" in a]
        assert len(sf_alerts) > 0

    def test_summary_fields(self, engine):
        result = engine.calculate_full_casing_design()
        s = result["summary"]
        for key in ["selected_grade", "max_burst_load_psi", "max_collapse_load_psi",
                     "total_tension_lbs", "burst_rating_psi", "collapse_rating_psi",
                     "sf_burst", "sf_collapse", "sf_tension",
                     "triaxial_status", "overall_status", "alerts",
                     "governing_burst_scenario", "governing_collapse_scenario",
                     "tension_governing_scenario"]:
            assert key in s, f"Missing summary key: {key}"

    def test_alerts_is_list(self, engine):
        result = engine.calculate_full_casing_design()
        assert isinstance(result["summary"]["alerts"], list)

    def test_default_params_produce_valid_design(self, engine):
        result = engine.calculate_full_casing_design()
        assert result["summary"]["selected_grade"] != ""
        assert result["summary"]["sf_burst"] > 0
        assert result["summary"]["sf_collapse"] > 0
        assert result["summary"]["sf_tension"] > 0


# ===========================================================================
# 11. LAMÉ THICK-WALL HOOP STRESS
# ===========================================================================
class TestLameHoopStress:
    """Validate Lamé thick-wall hoop stress calculation."""

    def test_external_pressure_only(self):
        """External pressure only -> hoop stress negative (compressive) at inner wall."""
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=0, p_external_psi=5000,
        )
        assert result["hoop_inner_psi"] < 0  # compressive

    def test_internal_pressure_only(self):
        """Internal pressure only -> hoop stress positive (tensile) at inner wall."""
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=5000, p_external_psi=0,
        )
        assert result["hoop_inner_psi"] > 0  # tensile

    def test_known_value_external(self):
        """Verify against manual Lamé calculation for 9-5/8 casing under external pressure."""
        # For 9.625" OD, 8.681" ID with 5000 psi external (Pi=0):
        # ro=4.8125, ri=4.3405
        # sigma_h(ri) = -2*Po*ro^2 / (ro^2-ri^2)
        #             = -10000*23.16 / 4.32 ≈ -53,609 psi (compressive)
        ro, ri = 9.625 / 2, 8.681 / 2
        expected = -10000 * ro ** 2 / (ro ** 2 - ri ** 2)
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=0, p_external_psi=5000,
        )
        assert result["hoop_inner_psi"] == pytest.approx(expected, abs=1)

    def test_radial_stress_at_walls(self):
        """Radial stress at inner wall = -P_internal, at outer wall = -P_external."""
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=3000, p_external_psi=5000,
        )
        assert result["radial_inner_psi"] == -3000
        assert result["radial_outer_psi"] == -5000

    def test_equal_pressures_hydrostatic(self):
        """Equal internal and external pressure: hoop = radial = -P (hydrostatic)."""
        P = 5000
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=P, p_external_psi=P,
        )
        assert result["hoop_inner_psi"] == pytest.approx(-P, abs=1)
        assert result["hoop_outer_psi"] == pytest.approx(-P, abs=1)

    def test_invalid_dimensions(self):
        """Invalid dimensions (OD <= ID) should return error."""
        result = CasingDesignEngine.calculate_hoop_stress_lame(
            od_in=5.0, id_in=6.0,
            p_internal_psi=1000, p_external_psi=1000,
        )
        assert "error" in result


# ===========================================================================
# 12. THERMAL AXIAL LOAD
# ===========================================================================
class TestThermalAxialLoad:
    """Validate thermal axial load calculation."""

    def test_heating_produces_compressive(self):
        """Heating above cement temperature produces compressive load."""
        result = CasingDesignEngine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681,
            surface_temp_f=80, bottomhole_temp_f=300, cement_temp_f=150,
        )
        assert result["load_type"] == "compressive"
        assert result["thermal_load_lbs"] > 0

    def test_cooling_produces_tensile(self):
        """Cooling below cement temperature produces tensile load."""
        result = CasingDesignEngine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681,
            surface_temp_f=80, bottomhole_temp_f=100, cement_temp_f=150,
        )
        assert result["load_type"] == "tensile"
        assert result["thermal_load_lbs"] > 0

    def test_no_delta_t_no_load(self):
        """No temperature change means no thermal load."""
        result = CasingDesignEngine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681,
            surface_temp_f=80, bottomhole_temp_f=150, cement_temp_f=150,
        )
        assert result["thermal_load_lbs"] == 0

    def test_free_casing_no_load(self):
        """Free (unlocked) casing has no thermal load regardless of temperature."""
        result = CasingDesignEngine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681, locked_in=False,
        )
        assert result["thermal_load_lbs"] == 0

    def test_known_value(self):
        """Verify against hand calculation: F = E * A * alpha * delta_T."""
        od, id_ = 9.625, 8.681
        area = math.pi / 4.0 * (od ** 2 - id_ ** 2)
        delta_t = 100  # 250 - 150
        expected_load = 30e6 * area * 6.9e-6 * delta_t
        result = CasingDesignEngine.calculate_thermal_axial_load(
            casing_od_in=od, casing_id_in=id_,
            surface_temp_f=80, bottomhole_temp_f=250, cement_temp_f=150,
        )
        assert abs(result["thermal_load_lbs"] - expected_load) < 100


# ===========================================================================
# 13. CONNECTION VERIFICATION
# ===========================================================================
class TestConnectionVerification:
    """Validate connection verification against API 5B catalog."""

    def test_stc_lower_tension_than_body(self):
        """STC connection has 60% tension efficiency — is weak link."""
        result = CasingDesignEngine.verify_connection(
            connection_type="STC",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert result["tension_rating_lbs"] == 600000  # 60% of 1M
        assert result["is_weak_link"] is True

    def test_premium_passes_all(self):
        """Premium connection has 95% efficiency and is gas-tight."""
        result = CasingDesignEngine.verify_connection(
            connection_type="PREMIUM",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert result["passes_all"] is True
        assert result["gas_tight"] is True

    def test_unknown_connection_error(self):
        """Unknown connection type returns error."""
        result = CasingDesignEngine.verify_connection(
            connection_type="XYZ",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert "error" in result

    def test_btc_tension_efficiency(self):
        """BTC has 80% tension efficiency."""
        result = CasingDesignEngine.verify_connection(
            connection_type="BTC",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert result["tension_rating_lbs"] == 800000  # 80% of 1M
        assert result["efficiency"] == 0.80

    def test_stc_fails_under_high_tension(self):
        """STC should fail when applied tension exceeds connection rating / SF."""
        result = CasingDesignEngine.verify_connection(
            connection_type="STC",
            pipe_body_yield_lbs=500000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=250000,  # STC rating = 300000, SF=1.6 -> need 400000
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        # STC tension rating = 300000, required = 250000 * 1.6 = 400000
        assert result["passes_tension"] is False


# ===========================================================================
# 14. SAFETY FACTOR VS DEPTH PROFILE
# ===========================================================================
class TestSFvsDepth:
    """Validate safety factor vs depth profile calculation."""

    def test_profile_length_matches_input(self):
        """Output profile length must match input burst profile length."""
        burst = [{"tvd_ft": i * 500, "burst_load_psi": 3000 - i * 100} for i in range(20)]
        collapse = [{"tvd_ft": i * 500, "collapse_load_psi": i * 200} for i in range(20)]
        result = CasingDesignEngine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        assert len(result["profile"]) == 20
        assert result["num_points"] == 20

    def test_sf_values_positive(self):
        """All safety factors must be positive."""
        burst = [{"tvd_ft": 0, "burst_load_psi": 3000}]
        collapse = [{"tvd_ft": 0, "collapse_load_psi": 2000}]
        result = CasingDesignEngine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        point = result["profile"][0]
        assert point["sf_burst"] > 0
        assert point["sf_collapse"] > 0
        assert point["sf_tension"] > 0
        assert result["min_sf"] > 0

    def test_min_sf_depth_reported(self):
        """Must report the depth of minimum safety factor."""
        burst = [
            {"tvd_ft": 0, "burst_load_psi": 1000},
            {"tvd_ft": 5000, "burst_load_psi": 5000},
            {"tvd_ft": 10000, "burst_load_psi": 2000},
        ]
        collapse = [
            {"tvd_ft": 0, "collapse_load_psi": 500},
            {"tvd_ft": 5000, "collapse_load_psi": 3000},
            {"tvd_ft": 10000, "collapse_load_psi": 4000},
        ]
        result = CasingDesignEngine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        assert result["min_sf_depth_ft"] in [0, 5000, 10000]
        assert result["min_sf"] < 99.0

    def test_empty_profiles(self):
        """Empty input profiles should return empty result."""
        result = CasingDesignEngine.calculate_sf_vs_depth(
            burst_profile=[], collapse_profile=[],
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        assert result["num_points"] == 0
        assert result["profile"] == []

    def test_governing_sf_is_minimum(self):
        """Governing SF at each depth must be the minimum of burst, collapse, tension."""
        burst = [{"tvd_ft": 5000, "burst_load_psi": 4000}]
        collapse = [{"tvd_ft": 5000, "collapse_load_psi": 3000}]
        result = CasingDesignEngine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        point = result["profile"][0]
        expected_gov = min(point["sf_burst"], point["sf_collapse"], point["sf_tension"])
        assert point["governing_sf"] == expected_gov
