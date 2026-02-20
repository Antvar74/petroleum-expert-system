"""
Unit tests for WorkoverHydraulicsEngine.
Tests: ct_dimensions, ct_pressure_loss, ct_buoyed_weight, ct_drag,
       snubbing_force, max_reach, workover_kill, full_workover, physical_invariants.
"""
import math
import pytest
from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine


# ============================================================
# Shared fixture: typical 2" CT job parameters
# ============================================================

@pytest.fixture
def typical_ct_params():
    """Typical 2" CT job in a 7" cased hole."""
    return {
        "ct_od": 2.0,
        "wall_thickness": 0.156,
        "ct_id": 2.0 - 2 * 0.156,       # 1.688"
        "ct_length": 15000.0,
        "hole_id": 6.276,                 # 7" csg inner diameter
        "flow_rate": 80.0,                # gpm (~1.9 bpm)
        "mud_weight": 9.5,
        "pv": 12.0,
        "yp": 8.0,
        "tvd": 10000.0,
        "inclination": 30.0,
        "friction_factor": 0.25,
        "wellhead_pressure": 1500.0,
        "reservoir_pressure": 5200.0,
        "yield_strength_psi": 80000.0,
    }


# ============================================================
# calculate_ct_dimensions (3 tests)
# ============================================================

class TestCTDimensions:

    def test_valid_dimensions(self):
        """2.0" OD, 0.156" wall -> ID = 1.688", positive areas and weight."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 0.156)
        assert dims["ct_id_in"] == pytest.approx(1.688, abs=0.001)
        assert dims["metal_area_in2"] > 0
        assert dims["weight_per_ft_lb"] > 0

    def test_zero_wall_returns_error(self):
        """Wall thickness that makes ID <= 0 should return error."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 1.0)
        assert "error" in dims

    def test_expected_weight_2inch(self):
        """2" OD, 0.156" wall CT weighs roughly 2-4 lb/ft (known range)."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 0.156)
        assert 2.0 < dims["weight_per_ft_lb"] < 4.0


# ============================================================
# calculate_ct_pressure_loss (4 tests)
# ============================================================

class TestCTPressureLoss:

    def test_typical_flow(self, typical_ct_params):
        """Typical CT pumping produces non-trivial pressure losses."""
        p = typical_ct_params
        result = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
            p["flow_rate"], p["mud_weight"], p["pv"], p["yp"],
            p["ct_od"], p["ct_id"], p["ct_length"],
            p["hole_id"], p["ct_length"]
        )
        assert result["pipe_loss_psi"] > 0
        assert result["annular_loss_psi"] > 0
        assert result["total_loss_psi"] == pytest.approx(
            result["pipe_loss_psi"] + result["annular_loss_psi"], abs=0.2
        )

    def test_zero_flow_rate(self, typical_ct_params):
        """Zero flow rate should give zero pressure losses."""
        p = typical_ct_params
        result = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
            0.0, p["mud_weight"], p["pv"], p["yp"],
            p["ct_od"], p["ct_id"], p["ct_length"],
            p["hole_id"], p["ct_length"]
        )
        assert result["pipe_loss_psi"] == 0.0
        assert result["annular_loss_psi"] == 0.0
        assert result["total_loss_psi"] == 0.0

    def test_high_flow_rate(self, typical_ct_params):
        """High flow rate should produce substantially higher losses."""
        p = typical_ct_params
        low = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
            40.0, p["mud_weight"], p["pv"], p["yp"],
            p["ct_od"], p["ct_id"], p["ct_length"],
            p["hole_id"], p["ct_length"]
        )
        high = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
            160.0, p["mud_weight"], p["pv"], p["yp"],
            p["ct_od"], p["ct_id"], p["ct_length"],
            p["hole_id"], p["ct_length"]
        )
        assert high["total_loss_psi"] > low["total_loss_psi"]

    def test_pipe_loss_exceeds_annular(self, typical_ct_params):
        """In small CT, pipe losses dominate over annular losses."""
        p = typical_ct_params
        result = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
            p["flow_rate"], p["mud_weight"], p["pv"], p["yp"],
            p["ct_od"], p["ct_id"], p["ct_length"],
            p["hole_id"], p["ct_length"]
        )
        assert result["pipe_loss_psi"] > result["annular_loss_psi"]


# ============================================================
# calculate_ct_buoyed_weight (3 tests)
# ============================================================

class TestCTBuoyedWeight:

    def test_vertical_well(self):
        """Vertical well (0 deg): axial component equals full buoyed weight."""
        result = WorkoverHydraulicsEngine.calculate_ct_buoyed_weight(
            weight_per_ft=3.0, length=10000.0, mud_weight=10.0, inclination=0.0
        )
        assert result["buoyed_weight_lb"] > 0
        assert result["axial_component_lb"] == pytest.approx(
            result["buoyed_weight_lb"], abs=1.0
        )

    def test_inclined_well(self):
        """At 60 deg inclination, axial component should be ~50% of buoyed weight."""
        result = WorkoverHydraulicsEngine.calculate_ct_buoyed_weight(
            weight_per_ft=3.0, length=10000.0, mud_weight=10.0, inclination=60.0
        )
        expected_axial = result["buoyed_weight_lb"] * math.cos(math.radians(60.0))
        assert result["axial_component_lb"] == pytest.approx(expected_axial, abs=1.0)

    def test_zero_length(self):
        """Zero CT length gives zero weight."""
        result = WorkoverHydraulicsEngine.calculate_ct_buoyed_weight(
            weight_per_ft=3.0, length=0.0, mud_weight=10.0, inclination=0.0
        )
        assert result["buoyed_weight_lb"] == 0.0
        assert result["air_weight_lb"] == 0.0


# ============================================================
# calculate_ct_drag (3 tests)
# ============================================================

class TestCTDrag:

    def test_vertical_no_drag(self):
        """Vertical well (0 deg) -> sin(0) = 0 -> no drag force."""
        result = WorkoverHydraulicsEngine.calculate_ct_drag(
            buoyed_weight=25000.0, inclination=0.0, friction_factor=0.25
        )
        assert result["drag_force_lb"] == 0.0
        assert result["normal_force_lb"] == 0.0

    def test_horizontal_max_drag(self):
        """Horizontal (90 deg) -> sin(90)=1 -> maximum normal force."""
        result = WorkoverHydraulicsEngine.calculate_ct_drag(
            buoyed_weight=25000.0, inclination=90.0, friction_factor=0.25
        )
        assert result["normal_force_lb"] == pytest.approx(25000.0, abs=1.0)
        assert result["drag_force_lb"] == pytest.approx(0.25 * 25000.0, abs=1.0)

    def test_friction_factor_scales_drag(self):
        """Higher friction factor linearly increases drag."""
        low_mu = WorkoverHydraulicsEngine.calculate_ct_drag(
            buoyed_weight=20000.0, inclination=45.0, friction_factor=0.15
        )
        high_mu = WorkoverHydraulicsEngine.calculate_ct_drag(
            buoyed_weight=20000.0, inclination=45.0, friction_factor=0.35
        )
        ratio = high_mu["drag_force_lb"] / max(low_mu["drag_force_lb"], 1.0)
        assert ratio == pytest.approx(0.35 / 0.15, abs=0.05)


# ============================================================
# calculate_snubbing_force (4 tests)
# ============================================================

class TestSnubbingForce:

    def test_pipe_heavy_no_snubbing(self):
        """Heavy pipe in hole with low WHP -> pipe heavy (no snubbing needed)."""
        result = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=200.0,
            ct_od=2.0,
            buoyed_weight=25000.0,
            ct_length_in_hole=10000.0,
            weight_per_ft=3.0,
            mud_weight=10.0
        )
        assert result["pipe_light"] is False
        assert result["snubbing_force_lb"] < 0

    def test_pipe_light(self):
        """High WHP with little pipe in hole -> pipe light (must snub in)."""
        result = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=5000.0,
            ct_od=2.0,
            buoyed_weight=500.0,
            ct_length_in_hole=200.0,
            weight_per_ft=3.0,
            mud_weight=10.0
        )
        assert result["pipe_light"] is True
        assert result["snubbing_force_lb"] > 0

    def test_light_heavy_point(self):
        """Light/heavy depth should be positive when pressure and weight exist."""
        result = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=2000.0,
            ct_od=2.0,
            buoyed_weight=10000.0,
            ct_length_in_hole=5000.0,
            weight_per_ft=3.0,
            mud_weight=10.0
        )
        assert result["light_heavy_depth_ft"] > 0

    def test_zero_pressure(self):
        """Zero WHP -> pressure force is zero, pipe is always heavy."""
        result = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=0.0,
            ct_od=2.0,
            buoyed_weight=20000.0,
            ct_length_in_hole=8000.0,
            weight_per_ft=3.0,
            mud_weight=10.0
        )
        assert result["pipe_light"] is False
        assert result["pressure_force_lb"] == 0.0


# ============================================================
# calculate_max_reach (3 tests)
# ============================================================

class TestMaxReach:

    def test_vertical_unlimited(self):
        """Near-vertical well should yield very large (capped) max reach."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 0.156)
        result = WorkoverHydraulicsEngine.calculate_max_reach(
            ct_od=2.0, ct_id=dims["ct_id_in"], wall_thickness=0.156,
            weight_per_ft=dims["weight_per_ft_lb"], mud_weight=9.5,
            inclination=0.0, friction_factor=0.25
        )
        # Vertical should hit the practical cap (35000 ft) or near it
        assert result["max_reach_ft"] >= 30000.0

    def test_horizontal_limited(self):
        """Horizontal well should have a finite, significantly lower max reach."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 0.156)
        vert = WorkoverHydraulicsEngine.calculate_max_reach(
            ct_od=2.0, ct_id=dims["ct_id_in"], wall_thickness=0.156,
            weight_per_ft=dims["weight_per_ft_lb"], mud_weight=9.5,
            inclination=0.0, friction_factor=0.25
        )
        horiz = WorkoverHydraulicsEngine.calculate_max_reach(
            ct_od=2.0, ct_id=dims["ct_id_in"], wall_thickness=0.156,
            weight_per_ft=dims["weight_per_ft_lb"], mud_weight=9.5,
            inclination=90.0, friction_factor=0.25
        )
        assert horiz["max_reach_ft"] < vert["max_reach_ft"]

    def test_yield_limit(self):
        """Very low yield strength should make yield the limiting factor."""
        dims = WorkoverHydraulicsEngine.calculate_ct_dimensions(2.0, 0.156)
        result = WorkoverHydraulicsEngine.calculate_max_reach(
            ct_od=2.0, ct_id=dims["ct_id_in"], wall_thickness=0.156,
            weight_per_ft=dims["weight_per_ft_lb"], mud_weight=9.5,
            inclination=60.0, friction_factor=0.25,
            yield_strength_psi=1000.0  # unrealistically low → F_yield < F_hb
        )
        assert result["limiting_factor"] == "CT Yield Strength"


# ============================================================
# calculate_workover_kill (3 tests)
# ============================================================

class TestWorkoverKill:

    def test_underbalanced(self):
        """Current mud too light for reservoir pressure -> UNDERBALANCED."""
        result = WorkoverHydraulicsEngine.calculate_workover_kill(
            reservoir_pressure=6000.0,
            tvd=10000.0,
            current_mud_weight=9.0,
            safety_margin_ppg=0.3
        )
        assert "UNDERBALANCED" in result["status"]
        assert result["kill_weight_ppg"] > 9.0

    def test_overbalanced(self):
        """Heavy mud overbalances the reservoir."""
        result = WorkoverHydraulicsEngine.calculate_workover_kill(
            reservoir_pressure=3000.0,
            tvd=10000.0,
            current_mud_weight=12.0,
            safety_margin_ppg=0.3
        )
        assert result["status"] == "Overbalanced"
        assert result["current_bhp_psi"] > result["reservoir_pressure_psi"]

    def test_zero_tvd(self):
        """Zero TVD is invalid and should return error status."""
        result = WorkoverHydraulicsEngine.calculate_workover_kill(
            reservoir_pressure=5000.0,
            tvd=0.0,
            current_mud_weight=10.0
        )
        assert "Error" in result["status"]


# ============================================================
# calculate_full_workover (4 tests)
# ============================================================

class TestFullWorkover:

    def test_returns_all_keys(self, typical_ct_params):
        """Full calculation should return all top-level sections."""
        p = typical_ct_params
        result = WorkoverHydraulicsEngine.calculate_full_workover(
            flow_rate=p["flow_rate"], mud_weight=p["mud_weight"],
            pv=p["pv"], yp=p["yp"], ct_od=p["ct_od"],
            wall_thickness=p["wall_thickness"], ct_length=p["ct_length"],
            hole_id=p["hole_id"], tvd=p["tvd"],
            inclination=p["inclination"],
            friction_factor=p["friction_factor"],
            wellhead_pressure=p["wellhead_pressure"],
            reservoir_pressure=p["reservoir_pressure"],
            yield_strength_psi=p["yield_strength_psi"]
        )
        for key in ["summary", "hydraulics", "ct_dimensions", "weight_analysis",
                     "drag_analysis", "snubbing", "max_reach", "kill_data",
                     "parameters", "alerts"]:
            assert key in result, f"Missing key: {key}"

    def test_alerts_generated(self):
        """Extreme parameters should trigger at least one alert."""
        result = WorkoverHydraulicsEngine.calculate_full_workover(
            flow_rate=160.0, mud_weight=9.0, pv=10.0, yp=6.0,
            ct_od=1.5, wall_thickness=0.109, ct_length=25000.0,
            hole_id=4.892, tvd=12000.0, inclination=60.0,
            friction_factor=0.35, wellhead_pressure=3000.0,
            reservoir_pressure=8000.0, yield_strength_psi=70000.0
        )
        assert len(result["alerts"]) > 0

    def test_pipe_light_scenario(self):
        """High WHP with short CT should flag pipe-light condition."""
        result = WorkoverHydraulicsEngine.calculate_full_workover(
            flow_rate=60.0, mud_weight=8.6, pv=10.0, yp=5.0,
            ct_od=2.0, wall_thickness=0.156, ct_length=500.0,
            hole_id=6.276, tvd=500.0, inclination=0.0,
            friction_factor=0.25, wellhead_pressure=5000.0,
            reservoir_pressure=3000.0
        )
        assert result["summary"]["pipe_light"] is True
        snub_alerts = [a for a in result["alerts"] if "pipe-light" in a.lower() or "snubbing" in a.lower()]
        assert len(snub_alerts) > 0

    def test_typical_ct_job(self, typical_ct_params):
        """A typical CT job should produce physically reasonable results."""
        p = typical_ct_params
        result = WorkoverHydraulicsEngine.calculate_full_workover(
            flow_rate=p["flow_rate"], mud_weight=p["mud_weight"],
            pv=p["pv"], yp=p["yp"], ct_od=p["ct_od"],
            wall_thickness=p["wall_thickness"], ct_length=p["ct_length"],
            hole_id=p["hole_id"], tvd=p["tvd"],
            inclination=p["inclination"],
            friction_factor=p["friction_factor"],
            wellhead_pressure=p["wellhead_pressure"],
            reservoir_pressure=p["reservoir_pressure"],
            yield_strength_psi=p["yield_strength_psi"]
        )
        summary = result["summary"]
        assert summary["total_pressure_loss_psi"] > 0
        assert summary["buoyed_weight_lb"] > 0
        assert summary["max_reach_ft"] > 0
        assert summary["kill_weight_ppg"] > 0


# ============================================================
# Physical Invariants (3 tests)
# ============================================================

class TestPhysicalInvariants:

    def test_buoyancy_factor_between_0_and_1(self):
        """Buoyancy factor must be in [0, 1] for any realistic fluid."""
        for mw in [7.0, 9.5, 12.0, 16.0, 20.0]:
            result = WorkoverHydraulicsEngine.calculate_ct_buoyed_weight(
                weight_per_ft=3.0, length=10000.0, mud_weight=mw
            )
            bf = result["buoyancy_factor"]
            assert 0.0 <= bf <= 1.0, f"BF out of range for mw={mw}: {bf}"

    def test_pressure_loss_always_non_negative(self):
        """Pressure losses must never be negative for any positive flow."""
        for q in [10.0, 50.0, 100.0, 200.0]:
            result = WorkoverHydraulicsEngine.calculate_ct_pressure_loss(
                flow_rate=q, mud_weight=10.0, pv=15.0, yp=10.0,
                ct_od=2.0, ct_id=1.688, ct_length=10000.0,
                hole_id=6.276, annular_length=10000.0
            )
            assert result["pipe_loss_psi"] >= 0, f"Negative pipe loss at q={q}"
            assert result["annular_loss_psi"] >= 0, f"Negative annular loss at q={q}"
            assert result["total_loss_psi"] >= 0, f"Negative total loss at q={q}"
            assert result["pipe_loss_psi"] < 10000, f"Unrealistic pipe loss at q={q}: {result['pipe_loss_psi']}"
            assert result["annular_loss_psi"] < 5000, f"Unrealistic annular loss at q={q}: {result['annular_loss_psi']}"

    def test_snubbing_force_sign(self):
        """Snubbing force positive when pipe light, negative when pipe heavy."""
        # Pipe light case: high pressure, small weight
        light = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=5000.0, ct_od=2.0,
            buoyed_weight=500.0, ct_length_in_hole=200.0,
            weight_per_ft=3.0, mud_weight=10.0
        )
        assert light["snubbing_force_lb"] > 0
        assert light["pipe_light"] is True

        # Pipe heavy case: low pressure, large weight
        heavy = WorkoverHydraulicsEngine.calculate_snubbing_force(
            wellhead_pressure=100.0, ct_od=2.0,
            buoyed_weight=30000.0, ct_length_in_hole=12000.0,
            weight_per_ft=3.0, mud_weight=10.0
        )
        assert heavy["snubbing_force_lb"] < 0
        assert heavy["pipe_light"] is False
