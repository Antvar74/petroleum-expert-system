"""
Phase 6 Elite Tests — Casing Design Engine Elite Upgrades.

Tests multi-scenario burst/collapse, temperature derating,
expanded catalog, combination strings, running loads, and wear allowance.
"""

import pytest
import math
from orchestrator.casing_design_engine import CasingDesignEngine


# ═══════════════════════════════════════════════════════════════
# Multi-Scenario Burst
# ═══════════════════════════════════════════════════════════════

class TestMultiScenarioBurst:
    """Test 5-scenario burst analysis."""

    def test_returns_5_scenarios(self):
        r = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0, gas_gradient_psi_ft=0.1
        )
        assert r["num_scenarios"] == 5
        assert "gas_to_surface" in r["scenarios"]
        assert "displacement_to_gas" in r["scenarios"]
        assert "tubing_leak" in r["scenarios"]
        assert "injection" in r["scenarios"]
        assert "dst" in r["scenarios"]

    def test_governing_scenario_selected(self):
        """Governing scenario should have the highest max burst."""
        r = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0
        )
        governing = r["governing_scenario"]
        gov_burst = r["scenarios"][governing]["max_burst_psi"]
        for name, data in r["scenarios"].items():
            assert gov_burst >= data["max_burst_psi"]

    def test_gas_to_surface_positive(self):
        r = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0
        )
        assert r["scenarios"]["gas_to_surface"]["max_burst_psi"] > 0

    def test_tubing_leak_with_pressure(self):
        """Tubing leak scenario should increase with higher tubing pressure."""
        r1 = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0, tubing_pressure_psi=1000
        )
        r2 = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0, tubing_pressure_psi=5000
        )
        assert r2["scenarios"]["tubing_leak"]["max_burst_psi"] > r1["scenarios"]["tubing_leak"]["max_burst_psi"]

    def test_profiles_have_correct_length(self):
        r = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0, num_points=10
        )
        for name, data in r["scenarios"].items():
            assert len(data["profile"]) == 10

    def test_higher_pore_pressure_more_burst(self):
        """Higher pore pressure → higher reservoir pressure → more burst."""
        r1 = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=8.0
        )
        r2 = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=12.0
        )
        assert r2["governing_burst_psi"] > r1["governing_burst_psi"]

    def test_injection_scenario(self):
        """Injection pressure should create burst at surface."""
        r = CasingDesignEngine.calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5,
            pore_pressure_ppg=9.0, injection_pressure_psi=5000
        )
        assert r["scenarios"]["injection"]["max_burst_psi"] > 0

    def test_invalid_tvd(self):
        r = CasingDesignEngine.calculate_burst_scenarios(tvd_ft=0, mud_weight_ppg=10.5, pore_pressure_ppg=9.0)
        assert "error" in r


# ═══════════════════════════════════════════════════════════════
# Multi-Scenario Collapse
# ═══════════════════════════════════════════════════════════════

class TestMultiScenarioCollapse:
    """Test 4-scenario collapse analysis."""

    def test_returns_4_scenarios(self):
        r = CasingDesignEngine.calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0
        )
        assert r["num_scenarios"] == 4
        assert "full_evacuation" in r["scenarios"]
        assert "partial_evacuation" in r["scenarios"]
        assert "cementing_collapse" in r["scenarios"]
        assert "production_depletion" in r["scenarios"]

    def test_full_evacuation_worst_case(self):
        """Full evacuation should typically be worst collapse case."""
        r = CasingDesignEngine.calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=12.0, pore_pressure_ppg=9.0
        )
        full_evac = r["scenarios"]["full_evacuation"]["max_collapse_psi"]
        partial = r["scenarios"]["partial_evacuation"]["max_collapse_psi"]
        assert full_evac >= partial

    def test_governing_collapse_selected(self):
        r = CasingDesignEngine.calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0
        )
        governing = r["governing_scenario"]
        gov_collapse = r["scenarios"][governing]["max_collapse_psi"]
        for name, data in r["scenarios"].items():
            assert gov_collapse >= data["max_collapse_psi"]

    def test_depletion_scenario(self):
        """Production depletion should cause collapse load."""
        r = CasingDesignEngine.calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            depleted_pressure_ppg=3.0
        )
        assert r["scenarios"]["production_depletion"]["max_collapse_psi"] > 0

    def test_deeper_well_more_collapse(self):
        """Deeper well → higher external pressure → more collapse."""
        r1 = CasingDesignEngine.calculate_collapse_scenarios(tvd_ft=5000, mud_weight_ppg=12.0, pore_pressure_ppg=9.0)
        r2 = CasingDesignEngine.calculate_collapse_scenarios(tvd_ft=15000, mud_weight_ppg=12.0, pore_pressure_ppg=9.0)
        assert r2["governing_collapse_psi"] > r1["governing_collapse_psi"]

    def test_invalid_tvd(self):
        r = CasingDesignEngine.calculate_collapse_scenarios(tvd_ft=0, mud_weight_ppg=10.5, pore_pressure_ppg=9.0)
        assert "error" in r


# ═══════════════════════════════════════════════════════════════
# Temperature Derating
# ═══════════════════════════════════════════════════════════════

class TestTemperatureDerating:
    """Test yield strength derating with temperature."""

    def test_no_derate_at_ambient(self):
        """No derating at ambient temperature."""
        r = CasingDesignEngine.derate_for_temperature(
            grade="N80", yield_strength_psi=80000, temperature_f=70
        )
        assert r["yield_derated_psi"] == 80000
        assert r["derate_factor"] == 1.0

    def test_derate_at_high_temp(self):
        """High temperature should reduce yield strength."""
        r = CasingDesignEngine.derate_for_temperature(
            grade="N80", yield_strength_psi=80000, temperature_f=400
        )
        assert r["yield_derated_psi"] < 80000
        assert r["derate_factor"] < 1.0

    def test_higher_temp_more_derate(self):
        """Higher temperature → more derating."""
        r300 = CasingDesignEngine.derate_for_temperature(
            grade="P110", yield_strength_psi=110000, temperature_f=300
        )
        r500 = CasingDesignEngine.derate_for_temperature(
            grade="P110", yield_strength_psi=110000, temperature_f=500
        )
        assert r500["yield_derated_psi"] < r300["yield_derated_psi"]

    def test_grade_affects_alpha(self):
        """Different grades have different alpha coefficients."""
        r_j55 = CasingDesignEngine.derate_for_temperature(
            grade="J55", yield_strength_psi=55000, temperature_f=400
        )
        r_q125 = CasingDesignEngine.derate_for_temperature(
            grade="Q125", yield_strength_psi=125000, temperature_f=400
        )
        assert r_j55["alpha"] != r_q125["alpha"]

    def test_minimum_derate_factor(self):
        """Derate factor should not drop below 0.5."""
        r = CasingDesignEngine.derate_for_temperature(
            grade="Q125", yield_strength_psi=125000, temperature_f=2000  # extreme
        )
        assert r["derate_factor"] >= 0.5


# ═══════════════════════════════════════════════════════════════
# Expanded Catalog
# ═══════════════════════════════════════════════════════════════

class TestExpandedCatalog:
    """Test expanded API 5CT casing catalog."""

    def test_lookup_9625(self):
        """9-5/8 casing should have multiple options."""
        r = CasingDesignEngine.lookup_casing_catalog(casing_od_in=9.625)
        assert r["count"] > 3
        assert all("weight" in opt for opt in r["options"])

    def test_lookup_7000(self):
        r = CasingDesignEngine.lookup_casing_catalog(casing_od_in=7.000)
        assert r["count"] > 4

    def test_grade_filter(self):
        """Filtering by grade should reduce results."""
        r_all = CasingDesignEngine.lookup_casing_catalog(casing_od_in=7.000)
        r_n80 = CasingDesignEngine.lookup_casing_catalog(casing_od_in=7.000, grade_filter="N80")
        assert r_n80["count"] < r_all["count"]
        assert all(opt["grade"] == "N80" for opt in r_n80["options"])

    def test_invalid_od(self):
        r = CasingDesignEngine.lookup_casing_catalog(casing_od_in=3.14)
        assert "error" in r


# ═══════════════════════════════════════════════════════════════
# Combination String Design
# ═══════════════════════════════════════════════════════════════

class TestCombinationString:
    """Test combination string design optimization."""

    def test_returns_sections(self):
        burst_profile = [{"tvd_ft": d, "burst_load_psi": 3000 + d * 0.3}
                         for d in range(0, 10001, 500)]
        collapse_profile = [{"tvd_ft": d, "collapse_load_psi": d * 0.5}
                            for d in range(0, 10001, 500)]
        r = CasingDesignEngine.design_combination_string(
            tvd_ft=10000, casing_od_in=9.625,
            burst_profile=burst_profile,
            collapse_profile=collapse_profile,
            tension_at_surface_lbs=500000,
            casing_length_ft=10000, mud_weight_ppg=10.5
        )
        assert "sections" in r
        assert len(r["sections"]) == 3  # top, middle, bottom

    def test_total_cost_positive(self):
        burst_profile = [{"tvd_ft": d, "burst_load_psi": 3000}
                         for d in range(0, 10001, 500)]
        collapse_profile = [{"tvd_ft": d, "collapse_load_psi": 2000}
                            for d in range(0, 10001, 500)]
        r = CasingDesignEngine.design_combination_string(
            tvd_ft=10000, casing_od_in=9.625,
            burst_profile=burst_profile,
            collapse_profile=collapse_profile,
            tension_at_surface_lbs=300000,
            casing_length_ft=10000, mud_weight_ppg=10.5
        )
        assert r["total_cost"] > 0
        assert r["total_weight_lbs"] > 0

    def test_sections_cover_full_length(self):
        burst_profile = [{"tvd_ft": d, "burst_load_psi": 3000}
                         for d in range(0, 10001, 500)]
        collapse_profile = [{"tvd_ft": d, "collapse_load_psi": 2000}
                            for d in range(0, 10001, 500)]
        r = CasingDesignEngine.design_combination_string(
            tvd_ft=10000, casing_od_in=9.625,
            burst_profile=burst_profile,
            collapse_profile=collapse_profile,
            tension_at_surface_lbs=300000,
            casing_length_ft=10000, mud_weight_ppg=10.5
        )
        total_length = sum(s["length_ft"] for s in r["sections"])
        assert abs(total_length - 10000) < 2

    def test_invalid_od(self):
        r = CasingDesignEngine.design_combination_string(
            tvd_ft=10000, casing_od_in=3.14,
            burst_profile=[], collapse_profile=[],
            tension_at_surface_lbs=0, casing_length_ft=10000, mud_weight_ppg=10.5
        )
        assert "error" in r


# ═══════════════════════════════════════════════════════════════
# Running Loads
# ═══════════════════════════════════════════════════════════════

class TestRunningLoads:
    """Test running loads calculation."""

    def test_returns_keys(self):
        r = CasingDesignEngine.calculate_running_loads(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            casing_od_in=9.625, casing_id_in=8.681, mud_weight_ppg=10.5
        )
        assert "buoyed_weight_lbs" in r
        assert "shock_load_lbs" in r
        assert "total_hookload_lbs" in r

    def test_shock_load_correct(self):
        """Shock load = 3200 * W_ppf (API formula)."""
        r = CasingDesignEngine.calculate_running_loads(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            casing_od_in=9.625, casing_id_in=8.681, mud_weight_ppg=10.5
        )
        assert r["shock_load_lbs"] == pytest.approx(3200 * 47.0, abs=10)

    def test_survey_adds_drag(self):
        """Survey with inclination should add drag."""
        survey = [
            {"md": 0, "inclination": 0},
            {"md": 5000, "inclination": 30},
            {"md": 10000, "inclination": 60},
        ]
        r_vert = CasingDesignEngine.calculate_running_loads(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            casing_od_in=9.625, casing_id_in=8.681, mud_weight_ppg=10.5
        )
        r_dev = CasingDesignEngine.calculate_running_loads(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            casing_od_in=9.625, casing_id_in=8.681, mud_weight_ppg=10.5,
            survey=survey
        )
        assert r_dev["drag_lbs"] > r_vert["drag_lbs"]
        assert r_dev["total_hookload_lbs"] > r_vert["total_hookload_lbs"]

    def test_buoyancy_applied(self):
        """Buoyed weight should be less than air weight."""
        r = CasingDesignEngine.calculate_running_loads(
            casing_weight_ppf=47.0, casing_length_ft=10000,
            casing_od_in=9.625, casing_id_in=8.681, mud_weight_ppg=12.0
        )
        air_weight = 47.0 * 10000
        assert r["buoyed_weight_lbs"] < air_weight


# ═══════════════════════════════════════════════════════════════
# Wear / Corrosion Allowance
# ═══════════════════════════════════════════════════════════════

class TestWearAllowance:
    """Test wear and corrosion derating."""

    def test_no_wear_no_change(self):
        r = CasingDesignEngine.apply_wear_allowance(
            casing_od_in=9.625, wall_thickness_in=0.472,
            yield_strength_psi=80000, wear_pct=0, corrosion_rate_in_yr=0
        )
        assert r["remaining_wall_pct"] == pytest.approx(100.0, abs=0.1)
        assert r["derated_burst_psi"] == r["original_burst_psi"]

    def test_wear_reduces_ratings(self):
        r = CasingDesignEngine.apply_wear_allowance(
            casing_od_in=9.625, wall_thickness_in=0.472,
            yield_strength_psi=80000, wear_pct=20
        )
        assert r["derated_burst_psi"] < r["original_burst_psi"]
        assert r["remaining_wall_pct"] < 100

    def test_corrosion_over_time(self):
        """Longer design life → more corrosion → less wall."""
        r_short = CasingDesignEngine.apply_wear_allowance(
            casing_od_in=9.625, wall_thickness_in=0.472,
            yield_strength_psi=80000, corrosion_rate_in_yr=0.005,
            design_life_years=5
        )
        r_long = CasingDesignEngine.apply_wear_allowance(
            casing_od_in=9.625, wall_thickness_in=0.472,
            yield_strength_psi=80000, corrosion_rate_in_yr=0.005,
            design_life_years=30
        )
        assert r_long["remaining_wall_in"] < r_short["remaining_wall_in"]
        assert r_long["derated_burst_psi"] < r_short["derated_burst_psi"]
