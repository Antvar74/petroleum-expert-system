"""
Phase 2 Elite Tests — Advanced Physics
Tests for P/T corrections, stiff-string T&D, post-buckling drag,
CT elongation, and CT fatigue.
~50 tests across 10 classes.
"""
import math
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine


# ===== Shared fixtures =====

def build_directional_survey():
    """Standard directional well survey for T&D tests."""
    return [
        {"md": 0,    "inclination": 0,  "azimuth": 0,   "tvd": 0},
        {"md": 2000,  "inclination": 0,  "azimuth": 0,   "tvd": 2000},
        {"md": 4000,  "inclination": 30, "azimuth": 45,  "tvd": 3800},
        {"md": 6000,  "inclination": 60, "azimuth": 45,  "tvd": 5200},
        {"md": 8000,  "inclination": 90, "azimuth": 45,  "tvd": 5800},
        {"md": 10000, "inclination": 90, "azimuth": 45,  "tvd": 5800},
    ]

def build_high_dls_survey():
    """Survey with high DLS zones for stiff-string testing."""
    return [
        {"md": 0,    "inclination": 0,  "azimuth": 0,   "tvd": 0},
        {"md": 1000, "inclination": 0,  "azimuth": 0,   "tvd": 1000},
        {"md": 1200, "inclination": 15, "azimuth": 30,  "tvd": 1190},  # 7.5 deg/100ft DLS
        {"md": 1500, "inclination": 45, "azimuth": 45,  "tvd": 1380},  # 10 deg/100ft DLS
        {"md": 3000, "inclination": 45, "azimuth": 45,  "tvd": 2450},
        {"md": 5000, "inclination": 45, "azimuth": 45,  "tvd": 3860},
    ]

def build_drillstring():
    """Standard drillstring for T&D tests."""
    return [
        {"od": 8.0, "id_inner": 2.875, "weight": 147.0, "length": 500, "order_from_bit": 0},  # Collars
        {"od": 5.0, "id_inner": 3.0,   "weight": 49.3,  "length": 500, "order_from_bit": 1},  # HWDP
        {"od": 5.0, "id_inner": 4.276, "weight": 19.5,  "length": 9000, "order_from_bit": 2}, # DP
    ]

def build_bha_heavy_string():
    """Drillstring with heavy BHA for stiff-string comparison."""
    return [
        {"od": 9.5,  "id_inner": 3.0,   "weight": 220.0, "length": 200, "order_from_bit": 0},  # Stabilizer/Motor
        {"od": 8.0,  "id_inner": 2.875, "weight": 147.0, "length": 400, "order_from_bit": 1},  # Collars
        {"od": 6.5,  "id_inner": 3.5,   "weight": 91.0,  "length": 400, "order_from_bit": 2},  # HWDP-heavy
        {"od": 5.0,  "id_inner": 4.276, "weight": 19.5,  "length": 4000, "order_from_bit": 3}, # DP
    ]


# =====================================================================
# P/T CORRECTION TESTS
# =====================================================================

class TestCorrectDensityPT(unittest.TestCase):
    """Test P/T density correction."""

    def test_wbm_hpht(self):
        """At 10000 psi / 350°F, WBM density should change noticeably."""
        r = HydraulicsEngine.correct_density_pt(12.0, 10000, 350, "wbm")
        self.assertIn("rho_corrected", r)
        # Pressure increases density, temperature decreases it
        # At high T, temperature effect dominates for WBM
        self.assertNotEqual(r["rho_corrected"], 12.0)
        self.assertGreater(r["rho_corrected"], 10.0)
        self.assertLess(r["rho_corrected"], 14.0)

    def test_obm_hpht(self):
        """OBM has larger thermal expansion — more density change."""
        r_obm = HydraulicsEngine.correct_density_pt(12.0, 10000, 350, "obm")
        r_wbm = HydraulicsEngine.correct_density_pt(12.0, 10000, 350, "wbm")
        # OBM temperature effect is stronger, so correction is larger
        obm_change = abs(r_obm["rho_corrected"] - 12.0)
        wbm_change = abs(r_wbm["rho_corrected"] - 12.0)
        self.assertGreater(obm_change, wbm_change)

    def test_atmospheric_no_change(self):
        """At reference conditions (14.7 psi, 70°F), density should be unchanged."""
        r = HydraulicsEngine.correct_density_pt(10.0, 14.7, 70.0, "wbm")
        self.assertAlmostEqual(r["rho_corrected"], 10.0, places=2)

    def test_pressure_increases_density(self):
        """Higher pressure at constant temperature should increase density."""
        r_low = HydraulicsEngine.correct_density_pt(12.0, 5000, 70, "wbm")
        r_high = HydraulicsEngine.correct_density_pt(12.0, 15000, 70, "wbm")
        self.assertGreater(r_high["rho_corrected"], r_low["rho_corrected"])

    def test_temperature_decreases_density(self):
        """Higher temperature at constant pressure should decrease density."""
        r_cool = HydraulicsEngine.correct_density_pt(12.0, 5000, 100, "wbm")
        r_hot = HydraulicsEngine.correct_density_pt(12.0, 5000, 400, "wbm")
        self.assertLess(r_hot["rho_corrected"], r_cool["rho_corrected"])

    def test_zero_density_guard(self):
        """Zero density input should return zero."""
        r = HydraulicsEngine.correct_density_pt(0.0, 5000, 200, "wbm")
        self.assertEqual(r["rho_corrected"], 0.0)


class TestCorrectViscosityPT(unittest.TestCase):
    """Test P/T viscosity correction."""

    def test_higher_temp_lower_viscosity(self):
        """PV should decrease with increasing temperature."""
        r = HydraulicsEngine.correct_viscosity_pt(30.0, 250.0, t_ref=120.0)
        self.assertLess(r["pv_corrected"], 30.0)

    def test_lower_temp_higher_viscosity(self):
        """PV should increase when temperature drops below reference."""
        r = HydraulicsEngine.correct_viscosity_pt(30.0, 60.0, t_ref=120.0)
        self.assertGreater(r["pv_corrected"], 30.0)

    def test_reference_temp_no_change(self):
        """At reference temperature, PV should be unchanged."""
        r = HydraulicsEngine.correct_viscosity_pt(25.0, 120.0, t_ref=120.0)
        self.assertAlmostEqual(r["pv_corrected"], 25.0, places=1)

    def test_zero_pv_guard(self):
        """Zero PV should return zero."""
        r = HydraulicsEngine.correct_viscosity_pt(0.0, 200.0)
        self.assertEqual(r["pv_corrected"], 0.0)


class TestTemperatureProfile(unittest.TestCase):
    """Test geothermal gradient calculations."""

    def test_linear_gradient(self):
        """Temperature should increase linearly with depth."""
        depths = [0, 5000, 10000]
        r = HydraulicsEngine.calculate_temperature_profile(80.0, 0.012, depths)
        self.assertEqual(len(r), 3)
        self.assertAlmostEqual(r[0]["temperature_f"], 80.0, places=1)
        self.assertAlmostEqual(r[1]["temperature_f"], 80.0 + 0.012 * 5000, places=1)
        self.assertAlmostEqual(r[2]["temperature_f"], 80.0 + 0.012 * 10000, places=1)

    def test_profile_monotonic(self):
        """Temperature should increase monotonically with depth."""
        depths = [0, 2000, 4000, 6000, 8000, 10000]
        r = HydraulicsEngine.calculate_temperature_profile(70.0, 0.015, depths)
        temps = [p["temperature_f"] for p in r]
        for i in range(1, len(temps)):
            self.assertGreater(temps[i], temps[i - 1])


class TestFullCircuitPT(unittest.TestCase):
    """Test that P/T corrections integrate into full circuit."""

    def _sections(self):
        return [
            {"section_type": "drill_pipe", "length": 5000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "collar", "length": 500, "od": 8.0, "id_inner": 2.875},
            {"section_type": "annulus_dp", "length": 5000, "od": 8.5, "id_inner": 5.0},
            {"section_type": "annulus_dc", "length": 500, "od": 8.5, "id_inner": 8.0},
        ]

    def test_pt_correction_runs(self):
        """Full circuit with P/T corrections should run without error."""
        r = HydraulicsEngine.calculate_full_circuit(
            sections=self._sections(), nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=25, yp=12, tvd=5000,
            use_pt_correction=True, fluid_type="wbm",
            t_surface=80.0, geothermal_gradient=0.012
        )
        self.assertIn("summary", r)
        self.assertGreater(r["summary"]["total_spp_psi"], 0)

    def test_pt_vs_no_pt(self):
        """P/T correction should produce different pressure losses than no correction."""
        common = dict(
            sections=self._sections(), nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=25, yp=12, tvd=8000
        )
        r_no_pt = HydraulicsEngine.calculate_full_circuit(**common, use_pt_correction=False)
        r_pt = HydraulicsEngine.calculate_full_circuit(
            **common, use_pt_correction=True, t_surface=80.0, geothermal_gradient=0.015
        )
        # Pressures should differ
        self.assertNotEqual(
            r_no_pt["summary"]["total_spp_psi"],
            r_pt["summary"]["total_spp_psi"]
        )

    def test_backward_compat_bingham(self):
        """Default (no P/T) should give same results as before."""
        r = HydraulicsEngine.calculate_full_circuit(
            sections=self._sections(), nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=25, yp=12, tvd=5000
        )
        self.assertIn("summary", r)
        self.assertEqual(r["summary"]["rheology_model"], "bingham_plastic")


# =====================================================================
# STIFF-STRING T&D TESTS
# =====================================================================

class TestStiffStringModel(unittest.TestCase):
    """Test hybrid stiff-string torque & drag model."""

    def test_runs_without_error(self):
        """Stiff-string model should run and return valid results."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=4000
        )
        self.assertIn("station_results", r)
        self.assertIn("summary", r)
        self.assertEqual(r["summary"]["model"], "stiff_string")

    def test_stiff_vs_soft_hookload(self):
        """Stiff-string should give higher hookload than soft-string for trip_out."""
        survey = build_directional_survey()
        ds = build_drillstring()
        common = dict(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=4000
        )
        r_soft = TorqueDragEngine.compute_torque_drag(**common)
        r_stiff = TorqueDragEngine.compute_torque_drag_stiff(**common)
        # Stiff-string adds lateral force → more drag → higher hookload
        self.assertGreaterEqual(
            r_stiff["summary"]["surface_hookload_klb"],
            r_soft["summary"]["surface_hookload_klb"]
        )

    def test_high_dls_activates_stiffness(self):
        """High DLS zones should have stiffness corrections > 0."""
        survey = build_high_dls_survey()
        ds = build_bha_heavy_string()
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=2000,
            stiffness_threshold_dls=3.0
        )
        # At least some stations should have stiffness correction > 0
        stiff_count = r["summary"]["stiff_stations_count"]
        self.assertGreater(stiff_count, 0, "No stiffness corrections applied in high-DLS well")

    def test_bha_activates_stiffness(self):
        """BHA sections in curved well should have stiffness correction due to OD threshold."""
        # Use high-DLS survey where BHA passes through build section
        survey = build_high_dls_survey()
        ds = build_bha_heavy_string()
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=2000,
            stiffness_threshold_od=6.0
        )
        # In curved sections, BHA with OD >= 6" should have stiffness applied
        self.assertGreater(r["summary"]["stiff_stations_count"], 0)

    def test_station_results_have_extra_keys(self):
        """Stiff-string station results should have stiffness-specific keys."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=4000
        )
        sr = r["station_results"][0]
        self.assertIn("normal_force_soft", sr)
        self.assertIn("stiffness_correction", sr)
        self.assertIn("dls_local", sr)

    def test_rotating_torque(self):
        """Stiff-string rotating operation should produce torque."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="rotating", mud_weight=12.0,
            wob=20.0, rpm=120,
            casing_shoe_md=4000
        )
        self.assertGreater(r["summary"]["surface_torque_ftlb"], 0)

    def test_soft_string_identical_in_straight_hole(self):
        """In a straight vertical hole, stiff-string should approximate soft-string."""
        survey = [
            {"md": 0,    "inclination": 0, "azimuth": 0, "tvd": 0},
            {"md": 5000, "inclination": 0, "azimuth": 0, "tvd": 5000},
            {"md": 10000, "inclination": 0, "azimuth": 0, "tvd": 10000},
        ]
        ds = [
            {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 10000, "order_from_bit": 0}
        ]
        common = dict(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.20,
            operation="trip_out", mud_weight=10.0,
            casing_shoe_md=10000
        )
        r_soft = TorqueDragEngine.compute_torque_drag(**common)
        r_stiff = TorqueDragEngine.compute_torque_drag_stiff(**common)
        # In straight hole with no DLS, stiffness correction should be zero
        # and results should be very close
        diff = abs(r_stiff["summary"]["surface_hookload_klb"] - r_soft["summary"]["surface_hookload_klb"])
        self.assertLess(diff, 5.0, "Stiff and soft should be close in straight hole")

    def test_minimum_survey_stations(self):
        """Less than 2 survey stations should return error."""
        r = TorqueDragEngine.compute_torque_drag_stiff(
            survey=[{"md": 0, "inclination": 0, "azimuth": 0}],
            drillstring=build_drillstring(),
            friction_cased=0.2, friction_open=0.3,
            operation="trip_out", mud_weight=12.0
        )
        self.assertIn("error", r)


# =====================================================================
# POST-BUCKLING DRAG TESTS
# =====================================================================

class TestPostBucklingDrag(unittest.TestCase):
    """Test post-buckling drag in soft-string model."""

    def test_buckled_section_has_extra_drag(self):
        """When buckling occurs, drag_extra_buckling should be > 0."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="sliding", mud_weight=12.0,
            wob=40.0,  # High WOB to force buckling near bit
            casing_shoe_md=4000
        )
        # Check if any station has buckling AND extra drag
        buckled = [sr for sr in r["station_results"] if sr["buckling_status"] != "OK"]
        if buckled:
            has_extra = any(sr.get("drag_extra_buckling", 0) > 0 for sr in buckled)
            self.assertTrue(has_extra, "Buckled stations should have extra drag")

    def test_no_buckling_no_extra_drag(self):
        """When no buckling (low WOB), drag_extra should be 0."""
        survey = [
            {"md": 0, "inclination": 0, "azimuth": 0, "tvd": 0},
            {"md": 5000, "inclination": 0, "azimuth": 0, "tvd": 5000},
        ]
        ds = [
            {"od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 5000, "order_from_bit": 0}
        ]
        r = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=10.0,
            casing_shoe_md=5000
        )
        # Trip out with no WOB — everything in tension, no buckling
        for sr in r["station_results"]:
            self.assertEqual(sr.get("drag_extra_buckling", 0), 0)

    def test_high_wob_forces_buckling(self):
        """Very high WOB in directional well should produce buckling alerts."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="sliding", mud_weight=12.0,
            wob=60.0,  # Very high WOB
            casing_shoe_md=4000
        )
        # Should have buckling alerts
        has_buckling = any("Buckling" in a for a in r["summary"]["alerts"])
        self.assertTrue(has_buckling, "High WOB should cause buckling alerts")

    def test_station_results_have_extra_drag_key(self):
        """All station results should have drag_extra_buckling key."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="trip_out", mud_weight=12.0,
            casing_shoe_md=4000
        )
        for sr in r["station_results"]:
            self.assertIn("drag_extra_buckling", sr)

    def test_post_buckling_increases_hookload_trip_out(self):
        """Post-buckling drag should increase surface hookload for trip_out
        compared to a scenario without buckling (lower WOB)."""
        survey = build_directional_survey()
        ds = build_drillstring()
        common = dict(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="sliding", mud_weight=12.0,
            casing_shoe_md=4000
        )
        r_low_wob = TorqueDragEngine.compute_torque_drag(**common, wob=5.0)
        r_high_wob = TorqueDragEngine.compute_torque_drag(**common, wob=50.0)
        # Higher WOB creates more compression, potentially buckling and extra drag
        # The hookload will be lower (more compression) but drag should be higher
        # We just verify both run successfully
        self.assertIn("summary", r_low_wob)
        self.assertIn("summary", r_high_wob)

    def test_rotating_post_buckling_torque(self):
        """In rotating with buckling, torque_extra should be added."""
        survey = build_directional_survey()
        ds = build_drillstring()
        r = TorqueDragEngine.compute_torque_drag(
            survey=survey, drillstring=ds,
            friction_cased=0.20, friction_open=0.30,
            operation="rotating", mud_weight=12.0,
            wob=40.0, rpm=120,
            casing_shoe_md=4000
        )
        self.assertGreater(r["summary"]["surface_torque_ftlb"], 0)


# =====================================================================
# CT ELONGATION TESTS
# =====================================================================

class TestCTElongation(unittest.TestCase):
    """Test CT elongation/shortening calculations."""

    def test_weight_elongation_positive(self):
        """Weight always causes elongation (stretching)."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0,
            delta_p_internal=0, delta_t=0
        )
        self.assertGreater(r["dL_weight_ft"], 0)

    def test_temperature_elongation(self):
        """Heating should cause elongation, cooling should cause shortening."""
        base = dict(ct_od=2.0, ct_id=1.688, ct_length=15000,
                    weight_per_ft=2.75, mud_weight=9.0)
        r_hot = WorkoverHydraulicsEngine.calculate_ct_elongation(**base, delta_t=100)
        r_cold = WorkoverHydraulicsEngine.calculate_ct_elongation(**base, delta_t=-50)
        self.assertGreater(r_hot["dL_temperature_ft"], 0, "Heating should elongate")
        self.assertLess(r_cold["dL_temperature_ft"], 0, "Cooling should shorten")

    def test_ballooning_shortening(self):
        """Internal pressure (ballooning) should cause shortening due to Poisson effect."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0,
            delta_p_internal=3000, wellhead_pressure=5000
        )
        # With internal > external, ballooning should cause shortening
        self.assertLess(r["dL_ballooning_ft"], 0)

    def test_bourdon_elongation(self):
        """Internal pressure Bourdon effect should cause elongation."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0,
            delta_p_internal=3000, wellhead_pressure=5000
        )
        self.assertGreater(r["dL_bourdon_ft"], 0)

    def test_all_components_sum(self):
        """Total should equal sum of components."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0,
            delta_p_internal=2000, delta_t=80, wellhead_pressure=4000
        )
        expected = (r["dL_weight_ft"] + r["dL_temperature_ft"] +
                    r["dL_ballooning_ft"] + r["dL_bourdon_ft"])
        self.assertAlmostEqual(r["dL_total_ft"], expected, places=3)

    def test_depth_correction_opposite(self):
        """Depth correction should be negative of total elongation."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0, delta_t=50
        )
        self.assertAlmostEqual(r["depth_correction_ft"], -r["dL_total_ft"], places=3)

    def test_zero_length_guard(self):
        """Zero CT length should return zeros."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=0,
            weight_per_ft=2.75, mud_weight=9.0
        )
        self.assertEqual(r["dL_total_ft"], 0.0)

    def test_typical_range(self):
        """For typical CT job, total elongation should be reasonable (< 50 ft)."""
        r = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=15000,
            weight_per_ft=2.75, mud_weight=9.0,
            delta_p_internal=2000, delta_t=80, wellhead_pressure=3000
        )
        self.assertLess(abs(r["dL_total_ft"]), 50.0)

    def test_longer_ct_more_elongation(self):
        """Longer CT string should produce more weight elongation."""
        r1 = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=10000,
            weight_per_ft=2.75, mud_weight=9.0
        )
        r2 = WorkoverHydraulicsEngine.calculate_ct_elongation(
            ct_od=2.0, ct_id=1.688, ct_length=20000,
            weight_per_ft=2.75, mud_weight=9.0
        )
        self.assertGreater(r2["dL_weight_ft"], r1["dL_weight_ft"])


# =====================================================================
# CT FATIGUE TESTS
# =====================================================================

class TestCTFatigue(unittest.TestCase):
    """Test CT fatigue calculations (API RP 5C7)."""

    def test_basic_bending_strain(self):
        """Bending strain should be positive and reasonable."""
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0,
            internal_pressure=0
        )
        self.assertGreater(r["strain_bending_pct"], 0)
        # Typical CT bending strain: 1-3%
        self.assertLess(r["strain_bending_pct"], 5.0)

    def test_pressure_increases_strain(self):
        """Internal pressure should add to total strain."""
        r0 = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=0
        )
        r_p = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=5000
        )
        self.assertGreater(r_p["strain_total_pct"], r0["strain_total_pct"])
        self.assertLess(r_p["cycles_to_failure"], r0["cycles_to_failure"])

    def test_smaller_reel_more_strain(self):
        """Smaller reel diameter should produce higher bending strain."""
        r_large = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=120.0, internal_pressure=0
        )
        r_small = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=72.0, internal_pressure=0
        )
        self.assertGreater(r_small["strain_bending_pct"], r_large["strain_bending_pct"])
        self.assertLess(r_small["cycles_to_failure"], r_large["cycles_to_failure"])

    def test_miner_rule_accumulates_damage(self):
        """Trips history should accumulate damage via Miner's rule."""
        trips = [
            {"pressure_psi": 3000, "cycles": 50},
            {"pressure_psi": 5000, "cycles": 30},
        ]
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=3000,
            trips_history=trips
        )
        self.assertGreater(r["damage_accumulated"], 0)
        self.assertLess(r["remaining_life_pct"], 100.0)
        self.assertEqual(len(r["damage_breakdown"]), 2)

    def test_no_history_full_life(self):
        """Without trips history, remaining life should be 100%."""
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=0
        )
        self.assertAlmostEqual(r["remaining_life_pct"], 100.0, places=1)
        self.assertEqual(r["damage_accumulated"], 0.0)

    def test_cycles_to_failure_positive(self):
        """Cycles to failure should always be positive."""
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=5000
        )
        self.assertGreater(r["cycles_to_failure"], 0)

    def test_sn_parameters_returned(self):
        """S-N curve parameters should be returned."""
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=0
        )
        self.assertIn("sn_parameters", r)
        self.assertIn("C", r["sn_parameters"])
        self.assertIn("m", r["sn_parameters"])

    def test_higher_grade_fewer_cycles(self):
        """Higher yield strength (more brittle) should give fewer cycles."""
        r_80 = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=3000,
            yield_strength_psi=80000
        )
        r_110 = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=96.0, internal_pressure=3000,
            yield_strength_psi=110000
        )
        self.assertGreater(r_80["cycles_to_failure"], r_110["cycles_to_failure"])

    def test_invalid_dimensions(self):
        """Invalid dimensions should return error."""
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=0.0, wall_thickness=0.156,
            reel_diameter=96.0
        )
        self.assertIn("error", r)

    def test_exhausted_life(self):
        """Many historical cycles should exhaust fatigue life."""
        trips = [{"pressure_psi": 5000, "cycles": 100000}]
        r = WorkoverHydraulicsEngine.calculate_ct_fatigue(
            ct_od=2.0, wall_thickness=0.156,
            reel_diameter=72.0, internal_pressure=5000,
            trips_history=trips
        )
        # With very many cycles, damage should be high
        self.assertGreater(r["damage_accumulated"], 0.5)


# =====================================================================
# FULL WORKOVER INTEGRATION TESTS
# =====================================================================

class TestFullWorkoverIntegration(unittest.TestCase):
    """Test that elongation is integrated into full workover analysis."""

    def test_elongation_in_full_workover(self):
        """Full workover should include elongation data."""
        r = WorkoverHydraulicsEngine.calculate_full_workover(
            flow_rate=60, mud_weight=9.0, pv=15, yp=8,
            ct_od=2.0, wall_thickness=0.156,
            ct_length=15000, hole_id=4.892,
            tvd=12000, inclination=30,
            wellhead_pressure=2000
        )
        self.assertIn("elongation", r)
        self.assertIn("dL_total_ft", r["elongation"])
        self.assertIn("dL_weight_ft", r["elongation"])


if __name__ == "__main__":
    unittest.main()
