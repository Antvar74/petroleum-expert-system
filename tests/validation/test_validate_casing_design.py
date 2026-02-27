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


class TestCollapseZoneClassification:
    """Validate collapse zone boundaries against API TR 5C3 published tables."""

    def test_9625_n80_collapse_zone_is_plastic(self):
        """9-5/8 47# N80 (D/t=20.39) should be in Plastic zone per API TR 5C3."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert result["collapse_zone"] == "Plastic", (
            f"Expected Plastic for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )

    def test_9625_n80_collapse_value_matches_api(self):
        """API TR 5C3 published collapse for 9-5/8 47# N80 ≈ 4760 psi (±10%)."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert 4280 <= result["collapse_rating_psi"] <= 5240, (
            f"Collapse {result['collapse_rating_psi']} outside API range 4760 ±10%"
        )

    def test_7_29_p110_collapse_value_matches_api(self):
        """API TR 5C3 plastic collapse for 7 29# P110 (D/t=17.16) ≈ 8530 psi (±10%).

        Note: The plastic collapse formula P = Yp*(A/dt - B) - C gives ~8530 psi
        for D/t=17.16 with P110 coefficients (A=3.181, B=0.0819, C=2852).
        Some references cite ~10680 psi which corresponds to 7" 32# P110 (t=0.453").
        """
        result = CasingDesignEngine.calculate_collapse_rating(7.0, 0.408, 110000)
        assert 7680 <= result["collapse_rating_psi"] <= 9390, (
            f"Collapse {result['collapse_rating_psi']} outside API range 8530 ±10%"
        )

    def test_transition_zone_identified_and_value(self):
        """D/t ≈ 27.3 for J55 should fall in Transition zone per API TR 5C3."""
        # 9.625" OD, t=0.352" -> D/t = 27.35, J55 (Yp=55000)
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.352, 55000)
        assert result["collapse_zone"] == "Transition", (
            f"Expected Transition for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )
        assert result["collapse_rating_psi"] > 0

    def test_thin_wall_not_yield_zone(self):
        """Very thin wall (D/t > 40) should NOT be Yield zone."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.200, 55000)
        assert result["collapse_zone"] in ("Transition", "Elastic"), (
            f"D/t={result['dt_ratio']} should be Transition/Elastic, got {result['collapse_zone']}"
        )

    def test_thick_wall_yield_zone(self):
        """Very thick wall (D/t < 12) should be Yield zone."""
        result = CasingDesignEngine.calculate_collapse_rating(7.0, 0.700, 80000)
        assert result["collapse_zone"] == "Yield", (
            f"D/t={result['dt_ratio']} should be Yield, got {result['collapse_zone']}"
        )

    def test_boundaries_physically_ordered(self):
        """Boundaries must be: dt_yp < dt_pt < dt_te for any valid grade and geometry."""
        test_cases = [
            # (od, t, yp) — varying both geometry and grade
            (9.625, 0.472, 55000),   # D/t=20.39, J55
            (9.625, 0.472, 80000),   # D/t=20.39, N80
            (7.0, 0.408, 110000),    # D/t=17.16, P110
            (7.0, 0.700, 125000),    # D/t=10.0, Q125 (thick wall)
            (13.375, 0.380, 55000),  # D/t=35.2, J55 (large OD, thin wall)
        ]
        for od, t, yp in test_cases:
            result = CasingDesignEngine.calculate_collapse_rating(od, t, yp)
            b = result["boundaries"]
            assert b["yield_plastic"] < b["plastic_transition"] < b["transition_elastic"], (
                f"Boundaries not ordered for OD={od}, t={t}, Yp={yp}: {b}"
            )


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
