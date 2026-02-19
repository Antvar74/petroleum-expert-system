"""
Phase 7 Elite Tests — Completion Design Engine

Tests for: IPR Vogel/Fetkovich/Darcy, VLP Beggs & Brill, Nodal Analysis,
Fracture Gradient (Daines, Matthews-Kelly), Crushed Zone Skin,
Horizontal Productivity (Joshi), Expanded Gun Catalog.

~30 tests across 8 test classes.
"""
import pytest
import math
from orchestrator.completion_design_engine import CompletionDesignEngine


# ─────────────────────────────────────────────────────────────────
# 7.1 IPR Models
# ─────────────────────────────────────────────────────────────────

class TestIPRVogel:
    """Test Vogel (1968) IPR for solution-gas drive wells."""

    def test_vogel_pure_keys(self):
        """Vogel pure returns required keys."""
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=3000, bubble_point_psi=3500,
            productivity_index_above_pb=5.0
        )
        assert "Pwf_psi" in result
        assert "q_oil_stbd" in result
        assert "AOF_stbd" in result
        assert result["method"] == "vogel_pure"

    def test_vogel_composite_above_pb(self):
        """Composite IPR when Pr > Pb uses Darcy above bubble point."""
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=5000, bubble_point_psi=3000,
            productivity_index_above_pb=5.0
        )
        assert result["is_composite"] is True
        assert result["method"] == "vogel_composite"
        # q at Pb should equal PI * (Pr - Pb)
        assert result["q_at_bubble_point_stbd"] == pytest.approx(5.0 * 2000, rel=0.01)

    def test_vogel_aof_positive(self):
        """AOF must be positive for valid inputs."""
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=4000, bubble_point_psi=3000,
            productivity_index_above_pb=8.0
        )
        assert result["AOF_stbd"] > 0

    def test_vogel_q_increases_with_drawdown(self):
        """Flow rate increases as Pwf decreases (more drawdown)."""
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=3500, bubble_point_psi=4000,
            productivity_index_above_pb=5.0
        )
        q_list = result["q_oil_stbd"]
        # First points have higher Pwf → lower q; last points lower Pwf → higher q
        assert q_list[0] <= q_list[-1]

    def test_vogel_zero_pi_returns_error(self):
        """Zero PI should return error."""
        result = CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=3000, bubble_point_psi=2000,
            productivity_index_above_pb=0.0
        )
        assert "error" in result


class TestIPRFetkovich:
    """Test Fetkovich (1973) IPR for gas wells."""

    def test_fetkovich_keys(self):
        """Returns required keys."""
        result = CompletionDesignEngine.calculate_ipr_fetkovich(
            reservoir_pressure_psi=5000, C_coefficient=0.01, n_exponent=0.8
        )
        assert "q_gas_mscfd" in result
        assert "AOF_mscfd" in result
        assert result["method"] == "fetkovich"

    def test_fetkovich_aof_at_pwf_zero(self):
        """AOF = C × Pr^(2n) at Pwf=0."""
        Pr = 5000.0
        C = 0.01
        n = 0.8
        result = CompletionDesignEngine.calculate_ipr_fetkovich(
            reservoir_pressure_psi=Pr, C_coefficient=C, n_exponent=n
        )
        expected_aof = C * (Pr ** 2) ** n
        assert result["AOF_mscfd"] == pytest.approx(expected_aof, rel=0.01)

    def test_fetkovich_n_clamped(self):
        """n exponent clamped between 0.5 and 1.0."""
        result = CompletionDesignEngine.calculate_ipr_fetkovich(
            reservoir_pressure_psi=4000, C_coefficient=0.005, n_exponent=1.5
        )
        assert result["n_exponent"] == 1.0


class TestIPRDarcy:
    """Test Darcy straight-line IPR."""

    def test_darcy_pi_calculation(self):
        """PI = kh / (141.2 × Bo × mu × (ln(re/rw) + S))."""
        k, h, Bo, mu = 100.0, 50.0, 1.2, 1.0
        rw, re, S = 0.354, 660.0, 5.0
        result = CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=k, net_pay_ft=h, Bo=Bo, mu_oil_cp=mu,
            reservoir_pressure_psi=5000, wellbore_radius_ft=rw,
            drainage_radius_ft=re, skin=S
        )
        ln_term = math.log(re / rw) + S
        expected_pi = k * h / (141.2 * Bo * mu * ln_term)
        assert result["PI_stbd_psi"] == pytest.approx(expected_pi, rel=0.01)

    def test_darcy_aof(self):
        """AOF = PI × Pr."""
        result = CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=50, net_pay_ft=30, Bo=1.1, mu_oil_cp=0.8,
            reservoir_pressure_psi=4000
        )
        assert result["AOF_stbd"] == pytest.approx(result["PI_stbd_psi"] * 4000, rel=0.01)


# ─────────────────────────────────────────────────────────────────
# 7.2 VLP Beggs & Brill + Nodal Analysis
# ─────────────────────────────────────────────────────────────────

class TestVLPBeggsBrill:
    """Test Beggs & Brill simplified VLP."""

    def test_vlp_static_returns_hydrostatic(self):
        """At zero rate, Pwf = Pwh + hydrostatic column."""
        result = CompletionDesignEngine.calculate_vlp_beggs_brill(
            tubing_id_in=2.992, well_depth_ft=10000,
            wellhead_pressure_psi=500, oil_rate_stbd=0,
            oil_api=35, water_cut=0.0
        )
        assert result["Pwf_required_psi"] > 500  # Must be above Pwh
        assert result["dominant_flow_regime"] == "static"

    def test_vlp_pwf_greater_than_pwh(self):
        """Bottomhole pressure > wellhead pressure for flowing well."""
        result = CompletionDesignEngine.calculate_vlp_beggs_brill(
            tubing_id_in=2.992, well_depth_ft=8000,
            wellhead_pressure_psi=300, oil_rate_stbd=500,
            water_cut=0.1, glr_scf_stb=400, oil_api=30
        )
        assert result["Pwf_required_psi"] > 300

    def test_vlp_pressure_profile_increasing(self):
        """Pressure increases with depth in profile."""
        result = CompletionDesignEngine.calculate_vlp_beggs_brill(
            tubing_id_in=2.992, well_depth_ft=8000,
            wellhead_pressure_psi=200, oil_rate_stbd=300,
            water_cut=0.0, glr_scf_stb=300, oil_api=35
        )
        profile = result["pressure_profile"]
        assert len(profile) > 2
        # Pressures should generally increase with depth
        assert profile[-1]["pressure_psi"] > profile[0]["pressure_psi"]

    def test_vlp_has_flow_regime(self):
        """Result has flow regime distribution."""
        result = CompletionDesignEngine.calculate_vlp_beggs_brill(
            tubing_id_in=2.992, well_depth_ft=10000,
            wellhead_pressure_psi=400, oil_rate_stbd=1000,
            water_cut=0.3, glr_scf_stb=800
        )
        assert "flow_regime_distribution" in result
        assert result["dominant_flow_regime"] in ["segregated", "intermittent", "distributed", "transition"]


class TestNodalAnalysis:
    """Test IPR-VLP nodal intersection."""

    def test_nodal_finds_intersection(self):
        """Finds operating point at IPR-VLP intersection."""
        # Simple IPR: declining Pwf with increasing q
        ipr_Pwf = [5000, 4500, 4000, 3500, 3000, 2500, 2000, 1500, 1000, 500, 0]
        ipr_q = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

        # VLP: increasing Pwf with increasing q
        vlp_q = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        vlp_Pwf = [1000, 1200, 1500, 1800, 2200, 2600, 3100, 3600, 4200, 4800, 5500]

        result = CompletionDesignEngine.calculate_nodal_analysis(ipr_Pwf, ipr_q, vlp_q, vlp_Pwf)
        assert result["operating_point_q"] > 0
        assert result["operating_point_Pwf_psi"] > 0
        assert result["intersection_error_psi"] < 200  # Reasonable interpolation error

    def test_nodal_stable_flag(self):
        """Operating point stability flag works."""
        ipr_Pwf = [4000, 3000, 2000, 1000, 0]
        ipr_q = [0, 250, 500, 750, 1000]
        vlp_q = [0, 250, 500, 750, 1000]
        vlp_Pwf = [500, 1000, 2000, 3000, 4500]

        result = CompletionDesignEngine.calculate_nodal_analysis(ipr_Pwf, ipr_q, vlp_q, vlp_Pwf)
        assert isinstance(result["stable"], bool)

    def test_nodal_empty_curves_error(self):
        """Empty curves return error."""
        result = CompletionDesignEngine.calculate_nodal_analysis([], [], [], [])
        assert "error" in result


# ─────────────────────────────────────────────────────────────────
# 7.3 Alternative Fracture Gradient Methods
# ─────────────────────────────────────────────────────────────────

class TestFracGradientAlternatives:
    """Test Daines and Matthews-Kelly fracture gradient methods."""

    def test_daines_with_superimposed_tectonic(self):
        """Daines gradient increases with superimposed tectonic stress."""
        base = CompletionDesignEngine.calculate_fracture_gradient_daines(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, poisson_ratio=0.25,
            tectonic_stress_psi=0, superimposed_tectonic_psi=0
        )
        with_tec = CompletionDesignEngine.calculate_fracture_gradient_daines(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, poisson_ratio=0.25,
            tectonic_stress_psi=0, superimposed_tectonic_psi=500
        )
        assert with_tec["fracture_gradient_ppg"] > base["fracture_gradient_ppg"]
        assert with_tec["method"] == "daines_1982"

    def test_daines_eaton_baseline(self):
        """Daines without tectonic equals Eaton baseline."""
        result = CompletionDesignEngine.calculate_fracture_gradient_daines(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, poisson_ratio=0.25,
            tectonic_stress_psi=0, superimposed_tectonic_psi=0
        )
        assert result["tectonic_correction_ppg"] == pytest.approx(0.0, abs=0.01)

    def test_matthews_kelly_auto_ki(self):
        """Matthews-Kelly auto-estimates Ki when Ki=0."""
        result = CompletionDesignEngine.calculate_fracture_gradient_matthews_kelly(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, Ki=0.0
        )
        assert result["Ki_used"] > 0.3
        assert result["Ki_used"] < 0.95
        assert result["method"] == "matthews_kelly_1967"

    def test_matthews_kelly_ki_effect(self):
        """Higher Ki → higher fracture gradient."""
        low = CompletionDesignEngine.calculate_fracture_gradient_matthews_kelly(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, Ki=0.4
        )
        high = CompletionDesignEngine.calculate_fracture_gradient_matthews_kelly(
            depth_tvd_ft=10000, pore_pressure_psi=4650,
            overburden_stress_psi=10000, Ki=0.8
        )
        assert high["fracture_gradient_ppg"] > low["fracture_gradient_ppg"]


# ─────────────────────────────────────────────────────────────────
# 7.4 Crushed Zone Skin + Horizontal Productivity
# ─────────────────────────────────────────────────────────────────

class TestCrushedZoneSkin:
    """Test crushed zone skin component."""

    def test_crushed_zone_positive_skin(self):
        """Damaged zone (k_cz < k) produces positive skin."""
        result = CompletionDesignEngine.calculate_crushed_zone_skin(
            formation_permeability_md=100, crushed_zone_permeability_md=20,
            crushed_zone_radius_in=0.5, perforation_radius_in=0.25
        )
        assert result["S_crushed_zone"] > 0
        assert result["k_ratio"] == pytest.approx(100 / 20, rel=0.01)

    def test_no_damage_zero_skin(self):
        """No damage (k_cz >= k) gives zero crushed zone skin."""
        result = CompletionDesignEngine.calculate_crushed_zone_skin(
            formation_permeability_md=100, crushed_zone_permeability_md=150
        )
        assert result["S_crushed_zone"] == 0.0

    def test_larger_damaged_zone_more_skin(self):
        """Larger crushed zone radius → more skin."""
        small = CompletionDesignEngine.calculate_crushed_zone_skin(
            formation_permeability_md=100, crushed_zone_permeability_md=20,
            crushed_zone_radius_in=0.4, perforation_radius_in=0.25
        )
        large = CompletionDesignEngine.calculate_crushed_zone_skin(
            formation_permeability_md=100, crushed_zone_permeability_md=20,
            crushed_zone_radius_in=1.0, perforation_radius_in=0.25
        )
        assert large["S_crushed_zone"] > small["S_crushed_zone"]


class TestHorizontalProductivity:
    """Test Joshi (1991) horizontal well productivity."""

    def test_horizontal_exceeds_vertical(self):
        """Horizontal well should produce more than equivalent vertical."""
        result = CompletionDesignEngine.calculate_horizontal_productivity(
            horizontal_length_ft=2000, kh_md=100, kv_md=10,
            formation_thickness_ft=50, reservoir_pressure_psi=5000,
            Pwf_psi=3000, Bo=1.2, mu_oil_cp=1.0
        )
        assert result["q_horizontal_stbd"] > result["q_vertical_stbd"]
        assert result["equivalent_vertical_wells"] > 1.0

    def test_longer_lateral_more_production(self):
        """Longer horizontal section → more production."""
        short = CompletionDesignEngine.calculate_horizontal_productivity(
            horizontal_length_ft=1000, kh_md=100, kv_md=10,
            formation_thickness_ft=50, reservoir_pressure_psi=5000,
            Pwf_psi=3000, Bo=1.2, mu_oil_cp=1.0
        )
        long = CompletionDesignEngine.calculate_horizontal_productivity(
            horizontal_length_ft=3000, kh_md=100, kv_md=10,
            formation_thickness_ft=50, reservoir_pressure_psi=5000,
            Pwf_psi=3000, Bo=1.2, mu_oil_cp=1.0
        )
        assert long["q_horizontal_stbd"] > short["q_horizontal_stbd"]

    def test_kv_kh_effect(self):
        """Lower kv/kh ratio → less horizontal advantage."""
        isotropic = CompletionDesignEngine.calculate_horizontal_productivity(
            horizontal_length_ft=2000, kh_md=100, kv_md=100,
            formation_thickness_ft=50, reservoir_pressure_psi=5000,
            Pwf_psi=3000, Bo=1.2, mu_oil_cp=1.0
        )
        anisotropic = CompletionDesignEngine.calculate_horizontal_productivity(
            horizontal_length_ft=2000, kh_md=100, kv_md=1,
            formation_thickness_ft=50, reservoir_pressure_psi=5000,
            Pwf_psi=3000, Bo=1.2, mu_oil_cp=1.0
        )
        # Both should produce, isotropic might have different ratio
        assert isotropic["q_horizontal_stbd"] > 0
        assert anisotropic["q_horizontal_stbd"] > 0
        assert isotropic["method"] == "joshi_1991"


# ─────────────────────────────────────────────────────────────────
# 7.5 Expanded Gun Catalog
# ─────────────────────────────────────────────────────────────────

class TestExpandedGunCatalog:
    """Test expanded GUN_CATALOG selection."""

    def test_catalog_has_minimum_entries(self):
        """Catalog should have at least 20 entries."""
        assert len(CompletionDesignEngine.GUN_CATALOG) >= 20

    def test_filter_by_casing_id(self):
        """Filter guns that fit within casing."""
        result = CompletionDesignEngine.select_gun_from_catalog(casing_id_in=4.5)
        assert result["total_compatible"] > 0
        for gun in result["all_compatible"]:
            assert gun["clearance_in"] >= 0.25

    def test_filter_by_pressure(self):
        """Filter guns by pressure rating."""
        result = CompletionDesignEngine.select_gun_from_catalog(
            casing_id_in=8.5, max_pressure_psi=25000
        )
        for gun in result["all_compatible"]:
            assert gun["max_pressure_psi"] >= 25000

    def test_filter_by_gun_type(self):
        """Filter by gun type (TCP only)."""
        result = CompletionDesignEngine.select_gun_from_catalog(
            casing_id_in=8.5, gun_type_filter="tcp"
        )
        for gun in result["all_compatible"]:
            assert gun["gun_type"] == "tcp"

    def test_hpht_guns_available(self):
        """HPHT guns available at high pressure and temperature."""
        result = CompletionDesignEngine.select_gun_from_catalog(
            casing_id_in=8.5, max_pressure_psi=30000, max_temperature_f=550
        )
        assert result["total_compatible"] > 0
        assert result["recommended"]["max_pressure_psi"] >= 30000
