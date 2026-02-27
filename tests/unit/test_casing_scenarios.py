"""Tests for multi-scenario burst and collapse analysis."""
import pytest
from orchestrator.casing_design_engine.scenarios import (
    calculate_burst_scenarios,
    calculate_collapse_scenarios,
)


class TestBurstScenarios:
    def test_returns_five_scenarios(self):
        result = calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
        )
        assert result["num_scenarios"] == 5
        assert "gas_to_surface" in result["scenarios"]
        assert "displacement_to_gas" in result["scenarios"]
        assert "tubing_leak" in result["scenarios"]
        assert "injection" in result["scenarios"]
        assert "dst" in result["scenarios"]

    def test_governing_scenario_identified(self):
        result = calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
        )
        assert result["governing_scenario"] in result["scenarios"]
        assert result["governing_burst_psi"] > 0

    def test_each_scenario_has_profile(self):
        result = calculate_burst_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            num_points=10,
        )
        for name, scenario in result["scenarios"].items():
            assert len(scenario["profile"]) == 10
            assert "max_burst_psi" in scenario

    def test_zero_tvd_error(self):
        result = calculate_burst_scenarios(tvd_ft=0, mud_weight_ppg=10.0, pore_pressure_ppg=9.0)
        assert "error" in result


class TestCollapseScenarios:
    def test_returns_four_scenarios(self):
        result = calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
        )
        assert result["num_scenarios"] == 4
        assert "full_evacuation" in result["scenarios"]
        assert "partial_evacuation" in result["scenarios"]
        assert "cementing_collapse" in result["scenarios"]
        assert "production_depletion" in result["scenarios"]

    def test_cementing_collapse_does_not_crash(self):
        """Regression: line 196 had 'depth' instead of 'd' — must not raise NameError."""
        result = calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
            cement_top_tvd_ft=5000.0, cement_density_ppg=16.0,
        )
        assert "cementing_collapse" in result["scenarios"]
        assert result["scenarios"]["cementing_collapse"]["max_collapse_psi"] >= 0

    def test_full_evacuation_max_at_shoe(self):
        """Full evacuation: max collapse at TD (deepest point)."""
        result = calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=12.0, pore_pressure_ppg=9.0,
        )
        profile = result["scenarios"]["full_evacuation"]["profile"]
        max_point = max(profile, key=lambda p: p["collapse_load_psi"])
        assert max_point["tvd_ft"] == pytest.approx(10000, abs=1)

    def test_full_evacuation_value_correct(self):
        """Full evacuation collapse at shoe = MW * 0.052 * TVD."""
        result = calculate_collapse_scenarios(
            tvd_ft=11000, mud_weight_ppg=14.0, pore_pressure_ppg=12.0,
            cement_top_tvd_ft=0.0,
        )
        expected = 14.0 * 0.052 * 11000  # 8008 psi
        actual = result["scenarios"]["full_evacuation"]["max_collapse_psi"]
        assert actual == pytest.approx(expected, rel=0.02)

    def test_governing_scenario_identified(self):
        result = calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.5, pore_pressure_ppg=9.0,
        )
        assert result["governing_scenario"] in result["scenarios"]
        assert result["governing_collapse_psi"] > 0

    def test_zero_tvd_error(self):
        result = calculate_collapse_scenarios(tvd_ft=0, mud_weight_ppg=10.0, pore_pressure_ppg=9.0)
        assert "error" in result
