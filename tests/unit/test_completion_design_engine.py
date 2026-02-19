"""
Unit tests for CompletionDesignEngine.
Tests: calculate_penetration_depth, calculate_productivity_ratio,
       calculate_underbalance, select_gun_configuration,
       calculate_fracture_initiation, calculate_fracture_gradient,
       optimize_perforation_design, calculate_full_completion_design.
"""
import math
import pytest
from orchestrator.completion_design_engine import CompletionDesignEngine


# ============================================================
# calculate_penetration_depth (6 tests)
# ============================================================

class TestPenetrationDepth:

    def test_correction_factors_in_valid_ranges(self):
        """All individual correction factors must stay within API RP 19B bounds."""
        r = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=20.0,
            effective_stress_psi=8000,
            temperature_f=400,
            completion_fluid="oil_based",
            cement_strength_psi=6000,
            casing_thickness_in=0.7,
        )
        cfs = r["correction_factors"]
        assert 0.60 <= cfs["cf_stress"] <= 1.00
        assert 0.80 <= cfs["cf_temperature"] <= 1.10
        assert 0.70 <= cfs["cf_fluid"] <= 1.00
        assert 0.90 <= cfs["cf_cement"] <= 1.00
        assert 0.90 <= cfs["cf_casing"] <= 1.00
        # Total CF is product of all, so verify consistency
        assert cfs["cf_total"] == pytest.approx(
            cfs["cf_stress"] * cfs["cf_temperature"] * cfs["cf_fluid"]
            * cfs["cf_cement"] * cfs["cf_casing"],
            abs=0.002,
        )

    def test_higher_stress_lowers_cf_stress(self):
        """Increasing effective stress must reduce cf_stress monotonically."""
        low = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=15.0, effective_stress_psi=1000
        )
        high = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=15.0, effective_stress_psi=12000
        )
        assert high["correction_factors"]["cf_stress"] < low["correction_factors"]["cf_stress"]
        assert high["penetration_corrected_in"] < low["penetration_corrected_in"]

    def test_different_fluids_yield_different_factors(self):
        """Acid gives cf_fluid=1.0 (best), diesel=0.75 (worst)."""
        acid = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=12.0, completion_fluid="acid"
        )
        diesel = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=12.0, completion_fluid="diesel"
        )
        assert acid["correction_factors"]["cf_fluid"] > diesel["correction_factors"]["cf_fluid"]
        assert acid["penetration_corrected_in"] > diesel["penetration_corrected_in"]

    def test_efficiency_is_cf_total_times_100(self):
        """efficiency_pct should equal cf_total * 100."""
        r = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=18.0,
            effective_stress_psi=5000,
            temperature_f=300,
            completion_fluid="brine",
        )
        assert r["efficiency_pct"] == pytest.approx(
            r["correction_factors"]["cf_total"] * 100, abs=0.15
        )

    def test_zero_stress_gives_unity_cf_stress(self):
        """With no effective stress, cf_stress should be 1.0."""
        r = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=10.0, effective_stress_psi=0.0
        )
        assert r["correction_factors"]["cf_stress"] == 1.0

    def test_entry_hole_positive_and_smaller_than_penetration(self):
        """Entry hole must be positive and significantly smaller than penetration."""
        r = CompletionDesignEngine.calculate_penetration_depth(
            penetration_berea_in=16.0, effective_stress_psi=4000
        )
        assert r["entry_hole_corrected_in"] > 0
        assert r["entry_hole_corrected_in"] < r["penetration_corrected_in"]


# ============================================================
# calculate_productivity_ratio (6 tests)
# ============================================================

class TestProductivityRatio:

    def test_pr_positive_and_classified(self):
        """Productivity ratio must be positive with valid quality label."""
        r = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100,
            perforation_length_in=12.0,
            perforation_radius_in=0.25,
            wellbore_radius_ft=0.354,
            spf=6,
            phasing_deg=90,
            formation_thickness_ft=50,
        )
        # PR can exceed 1.0 when negative skin (stimulated) via Karakas-Tariq
        assert r["productivity_ratio"] > 0
        assert r["quality"] in ("Excellent", "Good", "Fair", "Poor")

    def test_higher_spf_lower_skin(self):
        """More shots per foot should reduce total skin."""
        low_spf = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100, perforation_length_in=12.0,
            perforation_radius_in=0.25, wellbore_radius_ft=0.354,
            spf=2, phasing_deg=90, formation_thickness_ft=50,
        )
        high_spf = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100, perforation_length_in=12.0,
            perforation_radius_in=0.25, wellbore_radius_ft=0.354,
            spf=12, phasing_deg=90, formation_thickness_ft=50,
        )
        assert high_spf["skin_total"] <= low_spf["skin_total"]
        assert high_spf["productivity_ratio"] >= low_spf["productivity_ratio"]

    def test_different_phasings_produce_different_skins(self):
        """0-degree phasing should have different skin than 120-degree."""
        r0 = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=50, perforation_length_in=10.0,
            perforation_radius_in=0.20, wellbore_radius_ft=0.354,
            spf=6, phasing_deg=0, formation_thickness_ft=30,
        )
        r120 = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=50, perforation_length_in=10.0,
            perforation_radius_in=0.20, wellbore_radius_ft=0.354,
            spf=6, phasing_deg=120, formation_thickness_ft=30,
        )
        assert r0["skin_total"] != r120["skin_total"]

    def test_damage_increases_skin(self):
        """Adding formation damage must increase total skin and lower PR."""
        no_dmg = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100, perforation_length_in=12.0,
            perforation_radius_in=0.25, wellbore_radius_ft=0.354,
            spf=6, phasing_deg=90, formation_thickness_ft=50,
            damage_radius_ft=0.0, damage_permeability_md=0.0,
        )
        with_dmg = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100, perforation_length_in=12.0,
            perforation_radius_in=0.25, wellbore_radius_ft=0.354,
            spf=6, phasing_deg=90, formation_thickness_ft=50,
            damage_radius_ft=1.0, damage_permeability_md=10.0,
        )
        assert with_dmg["skin_components"]["s_damage"] > 0
        assert with_dmg["skin_total"] > no_dmg["skin_total"]
        assert with_dmg["productivity_ratio"] < no_dmg["productivity_ratio"]

    def test_skin_components_sum_to_total(self):
        """Individual skin components must add up to skin_total."""
        r = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=50, perforation_length_in=10.0,
            perforation_radius_in=0.20, wellbore_radius_ft=0.354,
            spf=4, phasing_deg=60, formation_thickness_ft=40,
            damage_radius_ft=0.8, damage_permeability_md=5.0,
        )
        sc = r["skin_components"]
        computed_sum = (sc["s_perforation"] + sc["s_vertical"]
                        + sc["s_wellbore"] + sc["s_damage"])
        assert r["skin_total"] == pytest.approx(computed_sum, abs=0.01)

    def test_quality_label_matches_pr_value(self):
        """Verify quality label thresholds: >=0.90 Excellent, >=0.75 Good, >=0.50 Fair, else Poor."""
        r = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=200, perforation_length_in=18.0,
            perforation_radius_in=0.35, wellbore_radius_ft=0.354,
            spf=12, phasing_deg=120, formation_thickness_ft=60,
        )
        pr = r["productivity_ratio"]
        if pr >= 0.90:
            assert r["quality"] == "Excellent"
        elif pr >= 0.75:
            assert r["quality"] == "Good"
        elif pr >= 0.50:
            assert r["quality"] == "Fair"
        else:
            assert r["quality"] == "Poor"


# ============================================================
# calculate_underbalance (5 tests)
# ============================================================

class TestUnderbalance:

    def test_optimal_underbalance(self):
        """Sandstone, medium perm, delta_p within 500-1500 => Optimal."""
        r = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=4000,
            formation_permeability_md=50,
            formation_type="sandstone",
        )
        assert r["underbalance_psi"] == pytest.approx(1000.0, abs=0.1)
        assert r["is_underbalanced"] is True
        assert r["status"] == "Optimal"

    def test_insufficient_underbalance(self):
        """Delta_p below recommended lower bound."""
        r = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=4900,
            formation_permeability_md=50,
            formation_type="sandstone",
        )
        assert r["underbalance_psi"] == pytest.approx(100.0, abs=0.1)
        assert r["status"] == "Insufficient Underbalance"

    def test_excessive_underbalance(self):
        """Delta_p above recommended upper bound."""
        r = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=1000,
            formation_permeability_md=50,
            formation_type="sandstone",
        )
        assert r["underbalance_psi"] == pytest.approx(4000.0, abs=0.1)
        assert r["status"] == "Excessive Underbalance"

    def test_overbalanced_condition(self):
        """Wellbore pressure > reservoir pressure => overbalanced."""
        r = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=4000,
            wellbore_pressure_psi=5000,
            formation_permeability_md=50,
            formation_type="sandstone",
        )
        assert r["is_underbalanced"] is False
        assert r["status"] == "Overbalanced"
        assert r["overbalance_psi"] == pytest.approx(1000.0, abs=0.1)

    def test_different_permeability_classes(self):
        """High, medium, and low permeability should yield different recommended ranges."""
        high = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000, wellbore_pressure_psi=4500,
            formation_permeability_md=200, formation_type="sandstone",
        )
        low = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000, wellbore_pressure_psi=4500,
            formation_permeability_md=5, formation_type="sandstone",
        )
        assert high["permeability_class"] == "High (>100 mD)"
        assert low["permeability_class"] == "Low (<10 mD)"
        assert high["recommended_range_psi"][0] < low["recommended_range_psi"][0]


# ============================================================
# select_gun_configuration (4 tests)
# ============================================================

class TestGunSelection:

    def test_compatible_guns_for_standard_7in_casing(self):
        """7-inch casing (ID ~6.276) should have multiple compatible guns."""
        r = CompletionDesignEngine.select_gun_configuration(
            casing_id_in=6.276
        )
        assert r["total_compatible_guns"] >= 2
        assert r["recommended"] is not None
        assert r["recommended"]["clearance_in"] >= 0.25

    def test_through_tubing_limits_gun_size(self):
        """Through-tubing perforating reduces available guns."""
        casing_only = CompletionDesignEngine.select_gun_configuration(
            casing_id_in=6.276, tubing_od_in=0.0
        )
        through_tubing = CompletionDesignEngine.select_gun_configuration(
            casing_id_in=6.276, tubing_od_in=2.875
        )
        assert through_tubing["is_through_tubing"] is True
        assert through_tubing["total_compatible_guns"] <= casing_only["total_compatible_guns"]

    def test_no_compatible_guns_for_very_small_casing(self):
        """An extremely small casing ID should yield no compatible guns."""
        r = CompletionDesignEngine.select_gun_configuration(
            casing_id_in=1.5
        )
        assert r["total_compatible_guns"] == 0
        assert r["recommended"] is None
        assert r["alternatives"] == []

    def test_large_casing_has_all_guns(self):
        """13-3/8 inch casing (ID ~12.415) should accommodate all gun sizes."""
        r = CompletionDesignEngine.select_gun_configuration(
            casing_id_in=12.415
        )
        assert r["total_compatible_guns"] == len(CompletionDesignEngine.GUN_DATABASE)


# ============================================================
# calculate_fracture_initiation (4 tests)
# ============================================================

class TestFractureInitiation:

    def test_breakdown_formula(self):
        """Verify P_breakdown = 3*sigma_min - sigma_max + T - alpha*Pp."""
        sigma_min = 5000.0
        sigma_max = 8000.0
        T = 500.0
        Pp = 4000.0
        alpha = 1.0
        expected = 3 * sigma_min - sigma_max + T - alpha * Pp
        r = CompletionDesignEngine.calculate_fracture_initiation(
            sigma_min_psi=sigma_min, sigma_max_psi=sigma_max,
            tensile_strength_psi=T, pore_pressure_psi=Pp,
            biot_coefficient=alpha,
        )
        assert r["breakdown_pressure_psi"] == pytest.approx(expected, abs=0.2)

    def test_reopening_less_than_breakdown(self):
        """Reopening pressure must always be lower than breakdown (T > 0)."""
        r = CompletionDesignEngine.calculate_fracture_initiation(
            sigma_min_psi=6000, sigma_max_psi=9000,
            tensile_strength_psi=800, pore_pressure_psi=3500,
            biot_coefficient=0.9,
        )
        assert r["reopening_pressure_psi"] < r["breakdown_pressure_psi"]
        diff = r["breakdown_pressure_psi"] - r["reopening_pressure_psi"]
        assert diff == pytest.approx(800.0, abs=0.2)  # diff = tensile strength

    def test_closure_equals_sigma_min(self):
        """Closure pressure should equal minimum horizontal stress."""
        r = CompletionDesignEngine.calculate_fracture_initiation(
            sigma_min_psi=4500, sigma_max_psi=7000,
            tensile_strength_psi=600, pore_pressure_psi=3000,
        )
        assert r["closure_pressure_psi"] == pytest.approx(4500.0, abs=0.1)

    def test_anisotropic_stress_orientation(self):
        """High stress ratio (>1.1) should report perpendicular fracture orientation."""
        r = CompletionDesignEngine.calculate_fracture_initiation(
            sigma_min_psi=4000, sigma_max_psi=6000,
            tensile_strength_psi=500, pore_pressure_psi=3000,
        )
        assert r["stress_ratio"] == pytest.approx(1.5, abs=0.01)
        assert "perpendicular" in r["fracture_orientation"].lower()


# ============================================================
# calculate_fracture_gradient (4 tests)
# ============================================================

class TestFractureGradient:

    def test_eaton_gradient_calculation(self):
        """Verify Eaton equation: FG = Pp/D + nu/(1-nu) * (OB-Pp)/D + tect/D."""
        depth = 10000.0
        Pp = 4500.0       # 0.45 psi/ft normal
        OB = 10000.0      # 1.0 psi/ft
        nu = 0.25
        tect = 0.0
        stress_ratio = nu / (1.0 - nu)
        expected_frac_p = Pp + stress_ratio * (OB - Pp) + tect
        expected_grad = expected_frac_p / depth

        r = CompletionDesignEngine.calculate_fracture_gradient(
            depth_tvd_ft=depth, pore_pressure_psi=Pp,
            overburden_stress_psi=OB, poisson_ratio=nu,
            tectonic_stress_psi=tect,
        )
        assert r["fracture_pressure_psi"] == pytest.approx(expected_frac_p, abs=1.0)
        assert r["fracture_gradient_psi_ft"] == pytest.approx(expected_grad, abs=0.001)

    def test_profile_generation(self):
        """Depth profile should contain entries and end at exact TVD."""
        r = CompletionDesignEngine.calculate_fracture_gradient(
            depth_tvd_ft=8500, pore_pressure_psi=3825,
            overburden_stress_psi=8500, poisson_ratio=0.25,
        )
        profile = r["depth_profile"]
        assert len(profile) >= 2
        # Last entry should be at TVD
        assert profile[-1]["depth_ft"] == 8500
        # All entries have required keys
        for entry in profile:
            assert "pore_pressure_ppg" in entry
            assert "fracture_gradient_ppg" in entry
            assert "overburden_ppg" in entry

    def test_mud_weight_window_positive(self):
        """Fracture gradient should exceed pore gradient, giving positive window."""
        r = CompletionDesignEngine.calculate_fracture_gradient(
            depth_tvd_ft=10000, pore_pressure_psi=4500,
            overburden_stress_psi=10000, poisson_ratio=0.25,
        )
        assert r["mud_weight_window_ppg"] > 0
        assert r["fracture_gradient_ppg"] > r["pore_gradient_ppg"]

    def test_zero_depth_returns_error(self):
        """Depth of zero should return an error dict."""
        r = CompletionDesignEngine.calculate_fracture_gradient(
            depth_tvd_ft=0, pore_pressure_psi=4000,
            overburden_stress_psi=10000, poisson_ratio=0.25,
        )
        assert "error" in r


# ============================================================
# optimize_perforation_design (4 tests)
# ============================================================

class TestOptimizePerforation:

    def test_25_configurations_tested(self):
        """5 SPF x 5 phasing = 25 total configurations."""
        r = CompletionDesignEngine.optimize_perforation_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=40,
            reservoir_pressure_psi=5000,
        )
        assert r["total_configurations_tested"] == 25

    def test_optimal_in_top_5(self):
        """The optimal config must be first in top_5 list."""
        r = CompletionDesignEngine.optimize_perforation_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=40,
            reservoir_pressure_psi=5000,
        )
        assert len(r["top_5_configurations"]) == 5
        opt = r["optimal_configuration"]
        assert r["top_5_configurations"][0]["productivity_ratio"] == opt["productivity_ratio"]
        assert r["top_5_configurations"][0]["spf"] == opt["spf"]

    def test_sensitivity_data_present(self):
        """Both SPF and phasing sensitivity arrays must be populated."""
        r = CompletionDesignEngine.optimize_perforation_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=40,
            reservoir_pressure_psi=5000,
        )
        assert len(r["spf_sensitivity"]) >= 2
        assert len(r["phasing_sensitivity"]) >= 2
        # SPF sensitivity entries have required keys
        for entry in r["spf_sensitivity"]:
            assert "spf" in entry
            assert "productivity_ratio" in entry

    def test_corrected_penetration_passed_through(self):
        """The corrected penetration value must be present in results."""
        r = CompletionDesignEngine.optimize_perforation_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=40,
            reservoir_pressure_psi=5000,
            penetration_berea_in=15.0,
            effective_stress_psi=5000,
        )
        assert r["penetration_corrected_in"] > 0
        assert r["penetration_corrected_in"] < 15.0  # must be reduced by CFs


# ============================================================
# calculate_full_completion_design (5 tests)
# ============================================================

class TestFullCompletionDesign:

    @pytest.fixture
    def full_result(self):
        """Standard full-design result for reuse across tests."""
        return CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=50,
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=4200,
            depth_tvd_ft=10000,
            overburden_stress_psi=10000,
            pore_pressure_psi=4500,
            sigma_min_psi=5500,
            sigma_max_psi=8000,
            tensile_strength_psi=500,
            poisson_ratio=0.25,
            penetration_berea_in=14.0,
            effective_stress_psi=4000,
            temperature_f=250,
            completion_fluid="brine",
        )

    def test_all_sub_results_present(self, full_result):
        """Full analysis must contain all sub-module keys."""
        required_keys = [
            "summary", "penetration", "gun_selection",
            "underbalance", "fracture_initiation",
            "fracture_gradient", "optimization", "alerts",
        ]
        for key in required_keys:
            assert key in full_result, f"Missing key: {key}"

    def test_summary_has_critical_fields(self, full_result):
        """Summary dict must contain the critical design parameters."""
        s = full_result["summary"]
        assert "penetration_corrected_in" in s
        assert "recommended_gun" in s
        assert "optimal_spf" in s
        assert "productivity_ratio" in s
        assert "underbalance_psi" in s
        assert "fracture_gradient_ppg" in s
        assert "breakdown_pressure_psi" in s
        assert "alerts" in s

    def test_alerts_generated_for_non_optimal_underbalance(self):
        """Overbalanced perforating should generate an alert."""
        r = CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=50,
            reservoir_pressure_psi=4000,
            wellbore_pressure_psi=5000,  # overbalanced
            depth_tvd_ft=10000,
            overburden_stress_psi=10000,
            pore_pressure_psi=4500,
            sigma_min_psi=5500,
            sigma_max_psi=8000,
        )
        assert len(r["alerts"]) >= 1
        underbalance_alert = any("Underbalance" in a or "underbalance" in a.lower()
                                  for a in r["alerts"])
        assert underbalance_alert, "Expected underbalance alert when overbalanced"

    def test_no_gun_alert_for_tiny_casing(self):
        """Very small casing should trigger 'no compatible guns' alert."""
        r = CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=1.5,  # impossibly small
            formation_permeability_md=100,
            formation_thickness_ft=50,
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=4000,
            depth_tvd_ft=10000,
            overburden_stress_psi=10000,
            pore_pressure_psi=4500,
            sigma_min_psi=5500,
            sigma_max_psi=8000,
        )
        gun_alert = any("No compatible guns" in a for a in r["alerts"])
        assert gun_alert, "Expected gun compatibility alert for tiny casing"

    def test_low_penetration_efficiency_alert(self):
        """Extreme downhole conditions should trigger low-efficiency alert."""
        r = CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=6.276,
            formation_permeability_md=100,
            formation_thickness_ft=50,
            reservoir_pressure_psi=5000,
            wellbore_pressure_psi=4000,
            depth_tvd_ft=10000,
            overburden_stress_psi=10000,
            pore_pressure_psi=4500,
            sigma_min_psi=5500,
            sigma_max_psi=8000,
            penetration_berea_in=12.0,
            effective_stress_psi=15000,   # very high stress
            temperature_f=550,             # very high temperature
            completion_fluid="diesel",     # worst fluid
        )
        efficiency = r["penetration"]["efficiency_pct"]
        if efficiency < 70:
            eff_alert = any("efficiency" in a.lower() for a in r["alerts"])
            assert eff_alert, "Expected low efficiency alert"
        # Either way, efficiency should be meaningfully degraded
        assert efficiency < 85


# ============================================================
# Edge-case / cross-cutting tests (1 test)
# ============================================================

class TestEdgeCases:

    def test_carbonate_formation_underbalance_ranges_differ(self):
        """Carbonate ranges should differ from sandstone for same permeability."""
        sand = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000, wellbore_pressure_psi=4500,
            formation_permeability_md=50, formation_type="sandstone",
        )
        carb = CompletionDesignEngine.calculate_underbalance(
            reservoir_pressure_psi=5000, wellbore_pressure_psi=4500,
            formation_permeability_md=50, formation_type="carbonate",
        )
        assert sand["recommended_range_psi"] != carb["recommended_range_psi"]
