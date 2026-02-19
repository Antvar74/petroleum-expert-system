"""
Unit tests for CementingEngine -- cement job simulation.

Covers fluid volumes, displacement schedule, multi-fluid ECD,
free-fall, U-tube equilibrium, BHP schedule, lift pressure,
and full master method integration.
"""
import pytest
from orchestrator.cementing_engine import CementingEngine


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def engine():
    """Return CementingEngine class (all static methods)."""
    return CementingEngine


@pytest.fixture
def typical_casing():
    """Standard 9-5/8" casing in 12-1/4" hole."""
    return dict(
        casing_od_in=9.625,
        casing_id_in=8.681,
        hole_id_in=12.25,
    )


@pytest.fixture
def typical_depths():
    return dict(
        casing_shoe_md_ft=10000,
        casing_shoe_tvd_ft=9500,
        toc_md_ft=5000,
        toc_tvd_ft=4750,
        float_collar_md_ft=9900,
    )


@pytest.fixture
def typical_job():
    return dict(
        mud_weight_ppg=10.5,
        spacer_density_ppg=11.5,
        lead_cement_density_ppg=13.5,
        tail_cement_density_ppg=16.0,
        tail_length_ft=500,
        spacer_volume_bbl=25,
        excess_pct=50,
        rat_hole_ft=50,
        pump_rate_bbl_min=5.0,
        pv_mud=15,
        yp_mud=10,
        fracture_gradient_ppg=16.5,
        pore_pressure_ppg=9.0,
    )


# ===========================================================================
# 1. FLUID VOLUMES
# ===========================================================================
class TestFluidVolumes:
    def test_total_cement_positive(self, engine, typical_casing):
        result = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900,
        )
        assert result["total_cement_bbl"] > 0

    def test_lead_plus_tail_equals_total(self, engine, typical_casing):
        result = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900,
        )
        total = result["lead_cement_bbl"] + result["tail_cement_bbl"]
        assert total == pytest.approx(result["total_cement_bbl"], abs=0.1)

    def test_sack_counts_positive(self, engine, typical_casing):
        result = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900,
        )
        assert result["lead_cement_sacks"] > 0
        assert result["tail_cement_sacks"] > 0

    def test_more_excess_more_volume(self, engine, typical_casing):
        low = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900, excess_pct=10,
        )
        high = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900, excess_pct=100,
        )
        assert high["total_cement_bbl"] > low["total_cement_bbl"]

    def test_displacement_volume_positive(self, engine, typical_casing):
        result = engine.calculate_fluid_volumes(
            **typical_casing, casing_shoe_md_ft=10000, toc_md_ft=5000,
            float_collar_md_ft=9900,
        )
        assert result["displacement_volume_bbl"] > 0

    def test_invalid_geometry(self, engine):
        result = engine.calculate_fluid_volumes(
            casing_od_in=14.0, casing_id_in=12.0, hole_id_in=10.0,
            casing_shoe_md_ft=10000, toc_md_ft=5000, float_collar_md_ft=9900,
        )
        assert "error" in result


# ===========================================================================
# 2. DISPLACEMENT SCHEDULE
# ===========================================================================
class TestDisplacementSchedule:
    def test_schedule_has_points(self, engine):
        result = engine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_rate_bbl_min=5.0, num_points=20,
        )
        assert len(result["schedule"]) == 20

    def test_four_events(self, engine):
        result = engine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_rate_bbl_min=5.0,
        )
        events = result["events"]
        assert len(events) == 4

    def test_events_chronological(self, engine):
        result = engine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_rate_bbl_min=5.0,
        )
        for i in range(len(result["events"]) - 1):
            assert result["events"][i]["time_min"] <= result["events"][i + 1]["time_min"]

    def test_total_time_consistent(self, engine):
        result = engine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_rate_bbl_min=5.0,
        )
        expected = result["total_volume_bbl"] / result["pump_rate_bbl_min"]
        assert result["total_time_min"] == pytest.approx(expected, abs=0.2)

    def test_zero_pump_rate_error(self, engine):
        result = engine.calculate_displacement_schedule(
            spacer_volume_bbl=25, lead_cement_bbl=100,
            tail_cement_bbl=50, displacement_volume_bbl=200,
            pump_rate_bbl_min=0.0,
        )
        assert "error" in result

    def test_higher_rate_shorter_time(self, engine):
        common = dict(spacer_volume_bbl=25, lead_cement_bbl=100,
                      tail_cement_bbl=50, displacement_volume_bbl=200)
        slow = engine.calculate_displacement_schedule(**common, pump_rate_bbl_min=3.0)
        fast = engine.calculate_displacement_schedule(**common, pump_rate_bbl_min=6.0)
        assert fast["total_time_min"] < slow["total_time_min"]


# ===========================================================================
# 3. ECD DURING JOB
# ===========================================================================
class TestECDDuringJob:
    def test_snapshots_generated(self, engine, typical_casing):
        result = engine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=9500, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
        )
        assert len(result["snapshots"]) > 0

    def test_max_ecd_is_max(self, engine):
        result = engine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=9500, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
        )
        actual_max = max(s["ecd_ppg"] for s in result["snapshots"])
        assert result["max_ecd_ppg"] == pytest.approx(actual_max, abs=0.01)

    def test_heavier_cement_higher_ecd(self, engine):
        common = dict(
            casing_shoe_tvd_ft=9500, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            fracture_gradient_ppg=20.0, pore_pressure_ppg=9.0,
        )
        light = engine.calculate_ecd_during_job(
            **common, lead_cement_density_ppg=12.0, tail_cement_density_ppg=13.0)
        heavy = engine.calculate_ecd_during_job(
            **common, lead_cement_density_ppg=16.0, tail_cement_density_ppg=18.0)
        assert heavy["max_ecd_ppg"] > light["max_ecd_ppg"]

    def test_critical_status_when_exceeded(self, engine):
        result = engine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=9500, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=14.0, spacer_density_ppg=14.0,
            lead_cement_density_ppg=18.0, tail_cement_density_ppg=19.0,
            pump_rate_bbl_min=8.0, pv_mud=25, yp_mud=20,
            fracture_gradient_ppg=14.5, pore_pressure_ppg=9.0,
        )
        assert "CRITICAL" in result["status"]

    def test_ok_status_with_margin(self, engine):
        result = engine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=9500, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.0, spacer_density_ppg=10.5,
            lead_cement_density_ppg=12.0, tail_cement_density_ppg=13.0,
            pump_rate_bbl_min=3.0, fracture_gradient_ppg=20.0,
        )
        assert "OK" in result["status"]

    def test_zero_tvd_error(self, engine):
        result = engine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=0, hole_id_in=12.25, casing_od_in=9.625,
            mud_weight_ppg=10.0, spacer_density_ppg=11.0,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
        )
        assert "error" in result


# ===========================================================================
# 4. FREE-FALL
# ===========================================================================
class TestFreeFall:
    def test_height_non_negative(self, engine, typical_casing):
        result = engine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.5,
            cement_density_ppg=16.0,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["free_fall_height_ft"] >= 0

    def test_no_free_fall_equal_density(self, engine, typical_casing):
        result = engine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=12.0,
            cement_density_ppg=12.0,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["free_fall_height_ft"] == 0
        assert result["free_fall_occurs"] is False

    def test_no_free_fall_lighter_cement(self, engine):
        result = engine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=14.0,
            cement_density_ppg=12.0,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["free_fall_occurs"] is False

    def test_free_fall_heavier_cement_falls_more(self, engine):
        """Corrected model: heavier cement should free-fall further (more driving force).
        Unlike the old simplified model where density cancelled out."""
        common = dict(casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
                      casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625)
        light = engine.calculate_free_fall(**common, cement_density_ppg=12.0)
        heavy = engine.calculate_free_fall(**common, cement_density_ppg=18.0)
        assert heavy["free_fall_height_ft"] > light["free_fall_height_ft"]
        assert light["free_fall_occurs"] is True

    def test_gradients_correct(self, engine):
        result = engine.calculate_free_fall(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["cement_gradient_psi_ft"] == pytest.approx(16.0 * 0.052, abs=0.001)
        assert result["mud_gradient_psi_ft"] == pytest.approx(10.0 * 0.052, abs=0.001)


# ===========================================================================
# 5. U-TUBE
# ===========================================================================
class TestUTube:
    def test_no_utube_equal_density(self, engine, typical_casing):
        result = engine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=12.0,
            cement_density_ppg=12.0, cement_top_tvd_ft=5000,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["utube_occurs"] is False

    def test_utube_with_heavy_cement(self, engine):
        result = engine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0, cement_top_tvd_ft=4000,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["utube_occurs"] is True
        assert result["pressure_imbalance_psi"] > 0

    def test_fluid_drop_non_negative(self, engine):
        result = engine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0, cement_top_tvd_ft=5000,
            casing_id_in=8.681, hole_id_in=12.25, casing_od_in=9.625,
        )
        assert result["fluid_drop_ft"] >= 0
        assert result["fluid_drop_bbl"] >= 0

    def test_invalid_geometry_error(self, engine):
        result = engine.calculate_utube_effect(
            casing_shoe_tvd_ft=9500, mud_weight_ppg=10.0,
            cement_density_ppg=16.0, cement_top_tvd_ft=5000,
            casing_id_in=8.0, hole_id_in=8.0, casing_od_in=9.625,
        )
        assert "error" in result


# ===========================================================================
# 6. BHP SCHEDULE
# ===========================================================================
class TestBHPSchedule:
    def test_schedule_has_points(self, engine, typical_casing):
        result = engine.calculate_bhp_schedule(
            casing_shoe_tvd_ft=9500,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
            spacer_volume_bbl=25, lead_cement_bbl=200,
            tail_cement_bbl=100, displacement_volume_bbl=500,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
            num_points=15,
        )
        assert len(result["bhp_schedule"]) == 15

    def test_max_bhp_is_max(self, engine, typical_casing):
        result = engine.calculate_bhp_schedule(
            casing_shoe_tvd_ft=9500,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
            spacer_volume_bbl=25, lead_cement_bbl=200,
            tail_cement_bbl=100, displacement_volume_bbl=500,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
        )
        actual_max = max(p["bhp_psi"] for p in result["bhp_schedule"])
        assert result["max_bhp_psi"] == pytest.approx(actual_max, abs=1.0)

    def test_zero_tvd_error(self, engine):
        result = engine.calculate_bhp_schedule(
            casing_shoe_tvd_ft=0,
            mud_weight_ppg=10.5, spacer_density_ppg=11.5,
            lead_cement_density_ppg=13.5, tail_cement_density_ppg=16.0,
            spacer_volume_bbl=25, lead_cement_bbl=200,
            tail_cement_bbl=100, displacement_volume_bbl=500,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert "error" in result


# ===========================================================================
# 7. LIFT PRESSURE
# ===========================================================================
class TestLiftPressure:
    def test_positive_when_cement_heavier(self, engine, typical_casing):
        result = engine.calculate_lift_pressure(
            casing_shoe_tvd_ft=9500, toc_tvd_ft=4750,
            cement_density_ppg=16.0, mud_weight_ppg=10.5,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert result["lift_pressure_psi"] > 0

    def test_non_negative_always(self, engine, typical_casing):
        result = engine.calculate_lift_pressure(
            casing_shoe_tvd_ft=9500, toc_tvd_ft=4750,
            cement_density_ppg=8.0, mud_weight_ppg=12.0,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert result["lift_pressure_psi"] >= 0

    def test_toc_at_shoe_zero(self, engine):
        result = engine.calculate_lift_pressure(
            casing_shoe_tvd_ft=9500, toc_tvd_ft=9500,
            cement_density_ppg=16.0, mud_weight_ppg=10.5,
            hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681,
        )
        assert result["lift_pressure_psi"] == 0

    def test_higher_friction_more_lift(self, engine):
        common = dict(casing_shoe_tvd_ft=9500, toc_tvd_ft=4750,
                      cement_density_ppg=16.0, mud_weight_ppg=10.5,
                      hole_id_in=12.25, casing_od_in=9.625, casing_id_in=8.681)
        low = engine.calculate_lift_pressure(**common, friction_factor=0.5)
        high = engine.calculate_lift_pressure(**common, friction_factor=2.0)
        assert high["lift_pressure_psi"] > low["lift_pressure_psi"]


# ===========================================================================
# 8. FULL CEMENTING MASTER METHOD
# ===========================================================================
class TestFullCementing:
    def test_all_keys_present(self, engine):
        result = engine.calculate_full_cementing()
        expected = {"volumes", "displacement", "ecd_during_job",
                    "free_fall", "utube", "bhp_schedule",
                    "lift_pressure", "summary"}
        assert expected.issubset(result.keys())

    def test_summary_fields(self, engine):
        result = engine.calculate_full_cementing()
        s = result["summary"]
        for key in ["total_cement_bbl", "total_cement_sacks", "job_time_hrs",
                     "max_ecd_ppg", "fracture_margin_ppg", "max_bhp_psi",
                     "lift_pressure_psi", "free_fall_ft", "utube_psi",
                     "ecd_status", "alerts"]:
            assert key in s, f"Missing summary key: {key}"

    def test_alerts_is_list(self, engine):
        result = engine.calculate_full_cementing()
        assert isinstance(result["summary"]["alerts"], list)

    def test_sub_results_are_dicts(self, engine):
        result = engine.calculate_full_cementing()
        for key in ["volumes", "displacement", "ecd_during_job",
                     "free_fall", "utube", "bhp_schedule", "lift_pressure"]:
            assert isinstance(result[key], dict)
            assert "error" not in result[key]

    def test_invalid_geometry_propagates(self, engine):
        result = engine.calculate_full_cementing(
            casing_od_in=14.0, casing_id_in=12.0, hole_id_in=10.0)
        assert "error" in result

    def test_summary_cement_bbl_matches_volumes(self, engine):
        result = engine.calculate_full_cementing()
        assert result["summary"]["total_cement_bbl"] == result["volumes"]["total_cement_bbl"]
