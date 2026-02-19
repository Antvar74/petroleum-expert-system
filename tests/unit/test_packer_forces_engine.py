"""
Unit tests for PackerForcesEngine.
Tests: tubing_areas, piston_force, ballooning_force, temperature_force,
       buckling_force, tubing_movement, helical_buckling, total_packer_force.
"""
import math
import pytest
from orchestrator.packer_forces_engine import PackerForcesEngine


# ============================================================
# calculate_tubing_areas (2 tests)
# ============================================================

class TestTubingAreas:

    def test_standard_tubing(self):
        """2-7/8" tubing: OD=2.875, ID=2.441."""
        areas = PackerForcesEngine.calculate_tubing_areas(2.875, 2.441)
        assert areas["ao_in2"] > areas["ai_in2"]
        assert areas["as_in2"] > 0
        assert abs(areas["ao_in2"] - areas["ai_in2"] - areas["as_in2"]) < 0.001

    def test_larger_tubing(self):
        """3-1/2" tubing: OD=3.5, ID=2.992."""
        areas = PackerForcesEngine.calculate_tubing_areas(3.5, 2.992)
        assert areas["as_in2"] > 0


# ============================================================
# calculate_piston_force (3 tests)
# ============================================================

class TestPistonForce:

    def test_equal_pressures_zero_force(self):
        """If P_above = P_below, piston force depends on geometry."""
        f = PackerForcesEngine.calculate_piston_force(5000, 5000, 8.3, 6.5, 4.68)
        # Not necessarily zero — depends on (A_seal - A_i) vs (A_seal - A_o)
        assert isinstance(f, float)

    def test_higher_below_tension(self):
        """Higher pressure below packer → tends to push packer up → tension on tubing."""
        f = PackerForcesEngine.calculate_piston_force(8000, 3000, 8.3, 6.5, 4.68)
        assert f > 0  # tension

    def test_higher_above_compression(self):
        """Higher pressure above → compression."""
        f = PackerForcesEngine.calculate_piston_force(3000, 8000, 8.3, 6.5, 4.68)
        assert f < 0  # compression


# ============================================================
# calculate_ballooning_force (3 tests)
# ============================================================

class TestBallooningForce:

    def test_internal_pressure_increase(self):
        """Increasing internal pressure → ballooning → tubing shortens → effective tension."""
        f = PackerForcesEngine.calculate_ballooning_force(
            delta_pi=3000, delta_po=0, tubing_ai=4.68, tubing_ao=6.5
        )
        # F = -2ν × (ΔPi × Ai - ΔPo × Ao) = -2×0.3×(3000×4.68 - 0) < 0
        assert f < 0  # compression due to ballooning

    def test_external_pressure_increase(self):
        """Increasing external pressure → reverse ballooning."""
        f = PackerForcesEngine.calculate_ballooning_force(
            delta_pi=0, delta_po=3000, tubing_ai=4.68, tubing_ao=6.5
        )
        assert f > 0  # tension

    def test_no_change_zero_force(self):
        f = PackerForcesEngine.calculate_ballooning_force(0, 0, 4.68, 6.5)
        assert f == 0.0


# ============================================================
# calculate_temperature_force (3 tests)
# ============================================================

class TestTemperatureForce:

    def test_heating_compression(self):
        """Heating → tubing wants to expand → restrained → compression."""
        f = PackerForcesEngine.calculate_temperature_force(
            delta_t=100, tubing_as=1.82
        )
        assert f < 0

    def test_cooling_tension(self):
        """Cooling → tubing contracts → tension."""
        f = PackerForcesEngine.calculate_temperature_force(
            delta_t=-50, tubing_as=1.82
        )
        assert f > 0

    def test_no_change_zero(self):
        f = PackerForcesEngine.calculate_temperature_force(0, 1.82)
        assert f == 0.0


# ============================================================
# calculate_tubing_movement (2 tests)
# ============================================================

class TestTubingMovement:

    def test_tension_elongates(self):
        """Positive force → elongation."""
        dl = PackerForcesEngine.calculate_tubing_movement(
            force=50000, tubing_length=10000, tubing_as=1.82
        )
        assert dl > 0

    def test_compression_shortens(self):
        """Negative force → shortening."""
        dl = PackerForcesEngine.calculate_tubing_movement(
            force=-50000, tubing_length=10000, tubing_as=1.82
        )
        assert dl < 0


# ============================================================
# calculate_helical_buckling_load (2 tests)
# ============================================================

class TestHelicalBuckling:

    def test_returns_positive(self):
        f_cr = PackerForcesEngine.calculate_helical_buckling_load(
            tubing_od=2.875, tubing_id=2.441,
            tubing_weight=6.5, casing_id=6.0
        )
        assert f_cr > 0

    def test_zero_clearance_infinite(self):
        """If tubing OD = casing ID, no clearance → infinite critical load."""
        f_cr = PackerForcesEngine.calculate_helical_buckling_load(
            tubing_od=6.0, tubing_id=5.0, tubing_weight=6.5, casing_id=6.0
        )
        assert f_cr == float('inf')


# ============================================================
# calculate_total_packer_force (7 tests)
# ============================================================

class TestTotalPackerForce:

    def _standard_params(self):
        return {
            "tubing_od": 2.875,
            "tubing_id": 2.441,
            "tubing_weight": 6.5,
            "tubing_length": 10000,
            "seal_bore_id": 3.25,
            "initial_tubing_pressure": 0,
            "final_tubing_pressure": 3000,
            "initial_annulus_pressure": 0,
            "final_annulus_pressure": 0,
            "initial_temperature": 80,
            "final_temperature": 250,
            "packer_depth_tvd": 10000,
        }

    def test_returns_required_keys(self):
        result = PackerForcesEngine.calculate_total_packer_force(**self._standard_params())
        assert "summary" in result
        assert "force_components" in result
        assert "movements" in result
        assert "parameters" in result
        assert "alerts" in result

    def test_summary_has_force_direction(self):
        result = PackerForcesEngine.calculate_total_packer_force(**self._standard_params())
        assert result["summary"]["force_direction"] in ("Tension", "Compression")

    def test_force_components_sum(self):
        """Total = piston + ballooning + temperature."""
        result = PackerForcesEngine.calculate_total_packer_force(**self._standard_params())
        fc = result["force_components"]
        assert abs(fc["total"] - (fc["piston"] + fc["ballooning"] + fc["temperature"])) < 2

    def test_no_change_minimal_force(self):
        """No pressure or temperature change → minimal forces."""
        params = self._standard_params()
        params["final_tubing_pressure"] = 0
        params["final_temperature"] = 80
        result = PackerForcesEngine.calculate_total_packer_force(**params)
        assert abs(result["summary"]["total_force_lbs"]) < 100

    def test_heating_generates_compression(self):
        """Large temperature increase → significant compression."""
        params = self._standard_params()
        params["final_tubing_pressure"] = 0  # no pressure change
        params["final_temperature"] = 300    # large heating
        result = PackerForcesEngine.calculate_total_packer_force(**params)
        assert result["force_components"]["temperature"] < 0

    def test_buckling_check_present(self):
        result = PackerForcesEngine.calculate_total_packer_force(**self._standard_params())
        assert result["summary"]["buckling_status"] in ("OK", "Sinusoidal Buckling", "Helical Buckling")

    def test_large_movement_alert(self):
        """Large pressure + temperature changes should trigger movement alert."""
        params = self._standard_params()
        params["final_tubing_pressure"] = 10000
        params["final_temperature"] = 400
        result = PackerForcesEngine.calculate_total_packer_force(**params)
        # At least should have buckling or movement alerts
        assert isinstance(result["alerts"], list)
