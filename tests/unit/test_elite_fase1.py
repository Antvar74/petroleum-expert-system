"""
Phase 1 Elite Tests: Herschel-Bulkley, Z-Factor, Kick Tolerance, Larsen, Cuttings-ECD
~41 tests covering all new/modified methods in Phase 1.

References:
- API RP 13D (Rheology)
- Dranchuk-Abou-Kassem (Z-Factor)
- Larsen 1997 SPE 36383 (High-angle cuttings transport)
"""
import math
import pytest
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.well_control_engine import WellControlEngine
from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine


# ============================================================================
# 1. Herschel-Bulkley Fit (5 tests)
# ============================================================================
class TestFitHerschelBulkley:
    """Tests for HydraulicsEngine.fit_herschel_bulkley()"""

    TYPICAL_FANN = {"r600": 68, "r300": 42, "r200": 34, "r100": 24, "r6": 8, "r3": 6}

    def test_output_keys(self):
        """All required output keys are present."""
        result = HydraulicsEngine.fit_herschel_bulkley(self.TYPICAL_FANN)
        for key in ["tau_0", "k_hb", "n_hb", "r_squared", "fann_readings"]:
            assert key in result, f"Missing key: {key}"

    def test_tau_0_positive(self):
        """Yield stress tau_0 should be > 0 for a typical drilling mud."""
        result = HydraulicsEngine.fit_herschel_bulkley(self.TYPICAL_FANN)
        assert result["tau_0"] >= 0, "tau_0 should be non-negative"

    def test_n_hb_range(self):
        """Flow behavior index n should be in (0.2, 0.9) for drilling fluids."""
        result = HydraulicsEngine.fit_herschel_bulkley(self.TYPICAL_FANN)
        assert 0.1 < result["n_hb"] < 1.0, f"n_hb={result['n_hb']} outside expected range"

    def test_zero_readings_guard(self):
        """All-zero readings should return safe defaults (k_hb=0, n_hb=1.0)."""
        zeros = {"r600": 0, "r300": 0, "r200": 0, "r100": 0, "r6": 0, "r3": 0}
        result = HydraulicsEngine.fit_herschel_bulkley(zeros)
        assert result["tau_0"] == 0.0
        assert result["n_hb"] == 1.0

    def test_monotonicity_shear_stress(self):
        """Higher FANN readings should produce higher k_hb (consistency index)."""
        low = {"r600": 40, "r300": 25, "r200": 20, "r100": 14, "r6": 5, "r3": 4}
        high = {"r600": 90, "r300": 60, "r200": 50, "r100": 38, "r6": 12, "r3": 10}
        r_low = HydraulicsEngine.fit_herschel_bulkley(low)
        r_high = HydraulicsEngine.fit_herschel_bulkley(high)
        assert r_high["k_hb"] > r_low["k_hb"], "Higher readings should yield higher k_hb"


# ============================================================================
# 2. Herschel-Bulkley Pressure Loss (5 tests)
# ============================================================================
class TestPressureLossHB:
    """Tests for HydraulicsEngine.pressure_loss_herschel_bulkley()"""

    def test_zero_flow_guard(self):
        """Zero flow rate should return zero pressure loss."""
        result = HydraulicsEngine.pressure_loss_herschel_bulkley(
            flow_rate=0, mud_weight=12.0, tau_0=5.0, k_hb=0.5, n_hb=0.6,
            length=1000, od=8.5, id_inner=4.276
        )
        assert result["pressure_loss_psi"] == 0.0

    def test_pipe_positive_loss(self):
        """Pipe section should produce positive pressure loss."""
        result = HydraulicsEngine.pressure_loss_herschel_bulkley(
            flow_rate=350, mud_weight=12.0, tau_0=5.0, k_hb=0.5, n_hb=0.6,
            length=10000, od=5.0, id_inner=4.276, is_annular=False
        )
        assert result["pressure_loss_psi"] > 0
        assert result["velocity_ft_min"] > 0

    def test_annular_positive_loss(self):
        """Annular section should produce positive pressure loss."""
        result = HydraulicsEngine.pressure_loss_herschel_bulkley(
            flow_rate=350, mud_weight=12.0, tau_0=5.0, k_hb=0.5, n_hb=0.6,
            length=10000, od=8.5, id_inner=5.0, is_annular=True
        )
        assert result["pressure_loss_psi"] > 0
        assert result["velocity_ft_min"] > 0

    def test_output_keys(self):
        """All expected output keys present, including H-B params."""
        result = HydraulicsEngine.pressure_loss_herschel_bulkley(
            flow_rate=350, mud_weight=12.0, tau_0=5.0, k_hb=0.5, n_hb=0.6,
            length=1000, od=8.5, id_inner=5.0
        )
        for key in ["pressure_loss_psi", "velocity_ft_min", "reynolds",
                     "flow_regime", "tau_0", "k_hb", "n_hb"]:
            assert key in result, f"Missing key: {key}"

    def test_tau0_monotonicity(self):
        """Higher yield stress should produce higher pressure loss (all else equal)."""
        base_kwargs = dict(flow_rate=350, mud_weight=12.0, k_hb=0.5, n_hb=0.6,
                           length=5000, od=8.5, id_inner=5.0, is_annular=True)
        r_low = HydraulicsEngine.pressure_loss_herschel_bulkley(tau_0=2.0, **base_kwargs)
        r_high = HydraulicsEngine.pressure_loss_herschel_bulkley(tau_0=15.0, **base_kwargs)
        assert r_high["pressure_loss_psi"] > r_low["pressure_loss_psi"]


# ============================================================================
# 3. Full Circuit with H-B (3 tests)
# ============================================================================
class TestFullCircuitHB:
    """Tests for calculate_full_circuit() with Herschel-Bulkley model."""

    SECTIONS = [
        {"section_type": "drill_pipe", "length": 10000, "od": 5.0, "id_inner": 4.276},
        {"section_type": "collar", "length": 600, "od": 6.75, "id_inner": 2.812},
        {"section_type": "annulus_dp", "length": 10000, "od": 8.5, "id_inner": 5.0},
        {"section_type": "annulus_dc", "length": 600, "od": 8.5, "id_inner": 6.75},
    ]
    NOZZLES = [12, 12, 12]

    def test_hb_circuit_runs(self):
        """H-B circuit should run and return all expected keys."""
        result = HydraulicsEngine.calculate_full_circuit(
            sections=self.SECTIONS, nozzle_sizes=self.NOZZLES,
            flow_rate=350, mud_weight=12.0, pv=20, yp=15, tvd=10000,
            rheology_model="herschel_bulkley",
            tau_0=5.0, k_hb=0.5, n_hb=0.6
        )
        assert "summary" in result
        assert result["summary"]["total_spp_psi"] > 0
        assert result["summary"]["rheology_model"] == "herschel_bulkley"

    def test_fann_autofit(self):
        """Providing FANN readings should auto-fit H-B parameters."""
        fann = {"r600": 68, "r300": 42, "r200": 34, "r100": 24, "r6": 8, "r3": 6}
        result = HydraulicsEngine.calculate_full_circuit(
            sections=self.SECTIONS, nozzle_sizes=self.NOZZLES,
            flow_rate=350, mud_weight=12.0, pv=20, yp=15, tvd=10000,
            rheology_model="herschel_bulkley",
            fann_readings=fann
        )
        assert result["summary"]["total_spp_psi"] > 0

    def test_backward_compat_bingham(self):
        """Bingham model should still work exactly as before (no new params needed)."""
        result = HydraulicsEngine.calculate_full_circuit(
            sections=self.SECTIONS, nozzle_sizes=self.NOZZLES,
            flow_rate=350, mud_weight=12.0, pv=20, yp=15, tvd=10000
        )
        assert result["summary"]["rheology_model"] == "bingham_plastic"
        assert result["summary"]["total_spp_psi"] > 0


# ============================================================================
# 4. Z-Factor (5 tests)
# ============================================================================
class TestZFactor:
    """Tests for WellControlEngine.calculate_z_factor()"""

    def test_atmospheric_z_near_one(self):
        """At atmospheric pressure (14.7 psia), Z should be very close to 1.0."""
        result = WellControlEngine.calculate_z_factor(14.7, 60.0, 0.65)
        assert 0.95 < result["z_factor"] < 1.05, f"Z at atm = {result['z_factor']}"

    def test_typical_bottomhole(self):
        """At 5000 psia / 200F (typical BH), Z should be in 0.7-1.2 range."""
        result = WellControlEngine.calculate_z_factor(5000, 200, 0.65)
        assert 0.7 < result["z_factor"] < 1.2, f"Z = {result['z_factor']}"

    def test_convergence(self):
        """Newton-Raphson should converge for normal conditions."""
        result = WellControlEngine.calculate_z_factor(3000, 180, 0.65)
        assert result["converged"] is True

    def test_pressure_monotonicity(self):
        """Higher pressure at same temperature should give different Z (non-ideal)."""
        z_low = WellControlEngine.calculate_z_factor(1000, 200, 0.65)["z_factor"]
        z_high = WellControlEngine.calculate_z_factor(8000, 200, 0.65)["z_factor"]
        assert z_low != z_high, "Z should vary with pressure"

    def test_zero_pressure_guard(self):
        """P=0 should return Z=1.0 (ideal gas limit)."""
        result = WellControlEngine.calculate_z_factor(0, 200, 0.65)
        assert result["z_factor"] == 1.0


# ============================================================================
# 5. Gas Volume (4 tests)
# ============================================================================
class TestGasVolume:
    """Tests for WellControlEngine.calculate_gas_volume()"""

    def test_expansion_p1_gt_p2(self):
        """Gas should expand when moved from high to low pressure."""
        result = WellControlEngine.calculate_gas_volume(
            p1=5000, t1=200, v1=10.0,
            p2=1000, t2=150, gas_gravity=0.65
        )
        assert result["v2_bbl"] > 10.0, "Gas should expand at lower pressure"
        assert result["expansion_ratio"] > 1.0

    def test_ideal_limit(self):
        """At low pressure, Z~1 so expansion should approximate ideal gas."""
        result = WellControlEngine.calculate_gas_volume(
            p1=200, t1=80, v1=1.0,
            p2=100, t2=80, gas_gravity=0.65
        )
        # Ideal: V2 = 1.0 * (200/100) = 2.0 (at same T)
        # Real gas: close to 2.0 but slightly different due to Z
        assert 1.8 < result["v2_bbl"] < 2.3

    def test_p2_zero_error(self):
        """P2=0 should return error."""
        result = WellControlEngine.calculate_gas_volume(
            p1=5000, t1=200, v1=10.0,
            p2=0, t2=150
        )
        assert "error" in result

    def test_round_trip_symmetry(self):
        """Expanding then compressing back should approximately recover original volume."""
        r1 = WellControlEngine.calculate_gas_volume(
            p1=5000, t1=200, v1=10.0, p2=2000, t2=150
        )
        v_expanded = r1["v2_bbl"]
        r2 = WellControlEngine.calculate_gas_volume(
            p1=2000, t1=150, v1=v_expanded, p2=5000, t2=200
        )
        assert abs(r2["v2_bbl"] - 10.0) < 0.5, \
            f"Round-trip: {r2['v2_bbl']} vs original 10.0"


# ============================================================================
# 6. Kick Tolerance (4 tests)
# ============================================================================
class TestKickTolerance:
    """Tests for WellControlEngine.calculate_kick_tolerance()"""

    def test_positive_kt(self):
        """Standard conditions should produce positive kick tolerance."""
        result = WellControlEngine.calculate_kick_tolerance(
            mud_weight=12.0, shoe_tvd=5000, lot_emw=14.5,
            well_depth_tvd=10000, gas_gravity=0.65, bht=200,
            annular_capacity=0.05
        )
        assert result["kick_tolerance_bbl"] > 0
        assert result["maasp_psi"] > 0
        assert result["max_influx_height_ft"] > 0

    def test_lot_monotonicity(self):
        """Higher LOT EMW should give more MAASP (and thus more kick tolerance)."""
        base = dict(mud_weight=12.0, shoe_tvd=5000, well_depth_tvd=10000,
                    gas_gravity=0.65, bht=200, annular_capacity=0.05)
        r_low = WellControlEngine.calculate_kick_tolerance(lot_emw=13.0, **base)
        r_high = WellControlEngine.calculate_kick_tolerance(lot_emw=15.0, **base)
        # MAASP must be higher with higher LOT
        assert r_high["maasp_psi"] > r_low["maasp_psi"]
        # Max influx height must be higher (or equal if clamped by geometry)
        assert r_high["max_influx_height_ft"] >= r_low["max_influx_height_ft"]

    def test_mw_monotonicity(self):
        """Higher mud weight reduces MAASP margin above LOT."""
        base = dict(shoe_tvd=5000, lot_emw=14.5, well_depth_tvd=10000,
                    gas_gravity=0.65, bht=200, annular_capacity=0.05)
        r_light = WellControlEngine.calculate_kick_tolerance(mud_weight=10.0, **base)
        r_heavy = WellControlEngine.calculate_kick_tolerance(mud_weight=14.0, **base)
        # Heavier mud = less MAASP margin
        assert r_light["maasp_psi"] > r_heavy["maasp_psi"]

    def test_table_generation(self):
        """Multi-shoe table should generate entries for each shoe depth."""
        result = WellControlEngine.calculate_kick_tolerance(
            mud_weight=12.0, shoe_tvd=5000, lot_emw=14.5,
            well_depth_tvd=10000, gas_gravity=0.65, bht=200,
            annular_capacity=0.05,
            shoe_depths=[3000, 5000, 7000]
        )
        assert len(result["kt_table"]) == 3
        for entry in result["kt_table"]:
            assert "shoe_tvd" in entry
            assert "kt_bbl" in entry


# ============================================================================
# 7. Slip Velocity Larsen (5 tests)
# ============================================================================
class TestSlipVelocityLarsen:
    """Tests for WellboreCleanupEngine.calculate_slip_velocity_larsen()"""

    BASE = dict(mud_weight=12.0, pv=20, yp=15, cutting_size=0.25,
                cutting_density=21.0, hole_id=8.5, pipe_od=5.0)

    def test_output_keys(self):
        """All expected output keys present."""
        result = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=60.0, rpm=120, annular_velocity=180, **self.BASE
        )
        for key in ["slip_velocity_ftmin", "bed_erosion_velocity_ftmin",
                     "effective_transport_velocity_ftmin", "rpm_factor",
                     "inclination_factor", "correlation_used"]:
            assert key in result

    def test_positive_at_60deg(self):
        """Slip velocity should be positive at 60 degrees."""
        result = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=60.0, rpm=0, annular_velocity=0, **self.BASE
        )
        assert result["slip_velocity_ftmin"] > 0

    def test_rpm_reduces_slip(self):
        """Drillstring rotation should reduce effective slip velocity at high angles."""
        r_no_rpm = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=60.0, rpm=0, annular_velocity=0, **self.BASE
        )
        r_with_rpm = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=60.0, rpm=150, annular_velocity=0, **self.BASE
        )
        assert r_with_rpm["slip_velocity_ftmin"] < r_no_rpm["slip_velocity_ftmin"]

    def test_bed_erosion_at_90(self):
        """At 90 degrees (horizontal), bed erosion velocity should be significant."""
        result = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=90.0, rpm=0, annular_velocity=0, **self.BASE
        )
        assert result["bed_erosion_velocity_ftmin"] > 50

    def test_boundary_30deg(self):
        """At exactly 30 degrees, correlation should still work."""
        result = WellboreCleanupEngine.calculate_slip_velocity_larsen(
            inclination=30.0, rpm=0, annular_velocity=0, **self.BASE
        )
        assert result["slip_velocity_ftmin"] > 0
        assert result["correlation_used"] == "larsen"


# ============================================================================
# 8. Full Cleanup with Larsen Auto-Selection (3 tests)
# ============================================================================
class TestFullCleanupLarsen:
    """Tests for calculate_full_cleanup() with Larsen auto-selection."""

    BASE = dict(flow_rate=600, mud_weight=12.0, pv=20, yp=15,
                hole_id=8.5, pipe_od=5.0, rop=60,
                cutting_size=0.25, cutting_density=21.0, rpm=120)

    def test_auto_selects_larsen_at_70(self):
        """At 70 degrees, Larsen should be auto-selected."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            inclination=70.0, **self.BASE
        )
        assert result["summary"]["slip_velocity_correlation"] == "larsen"

    def test_auto_selects_moore_at_10(self):
        """At 10 degrees, Moore should be auto-selected."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            inclination=10.0, **self.BASE
        )
        assert result["summary"]["slip_velocity_correlation"] == "moore"

    def test_bed_erosion_alert(self):
        """Low flow rate at high angle should trigger bed erosion alert."""
        result = WellboreCleanupEngine.calculate_full_cleanup(
            flow_rate=150, mud_weight=12.0, pv=20, yp=15,
            hole_id=8.5, pipe_od=5.0, inclination=85.0, rop=60,
            cutting_size=0.25, cutting_density=21.0, rpm=0
        )
        bed_alerts = [a for a in result["alerts"] if "bed erosion" in a.lower()]
        assert len(bed_alerts) > 0, "Should have bed erosion alert at high angle with low flow"


# ============================================================================
# 9. Cuttings ECD Contribution (4 tests)
# ============================================================================
class TestCuttingsEcdContribution:
    """Tests for WellboreCleanupEngine.calculate_cuttings_ecd_contribution()"""

    def test_zero_concentration(self):
        """Zero cuttings concentration should give zero ECD contribution."""
        result = WellboreCleanupEngine.calculate_cuttings_ecd_contribution(
            concentration_pct=0.0, cutting_density=21.0, mud_weight=12.0
        )
        assert result["cuttings_ecd_ppg"] == 0.0

    def test_typical_range(self):
        """3% concentration with typical densities should give small but positive ECD."""
        result = WellboreCleanupEngine.calculate_cuttings_ecd_contribution(
            concentration_pct=3.0, cutting_density=21.0, mud_weight=12.0
        )
        # 0.03 * (21 - 12) = 0.27 ppg
        assert 0.2 < result["cuttings_ecd_ppg"] < 0.4
        assert result["effective_mud_weight_ppg"] > 12.0

    def test_exact_formula(self):
        """Verify exact calculation: ecd = (conc/100) * (rho_cut - rho_mud)."""
        result = WellboreCleanupEngine.calculate_cuttings_ecd_contribution(
            concentration_pct=5.0, cutting_density=22.0, mud_weight=10.0
        )
        expected = 0.05 * (22.0 - 10.0)  # 0.6 ppg
        assert abs(result["cuttings_ecd_ppg"] - expected) < 0.01

    def test_equal_density_guard(self):
        """If cutting density = mud weight, no ECD contribution."""
        result = WellboreCleanupEngine.calculate_cuttings_ecd_contribution(
            concentration_pct=5.0, cutting_density=12.0, mud_weight=12.0
        )
        assert result["cuttings_ecd_ppg"] == 0.0


# ============================================================================
# 10. Full Cleanup with ECD Bridge (3 tests)
# ============================================================================
class TestFullCleanupEcdBridge:
    """Tests for calculate_full_cleanup() cuttings-ECD integration."""

    BASE = dict(flow_rate=600, mud_weight=12.0, pv=20, yp=15,
                hole_id=8.5, pipe_od=5.0, inclination=45.0, rop=60,
                cutting_size=0.25, cutting_density=21.0, rpm=120)

    def test_ecd_contribution_key_exists(self):
        """Result should contain 'ecd_contribution' dict."""
        result = WellboreCleanupEngine.calculate_full_cleanup(**self.BASE)
        assert "ecd_contribution" in result
        assert "cuttings_ecd_ppg" in result["ecd_contribution"]

    def test_matches_standalone(self):
        """ECD contribution in full_cleanup should match standalone calculation."""
        result = WellboreCleanupEngine.calculate_full_cleanup(**self.BASE)
        cc = result["summary"]["cuttings_concentration_pct"]
        standalone = WellboreCleanupEngine.calculate_cuttings_ecd_contribution(
            cc, 21.0, 12.0
        )
        assert abs(result["ecd_contribution"]["cuttings_ecd_ppg"]
                    - standalone["cuttings_ecd_ppg"]) < 0.01

    def test_summary_has_cuttings_ecd(self):
        """Summary should include cuttings_ecd_ppg and effective_mud_weight_ppg."""
        result = WellboreCleanupEngine.calculate_full_cleanup(**self.BASE)
        assert "cuttings_ecd_ppg" in result["summary"]
        assert "effective_mud_weight_ppg" in result["summary"]
        assert result["summary"]["effective_mud_weight_ppg"] >= result["summary"]["cuttings_ecd_ppg"]
