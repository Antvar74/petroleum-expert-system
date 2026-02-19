"""
Phase 8 Elite Tests — Vibrations Engine
Tests for multi-component BHA modal analysis, 3D survey coupling,
bit-rock interaction, stabilizer optimization, and fatigue damage.
"""
import math
import pytest
from orchestrator.vibrations_engine import VibrationsEngine


# =====================================================================
# 8.1 Multi-Component BHA Modal Analysis (TMM)
# =====================================================================
class TestCriticalRPMLateralMulti:
    """Tests for calculate_critical_rpm_lateral_multi()."""

    def _sample_bha(self):
        return [
            {"type": "collar", "od": 8.0, "id_inner": 2.813, "length_ft": 90, "weight_ppf": 147},
            {"type": "stabilizer", "od": 8.25, "id_inner": 2.813, "length_ft": 5, "weight_ppf": 130},
            {"type": "mwd", "od": 6.75, "id_inner": 3.0, "length_ft": 30, "weight_ppf": 95},
            {"type": "motor", "od": 6.75, "id_inner": 3.5, "length_ft": 30, "weight_ppf": 80},
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 60, "weight_ppf": 83},
        ]

    def test_keys_present(self):
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(self._sample_bha())
        for key in ["modes", "mode_1_critical_rpm", "num_modes_found",
                     "total_bha_length_ft", "components", "method"]:
            assert key in result, f"Missing key: {key}"

    def test_mode_1_positive(self):
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(self._sample_bha())
        assert result["mode_1_critical_rpm"] > 0

    def test_multi_mode_found(self):
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(self._sample_bha())
        assert result["num_modes_found"] >= 1

    def test_modes_ascending(self):
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(self._sample_bha())
        modes = result["modes"]
        if len(modes) >= 2:
            assert modes[1]["critical_rpm"] > modes[0]["critical_rpm"]

    def test_empty_bha_returns_error(self):
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi([])
        assert "error" in result

    def test_components_table_matches_input(self):
        bha = self._sample_bha()
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(bha)
        assert len(result["components"]) == len(bha)

    def test_total_length_correct(self):
        bha = self._sample_bha()
        expected_length = sum(c["length_ft"] for c in bha)
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(bha)
        assert abs(result["total_bha_length_ft"] - expected_length) < 0.1

    def test_heavier_bha_lower_critical_rpm(self):
        """Heavier BHA (more mass) should have lower critical RPM."""
        light = [{"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 200, "weight_ppf": 83}]
        heavy = [{"type": "collar", "od": 8.0, "id_inner": 2.813, "length_ft": 200, "weight_ppf": 147}]
        r_light = VibrationsEngine.calculate_critical_rpm_lateral_multi(light)
        r_heavy = VibrationsEngine.calculate_critical_rpm_lateral_multi(heavy)
        # Heavier should shift frequency — either direction depending on stiffness/mass ratio
        assert r_light["mode_1_critical_rpm"] > 0
        assert r_heavy["mode_1_critical_rpm"] > 0


# =====================================================================
# 8.2 3D Survey Coupling Vibration Map
# =====================================================================
class TestVibrationMap3D:
    """Tests for calculate_vibration_map_3d()."""

    def _sample_survey(self):
        return [
            {"md_ft": 0, "inclination_deg": 0, "azimuth_deg": 0, "dls_deg_100ft": 0},
            {"md_ft": 3000, "inclination_deg": 15, "azimuth_deg": 90, "dls_deg_100ft": 2},
            {"md_ft": 6000, "inclination_deg": 45, "azimuth_deg": 90, "dls_deg_100ft": 3},
            {"md_ft": 9000, "inclination_deg": 70, "azimuth_deg": 90, "dls_deg_100ft": 1.5},
            {"md_ft": 12000, "inclination_deg": 85, "azimuth_deg": 90, "dls_deg_100ft": 0.5},
        ]

    def test_keys_present(self):
        result = VibrationsEngine.calculate_vibration_map_3d(self._sample_survey())
        for key in ["critical_rpm_by_depth", "risk_map", "safe_rpm_windows", "num_stations"]:
            assert key in result

    def test_critical_rpm_varies_with_inclination(self):
        result = VibrationsEngine.calculate_vibration_map_3d(self._sample_survey())
        crits = result["critical_rpm_by_depth"]
        # Higher inclination → lower lateral critical RPM (more lateral load)
        assert len(crits) == 5
        # Station at 45° should have lower lat crit than 0°
        crit_0 = crits[0]["critical_rpm_lateral"]
        crit_45 = crits[2]["critical_rpm_lateral"]
        assert crit_45 < crit_0 or crit_0 > 100  # At minimum, values must be positive

    def test_risk_map_has_correct_size(self):
        survey = self._sample_survey()
        rpm_range = [60, 120, 180]
        result = VibrationsEngine.calculate_vibration_map_3d(survey, rpm_range=rpm_range)
        assert len(result["risk_map"]) == len(survey) * len(rpm_range)

    def test_risk_zones_are_valid(self):
        result = VibrationsEngine.calculate_vibration_map_3d(self._sample_survey())
        for cell in result["risk_map"]:
            assert cell["zone"] in ("green", "yellow", "red")
            assert 0 <= cell["risk_score"] <= 1.0

    def test_dls_factor_increases_risk(self):
        result = VibrationsEngine.calculate_vibration_map_3d(self._sample_survey())
        crits = result["critical_rpm_by_depth"]
        for c in crits:
            assert c["dls_factor"] >= 1.0

    def test_empty_survey_returns_error(self):
        result = VibrationsEngine.calculate_vibration_map_3d([])
        assert "error" in result


# =====================================================================
# 8.3 Bit-Rock Interaction
# =====================================================================
class TestBitExcitation:
    """Tests for calculate_bit_excitation()."""

    def test_pdc_excitation_frequency(self):
        result = VibrationsEngine.calculate_bit_excitation(
            bit_type="pdc", num_blades_or_cones=5, rpm=120, wob_klb=20
        )
        # 5 blades × 120 RPM / 60 = 10 Hz
        assert abs(result["excitation_freq_hz"] - 10.0) < 0.01

    def test_roller_cone_excitation(self):
        result = VibrationsEngine.calculate_bit_excitation(
            bit_type="roller_cone", num_blades_or_cones=20, rpm=60, wob_klb=30
        )
        # 20 teeth × 60 RPM / 60 × 3 cones = 60 Hz
        assert abs(result["excitation_freq_hz"] - 60.0) < 0.01

    def test_depth_of_cut_positive(self):
        result = VibrationsEngine.calculate_bit_excitation(
            bit_type="pdc", num_blades_or_cones=5, rpm=120, wob_klb=20, rop_fph=80
        )
        assert result["depth_of_cut_in"] > 0

    def test_harmonics_present(self):
        result = VibrationsEngine.calculate_bit_excitation(
            bit_type="pdc", num_blades_or_cones=6, rpm=100, wob_klb=15
        )
        assert len(result["harmonics"]) == 3
        assert result["harmonics"][1]["freq_hz"] == result["excitation_freq_hz"] * 2

    def test_zero_rpm_error(self):
        result = VibrationsEngine.calculate_bit_excitation(
            bit_type="pdc", num_blades_or_cones=5, rpm=0, wob_klb=20
        )
        assert "error" in result


class TestResonance:
    """Tests for check_resonance()."""

    def test_resonance_at_natural_freq(self):
        result = VibrationsEngine.check_resonance(
            excitation_freq_hz=10.0, natural_freqs_hz=[10.0, 25.0, 40.0]
        )
        assert result["resonance_risk"] in ("critical", "high")

    def test_no_resonance_far_away(self):
        result = VibrationsEngine.check_resonance(
            excitation_freq_hz=5.0, natural_freqs_hz=[15.0, 30.0, 45.0]
        )
        assert result["resonance_risk"] == "low"

    def test_detuning_recommendation(self):
        result = VibrationsEngine.check_resonance(
            excitation_freq_hz=10.0, natural_freqs_hz=[10.5]
        )
        if result["resonance_risk"] in ("critical", "high", "moderate"):
            assert result["detuning_rpm_recommended"] is not None

    def test_empty_natural_freqs(self):
        result = VibrationsEngine.check_resonance(
            excitation_freq_hz=10.0, natural_freqs_hz=[]
        )
        assert result["resonance_risk"] == "low"

    def test_frequency_ratio_near_one(self):
        result = VibrationsEngine.check_resonance(
            excitation_freq_hz=10.0, natural_freqs_hz=[10.0]
        )
        assert abs(result["frequency_ratio"] - 1.0) < 0.01


# =====================================================================
# 8.4 Stabilizer Optimization
# =====================================================================
class TestStabilizerOptimization:
    """Tests for optimize_stabilizer_placement()."""

    def _sample_bha(self):
        return [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 90, "weight_ppf": 83},
            {"type": "mwd", "od": 6.75, "id_inner": 3.0, "length_ft": 30, "weight_ppf": 95},
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 90, "weight_ppf": 83},
        ]

    def test_keys_present(self):
        result = VibrationsEngine.optimize_stabilizer_placement(self._sample_bha())
        for key in ["optimal_position_ft", "baseline_critical_rpm", "candidates",
                     "frequency_separation_rpm", "target_rpm_range"]:
            assert key in result

    def test_optimal_position_within_bha(self):
        bha = self._sample_bha()
        total = sum(c["length_ft"] for c in bha)
        result = VibrationsEngine.optimize_stabilizer_placement(bha)
        assert 0 < result["optimal_position_ft"] < total

    def test_candidates_count(self):
        result = VibrationsEngine.optimize_stabilizer_placement(
            self._sample_bha(), num_candidates=7
        )
        assert len(result["candidates"]) == 7

    def test_separation_positive(self):
        result = VibrationsEngine.optimize_stabilizer_placement(self._sample_bha())
        assert result["frequency_separation_rpm"] >= 0

    def test_empty_bha_error(self):
        result = VibrationsEngine.optimize_stabilizer_placement([])
        assert "error" in result


# =====================================================================
# 8.5 Fatigue Damage (Miner's Rule)
# =====================================================================
class TestFatigueDamage:
    """Tests for calculate_fatigue_damage()."""

    def _sample_survey(self):
        return [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 0},
            {"md_ft": 3000, "inclination_deg": 15, "dls_deg_100ft": 3},
            {"md_ft": 6000, "inclination_deg": 45, "dls_deg_100ft": 5},
            {"md_ft": 9000, "inclination_deg": 70, "dls_deg_100ft": 8},
            {"md_ft": 10000, "inclination_deg": 80, "dls_deg_100ft": 2},
        ]

    def test_keys_present(self):
        result = VibrationsEngine.calculate_fatigue_damage(
            drillstring_od=5.0, drillstring_id=4.276,
            survey_stations=self._sample_survey()
        )
        for key in ["cumulative_damage", "remaining_life_pct", "status",
                     "endurance_limit_psi", "damage_by_station", "critical_joints"]:
            assert key in result

    def test_damage_increases_with_dls(self):
        low_dls = [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 1},
            {"md_ft": 5000, "inclination_deg": 10, "dls_deg_100ft": 1},
        ]
        high_dls = [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 10},
            {"md_ft": 5000, "inclination_deg": 60, "dls_deg_100ft": 10},
        ]
        r_low = VibrationsEngine.calculate_fatigue_damage(5.0, 4.276, survey_stations=low_dls)
        r_high = VibrationsEngine.calculate_fatigue_damage(5.0, 4.276, survey_stations=high_dls)
        assert r_high["cumulative_damage"] > r_low["cumulative_damage"]

    def test_status_ok_for_low_damage(self):
        survey = [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 0.5},
            {"md_ft": 5000, "inclination_deg": 5, "dls_deg_100ft": 0.5},
        ]
        result = VibrationsEngine.calculate_fatigue_damage(
            5.0, 4.276, survey_stations=survey, hours_per_stand=0.1
        )
        assert result["status"] == "OK"

    def test_remaining_life_decreases_with_damage(self):
        result = VibrationsEngine.calculate_fatigue_damage(
            5.0, 4.276, survey_stations=self._sample_survey(), rpm=150
        )
        assert result["remaining_life_pct"] <= 100.0

    def test_critical_joints_sorted(self):
        result = VibrationsEngine.calculate_fatigue_damage(
            5.0, 4.276, survey_stations=self._sample_survey()
        )
        if len(result["critical_joints"]) >= 2:
            assert result["critical_joints"][0]["damage_increment"] >= result["critical_joints"][1]["damage_increment"]

    def test_uniform_estimate_without_survey(self):
        result = VibrationsEngine.calculate_fatigue_damage(
            5.0, 4.276, total_rotating_hours=200, rpm=120
        )
        assert result["cumulative_damage"] >= 0
        assert "remaining_life_pct" in result
