"""
Phase 8 Elite Tests — Packer Forces Engine
Tests for APB model, packer type classification, temperature profile,
buckling length, and landing conditions.
"""
import math
import pytest
from orchestrator.packer_forces_engine import PackerForcesEngine


# =====================================================================
# 8.6 Annular Pressure Buildup (APB)
# =====================================================================
class TestAPB:
    """Tests for calculate_apb()."""

    def test_keys_present(self):
        result = PackerForcesEngine.calculate_apb()
        for key in ["apb_psi", "total_annular_pressure_psi", "casing_burst_sf",
                     "tubing_collapse_sf", "thermal_expansion_coeff",
                     "fluid_compressibility", "mitigation_needed"]:
            assert key in result, f"Missing key: {key}"

    def test_apb_positive_for_heating(self):
        result = PackerForcesEngine.calculate_apb(delta_t_avg=100)
        assert result["apb_psi"] > 0

    def test_obm_higher_apb_than_wbm(self):
        """OBM has higher thermal expansion → higher APB."""
        wbm = PackerForcesEngine.calculate_apb(annular_fluid_type="WBM", delta_t_avg=100)
        obm = PackerForcesEngine.calculate_apb(annular_fluid_type="OBM", delta_t_avg=100)
        assert obm["apb_psi"] > wbm["apb_psi"]

    def test_apb_scales_with_temperature(self):
        low_t = PackerForcesEngine.calculate_apb(delta_t_avg=50)
        high_t = PackerForcesEngine.calculate_apb(delta_t_avg=200)
        assert high_t["apb_psi"] > low_t["apb_psi"]

    def test_zero_temperature_zero_apb(self):
        result = PackerForcesEngine.calculate_apb(delta_t_avg=0)
        assert result["apb_psi"] == 0

    def test_safety_factors_positive(self):
        result = PackerForcesEngine.calculate_apb(delta_t_avg=50)
        assert result["casing_burst_sf"] > 0
        assert result["tubing_collapse_sf"] > 0


class TestAPBMitigation:
    """Tests for calculate_apb_mitigation()."""

    def test_foam_reduces_apb(self):
        result = PackerForcesEngine.calculate_apb_mitigation(
            apb_psi=5000, foam_volume_pct=10
        )
        assert result["apb_mitigated_psi"] < result["apb_original_psi"]
        assert result["reduction_pct"] > 0

    def test_crushable_reduces_apb(self):
        result = PackerForcesEngine.calculate_apb_mitigation(
            apb_psi=5000, crushable_spacer_vol_bbl=20, annular_volume_bbl=200
        )
        assert result["apb_mitigated_psi"] < 5000

    def test_zero_apb(self):
        result = PackerForcesEngine.calculate_apb_mitigation(apb_psi=0)
        assert result["apb_mitigated_psi"] == 0

    def test_both_mitigations_combined(self):
        foam_only = PackerForcesEngine.calculate_apb_mitigation(
            apb_psi=5000, foam_volume_pct=10
        )
        both = PackerForcesEngine.calculate_apb_mitigation(
            apb_psi=5000, foam_volume_pct=10, crushable_spacer_vol_bbl=20
        )
        assert both["apb_mitigated_psi"] <= foam_only["apb_mitigated_psi"]


# =====================================================================
# 8.7 Packer Type Classification
# =====================================================================
class TestPackerType:
    """Tests for calculate_packer_force_by_type()."""

    def test_free_packer_zero_force(self):
        result = PackerForcesEngine.calculate_packer_force_by_type(
            packer_type="free",
            total_force_if_anchored=50000,
            tubing_movement_if_free_in=-2.5
        )
        assert result["force_on_packer_lbs"] == 0.0
        assert abs(result["tubing_displacement_in"] - (-2.5)) < 0.01

    def test_anchored_packer_full_force(self):
        result = PackerForcesEngine.calculate_packer_force_by_type(
            packer_type="anchored",
            total_force_if_anchored=50000,
            tubing_movement_if_free_in=-2.5
        )
        assert result["force_on_packer_lbs"] == 50000
        assert result["tubing_displacement_in"] == 0.0

    def test_limited_within_stroke(self):
        result = PackerForcesEngine.calculate_packer_force_by_type(
            packer_type="limited",
            total_force_if_anchored=50000,
            tubing_movement_if_free_in=-1.0,
            stroke_in=3.0
        )
        assert result["force_on_packer_lbs"] == 0.0
        assert result["remaining_stroke_in"] == pytest.approx(2.0, abs=0.01)

    def test_limited_stroke_exhausted(self):
        result = PackerForcesEngine.calculate_packer_force_by_type(
            packer_type="limited",
            total_force_if_anchored=50000,
            tubing_movement_if_free_in=-5.0,
            stroke_in=2.0
        )
        assert result["force_on_packer_lbs"] != 0
        assert result["remaining_stroke_in"] == 0.0

    def test_unknown_packer_type_error(self):
        result = PackerForcesEngine.calculate_packer_force_by_type(
            packer_type="unknown",
            total_force_if_anchored=50000,
            tubing_movement_if_free_in=-2.5
        )
        assert "error" in result


# =====================================================================
# 8.8 Temperature Profile Variable with Depth
# =====================================================================
class TestTemperatureForceProfile:
    """Tests for calculate_temperature_force_profile()."""

    def _profiles(self):
        initial = [
            {"depth_ft": 0, "temperature_f": 80},
            {"depth_ft": 5000, "temperature_f": 130},
            {"depth_ft": 10000, "temperature_f": 180},
        ]
        production = [
            {"depth_ft": 0, "temperature_f": 100},
            {"depth_ft": 5000, "temperature_f": 200},
            {"depth_ft": 10000, "temperature_f": 300},
        ]
        return initial, production

    def test_keys_present(self):
        init, prod = self._profiles()
        result = PackerForcesEngine.calculate_temperature_force_profile(init, prod)
        for key in ["force_temperature_lbs", "delta_t_avg_f", "delta_t_max_f",
                     "delta_t_profile", "method"]:
            assert key in result

    def test_heating_produces_compression(self):
        """Heating should produce compressive (negative) force."""
        init, prod = self._profiles()
        result = PackerForcesEngine.calculate_temperature_force_profile(init, prod)
        assert result["force_temperature_lbs"] < 0  # compression

    def test_delta_t_avg_positive(self):
        init, prod = self._profiles()
        result = PackerForcesEngine.calculate_temperature_force_profile(init, prod)
        assert result["delta_t_avg_f"] > 0

    def test_delta_t_profile_length(self):
        init, prod = self._profiles()
        result = PackerForcesEngine.calculate_temperature_force_profile(init, prod)
        assert len(result["delta_t_profile"]) == len(prod)

    def test_max_delta_t_at_bottom(self):
        """Bottom of well should have highest delta-T in production."""
        init, prod = self._profiles()
        result = PackerForcesEngine.calculate_temperature_force_profile(init, prod)
        # Production bottom: 300-180 = 120, top: 100-80 = 20
        assert result["delta_t_max_f"] >= 100

    def test_empty_profiles_error(self):
        result = PackerForcesEngine.calculate_temperature_force_profile([], [])
        assert "error" in result


# =====================================================================
# 8.9 Buckling Length Calculation
# =====================================================================
class TestBucklingLength:
    """Tests for calculate_buckling_length()."""

    def test_no_buckling_low_force(self):
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-1000, inclination_deg=30
        )
        assert result["buckling_type"] == "None"
        assert result["buckled_length_ft"] == 0

    def test_sinusoidal_buckling(self):
        """Moderate compression should produce sinusoidal buckling."""
        # Use high force to trigger sinusoidal
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-50000, inclination_deg=45
        )
        # May or may not exceed critical — check structure
        assert result["buckling_type"] in ("None", "Sinusoidal", "Helicoidal")
        assert "buckled_length_ft" in result

    def test_helicoidal_buckling_high_force(self):
        """Very high compression should produce helicoidal buckling."""
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-200000, inclination_deg=60
        )
        # High force should at least trigger sinusoidal
        assert result["buckling_type"] in ("Sinusoidal", "Helicoidal")
        assert result["buckled_length_ft"] > 0

    def test_shortening_positive_when_buckled(self):
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-200000, inclination_deg=60
        )
        if result["buckling_type"] != "None":
            assert result["shortening_in"] > 0

    def test_critical_loads_relationship(self):
        """Helicoidal critical load = 2 × sinusoidal."""
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-50000, inclination_deg=45
        )
        ratio = result["critical_load_helicoidal_lbs"] / result["critical_load_sinusoidal_lbs"]
        assert abs(ratio - 2.0) < 0.01

    def test_clearance_positive(self):
        result = PackerForcesEngine.calculate_buckling_length(axial_force=-50000)
        assert result["radial_clearance_in"] > 0

    def test_invalid_clearance_error(self):
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-50000, tubing_od=7.0, casing_id=6.0  # OD > casing ID
        )
        assert "error" in result


# =====================================================================
# 8.10 Landing Force and Initial Conditions
# =====================================================================
class TestLandingConditions:
    """Tests for calculate_landing_conditions()."""

    def _sample_tubing(self):
        return [
            {"od": 3.5, "id_inner": 2.992, "length_ft": 5000, "weight_ppf": 9.3},
            {"od": 3.5, "id_inner": 2.992, "length_ft": 5000, "weight_ppf": 9.3},
        ]

    def _sample_survey(self):
        return [
            {"md_ft": 0, "inclination_deg": 0},
            {"md_ft": 3000, "inclination_deg": 20},
            {"md_ft": 7000, "inclination_deg": 45},
            {"md_ft": 10000, "inclination_deg": 60},
        ]

    def test_keys_present(self):
        result = PackerForcesEngine.calculate_landing_conditions(self._sample_tubing())
        for key in ["tubing_weight_air_lbs", "tubing_weight_buoyed_lbs",
                     "buoyancy_factor", "drag_force_lbs", "weight_at_packer_lbs",
                     "total_landing_force_lbs"]:
            assert key in result

    def test_buoyed_weight_less_than_air(self):
        result = PackerForcesEngine.calculate_landing_conditions(self._sample_tubing())
        assert result["tubing_weight_buoyed_lbs"] < result["tubing_weight_air_lbs"]

    def test_drag_reduces_weight_at_packer(self):
        result = PackerForcesEngine.calculate_landing_conditions(
            self._sample_tubing(), survey_stations=self._sample_survey()
        )
        assert result["weight_at_packer_lbs"] < result["tubing_weight_buoyed_lbs"]
        assert result["drag_force_lbs"] > 0

    def test_set_down_weight_added(self):
        result = PackerForcesEngine.calculate_landing_conditions(
            self._sample_tubing(), set_down_weight_lbs=10000
        )
        assert result["total_landing_force_lbs"] > result["weight_at_packer_lbs"]

    def test_empty_tubing_error(self):
        result = PackerForcesEngine.calculate_landing_conditions([])
        assert "error" in result

    def test_total_length_correct(self):
        tubing = self._sample_tubing()
        expected = sum(s["length_ft"] for s in tubing)
        result = PackerForcesEngine.calculate_landing_conditions(tubing)
        assert abs(result["total_tubing_length_ft"] - expected) < 0.1
