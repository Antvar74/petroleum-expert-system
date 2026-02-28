"""
V&V: Casing Design engine against API TR 5C3 (ISO 10400) benchmark data.
Validates burst, collapse, and tension calculations across all 7 catalog
OD sizes (4-1/2 to 20 inch) and grades J55 through P110.

20 benchmark cases covering Yield, Plastic, Transition, and Elastic
collapse zones per API TR 5C3 four-zone model.
"""
import pytest
from orchestrator.casing_design_engine import CasingDesignEngine
from tests.validation.benchmark_data import ALL_API_5C3_BENCHMARKS


# ──────────────────────────────────────────────────────────────
# Comprehensive parametrized validation: all 20 benchmarks
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "benchmark",
    ALL_API_5C3_BENCHMARKS,
    ids=lambda b: b.get("reference", "unknown"),
)
class TestComprehensiveApiValidation:
    """Validate burst and collapse ratings for all 20 API 5C3 benchmarks."""

    def test_burst_rating(self, benchmark):
        """Burst rating (Barlow) within tolerance of API 5C3 published value."""
        od = benchmark["od"]
        wall = benchmark["wall_thickness"]
        yp = benchmark["yield_psi"]
        result = CasingDesignEngine.calculate_burst_rating(
            casing_od_in=od,
            wall_thickness_in=wall,
            yield_strength_psi=yp,
        )
        expected = benchmark["expected"]["burst_psi"]
        assert result["burst_rating_psi"] == pytest.approx(
            expected["value"], rel=expected["tolerance_pct"] / 100
        )

    def test_collapse_rating(self, benchmark):
        """Collapse rating (API TR 5C3 four-zone) within tolerance."""
        od = benchmark["od"]
        wall = benchmark["wall_thickness"]
        yp = benchmark["yield_psi"]
        result = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=od,
            wall_thickness_in=wall,
            yield_strength_psi=yp,
        )
        expected = benchmark["expected"]["collapse_psi"]
        assert result["collapse_rating_psi"] == pytest.approx(
            expected["value"], rel=expected["tolerance_pct"] / 100
        )

    def test_collapse_zone_valid(self, benchmark):
        """Collapse zone must be one of the four API TR 5C3 zones."""
        od = benchmark["od"]
        wall = benchmark["wall_thickness"]
        yp = benchmark["yield_psi"]
        result = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=od,
            wall_thickness_in=wall,
            yield_strength_psi=yp,
        )
        assert result["collapse_zone"] in (
            "Yield", "Plastic", "Transition", "Elastic"
        ), f"Unknown collapse zone: {result['collapse_zone']}"


# ──────────────────────────────────────────────────────────────
# Physics sanity checks
# ──────────────────────────────────────────────────────────────

class TestBurstPhysics:
    """Verify burst rating physical behavior."""

    def test_burst_increases_with_wall_thickness(self):
        """Physics: thicker wall -> higher burst rating."""
        thin = CasingDesignEngine.calculate_burst_rating(9.625, 0.395, 80000)
        thick = CasingDesignEngine.calculate_burst_rating(9.625, 0.545, 80000)
        assert thick["burst_rating_psi"] > thin["burst_rating_psi"]

    def test_burst_increases_with_yield_strength(self):
        """Physics: higher yield strength -> higher burst rating."""
        low_grade = CasingDesignEngine.calculate_burst_rating(7.0, 0.362, 55000)
        high_grade = CasingDesignEngine.calculate_burst_rating(7.0, 0.362, 110000)
        assert high_grade["burst_rating_psi"] > low_grade["burst_rating_psi"]

    def test_burst_decreases_with_od(self):
        """Physics: larger OD at same wall -> lower burst rating."""
        small = CasingDesignEngine.calculate_burst_rating(5.500, 0.304, 80000)
        large = CasingDesignEngine.calculate_burst_rating(10.750, 0.304, 80000)
        assert small["burst_rating_psi"] > large["burst_rating_psi"]


class TestCollapsePhysics:
    """Verify collapse rating physical behavior."""

    def test_collapse_increases_with_wall_thickness(self):
        """Physics: thicker wall -> higher collapse resistance."""
        thin = CasingDesignEngine.calculate_collapse_rating(9.625, 0.395, 80000)
        thick = CasingDesignEngine.calculate_collapse_rating(9.625, 0.545, 80000)
        assert thick["collapse_rating_psi"] > thin["collapse_rating_psi"]

    def test_collapse_increases_with_yield_strength(self):
        """Physics: higher yield strength -> higher collapse rating (same geometry)."""
        low_grade = CasingDesignEngine.calculate_collapse_rating(7.0, 0.362, 55000)
        high_grade = CasingDesignEngine.calculate_collapse_rating(7.0, 0.362, 110000)
        assert high_grade["collapse_rating_psi"] > low_grade["collapse_rating_psi"]


# ──────────────────────────────────────────────────────────────
# Collapse zone classification (API TR 5C3 boundaries)
# ──────────────────────────────────────────────────────────────

class TestCollapseZoneClassification:
    """Validate collapse zone boundaries against API TR 5C3 published tables."""

    def test_9625_n80_collapse_zone_is_plastic(self):
        """9-5/8 47# N80 (D/t=20.39) should be in Plastic zone per API TR 5C3."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert result["collapse_zone"] == "Plastic", (
            f"Expected Plastic for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )

    def test_9625_n80_collapse_value_matches_api(self):
        """API TR 5C3 published collapse for 9-5/8 47# N80 ~ 4760 psi (+/-10%)."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert 4280 <= result["collapse_rating_psi"] <= 5240, (
            f"Collapse {result['collapse_rating_psi']} outside API range 4760 +/-10%"
        )

    def test_7_29_p110_collapse_value_matches_api(self):
        """API TR 5C3 plastic collapse for 7 29# P110 (D/t=17.16) ~ 8530 psi (+/-10%)."""
        result = CasingDesignEngine.calculate_collapse_rating(7.0, 0.408, 110000)
        assert 7680 <= result["collapse_rating_psi"] <= 9390, (
            f"Collapse {result['collapse_rating_psi']} outside API range 8530 +/-10%"
        )

    def test_transition_zone_identified_and_value(self):
        """D/t ~ 27.3 for J55 should fall in Transition zone per API TR 5C3."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.352, 55000)
        assert result["collapse_zone"] == "Transition", (
            f"Expected Transition for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )
        assert result["collapse_rating_psi"] > 0

    def test_elastic_zone_for_large_dt(self):
        """20 inch 94# J55 (D/t=45.66) should fall in Elastic zone."""
        result = CasingDesignEngine.calculate_collapse_rating(20.0, 0.438, 55000)
        assert result["collapse_zone"] == "Elastic", (
            f"Expected Elastic for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )

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
            (9.625, 0.472, 55000),   # D/t=20.39, J55
            (9.625, 0.472, 80000),   # D/t=20.39, N80
            (7.0, 0.408, 110000),    # D/t=17.16, P110
            (7.0, 0.700, 125000),    # D/t=10.0, Q125 (thick wall)
            (13.375, 0.380, 55000),  # D/t=35.2, J55 (large OD, thin wall)
            (20.0, 0.438, 55000),    # D/t=45.66, J55 (elastic zone)
        ]
        for od, t, yp in test_cases:
            result = CasingDesignEngine.calculate_collapse_rating(od, t, yp)
            b = result["boundaries"]
            assert b["yield_plastic"] < b["plastic_transition"] < b["transition_elastic"], (
                f"Boundaries not ordered for OD={od}, t={t}, Yp={yp}: {b}"
            )


# ──────────────────────────────────────────────────────────────
# Tension load validation
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# Collapse load scenarios
# ──────────────────────────────────────────────────────────────

class TestFullEvacuationCollapseLoad:
    """Validate that full evacuation produces correct collapse loads."""

    def test_11000ft_14ppg_full_evacuation(self):
        """Full evacuation: P_collapse = MW * 0.052 * TVD at shoe."""
        from orchestrator.casing_design_engine.scenarios import calculate_collapse_scenarios
        result = calculate_collapse_scenarios(
            tvd_ft=11000, mud_weight_ppg=14.0, pore_pressure_ppg=12.0,
            cement_top_tvd_ft=0.0,
        )
        expected_max = 14.0 * 0.052 * 11000  # 8008 psi
        actual = result["scenarios"]["full_evacuation"]["max_collapse_psi"]
        assert abs(actual - expected_max) / expected_max < 0.02, \
            f"Full evacuation collapse {actual} vs expected {expected_max}"

    def test_10000ft_10ppg_full_evacuation(self):
        from orchestrator.casing_design_engine.scenarios import calculate_collapse_scenarios
        result = calculate_collapse_scenarios(
            tvd_ft=10000, mud_weight_ppg=10.0, pore_pressure_ppg=9.0,
        )
        expected_max = 10.0 * 0.052 * 10000  # 5200 psi
        actual = result["scenarios"]["full_evacuation"]["max_collapse_psi"]
        assert abs(actual - expected_max) / expected_max < 0.02
