"""
Unit tests for VibrationsEngine -- drillstring vibration analysis.

Covers axial (bit bounce), lateral (whirl), torsional (stick-slip),
MSE optimization, stability index, vibration heatmap, and full analysis.
"""
import math
import pytest
from orchestrator.vibrations_engine import VibrationsEngine


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def engine():
    """Return VibrationsEngine class (all static methods)."""
    return VibrationsEngine


@pytest.fixture
def typical_bha():
    """Typical 6-3/4" drill-collar BHA parameters."""
    return dict(
        bha_length_ft=300,
        bha_od_in=6.75,
        bha_id_in=2.813,
        bha_weight_lbft=83.0,
        mud_weight_ppg=10.0,
    )


@pytest.fixture
def typical_wellbore():
    """Standard 8-1/2" hole parameters."""
    return dict(
        hole_diameter_in=8.5,
        inclination_deg=0.0,
    )


@pytest.fixture
def typical_operating():
    """Typical drilling operating parameters."""
    return dict(
        wob_klb=20.0,
        rpm=120,
        rop_fph=50.0,
        torque_ftlb=10000.0,
        bit_diameter_in=8.5,
    )


@pytest.fixture
def axial_result(engine, typical_bha):
    """Pre-computed axial vibration result."""
    return engine.calculate_critical_rpm_axial(**typical_bha)


@pytest.fixture
def lateral_result(engine, typical_bha, typical_wellbore):
    """Pre-computed lateral vibration result."""
    return engine.calculate_critical_rpm_lateral(**typical_bha, **typical_wellbore)


@pytest.fixture
def stick_slip_result(engine, typical_bha, typical_operating):
    """Pre-computed stick-slip result."""
    return engine.calculate_stick_slip_severity(
        surface_rpm=typical_operating["rpm"],
        wob_klb=typical_operating["wob_klb"],
        torque_ftlb=typical_operating["torque_ftlb"],
        bit_diameter_in=typical_operating["bit_diameter_in"],
        bha_length_ft=typical_bha["bha_length_ft"],
        bha_od_in=typical_bha["bha_od_in"],
        bha_id_in=typical_bha["bha_id_in"],
        mud_weight_ppg=typical_bha["mud_weight_ppg"],
    )


@pytest.fixture
def mse_result(engine, typical_operating):
    """Pre-computed MSE result."""
    return engine.calculate_mse(**typical_operating)


# ===========================================================================
# 1. AXIAL VIBRATION TESTS
# ===========================================================================
class TestAxialVibrations:
    """Tests for calculate_critical_rpm_axial."""

    def test_critical_rpm_is_positive(self, axial_result):
        """First-mode critical RPM must be a positive number."""
        assert axial_result["critical_rpm_1st"] > 0

    def test_buoyancy_factor_correct(self, engine):
        """BF = 1 - MW/65.5; for 10 ppg BF ~ 0.8473."""
        result = engine.calculate_critical_rpm_axial(
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, mud_weight_ppg=10.0,
        )
        expected_bf = 1.0 - 10.0 / 65.5
        assert result["buoyancy_factor"] == pytest.approx(expected_bf, abs=0.001)

    def test_harmonics_are_integer_multiples(self, axial_result):
        """2nd and 3rd harmonics must be 2x and 3x the 1st mode."""
        rpm_1 = axial_result["critical_rpm_1st"]
        rpm_2 = axial_result["critical_rpm_2nd"]
        rpm_3 = axial_result["critical_rpm_3rd"]
        assert rpm_2 == pytest.approx(2 * rpm_1, abs=1.0)
        assert rpm_3 == pytest.approx(3 * rpm_1, abs=1.0)

    def test_safe_bands_present(self, axial_result):
        """Safe operating bands should be returned and non-empty."""
        bands = axial_result["safe_operating_bands"]
        assert isinstance(bands, list)
        assert len(bands) >= 1
        for band in bands:
            assert band["max_rpm"] > band["min_rpm"]

    def test_zero_length_returns_error(self, engine):
        """BHA length = 0 must return an error dict."""
        result = engine.calculate_critical_rpm_axial(
            bha_length_ft=0, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, mud_weight_ppg=10.0,
        )
        assert "error" in result

    def test_heavier_mud_raises_critical_rpm(self, engine):
        """Higher mud weight lowers effective density, raising wave speed and critical RPM."""
        base = dict(bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
                    bha_weight_lbft=83.0)
        result_light = engine.calculate_critical_rpm_axial(**base, mud_weight_ppg=8.6)
        result_heavy = engine.calculate_critical_rpm_axial(**base, mud_weight_ppg=16.0)
        # Heavier mud -> lower rho_eff -> higher c_steel -> higher critical RPM
        assert result_heavy["critical_rpm_1st"] > result_light["critical_rpm_1st"]


# ===========================================================================
# 2. LATERAL VIBRATION TESTS
# ===========================================================================
class TestLateralVibrations:
    """Tests for calculate_critical_rpm_lateral (Paslay-Dawson)."""

    def test_critical_rpm_is_positive(self, lateral_result):
        """Paslay-Dawson critical RPM must be positive."""
        assert lateral_result["critical_rpm"] > 0

    def test_shorter_span_higher_critical_rpm(self, engine):
        """Shorter stabilizer spacing => higher critical RPM."""
        common = dict(bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
                      bha_weight_lbft=83.0, hole_diameter_in=8.5, mud_weight_ppg=10.0)
        long_span = engine.calculate_critical_rpm_lateral(stabilizer_spacing_ft=90, **common)
        short_span = engine.calculate_critical_rpm_lateral(stabilizer_spacing_ft=60, **common)
        assert short_span["critical_rpm"] > long_span["critical_rpm"]

    def test_whirl_severity_increases_with_inclination(self, engine, typical_bha):
        """Inclination adds sin(inc) factor to whirl severity."""
        vertical = engine.calculate_critical_rpm_lateral(
            **typical_bha, hole_diameter_in=8.5, inclination_deg=0.0,
        )
        inclined = engine.calculate_critical_rpm_lateral(
            **typical_bha, hole_diameter_in=8.5, inclination_deg=60.0,
        )
        assert inclined["whirl_severity_factor"] > vertical["whirl_severity_factor"]

    def test_radial_clearance_calculation(self, engine, typical_bha):
        """Clearance = (hole_diam - bha_od) / 2."""
        result = engine.calculate_critical_rpm_lateral(
            **typical_bha, hole_diameter_in=8.5,
        )
        expected = (8.5 - 6.75) / 2.0
        assert result["radial_clearance_in"] == pytest.approx(expected, abs=0.01)

    def test_estimated_span_caps_at_90ft(self, engine):
        """When no stabilizer_spacing given, L = min(bha_length, 90) — not full BHA length."""
        result = engine.calculate_critical_rpm_lateral(
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, hole_diameter_in=8.5, mud_weight_ppg=10.0,
        )
        # With L=90 ft (capped), lateral RPM must be > 30 RPM
        assert result["critical_rpm"] > 30
        assert result["span_used_ft"] == 90.0
        assert result["span_source"] == "estimated"

    def test_user_provided_stabilizer_spacing(self, engine):
        """When stabilizer_spacing_ft is given, use it directly."""
        result = engine.calculate_critical_rpm_lateral(
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, hole_diameter_in=8.5, mud_weight_ppg=10.0,
            stabilizer_spacing_ft=60.0,
        )
        assert result["critical_rpm"] > 50
        assert result["span_used_ft"] == 60.0
        assert result["span_source"] == "user"

    def test_critical_rpm_physical_range(self, lateral_result):
        """Lateral critical RPM for 300 ft BHA must be in realistic range (30-500 RPM)."""
        assert 30 <= lateral_result["critical_rpm"] <= 500

    def test_zero_length_returns_error(self, engine):
        """Zero BHA length must produce error."""
        result = engine.calculate_critical_rpm_lateral(
            bha_length_ft=0, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, hole_diameter_in=8.5,
        )
        assert "error" in result


# ===========================================================================
# 3. STICK-SLIP TESTS
# ===========================================================================
class TestStickSlip:
    """Tests for calculate_stick_slip_severity."""

    def test_severity_classification_mild(self, engine, typical_bha):
        """Low WOB + high RPM should yield Mild severity (<0.5)."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=180, wob_klb=5.0, torque_ftlb=5000,
            bit_diameter_in=8.5, bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"], bha_id_in=typical_bha["bha_id_in"],
            mud_weight_ppg=typical_bha["mud_weight_ppg"], friction_factor=0.20,
        )
        assert result["severity_index"] < 0.5
        assert result["classification"] == "Mild"

    def test_severity_increases_with_extreme_params(self, engine, typical_bha):
        """Very high WOB + low RPM + high friction should produce higher severity than baseline."""
        baseline = engine.calculate_stick_slip_severity(
            surface_rpm=180, wob_klb=5.0, torque_ftlb=5000,
            bit_diameter_in=8.5, bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"], bha_id_in=typical_bha["bha_id_in"],
            mud_weight_ppg=typical_bha["mud_weight_ppg"], friction_factor=0.20,
        )
        extreme = engine.calculate_stick_slip_severity(
            surface_rpm=40, wob_klb=50.0, torque_ftlb=25000,
            bit_diameter_in=12.25, bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"], bha_id_in=typical_bha["bha_id_in"],
            mud_weight_ppg=typical_bha["mud_weight_ppg"], friction_factor=0.40,
        )
        assert extreme["severity_index"] > baseline["severity_index"]
        # With extreme WOB/friction and large bit, severity should be meaningful
        assert extreme["severity_index"] > 0.05

    def test_rpm_at_bit_range(self, stick_slip_result):
        """Minimum RPM at bit >= 0 and maximum >= surface RPM."""
        assert stick_slip_result["rpm_min_at_bit"] >= 0
        assert stick_slip_result["rpm_max_at_bit"] >= stick_slip_result["surface_rpm"]

    def test_higher_wob_higher_severity(self, engine, typical_bha):
        """Increasing WOB should increase stick-slip severity."""
        common = dict(
            surface_rpm=100, torque_ftlb=10000, bit_diameter_in=8.5,
            bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
            mud_weight_ppg=typical_bha["mud_weight_ppg"],
        )
        low_wob = engine.calculate_stick_slip_severity(wob_klb=10, **common)
        high_wob = engine.calculate_stick_slip_severity(wob_klb=40, **common)
        assert high_wob["severity_index"] > low_wob["severity_index"]

    def test_friction_torque_uses_two_thirds_radius(self, engine, typical_bha):
        """Friction torque must use 2R/3 effective radius (centroid of uniform PDC face)."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=120, wob_klb=20.0, torque_ftlb=12000,
            bit_diameter_in=8.5, bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"], bha_id_in=typical_bha["bha_id_in"],
            mud_weight_ppg=typical_bha["mud_weight_ppg"], friction_factor=0.25,
        )
        # T = mu * WOB * 2R/3 = 0.25 * 20000 * 2*(8.5/24)/3 = 1181 ft-lb
        assert 1100 <= result["friction_torque_ftlb"] <= 1250

    def test_zero_rpm_returns_error(self, engine, typical_bha):
        """RPM = 0 should produce error dict."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=0, wob_klb=20, torque_ftlb=10000, bit_diameter_in=8.5,
            bha_length_ft=typical_bha["bha_length_ft"],
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
        )
        assert "error" in result


# ===========================================================================
# 4. MSE TESTS
# ===========================================================================
class TestMSE:
    """Tests for calculate_mse (Teale, 1965)."""

    def test_teale_formula_rotary_component(self, engine):
        """MSE_rotary = 480 * T * RPM / (d^2 * ROP)."""
        t, rpm, d, rop = 10000, 120, 8.5, 50
        result = engine.calculate_mse(
            wob_klb=20, torque_ftlb=t, rpm=rpm, rop_fph=rop, bit_diameter_in=d,
        )
        expected_rotary = (480.0 * t * rpm) / (d * d * rop)
        assert result["mse_rotary_psi"] == pytest.approx(expected_rotary, rel=0.01)

    def test_teale_formula_thrust_component(self, engine):
        """MSE_thrust = 4 * WOB / (pi * d^2)."""
        wob_klb, d = 20, 8.5
        result = engine.calculate_mse(
            wob_klb=wob_klb, torque_ftlb=10000, rpm=120, rop_fph=50,
            bit_diameter_in=d,
        )
        expected_thrust = (4.0 * wob_klb * 1000.0) / (math.pi * d * d)
        assert result["mse_thrust_psi"] == pytest.approx(expected_thrust, rel=0.01)

    def test_rotary_plus_thrust_equals_total(self, mse_result):
        """Total MSE = rotary component + thrust component."""
        total = mse_result["mse_total_psi"]
        parts = mse_result["mse_rotary_psi"] + mse_result["mse_thrust_psi"]
        assert total == pytest.approx(parts, rel=0.001)

    def test_efficiency_bounded(self, mse_result):
        """Efficiency is None without UCS (fixture has no UCS)."""
        assert mse_result["efficiency_pct"] is None

    def test_efficiency_none_without_ucs(self, engine):
        """Without UCS, efficiency must be None (not the old hard-coded 35%)."""
        result = engine.calculate_mse(
            wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5,
        )
        assert result["efficiency_pct"] is None
        assert result["classification_basis"] == "absolute_mse"

    def test_efficiency_calculated_with_ucs(self, engine):
        """With UCS provided, efficiency = UCS / MSE * 100."""
        result = engine.calculate_mse(
            wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5,
            ucs_psi=55000,
        )
        assert result["efficiency_pct"] is not None
        assert 30 <= result["efficiency_pct"] <= 40  # ~34.4% for these params
        assert result["classification_basis"] == "ucs_based"

    def test_high_mse_classification(self, engine):
        """Extremely high MSE (low ROP, high torque) should classify as Highly Inefficient."""
        result = engine.calculate_mse(
            wob_klb=40, torque_ftlb=30000, rpm=120, rop_fph=5,
            bit_diameter_in=8.5,
        )
        # Very high MSE → inefficient classification
        assert result["mse_total_psi"] > 100000
        assert result["classification"] == "Highly Inefficient"
        assert result["color"] == "red"

    def test_zero_rop_returns_error(self, engine):
        """ROP = 0 should produce an error."""
        result = engine.calculate_mse(
            wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=0,
            bit_diameter_in=8.5,
        )
        assert "error" in result


# ===========================================================================
# 5. STABILITY INDEX TESTS
# ===========================================================================
class TestStabilityIndex:
    """Tests for calculate_stability_index."""

    def test_index_within_0_to_100(self, engine, axial_result, lateral_result,
                                   stick_slip_result, mse_result):
        """Stability index must be in [0, 100]."""
        result = engine.calculate_stability_index(
            axial_result, lateral_result, stick_slip_result, mse_result,
            operating_rpm=120,
        )
        assert 0 <= result["stability_index"] <= 100

    def test_weights_sum_to_one(self, engine, axial_result, lateral_result,
                                stick_slip_result, mse_result):
        """Declared weights must add up to 1.0."""
        result = engine.calculate_stability_index(
            axial_result, lateral_result, stick_slip_result, mse_result,
            operating_rpm=120,
        )
        total_weight = sum(result["weights"].values())
        assert total_weight == pytest.approx(1.0, abs=0.001)

    def test_weight_keys_match_scores(self, engine, axial_result, lateral_result,
                                      stick_slip_result, mse_result):
        """Weight keys (axial, lateral, torsional, mse) must match score keys."""
        result = engine.calculate_stability_index(
            axial_result, lateral_result, stick_slip_result, mse_result,
            operating_rpm=120,
        )
        assert set(result["weights"].keys()) == set(result["mode_scores"].keys())

    def test_status_thresholds(self, engine, axial_result, lateral_result,
                               stick_slip_result, mse_result):
        """Status should be one of the defined classifications."""
        result = engine.calculate_stability_index(
            axial_result, lateral_result, stick_slip_result, mse_result,
            operating_rpm=120,
        )
        assert result["status"] in ("Stable", "Marginal", "Unstable", "Critical")

    def test_weighted_calculation_is_correct(self, engine, axial_result,
                                             lateral_result, stick_slip_result,
                                             mse_result):
        """Verify the weighted sum: axial 20%, lateral 30%, torsional 35%, mse 15%."""
        result = engine.calculate_stability_index(
            axial_result, lateral_result, stick_slip_result, mse_result,
            operating_rpm=120,
        )
        scores = result["mode_scores"]
        w = result["weights"]
        expected = sum(scores[k] * w[k] for k in scores)
        assert result["stability_index"] == pytest.approx(expected, abs=0.2)


# ===========================================================================
# 6. VIBRATION MAP TESTS
# ===========================================================================
class TestVibrationMap:
    """Tests for generate_vibration_map."""

    def test_default_map_has_72_points(self, engine, typical_bha):
        """Default 8 WOB x 9 RPM = 72 map points."""
        result = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
            bha_weight_lbft=typical_bha["bha_weight_lbft"],
            bha_length_ft=typical_bha["bha_length_ft"],
            hole_diameter_in=8.5,
            mud_weight_ppg=typical_bha["mud_weight_ppg"],
        )
        assert len(result["map_data"]) == 72

    def test_optimal_point_has_highest_score(self, engine, typical_bha):
        """Optimal point score >= every other point's score."""
        result = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
            bha_weight_lbft=typical_bha["bha_weight_lbft"],
            bha_length_ft=typical_bha["bha_length_ft"],
            hole_diameter_in=8.5,
            mud_weight_ppg=typical_bha["mud_weight_ppg"],
        )
        max_in_data = max(pt["stability_index"] for pt in result["map_data"])
        assert result["optimal_point"]["score"] == pytest.approx(max_in_data, abs=0.1)

    def test_map_has_meaningful_range(self, engine, typical_bha):
        """Stability index must vary by > 5 points across the map (was 2.7 with L=300 bug)."""
        result = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
            bha_weight_lbft=typical_bha["bha_weight_lbft"],
            bha_length_ft=typical_bha["bha_length_ft"],
            hole_diameter_in=8.5,
            mud_weight_ppg=typical_bha["mud_weight_ppg"],
        )
        scores = [pt["stability_index"] for pt in result["map_data"]]
        score_range = max(scores) - min(scores)
        assert score_range > 5, f"Map range too flat: {score_range:.1f} (min={min(scores):.1f}, max={max(scores):.1f})"

    def test_custom_ranges_respected(self, engine, typical_bha):
        """Custom WOB and RPM ranges produce correct grid size."""
        wob_list = [10, 20, 30]
        rpm_list = [80, 120, 160, 200]
        result = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=typical_bha["bha_od_in"],
            bha_id_in=typical_bha["bha_id_in"],
            bha_weight_lbft=typical_bha["bha_weight_lbft"],
            bha_length_ft=typical_bha["bha_length_ft"],
            hole_diameter_in=8.5,
            mud_weight_ppg=typical_bha["mud_weight_ppg"],
            wob_range=wob_list,
            rpm_range=rpm_list,
        )
        assert len(result["map_data"]) == 3 * 4  # 12 points


# ===========================================================================
# 7. FULL ANALYSIS TESTS
# ===========================================================================
class TestFullVibrationAnalysis:
    """Tests for calculate_full_vibration_analysis."""

    def test_all_sub_results_present(self, engine):
        """Full analysis must contain all expected top-level keys."""
        result = engine.calculate_full_vibration_analysis(
            wob_klb=20, rpm=120, rop_fph=50, torque_ftlb=10000,
            bit_diameter_in=8.5,
        )
        expected_keys = {
            "summary", "axial_vibrations", "lateral_vibrations",
            "stick_slip", "mse", "stability", "vibration_map", "alerts",
        }
        assert expected_keys.issubset(result.keys())

    def test_summary_fields_complete(self, engine):
        """Summary dict must contain all required metric fields."""
        result = engine.calculate_full_vibration_analysis(
            wob_klb=20, rpm=120, rop_fph=50, torque_ftlb=10000,
            bit_diameter_in=8.5,
        )
        summary = result["summary"]
        required = [
            "stability_index", "stability_status",
            "critical_rpm_axial", "critical_rpm_lateral",
            "stick_slip_severity", "stick_slip_class",
            "mse_psi", "mse_efficiency_pct",
            "optimal_wob", "optimal_rpm", "alerts",
        ]
        for key in required:
            assert key in summary, f"Missing summary key: {key}"

    def test_alerts_is_list(self, engine):
        """Alerts must be a list (possibly empty)."""
        result = engine.calculate_full_vibration_analysis(
            wob_klb=20, rpm=120, rop_fph=50, torque_ftlb=10000,
            bit_diameter_in=8.5,
        )
        assert isinstance(result["alerts"], list)

    def test_near_resonance_generates_alert(self, engine):
        """Operating near axial critical RPM should trigger an alert."""
        # First, find the axial critical RPM for the default BHA
        axial = engine.calculate_critical_rpm_axial(
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, mud_weight_ppg=10.0,
        )
        crit_rpm = axial["critical_rpm_1st"]
        # Run full analysis AT the critical RPM
        result = engine.calculate_full_vibration_analysis(
            wob_klb=20, rpm=crit_rpm, rop_fph=50, torque_ftlb=10000,
            bit_diameter_in=8.5, bha_length_ft=300, bha_od_in=6.75,
            bha_id_in=2.813, bha_weight_lbft=83.0, mud_weight_ppg=10.0,
        )
        alert_text = " ".join(result["alerts"])
        assert "axial" in alert_text.lower() or "resonance" in alert_text.lower() or len(result["alerts"]) > 0
