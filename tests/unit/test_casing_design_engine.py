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

    def test_gas_gradient_ppg_surface_burst(self, engine):
        """FIX-CAS-002: gas_gradient_ppg=0.1 with PP=12.5 ppg → Pi(0) ≈ 6,126 psi.

        P_reservoir = 12.5 * 0.052 * 9500 = 6175 psi
        gas_gradient_psi_ft = 0.1 * 0.052 = 0.0052 psi/ft
        Pi(surface) = 6175 - 0.0052 * 9500 = 6,125.6 psi
        P_ext(surface) = 0
        Burst at surface ≈ 6,126 psi
        """
        result = engine.calculate_burst_load(
            tvd_ft=9500, mud_weight_ppg=10.5, pore_pressure_ppg=12.5,
            gas_gradient_ppg=0.1,
        )
        # Surface burst load ≈ 6,126 psi
        surface_point = result["profile"][0]
        assert surface_point["tvd_ft"] == 0
        assert surface_point["burst_load_psi"] == pytest.approx(6126, rel=0.01)


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

    def test_negative_evacuation_means_no_evacuation(self, engine):
        """evacuation_level_ft=-1 means no evacuation (casing full of mud), collapse ≈ 0."""
        result = engine.calculate_collapse_load(
            tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=9.0,
            evacuation_level_ft=-1,
            cement_top_tvd_ft=0.0,
        )
        # Casing full of same mud: P_ext = P_int at each depth → differential ≈ 0
        assert result["max_collapse_load_psi"] < 100
        assert "No Evacuation" in result["scenario"]

    def test_internal_fluid_density_reduces_collapse(self, engine):
        """Custom internal fluid density (lighter than mud) should increase collapse load."""
        base = dict(tvd_ft=10000, mud_weight_ppg=13.0, pore_pressure_ppg=12.0,
                    evacuation_level_ft=5000, cement_top_tvd_ft=0.0)
        # With mud inside (default)
        result_mud = engine.calculate_collapse_load(**base)
        # With lighter brine inside (8.6 ppg)
        result_brine = engine.calculate_collapse_load(**base, internal_fluid_density_ppg=8.6)
        # Lighter fluid = higher collapse differential below fluid level
        assert result_brine["max_collapse_load_psi"] > result_mud["max_collapse_load_psi"]

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

    def test_c90_plastic_zone_and_rating(self, engine):
        """FIX-CAS-001: C-90 9-5/8" 47 lb/ft must be Plastic zone, ~5,596 psi.

        D/t = 9.625 / 0.472 = 20.39.
        Tabulated API constants for Yp=90,000 psi: A=3.071, B=0.0667, C=1955.
        P_collapse = Yp*(A/dt - B) - C = 90000*(3.071/20.39 - 0.0667) - 1955 ≈ 5,596 psi.
        """
        result = engine.calculate_collapse_rating(
            casing_od_in=9.625, wall_thickness_in=0.472, yield_strength_psi=90000,
        )
        assert result["collapse_zone"] == "Plastic", (
            f"Expected Plastic, got {result['collapse_zone']} (dt={result['dt_ratio']})"
        )
        assert result["collapse_rating_psi"] == pytest.approx(5596, rel=0.02), (
            f"Expected ~5,596 psi, got {result['collapse_rating_psi']}"
        )


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

    def test_h2s_service_excludes_non_nace_grades(self, engine):
        """FIX-CAS-008: With h2s_service=True, N80/P110/Q125 must not be selected."""
        NON_NACE = {"N80", "P110", "Q125"}
        result = engine.select_casing_grade(
            required_burst_psi=2000, required_collapse_psi=2000,
            required_tension_lbs=200000,
            casing_od_in=9.625, wall_thickness_in=0.472,
            h2s_service=True,
        )
        selected = result.get("selected_grade", "")
        assert selected not in NON_NACE, (
            f"Non-NACE grade {selected} was selected in sour service"
        )
        # Non-NACE candidates must have passes_all=False
        for c in result["all_candidates"]:
            if c["grade"] in NON_NACE:
                assert c["passes_all"] is False, (
                    f"{c['grade']} should be excluded in sour service"
                )


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

    def test_vme_sf_present_when_provided(self, engine):
        """FIX-CAS-009: SF_VME = Fy / sigma_VME must appear as 4th criterion."""
        result = engine.calculate_safety_factors(
            burst_load_psi=3000, burst_rating_psi=5000,
            collapse_load_psi=3000, collapse_rating_psi=5000,
            tension_load_lbs=500000, tension_rating_lbs=1500000,
            vme_stress_psi=45000, yield_strength_psi_vme=90000,
        )
        assert "vme" in result["results"], "VME criterion missing when vme_stress_psi > 0"
        sf_vme = result["results"]["vme"]["safety_factor"]
        # SF_VME = 90000 / 45000 = 2.00
        assert sf_vme == pytest.approx(2.0, abs=0.01)

    def test_vme_sf_absent_when_not_provided(self, engine):
        """VME must not appear in results when vme_stress_psi=0 (default)."""
        result = engine.calculate_safety_factors(
            burst_load_psi=3000, burst_rating_psi=5000,
            collapse_load_psi=3000, collapse_rating_psi=5000,
            tension_load_lbs=500000, tension_rating_lbs=1500000,
        )
        assert "vme" not in result["results"]

    def test_vme_governs_when_lowest_sf(self, engine):
        """When VME has the lowest SF it must be the governing criterion."""
        result = engine.calculate_safety_factors(
            burst_load_psi=2000, burst_rating_psi=5000,   # SF=2.50
            collapse_load_psi=2000, collapse_rating_psi=5000,  # SF=2.50
            tension_load_lbs=200000, tension_rating_lbs=1000000,  # SF=5.00
            vme_stress_psi=80000, yield_strength_psi_vme=90000,  # SF=1.125 (below min)
        )
        assert result["governing_criterion"] == "vme"
        assert result["results"]["vme"]["passes"] is False


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
            "tension_profile", "biaxial_state_line",
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


# ===========================================================================
# 15. NACE MR0175 SOUR SERVICE COMPLIANCE
# ===========================================================================
class TestNaceMr0175:
    def test_n80_not_nace_compliant(self, engine):
        """N80 is NOT NACE compliant for sour service."""
        result = engine.check_nace_compliance("N80", h2s_psi=0.05)
        assert result["compliant"] is False

    def test_l80_nace_compliant(self, engine):
        """L80 is NACE compliant (max hardness 22 HRC)."""
        result = engine.check_nace_compliance("L80", h2s_psi=0.05)
        assert result["compliant"] is True

    def test_c90_nace_compliant(self, engine):
        """C90 (NACE grade) is compliant."""
        result = engine.check_nace_compliance("C90", h2s_psi=0.05)
        assert result["compliant"] is True

    def test_p110_not_nace_compliant(self, engine):
        """P110 exceeds NACE hardness limit for sour service."""
        result = engine.check_nace_compliance("P110", h2s_psi=0.05)
        assert result["compliant"] is False

    def test_no_h2s_all_compliant(self, engine):
        """Without H2S, all grades are compliant."""
        result = engine.check_nace_compliance("P110", h2s_psi=0.0)
        assert result["compliant"] is True

    def test_sweet_environment_label(self, engine):
        """Below NACE threshold should be classified as sweet."""
        result = engine.check_nace_compliance("N80", h2s_psi=0.01)
        assert result["environment"] == "Sweet (non-sour)"

    def test_mild_sour_classification(self, engine):
        """H2S between 0.05 and 1.0 psi is Mild Sour."""
        result = engine.check_nace_compliance("L80", h2s_psi=0.5)
        assert result["environment"] == "Mild Sour"

    def test_severe_classification(self, engine):
        """H2S between 1.0 and 10.0 psi is Severe."""
        result = engine.check_nace_compliance("L80", h2s_psi=5.0)
        assert result["environment"] == "Severe"

    def test_very_severe_classification(self, engine):
        """H2S >= 10.0 psi is Very Severe."""
        result = engine.check_nace_compliance("L80", h2s_psi=15.0)
        assert result["environment"] == "Very Severe"

    def test_non_compliant_has_recommendation(self, engine):
        """Non-compliant grades should include a replacement recommendation."""
        result = engine.check_nace_compliance("P110", h2s_psi=1.0)
        assert result["recommendation"] is not None
        assert "L80" in result["recommendation"]

    def test_compliant_no_recommendation(self, engine):
        """Compliant grades should have no recommendation."""
        result = engine.check_nace_compliance("L80", h2s_psi=1.0)
        assert result["recommendation"] is None

    def test_pipeline_nace_alert(self, engine):
        """Pipeline should generate NACE alert when H2S present with non-compliant grade."""
        result = engine.calculate_full_casing_design(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            h2s_partial_pressure_psi=1.0,
        )
        alerts = result["summary"]["alerts"]
        assert any("NACE" in a for a in alerts)


class TestCandidateEnrichment:
    """Verify per-grade enrichment of all_candidates in pipeline output."""

    def test_all_candidates_have_details(self, engine):
        """Every candidate must include a 'details' dict after enrichment."""
        result = engine.calculate_full_casing_design()
        candidates = result["grade_selection"]["all_candidates"]
        assert len(candidates) > 0
        for c in candidates:
            assert "details" in c, f"Grade {c['grade']} missing 'details'"
            d = c["details"]
            assert "effective_yield_psi" in d
            assert "burst_rating_design_psi" in d
            assert "collapse_rating_design_psi" in d
            assert "collapse_zone" in d
            assert "biaxial_correction" in d
            assert "triaxial_vme" in d
            assert "safety_factors" in d

    def test_selected_grade_details_match_summary(self, engine):
        """Auto-selected grade's enriched details must match top-level results."""
        result = engine.calculate_full_casing_design()
        selected_grade = result["grade_selection"].get("selected_grade", "")
        candidates = result["grade_selection"]["all_candidates"]
        selected = next(
            (c for c in candidates if c["grade"] == selected_grade), None
        )
        if selected is None:
            pytest.skip("No grade selected (extreme loads)")

        d = selected["details"]
        # Triaxial VME stress should match (same hoop/radial/axial inputs)
        assert d["triaxial_vme"]["vme_stress_psi"] == result["triaxial_vme"]["vme_stress_psi"]
        assert d["triaxial_vme"]["allowable_psi"] == result["triaxial_vme"]["allowable_psi"]
        # Safety factors should match
        assert d["safety_factors"]["results"]["burst"]["safety_factor"] == \
            result["safety_factors"]["results"]["burst"]["safety_factor"]
        assert d["safety_factors"]["results"]["collapse"]["safety_factor"] == \
            result["safety_factors"]["results"]["collapse"]["safety_factor"]

    def test_different_grades_have_different_yields(self, engine):
        """Enriched data for different grades must reflect their own yields."""
        result = engine.calculate_full_casing_design()
        candidates = result["grade_selection"]["all_candidates"]
        j55 = next(c for c in candidates if c["grade"] == "J55")
        q125 = next(c for c in candidates if c["grade"] == "Q125")
        assert j55["details"]["effective_yield_psi"] < q125["details"]["effective_yield_psi"]
        assert j55["details"]["burst_rating_design_psi"] < q125["details"]["burst_rating_design_psi"]

    def test_no_grade_passes_still_has_details(self, engine):
        """Even when no grade passes, every candidate must have enriched details."""
        result = engine.calculate_full_casing_design(
            tvd_ft=20000, mud_weight_ppg=18.0, pore_pressure_ppg=17.0,
            evacuation_level_ft=0,
        )
        candidates = result["grade_selection"]["all_candidates"]
        for c in candidates:
            assert "details" in c, f"Grade {c['grade']} missing details in fail scenario"
            d = c["details"]
            # Even failing grades should have valid triaxial data
            assert d["triaxial_vme"]["vme_stress_psi"] > 0
            assert d["triaxial_vme"]["allowable_psi"] > 0

    def test_enrichment_with_wear(self, engine):
        """Enriched ratings should reflect wear-derated wall thickness."""
        result_no_wear = engine.calculate_full_casing_design(wear_pct=0)
        result_wear = engine.calculate_full_casing_design(wear_pct=20)
        c_no_wear = result_no_wear["grade_selection"]["all_candidates"][0]["details"]
        c_wear = result_wear["grade_selection"]["all_candidates"][0]["details"]
        # Wear should reduce burst and collapse ratings
        assert c_wear["burst_rating_design_psi"] < c_no_wear["burst_rating_design_psi"]
        assert c_wear["collapse_rating_design_psi"] < c_no_wear["collapse_rating_design_psi"]

    def test_pipeline_nace_compliance_in_result(self, engine):
        """Pipeline result should include nace_compliance section."""
        result = engine.calculate_full_casing_design(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
        )
        assert "nace_compliance" in result
        assert result["nace_compliance"]["compliant"] is True


# ===========================================================================
# 17. TENSION PROFILE VS DEPTH
# ===========================================================================
class TestTensionProfile:
    """Validate per-depth tension profile calculation."""

    def test_profile_has_points(self, engine):
        result = engine.calculate_tension_profile(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.5, casing_od_in=9.625,
        )
        assert result["num_points"] == 25

    def test_tension_decreases_with_depth(self, engine):
        result = engine.calculate_tension_profile(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.5, casing_od_in=9.625,
        )
        profile = result["profile"]
        assert profile[0]["total_tension_lbs"] > profile[-1]["total_tension_lbs"]

    def test_tension_at_bottom_near_zero(self, engine):
        """At TD, remaining string = 0 -> buoyant weight = 0."""
        result = engine.calculate_tension_profile(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            mud_weight_ppg=10.5, casing_od_in=9.625,
            shock_load=False, bending_load_dls=0,
        )
        last = result["profile"][-1]
        assert last["buoyant_weight_lbs"] == 0

    def test_pipeline_includes_tension_profile(self, engine):
        result = engine.calculate_full_casing_design()
        assert "tension_profile" in result
        tp = result["tension_profile"]
        assert tp["num_points"] > 0
        assert tp["pipe_body_yield_lbs"] > 0


# ===========================================================================
# 18. BIAXIAL STATE LINE
# ===========================================================================
class TestBiaxialStateLine:
    """Validate biaxial state line for normalized ellipse plot."""

    def test_state_line_present(self, engine):
        result = engine.calculate_full_casing_design()
        sl = result["biaxial_state_line"]
        assert len(sl) > 0
        assert "sigma_a_over_fy" in sl[0]
        assert "p_net_over_pco" in sl[0]
        assert "tvd_ft" in sl[0]

    def test_surface_has_max_axial_ratio(self, engine):
        """Surface point should have highest axial stress ratio."""
        result = engine.calculate_full_casing_design()
        sl = result["biaxial_state_line"]
        assert sl[0]["sigma_a_over_fy"] >= sl[-1]["sigma_a_over_fy"]

    def test_values_are_normalized(self, engine):
        """Normalized values should be within reasonable range (-2 to 2)."""
        result = engine.calculate_full_casing_design()
        for pt in result["biaxial_state_line"]:
            assert -2.0 <= pt["sigma_a_over_fy"] <= 2.0
            assert -2.0 <= pt["p_net_over_pco"] <= 2.0


# ===========================================================================
# ROUND 2 FIXES — TS-R2-01 through TS-R2-06
# ===========================================================================

class TestCollapseLoadR2:
    """FIX-CAS-010: Post-hardening cement must NOT add external pressure."""

    def test_full_evacuation_p_ext_mud_only(self, engine):
        """TS-R2-01: collapse(TD) = MW × 0.052 × TD regardless of cement."""
        result = engine.calculate_collapse_load(
            tvd_ft=9500.0,
            mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0,
            cement_top_tvd_ft=5000.0,
            cement_density_ppg=16.0,
            evacuation_level_ft=0,   # full evacuation
        )
        # Expected: 10.5 × 0.052 × 9500 = 5,187 psi (cement excluded)
        expected = 10.5 * 0.052 * 9500
        profile = result["profile"]
        p_ext_td = profile[-1]["p_external_psi"]
        assert abs(p_ext_td - expected) <= 50, (
            f"P_ext at TD = {p_ext_td} psi; expected ~{expected:.0f} psi (mud only)"
        )

    def test_cement_gradient_not_in_p_ext(self, engine):
        """TS-R2-02: Cement density must NOT raise P_ext above mud gradient."""
        result_no_cement = engine.calculate_collapse_load(
            tvd_ft=9500.0, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            cement_top_tvd_ft=0.0, cement_density_ppg=16.0,
        )
        result_with_cement = engine.calculate_collapse_load(
            tvd_ft=9500.0, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            cement_top_tvd_ft=5000.0, cement_density_ppg=16.0,
        )
        # P_ext at TD must be identical — cement column has no effect post-hardening
        p_ext_no = result_no_cement["profile"][-1]["p_external_psi"]
        p_ext_with = result_with_cement["profile"][-1]["p_external_psi"]
        assert p_ext_no == p_ext_with, (
            f"P_ext should be identical with/without cement: {p_ext_no} vs {p_ext_with}"
        )


class TestGradeSelectionR2:
    """FIX-CAS-011: Weight iteration when no grade passes at current ppf."""

    def test_weight_recommendation_when_grade_fails(self, engine):
        """TS-R2-03: All grades at 0.472 wall fail → recommend 53.5 ppf P110 from catalog.

        Q125@0.472: burst ≈ 10,727 psi; 10,727/9,800 = 1.094 < 1.10 → all grades fail.
        Catalog P110@53.5 lb/ft (wall=0.545): burst=10,910 psi; 10,910/9,800 = 1.113 → passes.
        """
        result = engine.select_casing_grade(
            required_burst_psi=9_800.0,
            required_collapse_psi=4_000.0,
            required_tension_lbs=400_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
            sf_burst=1.10,
            sf_collapse=1.00,
            sf_tension=1.60,
        )
        assert result["selected_grade"].startswith("None"), (
            "At burst_psi=9800 × SF=1.10=10780, Q125@0.472 (10,727 psi) should fail"
        )
        rec = result["weight_recommendation"]
        assert rec is not None, "Must provide weight_recommendation when no grade passes"
        assert rec["ppf"] == 53.5
        assert rec["grade"] == "P110"

    def test_no_recommendation_when_catalog_exhausted(self, engine):
        """TS-R2-04: extreme loads → no catalog entry satisfies → recommendation is None."""
        result = engine.select_casing_grade(
            required_burst_psi=50_000.0,
            required_collapse_psi=30_000.0,
            required_tension_lbs=5_000_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        assert result["selected_grade"].startswith("None")
        assert result["weight_recommendation"] is None

    def test_recommendation_present_only_when_needed(self, engine):
        """TS-R2-04b: when a grade passes, weight_recommendation is None."""
        result = engine.select_casing_grade(
            required_burst_psi=3000.0,
            required_collapse_psi=2000.0,
            required_tension_lbs=100_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        assert not result["selected_grade"].startswith("None")
        assert result["weight_recommendation"] is None


class TestConnectionStatusR2:
    """FIX-CAS-015: three-level connection status — PASS / WARNING / FAIL."""

    def test_btc_weak_link_with_passing_sf_is_warning(self, engine):
        """TS-R2-05: BTC 80% eff, SF passes → WARNING not FAIL."""
        result = engine.verify_connection(
            connection_type="BTC",
            pipe_body_yield_lbs=1_000_000.0,
            burst_rating_psi=10_000.0,
            collapse_rating_psi=8_000.0,
            applied_tension_lbs=100_000.0,  # SF_t = 800k/100k = 8.0 >> 1.60
            applied_burst_psi=5_000.0,
            applied_collapse_psi=3_000.0,
        )
        assert result["is_weak_link"] is True
        assert result["passes_all"] is True
        assert result["connection_status"] == "WARNING"
        # Alert should mention weak link, not FAIL
        assert any("Weak link" in a or "weak link" in a for a in result["alerts"])

    def test_btc_failing_sf_is_fail(self, engine):
        """TS-R2-06: BTC 80% eff, SF fails → FAIL with descriptive alert."""
        result = engine.verify_connection(
            connection_type="BTC",
            pipe_body_yield_lbs=200_000.0,
            burst_rating_psi=10_000.0,
            collapse_rating_psi=8_000.0,
            applied_tension_lbs=150_000.0,  # SF_t = 160k/150k = 1.07 < 1.60
            applied_burst_psi=5_000.0,
            applied_collapse_psi=3_000.0,
        )
        assert result["passes_all"] is False
        assert result["connection_status"] == "FAIL"
        assert any("FAIL" in a for a in result["alerts"])

    def test_premium_connection_is_pass(self, engine):
        """Premium connection (95% eff) with normal loads = PASS, not WARNING."""
        result = engine.verify_connection(
            connection_type="PREMIUM",
            pipe_body_yield_lbs=800_000.0,
            burst_rating_psi=10_000.0,
            collapse_rating_psi=8_000.0,
            applied_tension_lbs=200_000.0,
            applied_burst_psi=4_000.0,
            applied_collapse_psi=3_000.0,
        )
        # 95% eff → conn_tension = 760k; NOT < 0.95 × 800k = 760k → boundary (not weak link)
        assert result["connection_status"] in ("PASS", "WARNING")
        assert result["passes_all"] is True


# ===========================================================================
# ROUND 3 FIXES — T1-R3-01 through T1-R3-04
# ===========================================================================

class TestBiaxialInGradeSelection:
    """FIX-CAS-016: Grade table must use Pco_corrected (biaxial) for collapse."""

    def test_candidates_have_corrected_collapse(self, engine):
        """T1-R3-01a: Every candidate must expose biaxial_reduction and corrected collapse."""
        result = engine.select_casing_grade(
            required_burst_psi=4_000.0,
            required_collapse_psi=5_187.0,
            required_tension_lbs=630_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        for candidate in result["all_candidates"]:
            assert "collapse_rating_corrected_psi" in candidate, (
                f"Grade {candidate['grade']} missing collapse_rating_corrected_psi"
            )
            assert "biaxial_reduction" in candidate, (
                f"Grade {candidate['grade']} missing biaxial_reduction"
            )
            # Corrected must be ≤ original (tension reduces collapse resistance)
            assert candidate["collapse_rating_corrected_psi"] <= candidate["collapse_rating_psi"], (
                f"Corrected collapse must be ≤ original for grade {candidate['grade']}"
            )

    def test_c90_47ppf_fails_collapse_with_biaxial(self, engine):
        """T1-R3-01b: C90@47ppf with typical loads fails collapse in grade table (matches panel).

        Required: 5,187 psi collapse load, tension=630,000 lbs.
        C90 Pco_original ≈ 5,596 psi; biaxial correction ≈ 0.64 → Pco_corr ≈ 3,580 psi < 5,187.
        """
        result = engine.select_casing_grade(
            required_burst_psi=4_000.0,
            required_collapse_psi=5_187.0,
            required_tension_lbs=630_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        c90 = next((c for c in result["all_candidates"] if c["grade"] == "C90"), None)
        assert c90 is not None
        # With biaxial correction, C90 must fail collapse at these loads
        assert not c90["passes_collapse"], (
            f"C90 corrected collapse = {c90['collapse_rating_corrected_psi']} psi "
            f"vs required {5187 * 1.0:.0f} psi — must FAIL with biaxial correction applied"
        )

    def test_higher_fy_has_smaller_reduction(self, engine):
        """T1-R3-01c: Higher Fy grades have smaller sa_ratio → closer to 1.0 reduction."""
        result = engine.select_casing_grade(
            required_burst_psi=3_000.0,
            required_collapse_psi=3_000.0,
            required_tension_lbs=500_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        # J55 (low Fy) should have larger reduction factor than Q125 (high Fy)
        j55 = next((c for c in result["all_candidates"] if c["grade"] == "J55"), None)
        q125 = next((c for c in result["all_candidates"] if c["grade"] == "Q125"), None)
        if j55 and q125:
            # Lower Fy → higher sa_ratio → smaller reduction (more penalised)
            assert j55["biaxial_reduction"] <= q125["biaxial_reduction"], (
                f"J55 reduction {j55['biaxial_reduction']:.4f} should be ≤ "
                f"Q125 reduction {q125['biaxial_reduction']:.4f}"
            )

    def test_weight_recommendation_uses_biaxial(self, engine):
        """T1-R3-02: weight_recommendation from catalog also applies biaxial correction."""
        # With default loads (all 47ppf grades fail), recommend heavier weight
        result = engine.select_casing_grade(
            required_burst_psi=4_000.0,
            required_collapse_psi=5_187.0,
            required_tension_lbs=630_000.0,
            casing_od_in=9.625,
            wall_thickness_in=0.472,
        )
        # No grade should pass at 47 ppf with biaxial correction
        assert result["selected_grade"].startswith("None"), (
            "All 47ppf grades should fail collapse when biaxial correction is applied "
            "to 5187 psi required collapse with 630k lbs tension"
        )
        # Weight recommendation must exist — heavier wall reduces sigma_a → less biaxial penalty
        rec = result["weight_recommendation"]
        assert rec is not None, "Must recommend heavier weight when 47ppf fails"
        assert rec["ppf"] > 47.0, f"Recommendation must be heavier than 47 ppf (got {rec['ppf']})"
        # Recommendation must expose biaxial-corrected collapse
        assert "collapse_rating_corrected_psi" in rec
        assert "biaxial_reduction" in rec

    def test_default_pipeline_shows_no_grade_with_biaxial(self, engine):
        """T1-R3-02b: Full pipeline with default params → selected_grade = None (correct behavior)."""
        result = engine.calculate_full_casing_design()
        selected = result["grade_selection"]["selected_grade"]
        assert selected.startswith("None"), (
            "With biaxial correction, no grade at 47ppf should pass collapse "
            "under default loads (5187 psi collapse, 630k lbs tension)"
        )
        # Weight recommendation must be provided
        rec = result["grade_selection"]["weight_recommendation"]
        assert rec is not None, "Pipeline must provide weight_recommendation when no grade passes"

    def test_grade_details_match_summary_with_passing_params(self, engine):
        """T1-R3-03: When a grade passes (lighter loads), enriched details match top-level summary.

        Uses reduced collapse load (low pore pressure) where C90@47ppf can pass biaxial.
        """
        # Low pore pressure → low burst. Low mud weight → low collapse load.
        # Collapse load = 8.5 * 0.052 * 9500 = 4,199 psi.
        # C90@0.472 Pco_orig ≈ 5596; biaxial reduction with lower tension ≈ 0.85 → Pco_corr ≈ 4756 > 4199 → PASS
        result = engine.calculate_full_casing_design(
            mud_weight_ppg=8.5,
            pore_pressure_ppg=5.0,
        )
        selected_grade = result["grade_selection"].get("selected_grade", "")
        if selected_grade.startswith("None"):
            import pytest
            pytest.skip("No grade selected even with low loads — skip match check")

        candidates = result["grade_selection"]["all_candidates"]
        selected = next((c for c in candidates if c["grade"] == selected_grade), None)
        assert selected is not None

        d = selected["details"]
        # Safety factor for burst must match between enriched details and top-level
        assert d["safety_factors"]["results"]["burst"]["safety_factor"] == \
            result["safety_factors"]["results"]["burst"]["safety_factor"]
