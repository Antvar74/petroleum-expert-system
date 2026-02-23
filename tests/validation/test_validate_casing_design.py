"""
V&V: Casing Design engine against API TR 5C3 (ISO 10400) benchmark data.
Validates burst, collapse, and tension calculations.
"""
import pytest
from orchestrator.casing_design_engine import CasingDesignEngine
from tests.validation.benchmark_data import (
    API_5C3_CASING_9_625_N80,
    API_5C3_CASING_7_29_P110,
)
from tests.validation.conftest import assert_within_tolerance


class TestCasingBurstValidation:
    """Validate burst pressure rating against API TR 5C3."""

    def test_burst_9_625_n80(self):
        """API TR 5C3: 9-5/8 47# N80 burst rating within 5%."""
        bm = API_5C3_CASING_9_625_N80
        result = CasingDesignEngine.calculate_burst_rating(
            casing_od_in=bm["od"],
            wall_thickness_in=bm["wall_thickness"],
            yield_strength_psi=bm["yield_psi"],
        )
        expected = bm["expected"]["burst_psi"]
        assert_within_tolerance(
            result["burst_rating_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API 5C3 Burst 9-5/8 N80",
        )

    def test_burst_7_p110(self):
        """API TR 5C3: 7 inch 29# P110 burst rating within 5%."""
        bm = API_5C3_CASING_7_29_P110
        result = CasingDesignEngine.calculate_burst_rating(
            casing_od_in=bm["od"],
            wall_thickness_in=bm["wall_thickness"],
            yield_strength_psi=bm["yield_psi"],
        )
        expected = bm["expected"]["burst_psi"]
        assert_within_tolerance(
            result["burst_rating_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API 5C3 Burst 7 P110",
        )

    def test_burst_increases_with_wall_thickness(self):
        """Physics: thicker wall → higher burst rating."""
        thin = CasingDesignEngine.calculate_burst_rating(9.625, 0.395, 80000)
        thick = CasingDesignEngine.calculate_burst_rating(9.625, 0.545, 80000)
        assert thick["burst_rating_psi"] > thin["burst_rating_psi"]


class TestCasingCollapseValidation:
    """Validate collapse pressure rating against API TR 5C3."""

    def test_collapse_9_625_n80(self):
        """API TR 5C3: 9-5/8 47# N80 collapse rating within 10%."""
        bm = API_5C3_CASING_9_625_N80
        result = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=bm["od"],
            wall_thickness_in=bm["wall_thickness"],
            yield_strength_psi=bm["yield_psi"],
        )
        expected = bm["expected"]["collapse_psi"]
        assert_within_tolerance(
            result["collapse_rating_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API 5C3 Collapse 9-5/8 N80",
        )

    def test_collapse_7_p110(self):
        """API TR 5C3: 7 inch 29# P110 collapse rating within 10%."""
        bm = API_5C3_CASING_7_29_P110
        result = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=bm["od"],
            wall_thickness_in=bm["wall_thickness"],
            yield_strength_psi=bm["yield_psi"],
        )
        expected = bm["expected"]["collapse_psi"]
        assert_within_tolerance(
            result["collapse_rating_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API 5C3 Collapse 7 P110",
        )

    def test_collapse_zone_identified(self):
        """Must identify the correct collapse zone (Yield/Plastic/Transition/Elastic)."""
        bm = API_5C3_CASING_9_625_N80
        result = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=bm["od"],
            wall_thickness_in=bm["wall_thickness"],
            yield_strength_psi=bm["yield_psi"],
        )
        assert result["collapse_zone"] in ("Yield", "Plastic", "Transition", "Elastic"), \
            f"Unknown collapse zone: {result['collapse_zone']}"

    def test_collapse_increases_with_wall_thickness(self):
        """Physics: thicker wall → higher collapse resistance."""
        thin = CasingDesignEngine.calculate_collapse_rating(9.625, 0.395, 80000)
        thick = CasingDesignEngine.calculate_collapse_rating(9.625, 0.545, 80000)
        assert thick["collapse_rating_psi"] > thin["collapse_rating_psi"]


class TestCasingTensionValidation:
    """Validate tension load calculations."""

    def test_air_weight_calculation(self):
        """Air weight = weight_ppf * length_ft (basic physics)."""
        result = CasingDesignEngine.calculate_tension_load(
            casing_weight_ppf=47.0,
            casing_length_ft=10000,
            mud_weight_ppg=10.0,
            casing_od_in=9.625,
            casing_id_in=8.681,
            buoyancy_applied=False,
            shock_load=False,
            overpull_lbs=0,
        )
        expected_air_weight = 47.0 * 10000  # 470,000 lbs
        assert abs(result["air_weight_lbs"] - expected_air_weight) < 1000, \
            f"Air weight {result['air_weight_lbs']} != expected {expected_air_weight}"

    def test_buoyancy_reduces_weight(self):
        """Buoyant weight must be less than air weight."""
        result = CasingDesignEngine.calculate_tension_load(
            casing_weight_ppf=47.0,
            casing_length_ft=10000,
            mud_weight_ppg=10.0,
            casing_od_in=9.625,
            casing_id_in=8.681,
            buoyancy_applied=True,
            shock_load=False,
            overpull_lbs=0,
        )
        assert result["buoyant_weight_lbs"] < result["air_weight_lbs"]
