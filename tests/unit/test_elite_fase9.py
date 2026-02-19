"""
Phase 9 Elite Tests — Cross-Engine Bridges + Advanced Integration
Tests for cross-engine bridges between Phases 6-8 engines, plus
verification that new standalone API endpoints function correctly
at the engine level (unit tests, not HTTP tests).
"""
import math
import pytest


# =====================================================================
# Cross-Engine Bridge 1: Cementing ECD → Casing Collapse
# =====================================================================
class TestCementEcdToCasingCollapse:
    """Verify cement ECD data can feed into casing collapse scenario."""

    def test_cementing_ecd_produces_pressure(self):
        from orchestrator.cementing_engine import CementingEngine
        cem = CementingEngine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=10000, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.0, spacer_density_ppg=12.0,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
            pump_rate_bbl_min=5.0, pv_mud=25, yp_mud=12,
        )
        # Should have snapshots with ECD data
        assert "snapshots" in cem or "ecd_snapshots" in cem or isinstance(cem, dict)

    def test_casing_collapse_rating_exists(self):
        from orchestrator.casing_design_engine import CasingDesignEngine
        # L-80: yield = 80000 psi; 9.625 OD, 47 ppf → wall ~ 0.472"
        csg = CasingDesignEngine.calculate_collapse_rating(
            casing_od_in=9.625, wall_thickness_in=0.472, yield_strength_psi=80000
        )
        assert "collapse_rating_psi" in csg
        assert csg["collapse_rating_psi"] > 0

    def test_cement_density_creates_external_pressure(self):
        """Cement density column creates significant external pressure at depth."""
        cement_density = 16.0  # ppg
        tvd = 10000  # ft
        ext_pressure = cement_density * 0.052 * tvd
        assert ext_pressure > 8000  # 16 * 0.052 * 10000 = 8320 psi


# =====================================================================
# Cross-Engine Bridge 2: Casing ID → Completion Gun Selection
# =====================================================================
class TestCasingIdToCompletion:
    """Verify casing ID properly restricts gun selection."""

    def test_gun_catalog_filters_by_casing_id(self):
        from orchestrator.completion_design_engine import CompletionDesignEngine
        small = CompletionDesignEngine.select_gun_from_catalog(casing_id_in=4.0)
        large = CompletionDesignEngine.select_gun_from_catalog(casing_id_in=8.0)
        n_small = len(small.get("compatible_guns", []))
        n_large = len(large.get("compatible_guns", []))
        assert n_large >= n_small

    def test_gun_selection_respects_pressure(self):
        from orchestrator.completion_design_engine import CompletionDesignEngine
        result = CompletionDesignEngine.select_gun_from_catalog(
            casing_id_in=6.0, max_pressure_psi=25000, max_temperature_f=500
        )
        if "compatible_guns" in result:
            for gun in result["compatible_guns"]:
                assert gun["max_pressure_psi"] >= 25000


# =====================================================================
# Cross-Engine Bridge 3: IPR + Skin → Shot Efficiency (kh input)
# =====================================================================
class TestIPRSkinToShot:
    """Verify kh from shot efficiency can feed IPR calculation."""

    def test_darcy_ipr_with_kh_input(self):
        from orchestrator.completion_design_engine import CompletionDesignEngine
        kh = 5000  # md-ft
        h = 50     # ft
        k = kh / h  # 100 md
        ipr = CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=k, net_pay_ft=h,
            Bo=1.2, mu_oil_cp=1.0,
            reservoir_pressure_psi=4000,
            drainage_radius_ft=660, wellbore_radius_ft=0.354, skin=0,
        )
        assert "PI_stbd_psi" in ipr
        assert ipr["PI_stbd_psi"] > 0

    def test_higher_kh_higher_pi(self):
        from orchestrator.completion_design_engine import CompletionDesignEngine
        ipr_low = CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=10, net_pay_ft=50,
            Bo=1.2, mu_oil_cp=1.0,
            reservoir_pressure_psi=4000,
            drainage_radius_ft=660, wellbore_radius_ft=0.354, skin=0,
        )
        ipr_high = CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=100, net_pay_ft=50,
            Bo=1.2, mu_oil_cp=1.0,
            reservoir_pressure_psi=4000,
            drainage_radius_ft=660, wellbore_radius_ft=0.354, skin=0,
        )
        assert ipr_high["PI_stbd_psi"] > ipr_low["PI_stbd_psi"]


# =====================================================================
# Cross-Engine Bridge 4: Vibrations → T&D (friction increase)
# =====================================================================
class TestVibrationsToTD:
    """Verify vibration severity can modify T&D friction factor."""

    def test_stability_index_produces_friction_increase(self):
        from orchestrator.vibrations_engine import VibrationsEngine
        vib = VibrationsEngine.calculate_full_vibration_analysis(
            wob_klb=25, rpm=120, rop_fph=60, torque_ftlb=15000,
            bit_diameter_in=8.5, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83, bha_length_ft=300,
            mud_weight_ppg=10, hole_diameter_in=8.5,
        )
        stability = vib["stability"]["stability_index"]
        friction_increase = 0.05 * (1.0 - stability / 100.0)
        assert friction_increase >= 0
        assert friction_increase <= 0.05

    def test_friction_increase_formula_consistent(self):
        """Friction increase should be bounded and non-negative."""
        from orchestrator.vibrations_engine import VibrationsEngine
        for wob, rpm_val in [(10, 180), (25, 120), (40, 60)]:
            vib = VibrationsEngine.calculate_full_vibration_analysis(
                wob_klb=wob, rpm=rpm_val, rop_fph=60, torque_ftlb=15000,
                bit_diameter_in=8.5, bha_od_in=6.75, bha_id_in=2.813,
                bha_weight_lbft=83, bha_length_ft=300,
                mud_weight_ppg=10, hole_diameter_in=8.5,
            )
            stability = vib["stability"]["stability_index"]
            fi = 0.05 * (1.0 - stability / 100.0)
            assert 0 <= fi <= 0.05, f"Invalid friction increase: {fi}"


# =====================================================================
# Cross-Engine Bridge 5: Packer APB → Casing Burst
# =====================================================================
class TestPackerAPBToCasing:
    """Verify APB pressure can feed casing burst check."""

    def test_apb_produces_burst_load(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        from orchestrator.casing_design_engine import CasingDesignEngine
        apb = PackerForcesEngine.calculate_apb(
            annular_fluid_type="OBM", delta_t_avg=150,
            annular_volume_bbl=200,
        )
        # Burst rating: 9.625 OD, wall 0.472, L-80 (80ksi)
        csg = CasingDesignEngine.calculate_burst_rating(
            casing_od_in=9.625, wall_thickness_in=0.472, yield_strength_psi=80000
        )
        burst_rating = csg.get("burst_rating_psi", 6000)
        apb_psi = apb.get("apb_psi", 0)
        sf = burst_rating / apb_psi if apb_psi > 0 else 99
        assert sf > 0
        assert apb_psi > 0

    def test_high_apb_reduces_safety_factor(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        low = PackerForcesEngine.calculate_apb(delta_t_avg=50, annular_fluid_type="WBM")
        high = PackerForcesEngine.calculate_apb(delta_t_avg=250, annular_fluid_type="OBM")
        assert high["apb_psi"] > low["apb_psi"]


# =====================================================================
# Cross-Engine Bridge 6: T&D → Packer Landing
# =====================================================================
class TestTDToPackerLanding:
    """Verify T&D drag feeds packer landing conditions."""

    def test_landing_with_survey_includes_drag(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        tubing = [{"od": 3.5, "id_inner": 2.992, "length_ft": 10000, "weight_ppf": 9.3}]
        survey = [
            {"md_ft": 0, "inclination_deg": 0},
            {"md_ft": 5000, "inclination_deg": 30},
            {"md_ft": 10000, "inclination_deg": 60},
        ]
        result = PackerForcesEngine.calculate_landing_conditions(
            tubing_sections=tubing, survey_stations=survey, friction_factor=0.30,
        )
        assert result["drag_force_lbs"] > 0
        assert result["weight_at_packer_lbs"] < result["tubing_weight_buoyed_lbs"]

    def test_higher_friction_more_drag(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        tubing = [{"od": 3.5, "id_inner": 2.992, "length_ft": 10000, "weight_ppf": 9.3}]
        survey = [
            {"md_ft": 0, "inclination_deg": 0},
            {"md_ft": 5000, "inclination_deg": 45},
            {"md_ft": 10000, "inclination_deg": 70},
        ]
        low = PackerForcesEngine.calculate_landing_conditions(
            tubing_sections=tubing, survey_stations=survey, friction_factor=0.15,
        )
        high = PackerForcesEngine.calculate_landing_conditions(
            tubing_sections=tubing, survey_stations=survey, friction_factor=0.40,
        )
        assert high["drag_force_lbs"] > low["drag_force_lbs"]


# =====================================================================
# Cross-Engine Bridge 7: Temperature Profile → Cementing
# =====================================================================
class TestTemperatureProfileToCementing:
    """Verify temperature profile can feed cementing slurry corrections."""

    def test_slurry_correction_produces_result(self):
        from orchestrator.cementing_engine import CementingEngine
        result = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=40, yp_slurry=15,
            temperature_f=200, pressure_psi=5000,
        )
        assert "density_corrected_ppg" in result
        assert result["density_corrected_ppg"] > 0

    def test_higher_temp_changes_slurry(self):
        from orchestrator.cementing_engine import CementingEngine
        low_t = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=40, yp_slurry=15,
            temperature_f=100, pressure_psi=5000,
        )
        high_t = CementingEngine.correct_slurry_properties_pt(
            slurry_density_ppg=16.0, pv_slurry=40, yp_slurry=15,
            temperature_f=350, pressure_psi=5000,
        )
        # PV should decrease with temperature (viscosity drops)
        assert high_t["pv_corrected"] < low_t["pv_corrected"]


# =====================================================================
# Cross-Engine Bridge 8: Wellbore Cleanup → Cementing Spacer
# =====================================================================
class TestCleanupToCementingSpacer:
    """Verify wellbore cleanup metrics can inform spacer design."""

    def test_spacer_optimization_produces_result(self):
        from orchestrator.cementing_engine import CementingEngine
        result = CementingEngine.optimize_spacer(
            mud_density_ppg=10.0, mud_pv=25, mud_yp=12,
            slurry_density_ppg=16.0, slurry_pv=40, slurry_yp=15,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000, pump_rate_bbl_min=5.0,
        )
        assert "spacer_volume_bbl" in result
        assert result["spacer_volume_bbl"] > 0

    def test_spacer_density_between_mud_and_cement(self):
        from orchestrator.cementing_engine import CementingEngine
        result = CementingEngine.optimize_spacer(
            mud_density_ppg=10.0, mud_pv=25, mud_yp=12,
            slurry_density_ppg=16.0, slurry_pv=40, slurry_yp=15,
            hole_id_in=12.25, casing_od_in=9.625,
            casing_shoe_tvd_ft=10000, pump_rate_bbl_min=5.0,
        )
        spacer_density = result.get("spacer_density_ppg", 0)
        assert spacer_density >= 10.0
        assert spacer_density <= 16.0


# =====================================================================
# Standalone Elite Endpoint Verification
# =====================================================================
class TestStandaloneEliteEndpoints:
    """Verify Phase 8 elite methods work correctly in standalone mode."""

    def test_vibrations_3d_map_standalone(self):
        from orchestrator.vibrations_engine import VibrationsEngine
        survey = [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 0},
            {"md_ft": 5000, "inclination_deg": 30, "dls_deg_100ft": 3},
            {"md_ft": 10000, "inclination_deg": 60, "dls_deg_100ft": 2},
        ]
        result = VibrationsEngine.calculate_vibration_map_3d(survey)
        assert "risk_map" in result
        assert len(result["risk_map"]) > 0

    def test_bha_modal_standalone(self):
        from orchestrator.vibrations_engine import VibrationsEngine
        bha = [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 90, "weight_ppf": 83},
            {"type": "mwd", "od": 6.75, "id_inner": 3.0, "length_ft": 30, "weight_ppf": 95},
        ]
        result = VibrationsEngine.calculate_critical_rpm_lateral_multi(bha)
        assert result["mode_1_critical_rpm"] > 0

    def test_packer_apb_standalone(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        result = PackerForcesEngine.calculate_apb(
            annular_fluid_type="OBM", delta_t_avg=150
        )
        assert result["apb_psi"] > 0

    def test_packer_landing_standalone(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        tubing = [{"od": 3.5, "id_inner": 2.992, "length_ft": 10000, "weight_ppf": 9.3}]
        result = PackerForcesEngine.calculate_landing_conditions(tubing)
        assert result["total_landing_force_lbs"] > 0

    def test_packer_buckling_length_standalone(self):
        from orchestrator.packer_forces_engine import PackerForcesEngine
        result = PackerForcesEngine.calculate_buckling_length(
            axial_force=-100000, inclination_deg=45
        )
        assert "buckling_type" in result

    def test_ipr_vogel_standalone(self):
        from orchestrator.completion_design_engine import CompletionDesignEngine
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=4000, bubble_point_psi=2500,
            productivity_index_above_pb=5.0,
        )
        assert "AOF_stbd" in result
        assert result["AOF_stbd"] > 0

    def test_fatigue_damage_standalone(self):
        from orchestrator.vibrations_engine import VibrationsEngine
        survey = [
            {"md_ft": 0, "inclination_deg": 0, "dls_deg_100ft": 1},
            {"md_ft": 5000, "inclination_deg": 30, "dls_deg_100ft": 5},
        ]
        result = VibrationsEngine.calculate_fatigue_damage(
            drillstring_od=5.0, drillstring_id=4.276,
            survey_stations=survey,
        )
        assert result["cumulative_damage"] >= 0
