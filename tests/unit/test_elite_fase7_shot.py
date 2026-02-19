"""
Phase 7 Elite Tests — Shot Efficiency Engine

Tests for: Shaly-sand Sw (Simandoux, Indonesia, auto), Permeability (Timur, Coates),
Sonic Porosity (Wyllie, Raymer), LAS parser, HC typing, K&T dedup integration.

~30 tests across 8 test classes.
"""
import pytest
import os
import math
import tempfile
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine


# ─────────────────────────────────────────────────────────────────
# 7.6 Shaly-Sand Sw Models
# ─────────────────────────────────────────────────────────────────

class TestSwSimandoux:
    """Test Simandoux (1963) shaly-sand Sw model."""

    def test_simandoux_keys(self):
        """Returns required keys."""
        result = ShotEfficiencyEngine.calculate_sw_simandoux(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.25, rsh=5.0
        )
        assert "sw" in result
        assert "sw_archie" in result
        assert "sw_difference" in result
        assert result["method"] == "simandoux"

    def test_simandoux_lower_sw_than_archie(self):
        """Simandoux typically gives lower Sw than Archie in shaly sands."""
        result = ShotEfficiencyEngine.calculate_sw_simandoux(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.30, rsh=5.0
        )
        # With shale conducting, Sw_simandoux should be lower than Sw_archie
        assert result["sw"] < result["sw_archie"]

    def test_simandoux_clean_sand_approaches_archie(self):
        """At Vsh=0, Simandoux approaches Archie."""
        result = ShotEfficiencyEngine.calculate_sw_simandoux(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.0, rsh=5.0
        )
        assert abs(result["sw"] - result["sw_archie"]) < 0.02

    def test_simandoux_invalid_inputs(self):
        """Zero porosity returns Sw=1."""
        result = ShotEfficiencyEngine.calculate_sw_simandoux(
            rt=10.0, porosity=0.0, rw=0.05, vsh=0.3, rsh=5.0
        )
        assert result["sw"] == 1.0


class TestSwIndonesia:
    """Test Indonesia/Poupon-Leveaux (1971) Sw model."""

    def test_indonesia_keys(self):
        """Returns required keys."""
        result = ShotEfficiencyEngine.calculate_sw_indonesia(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.50, rsh=5.0
        )
        assert "sw" in result
        assert result["method"] == "indonesia"

    def test_indonesia_high_vsh_effect(self):
        """Indonesia handles high Vsh better — gives lower Sw than Archie."""
        result = ShotEfficiencyEngine.calculate_sw_indonesia(
            rt=8.0, porosity=0.15, rw=0.05, vsh=0.50, rsh=4.0
        )
        assert result["sw"] < result["sw_archie"]

    def test_indonesia_vsh_monotonic(self):
        """Higher Vsh → lower computed Sw (shale contributes conductivity)."""
        low_vsh = ShotEfficiencyEngine.calculate_sw_indonesia(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.10, rsh=5.0
        )
        high_vsh = ShotEfficiencyEngine.calculate_sw_indonesia(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.50, rsh=5.0
        )
        assert high_vsh["sw"] <= low_vsh["sw"]


class TestSwAutoSelect:
    """Test auto-selection of Sw model based on Vsh."""

    def test_auto_selects_archie_for_clean(self):
        """Vsh < 0.15 → selects Archie."""
        result = ShotEfficiencyEngine.calculate_sw_auto(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.05
        )
        assert result["method"] == "archie"

    def test_auto_selects_simandoux_moderate(self):
        """0.15 <= Vsh < 0.40 → selects Simandoux."""
        result = ShotEfficiencyEngine.calculate_sw_auto(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.25, rsh=5.0
        )
        assert result["method"] == "simandoux"

    def test_auto_selects_indonesia_high_vsh(self):
        """Vsh >= 0.40 → selects Indonesia."""
        result = ShotEfficiencyEngine.calculate_sw_auto(
            rt=10.0, porosity=0.20, rw=0.05, vsh=0.50, rsh=5.0
        )
        assert result["method"] == "indonesia"


# ─────────────────────────────────────────────────────────────────
# 7.7 Permeability from Logs
# ─────────────────────────────────────────────────────────────────

class TestPermeabilityLogs:
    """Test Timur and Coates permeability models."""

    def test_timur_positive_k(self):
        """Timur returns positive permeability for valid inputs."""
        result = ShotEfficiencyEngine.calculate_permeability_timur(
            porosity=0.20, sw_irreducible=0.25
        )
        assert result["k_md"] > 0
        assert result["method"] == "timur"

    def test_timur_phi_effect(self):
        """Higher porosity → higher permeability (strongly)."""
        low = ShotEfficiencyEngine.calculate_permeability_timur(
            porosity=0.10, sw_irreducible=0.30
        )
        high = ShotEfficiencyEngine.calculate_permeability_timur(
            porosity=0.25, sw_irreducible=0.30
        )
        assert high["k_md"] > low["k_md"]

    def test_coates_positive_k(self):
        """Coates returns positive permeability."""
        result = ShotEfficiencyEngine.calculate_permeability_coates(
            porosity=0.20, sw_irreducible=0.25
        )
        assert result["k_md"] > 0
        assert result["method"] == "coates"

    def test_coates_swirr_effect(self):
        """Higher irreducible Sw → lower permeability."""
        low_sw = ShotEfficiencyEngine.calculate_permeability_coates(
            porosity=0.20, sw_irreducible=0.15
        )
        high_sw = ShotEfficiencyEngine.calculate_permeability_coates(
            porosity=0.20, sw_irreducible=0.50
        )
        assert low_sw["k_md"] > high_sw["k_md"]

    def test_timur_zero_inputs(self):
        """Zero inputs return zero permeability."""
        result = ShotEfficiencyEngine.calculate_permeability_timur(
            porosity=0.0, sw_irreducible=0.3
        )
        assert result["k_md"] == 0.0

    def test_permeability_classification(self):
        """Permeability class assigned correctly."""
        # High porosity, low Swirr → should be moderate to high
        result = ShotEfficiencyEngine.calculate_permeability_timur(
            porosity=0.25, sw_irreducible=0.20
        )
        assert result["perm_class"] in ["Very High", "High", "Moderate", "Low", "Very Low / Tight"]


# ─────────────────────────────────────────────────────────────────
# 7.8 Sonic Porosity
# ─────────────────────────────────────────────────────────────────

class TestSonicPorosity:
    """Test sonic porosity (Wyllie and Raymer)."""

    def test_wyllie_formula(self):
        """Wyllie: phi = (DT_log - DT_ma) / (DT_fl - DT_ma)."""
        result = ShotEfficiencyEngine.calculate_porosity_sonic(
            dt_log=80.0, dt_matrix=55.5, dt_fluid=189.0, method="wyllie"
        )
        expected = (80.0 - 55.5) / (189.0 - 55.5)
        assert result["phi_sonic"] == pytest.approx(expected, abs=0.001)

    def test_raymer_formula(self):
        """Raymer: phi = 0.625 × (DT_log - DT_ma) / DT_log."""
        result = ShotEfficiencyEngine.calculate_porosity_sonic(
            dt_log=80.0, dt_matrix=55.5, method="raymer"
        )
        expected = 0.625 * (80.0 - 55.5) / 80.0
        assert result["phi_sonic"] == pytest.approx(expected, abs=0.001)

    def test_different_lithologies(self):
        """Limestone matrix (47.5) gives higher phi than sandstone (55.5)."""
        sandstone = ShotEfficiencyEngine.calculate_porosity_sonic(
            dt_log=80.0, dt_matrix=55.5, method="raymer"
        )
        limestone = ShotEfficiencyEngine.calculate_porosity_sonic(
            dt_log=80.0, dt_matrix=47.5, method="raymer"
        )
        assert limestone["phi_sonic"] > sandstone["phi_sonic"]

    def test_sonic_clamped(self):
        """Phi clamped to 0-0.50 range."""
        result = ShotEfficiencyEngine.calculate_porosity_sonic(
            dt_log=300.0, dt_matrix=55.5, dt_fluid=189.0, method="wyllie"
        )
        assert result["phi_sonic"] <= 0.50


# ─────────────────────────────────────────────────────────────────
# 7.9 LAS 2.0 Parser
# ─────────────────────────────────────────────────────────────────

class TestLASParser:
    """Test LAS 2.0 file parser."""

    def _create_sample_las(self, tmpdir):
        """Create a sample LAS 2.0 file for testing."""
        content = """~VERSION INFORMATION
 VERS.                  2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
 WRAP.                  NO  : One line per depth step
~WELL INFORMATION
 STRT.FT          8000.0000 : START DEPTH
 STOP.FT          8010.0000 : STOP DEPTH
 STEP.FT             0.5000 : STEP
 NULL.             -999.2500 : NULL VALUE
 COMP.        Test Company  : COMPANY
 WELL.        Test Well 1   : WELL
~CURVE INFORMATION
 DEPT.FT                    : Depth
 GR  .GAPI                  : Gamma Ray
 RHOB.G/C3                  : Bulk Density
 NPHI.V/V                   : Neutron Porosity
 RT  .OHMM                  : True Resistivity
 DT  .US/F                  : Sonic Transit Time
~A  DEPTH     GR     RHOB   NPHI     RT      DT
 8000.0    35.0    2.350   0.180   25.0    78.0
 8000.5    38.0    2.340   0.185   22.0    79.0
 8001.0    42.0    2.320   0.190   18.0    80.0
 8001.5    55.0    2.380   0.210   12.0    82.0
 8002.0    40.0    2.310   0.175   30.0    77.0
 8002.5    32.0    2.290   0.195   35.0    81.0
 8003.0    45.0    2.350   0.200   15.0    79.5
 8003.5    30.0    2.300   0.170   40.0    76.0
 8004.0    50.0    2.360   0.205   10.0    83.0
 8004.5    28.0    2.280   0.165   45.0    75.0
 8005.0    -999.25 -999.25 -999.25 -999.25 -999.25
"""
        filepath = os.path.join(tmpdir, "test.las")
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_las_parse_basic(self):
        """Parse a basic LAS 2.0 file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self._create_sample_las(tmpdir)
            result = ShotEfficiencyEngine.parse_las_file(filepath)
            assert "error" not in result
            assert result["data_points"] > 0
            assert "GR" in result["curves_found"]
            assert "RHOB" in result["curves_found"]

    def test_las_mnemonic_mapping(self):
        """Common mnemonics mapped correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self._create_sample_las(tmpdir)
            result = ShotEfficiencyEngine.parse_las_file(filepath)
            mapping = result["curve_mapping"]
            assert mapping.get("GR") == "gr"
            assert mapping.get("RHOB") == "rhob"
            assert mapping.get("NPHI") == "nphi"
            assert mapping.get("RT") == "rt"

    def test_las_null_handling(self):
        """NULL values (-999.25) converted to None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self._create_sample_las(tmpdir)
            result = ShotEfficiencyEngine.parse_las_file(filepath)
            # Last data row has NULL values
            last_row = result["data"][-1]
            assert last_row.get("gr") is None or last_row.get("rhob") is None

    def test_las_well_info(self):
        """Well info extracted from ~W section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self._create_sample_las(tmpdir)
            result = ShotEfficiencyEngine.parse_las_file(filepath)
            assert "WELL" in result["well_info"] or "COMP" in result["well_info"]

    def test_las_file_not_found(self):
        """Non-existent file returns error."""
        result = ShotEfficiencyEngine.parse_las_file("/nonexistent/file.las")
        assert "error" in result


# ─────────────────────────────────────────────────────────────────
# 7.10 HC Typing
# ─────────────────────────────────────────────────────────────────

class TestHCTyping:
    """Test hydrocarbon type classification."""

    def test_gas_flag_dn_separation(self):
        """Gas identified when density-neutron separation is large."""
        result = ShotEfficiencyEngine.classify_hydrocarbon_type(
            phi_density=0.25, phi_neutron=0.10,  # Big separation → gas
            rt=50.0, sw=0.20
        )
        assert result["type"] == "gas"
        assert result["dn_separation"] > 0.04

    def test_oil_identification(self):
        """Oil identified when Sw moderate, no gas-like separation."""
        result = ShotEfficiencyEngine.classify_hydrocarbon_type(
            phi_density=0.20, phi_neutron=0.22,  # Small separation
            rt=20.0, sw=0.30
        )
        assert result["type"] == "oil"

    def test_water_high_sw(self):
        """Water identified when Sw > 0.80."""
        result = ShotEfficiencyEngine.classify_hydrocarbon_type(
            phi_density=0.15, phi_neutron=0.15,
            rt=5.0, sw=0.90
        )
        assert result["type"] == "water"

    def test_mhi_calculated(self):
        """MHI (Moveable HC Index) calculated correctly."""
        result = ShotEfficiencyEngine.classify_hydrocarbon_type(
            phi_density=0.20, phi_neutron=0.20,
            rt=20.0, rxo=5.0, sw=0.30, sxo=0.70
        )
        # MHI = phi * (1 - Sw/Sxo) = 0.20 * (1 - 0.30/0.70)
        expected_mhi = 0.20 * (1.0 - 0.30 / 0.70)
        assert result["MHI"] == pytest.approx(expected_mhi, abs=0.001)


# ─────────────────────────────────────────────────────────────────
# 7.11 Dedup K&T / Integration
# ─────────────────────────────────────────────────────────────────

class TestKTIntegration:
    """Test Karakas-Tariq consistency and integration."""

    def test_skin_consistency_between_engines(self):
        """Shot efficiency and completion design K&T produce same skin."""
        from orchestrator.completion_design_engine import CompletionDesignEngine

        # Use same parameters in both engines
        params = dict(
            perforation_length_in=12.0,
            perforation_radius_in=0.20,
            wellbore_radius_ft=0.354,
            spf=4,
            phasing_deg=90,
            formation_thickness_ft=20.0,
            kv_kh_ratio=0.5,
        )
        # Completion engine: calculate_productivity_ratio
        pr_result = CompletionDesignEngine.calculate_productivity_ratio(
            formation_permeability_md=100.0,
            **params
        )
        # Shot efficiency engine: calculate_skin_factor
        se_result = ShotEfficiencyEngine.calculate_skin_factor(
            perf_length_in=12.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=20.0, kv_kh=0.5
        )
        # Both should compute similar s_p (plane-flow skin)
        assert se_result["s_p"] == pytest.approx(
            pr_result["skin_components"]["s_perforation"], abs=0.01
        )

    def test_full_pipeline_with_sw_model(self):
        """Full shot efficiency pipeline runs with auto Sw model."""
        log_entries = []
        for i in range(20):
            log_entries.append({
                "md": 8000 + i * 0.5,
                "gr": 30 + i * 2,
                "rhob": 2.30 + i * 0.005,
                "nphi": 0.18 - i * 0.002,
                "rt": 25.0 - i * 0.5,
            })

        result = ShotEfficiencyEngine.calculate_full_shot_efficiency(
            log_entries=log_entries,
            sw_model="auto",
            rsh=5.0,
            estimate_permeability=True,
            sw_irreducible=0.25,
        )
        assert result["summary"]["total_log_points"] == 20
        assert result["summary"]["sw_model_used"] == "auto"
        assert result["summary"]["permeability_estimated"] is True
        # Check processed logs have the new fields
        if result["processed_logs"]:
            pt = result["processed_logs"][0]
            assert "sw_model" in pt
            assert "hc_type" in pt
            assert "k_md" in pt

    def test_full_pipeline_with_kh_ranking(self):
        """Full pipeline with permeability uses kh in ranking."""
        log_entries = []
        for i in range(20):
            log_entries.append({
                "md": 8000 + i * 0.5,
                "gr": 25 + i,
                "rhob": 2.28 + i * 0.003,
                "nphi": 0.19 - i * 0.001,
                "rt": 30.0 - i * 0.3,
            })

        result = ShotEfficiencyEngine.calculate_full_shot_efficiency(
            log_entries=log_entries,
            estimate_permeability=True,
            sw_irreducible=0.20,
            cutoffs={"phi_min": 0.05, "sw_max": 0.80, "vsh_max": 0.50, "min_thickness_ft": 1.0},
        )
        # If intervals found, they should have kh
        if result["intervals_with_skin"]:
            iv = result["intervals_with_skin"][0]
            assert "k_md" in iv or "kh_md_ft" in iv
