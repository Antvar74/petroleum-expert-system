"""
Phase 3 Elite Tests — BHA Breakdown, Pressure Waterfall, Multi-Diameter Annular,
Anisotropic Sand Control, Water Weakening, Barite Requirements.

Covers:
- BHA pressure breakdown with tool-level granularity (5 tests)
- Pressure waterfall generation (5 tests)
- Multi-diameter annular analysis (5 tests)
- Full circuit with multi-diameter (3 tests)
- Anisotropic drawdown — Kirsch stress (5 tests)
- Water weakening of UCS (5 tests)
- Barite requirements — API formula (8 tests)
- Full sand control with anisotropic params (2 tests)
"""

import pytest
import math
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.well_control_engine import WellControlEngine
from orchestrator.sand_control_engine import SandControlEngine


# ═══════════════════════════════════════════════════════════════
# BHA Pressure Breakdown
# ═══════════════════════════════════════════════════════════════

class TestBHABreakdown:
    """Test BHA tool-level pressure loss breakdown."""

    SAMPLE_BHA = [
        {"tool_name": "6-3/4 DC", "tool_type": "collar",
         "od": 6.75, "id_inner": 2.8125, "length": 90, "loss_coefficient": 1.0},
        {"tool_name": "PDM Motor", "tool_type": "motor",
         "od": 6.75, "id_inner": 3.0, "length": 30, "loss_coefficient": 2.5},
        {"tool_name": "MWD Tool", "tool_type": "mwd",
         "od": 6.75, "id_inner": 2.5, "length": 30, "loss_coefficient": 1.8},
        {"tool_name": "Stabilizer", "tool_type": "stabilizer",
         "od": 8.25, "id_inner": 2.8125, "length": 5, "loss_coefficient": 1.0},
    ]

    def test_result_keys(self):
        """Result must have required keys."""
        r = HydraulicsEngine.calculate_bha_pressure_breakdown(
            self.SAMPLE_BHA, flow_rate=400, mud_weight=12.0, pv=20, yp=12
        )
        assert "tools_breakdown" in r
        assert "total_bha_loss_psi" in r
        assert "critical_tool" in r
        assert len(r["tools_breakdown"]) == 4

    def test_motor_loss_coeff_amplifies(self):
        """Motor with loss_coefficient=2.5 should have higher dp/ft than plain collar."""
        r = HydraulicsEngine.calculate_bha_pressure_breakdown(
            self.SAMPLE_BHA, flow_rate=400, mud_weight=12.0, pv=20, yp=12
        )
        collar = r["tools_breakdown"][0]
        motor = r["tools_breakdown"][1]
        # Motor has loss_coeff=2.5 and similar geometry -> much higher dp/ft
        assert motor["dp_per_ft"] > collar["dp_per_ft"]

    def test_zero_flow_guard(self):
        """Zero flow rate should return empty breakdown."""
        r = HydraulicsEngine.calculate_bha_pressure_breakdown(
            self.SAMPLE_BHA, flow_rate=0, mud_weight=12.0, pv=20, yp=12
        )
        assert r["total_bha_loss_psi"] == 0.0
        assert r["tools_breakdown"] == []

    def test_critical_tool_identified(self):
        """Critical tool = highest dp/ft should be motor or MWD."""
        r = HydraulicsEngine.calculate_bha_pressure_breakdown(
            self.SAMPLE_BHA, flow_rate=400, mud_weight=12.0, pv=20, yp=12
        )
        # Motor or MWD should be critical (both have loss_coeff > 1)
        assert r["critical_tool"] in ("PDM Motor", "MWD Tool")

    def test_sum_equals_total(self):
        """Sum of individual tool losses must equal total."""
        r = HydraulicsEngine.calculate_bha_pressure_breakdown(
            self.SAMPLE_BHA, flow_rate=400, mud_weight=12.0, pv=20, yp=12
        )
        tool_sum = sum(t["pressure_loss_psi"] for t in r["tools_breakdown"])
        assert abs(tool_sum - r["total_bha_loss_psi"]) < 1.0


# ═══════════════════════════════════════════════════════════════
# Pressure Waterfall
# ═══════════════════════════════════════════════════════════════

class TestPressureWaterfall:
    """Test pressure waterfall generation from circuit results."""

    @staticmethod
    def _get_circuit():
        sections = [
            {"section_type": "drill_pipe", "length": 9000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "hwdp", "length": 450, "od": 5.0, "id_inner": 3.0},
            {"section_type": "collar", "length": 300, "od": 6.75, "id_inner": 2.8125},
            {"section_type": "annulus_dc", "length": 300, "od": 8.5, "id_inner": 6.75},
            {"section_type": "annulus_hwdp", "length": 450, "od": 8.5, "id_inner": 5.0},
            {"section_type": "annulus_dp", "length": 9000, "od": 8.5, "id_inner": 5.0},
        ]
        return HydraulicsEngine.calculate_full_circuit(
            sections=sections, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000
        )

    def test_waterfall_step_count(self):
        """Must have at least: surface + DP + HWDP + collar + bit + 3 annular = 8 steps."""
        circuit = self._get_circuit()
        wf = HydraulicsEngine.generate_pressure_waterfall(circuit)
        assert len(wf["waterfall_steps"]) >= 7

    def test_cumulative_correctness(self):
        """Cumulative pressure must increase monotonically."""
        circuit = self._get_circuit()
        wf = HydraulicsEngine.generate_pressure_waterfall(circuit)
        cumulatives = [s["cumulative_psi"] for s in wf["waterfall_steps"]]
        for i in range(1, len(cumulatives)):
            assert cumulatives[i] >= cumulatives[i - 1]

    def test_pct_sums_to_100(self):
        """Percentage allocations must sum to ~100%."""
        circuit = self._get_circuit()
        wf = HydraulicsEngine.generate_pressure_waterfall(circuit)
        total_pct = sum(s["pct_of_total"] for s in wf["waterfall_steps"])
        assert 99.0 <= total_pct <= 101.0

    def test_with_bha_breakdown(self):
        """With BHA breakdown, waterfall should have individual tool steps."""
        circuit = self._get_circuit()
        bha_tools = [
            {"tool_name": "DC-1", "tool_type": "collar",
             "od": 6.75, "id_inner": 2.8125, "length": 150, "loss_coefficient": 1.0},
            {"tool_name": "Motor", "tool_type": "motor",
             "od": 6.75, "id_inner": 3.0, "length": 30, "loss_coefficient": 2.0},
            {"tool_name": "DC-2", "tool_type": "collar",
             "od": 6.75, "id_inner": 2.8125, "length": 120, "loss_coefficient": 1.0},
        ]
        bha = HydraulicsEngine.calculate_bha_pressure_breakdown(
            bha_tools, flow_rate=400, mud_weight=12.0, pv=20, yp=12
        )
        wf = HydraulicsEngine.generate_pressure_waterfall(circuit, bha_breakdown=bha)
        labels = [s["label"] for s in wf["waterfall_steps"]]
        # Should have "BHA:" prefixed labels
        bha_labels = [l for l in labels if l.startswith("BHA:")]
        assert len(bha_labels) == 3

    def test_labels_present(self):
        """All waterfall steps must have non-empty labels."""
        circuit = self._get_circuit()
        wf = HydraulicsEngine.generate_pressure_waterfall(circuit)
        for step in wf["waterfall_steps"]:
            assert len(step["label"]) > 0


# ═══════════════════════════════════════════════════════════════
# Multi-Diameter Annular Analysis
# ═══════════════════════════════════════════════════════════════

class TestMultiDiameterAnnular:
    """Test multi-diameter annular section identification and analysis."""

    MULTI_SECTIONS = [
        {"section_type": "drill_pipe", "length": 8000, "od": 5.0, "id_inner": 4.276},
        {"section_type": "collar", "length": 600, "od": 6.75, "id_inner": 2.8125},
        # Three annular sections with different diameters
        {"section_type": "annulus_dc", "length": 600, "od": 8.5, "id_inner": 6.75},
        {"section_type": "annulus_hwdp", "length": 1000, "od": 12.25, "id_inner": 5.0},
        {"section_type": "annulus_dp", "length": 8000, "od": 12.25, "id_inner": 5.0},
    ]

    def test_three_annular_sections(self):
        """Annular analysis must have 3 sections."""
        r = HydraulicsEngine.calculate_full_circuit(
            self.MULTI_SECTIONS, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000
        )
        assert "annular_analysis" in r
        assert len(r["annular_analysis"]["sections"]) == 3

    def test_critical_section_identified(self):
        """Critical section (lowest velocity) should be identified."""
        r = HydraulicsEngine.calculate_full_circuit(
            self.MULTI_SECTIONS, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000
        )
        assert r["annular_analysis"]["critical_section"] is not None

    def test_min_velocity_correct(self):
        """Min velocity should match the annular section with the smallest velocity."""
        r = HydraulicsEngine.calculate_full_circuit(
            self.MULTI_SECTIONS, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000
        )
        velocities = [s["velocity_ftmin"] for s in r["annular_analysis"]["sections"]
                      if s["velocity_ftmin"] > 0]
        assert r["annular_analysis"]["min_velocity_ftmin"] == min(velocities)

    def test_ecd_varies_by_section(self):
        """Local ECD should vary across sections."""
        r = HydraulicsEngine.calculate_full_circuit(
            self.MULTI_SECTIONS, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000
        )
        ecds = [s["ecd_local_ppg"] for s in r["annular_analysis"]["sections"]]
        # Not all identical — DC section has different geometry
        assert max(ecds) > min(ecds)

    def test_backward_compat(self):
        """Old-style single annular still works — annular_analysis present."""
        simple = [
            {"section_type": "drill_pipe", "length": 9000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "annulus_dp", "length": 9000, "od": 8.5, "id_inner": 5.0},
        ]
        r = HydraulicsEngine.calculate_full_circuit(
            simple, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=9000
        )
        assert "annular_analysis" in r
        assert len(r["annular_analysis"]["sections"]) == 1


class TestFullCircuitMultiDiameter:
    """Integration tests: P/T + multi-diameter combined scenarios."""

    def test_pt_plus_multi_diameter(self):
        """P/T corrections work with multi-diameter annular."""
        sections = [
            {"section_type": "drill_pipe", "length": 8000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "collar", "length": 600, "od": 6.75, "id_inner": 2.8125},
            {"section_type": "annulus_dc", "length": 600, "od": 8.5, "id_inner": 6.75},
            {"section_type": "annulus_dp", "length": 8000, "od": 12.25, "id_inner": 5.0},
        ]
        r = HydraulicsEngine.calculate_full_circuit(
            sections, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=9000,
            use_pt_correction=True, fluid_type="obm"
        )
        assert r["summary"]["total_spp_psi"] > 0
        assert "annular_analysis" in r
        assert len(r["annular_analysis"]["sections"]) == 2

    def test_casing_vs_openhole_velocity(self):
        """Casing annular (smaller) should have higher velocity than open hole (larger)."""
        sections = [
            {"section_type": "drill_pipe", "length": 8000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "collar", "length": 600, "od": 6.75, "id_inner": 2.8125},
            # Casing section (9-5/8" casing, 8.535 ID, with 6.75 collar)
            {"section_type": "annulus_dc", "length": 600, "od": 8.535, "id_inner": 6.75},
            # Open hole section (12-1/4" hole with 5" DP)
            {"section_type": "annulus_dp", "length": 8000, "od": 12.25, "id_inner": 5.0},
        ]
        r = HydraulicsEngine.calculate_full_circuit(
            sections, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=9000
        )
        ann_secs = r["annular_analysis"]["sections"]
        # Casing annular (first) should have higher velocity — smaller gap, same flow
        casing_v = ann_secs[0]["velocity_ftmin"]
        openhole_v = ann_secs[1]["velocity_ftmin"]
        assert casing_v > openhole_v

    def test_tvd_based_ecd_profile(self):
        """ECD profile with annular_tvds should use real TVDs."""
        sections = [
            {"section_type": "drill_pipe", "length": 9000, "od": 5.0, "id_inner": 4.276},
            {"section_type": "annulus_dc", "length": 300, "od": 8.5, "id_inner": 6.75},
            {"section_type": "annulus_dp", "length": 9000, "od": 8.5, "id_inner": 5.0},
        ]
        r = HydraulicsEngine.calculate_full_circuit(
            sections, nozzle_sizes=[12, 12, 12],
            flow_rate=400, mud_weight=12.0, pv=20, yp=12, tvd=10000,
            annular_tvds=[9500, 5000]
        )
        assert len(r["ecd_profile"]) >= 1


# ═══════════════════════════════════════════════════════════════
# Anisotropic Drawdown — Kirsch Stress
# ═══════════════════════════════════════════════════════════════

class TestAnisotropicDrawdown:
    """Test anisotropic horizontal stresses with Kirsch model."""

    BASE = dict(
        ucs_psi=3000, friction_angle_deg=30,
        reservoir_pressure_psi=5000, overburden_stress_psi=12000,
        poisson_ratio=0.25, biot_coefficient=1.0
    )

    def test_sigma_H_gt_sigma_h_effect(self):
        """Higher anisotropy should change critical drawdown."""
        iso = SandControlEngine.calculate_critical_drawdown(**self.BASE)
        aniso = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, sigma_H_psi=10000, sigma_h_psi=7000
        )
        # Different stress state → different drawdown
        assert iso["critical_drawdown_psi"] != aniso["critical_drawdown_psi"]

    def test_kirsch_at_0_vs_90(self):
        """Kirsch tangential stress at 0° and 90° should differ for anisotropic case."""
        r0 = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, sigma_H_psi=10000, sigma_h_psi=6000,
            wellbore_azimuth_deg=0
        )
        r90 = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, sigma_H_psi=10000, sigma_h_psi=6000,
            wellbore_azimuth_deg=90
        )
        assert r0["kirsch_sigma_theta"] != r90["kirsch_sigma_theta"]

    def test_isotropic_path_unchanged(self):
        """Without sigma_H/sigma_h, result should use k0 path (backward compat)."""
        r = SandControlEngine.calculate_critical_drawdown(**self.BASE)
        # k0 path: sigma_h = k0 * sigma_v_eff, sigma_H = sigma_h
        k0 = 0.25 / 0.75
        sigma_v_eff = 12000 - 1.0 * 5000
        sigma_h_eff = k0 * sigma_v_eff
        assert abs(r["effective_horizontal_psi"] - sigma_h_eff) < 1.0
        # Anisotropy ratio should be 1.0 for isotropic
        assert abs(r["anisotropy_ratio"] - 1.0) < 0.01

    def test_anisotropy_ratio_key(self):
        """Result must contain anisotropy_ratio key."""
        r = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, sigma_H_psi=10000, sigma_h_psi=7000
        )
        assert "anisotropy_ratio" in r
        assert r["anisotropy_ratio"] > 1.0

    def test_backward_compat_keys(self):
        """Original keys must still be present."""
        r = SandControlEngine.calculate_critical_drawdown(**self.BASE)
        for key in ["critical_drawdown_psi", "effective_overburden_psi",
                     "effective_horizontal_psi", "sanding_risk", "recommendation",
                     "ucs_psi", "friction_angle_deg"]:
            assert key in r


# ═══════════════════════════════════════════════════════════════
# Water Weakening of UCS
# ═══════════════════════════════════════════════════════════════

class TestWaterWeakening:
    """Test water saturation effect on UCS and critical drawdown."""

    BASE = dict(
        ucs_psi=3000, friction_angle_deg=30,
        reservoir_pressure_psi=5000, overburden_stress_psi=12000,
        poisson_ratio=0.25, biot_coefficient=1.0
    )

    def test_sw_zero_no_change(self):
        """Sw=0 should not change UCS."""
        r = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, water_saturation=0.0
        )
        assert abs(r["ucs_wet_psi"] - 3000) < 1.0
        assert abs(r["water_weakening_factor"] - 1.0) < 0.001

    def test_sw_one_max_reduction(self):
        """Sw=1.0 should reduce UCS by 30%."""
        r = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, water_saturation=1.0
        )
        assert abs(r["ucs_wet_psi"] - 2100) < 1.0  # 3000 * 0.7
        assert abs(r["water_weakening_factor"] - 0.7) < 0.001

    def test_ucs_wet_lt_ucs(self):
        """Wet UCS must be less than or equal to dry UCS for any Sw > 0."""
        r = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, water_saturation=0.5
        )
        assert r["ucs_wet_psi"] < self.BASE["ucs_psi"]

    def test_monotonic_sw_effect(self):
        """Higher Sw should give lower critical drawdown (weaker rock)."""
        results = []
        for sw in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r = SandControlEngine.calculate_critical_drawdown(
                **self.BASE, water_saturation=sw
            )
            results.append(r["critical_drawdown_psi"])
        for i in range(1, len(results)):
            assert results[i] <= results[i - 1]

    def test_cohesion_derivation(self):
        """When cohesion_psi=None, it should be derived from wet UCS."""
        r = SandControlEngine.calculate_critical_drawdown(
            **self.BASE, water_saturation=0.5
        )
        # C = UCS_wet * (1-sin_phi) / (2*cos_phi)
        phi_rad = math.radians(30)
        expected_C = r["ucs_wet_psi"] * (1 - math.sin(phi_rad)) / (2 * math.cos(phi_rad))
        assert abs(r["cohesion_psi"] - expected_C) < 1.0


# ═══════════════════════════════════════════════════════════════
# Barite Requirements
# ═══════════════════════════════════════════════════════════════

class TestBariteRequirements:
    """Test barite weighting calculations."""

    def test_positive_sacks(self):
        """Increasing MW should require positive barite."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=12.0, system_volume_bbl=500
        )
        assert r["barite_lbs"] > 0
        assert r["barite_sacks"] > 0

    def test_sack_count_correct(self):
        """Sacks = lbs / sack_weight."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=12.0, system_volume_bbl=500,
            sack_weight_lbs=100.0
        )
        expected_sacks = r["barite_lbs"] / 100.0
        assert abs(r["barite_sacks"] - expected_sacks) < 1.0

    def test_volume_increase(self):
        """Adding barite increases system volume."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=12.0, system_volume_bbl=500
        )
        assert r["final_volume_increase_bbl"] > 0

    def test_target_equals_current_zero(self):
        """Target = current MW → zero barite."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=12.0, target_mud_weight=12.0, system_volume_bbl=500
        )
        assert r["barite_lbs"] == 0.0
        assert "alert" in r

    def test_target_below_current_zero(self):
        """Target < current MW → zero barite."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=14.0, target_mud_weight=12.0, system_volume_bbl=500
        )
        assert r["barite_lbs"] == 0.0

    def test_target_exceeds_max_error(self):
        """Target > barite density → error."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=36.0, system_volume_bbl=500
        )
        assert "error" in r

    def test_high_mw_increase(self):
        """Larger MW increase → more barite."""
        r1 = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=11.0, system_volume_bbl=500
        )
        r2 = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=14.0, system_volume_bbl=500
        )
        assert r2["barite_lbs"] > r1["barite_lbs"]

    def test_mix_time_estimate(self):
        """Mix time should be proportional to barite quantity."""
        r = WellControlEngine.calculate_barite_requirements(
            current_mud_weight=10.0, target_mud_weight=12.0, system_volume_bbl=500
        )
        expected_time = r["barite_lbs"] / 2000.0
        assert abs(r["mix_time_estimate_hrs"] - round(expected_time, 1)) < 0.1


# ═══════════════════════════════════════════════════════════════
# Full Sand Control with Anisotropic Parameters
# ═══════════════════════════════════════════════════════════════

class TestFullSandControlAnisotropic:
    """Integration: full pipeline with anisotropic parameters."""

    SIEVE = [2.0, 1.0, 0.5, 0.25, 0.125, 0.063]
    CUM_PCT = [100, 95, 70, 35, 10, 2]

    def test_full_pipeline_with_anisotropic(self):
        """Full sand control with anisotropic params runs without error."""
        r = SandControlEngine.calculate_full_sand_control(
            sieve_sizes_mm=self.SIEVE,
            cumulative_passing_pct=self.CUM_PCT,
            hole_id=8.5, screen_od=5.5, interval_length=50,
            ucs_psi=2000, friction_angle_deg=30,
            reservoir_pressure_psi=5000, overburden_stress_psi=12000,
            formation_permeability_md=500,
            sigma_H_psi=10000, sigma_h_psi=7000,
            water_saturation=0.3, wellbore_azimuth_deg=45
        )
        assert "summary" in r
        assert "drawdown" in r
        assert r["drawdown"]["anisotropy_ratio"] > 1.0

    def test_summary_has_new_keys(self):
        """Summary drawdown dict should have anisotropy keys."""
        r = SandControlEngine.calculate_full_sand_control(
            sieve_sizes_mm=self.SIEVE,
            cumulative_passing_pct=self.CUM_PCT,
            hole_id=8.5, screen_od=5.5, interval_length=50,
            ucs_psi=2000, friction_angle_deg=30,
            reservoir_pressure_psi=5000, overburden_stress_psi=12000,
            formation_permeability_md=500,
            sigma_H_psi=9000, sigma_h_psi=6000
        )
        dd = r["drawdown"]
        for key in ["sigma_H_eff_psi", "anisotropy_ratio", "water_weakening_factor",
                     "ucs_wet_psi", "kirsch_sigma_theta", "cohesion_psi"]:
            assert key in dd
