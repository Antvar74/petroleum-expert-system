"""
Unit tests for PetrophysicsEngine.

Covers: LAS parsing (lasio), Waxman-Smits Sw, Dual-Water Sw,
        Pickett plot, Density-Neutron crossplot, advanced permeability,
        full petrophysical evaluation.
"""
import math
import pytest
from orchestrator.petrophysics_engine import PetrophysicsEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_las_content():
    """Minimal valid LAS 2.0 content."""
    return """~VERSION INFORMATION
 VERS.                          2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
 WRAP.                          NO  : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 WELL.                  VOLVE-15/9-F-1 : WELL NAME
 STRT.FT              5000.0000 : START DEPTH
 STOP.FT              5020.0000 : STOP DEPTH
 STEP.FT                 5.0000 : STEP
 NULL.                 -999.2500 : NULL VALUE
~CURVE INFORMATION
 DEPT.FT                        : DEPTH
 GR  .GAPI                      : GAMMA RAY
 RHOB.G/C3                      : BULK DENSITY
 NPHI.V/V                       : NEUTRON POROSITY
 RT  .OHMM                      : DEEP RESISTIVITY
 DT  .US/FT                     : SONIC TRANSIT TIME
~A  DEPTH        GR       RHOB     NPHI       RT        DT
 5000.0000    35.0000   2.3200   0.2200   45.0000   85.0000
 5005.0000    40.0000   2.3500   0.2000   38.0000   88.0000
 5010.0000    90.0000   2.5500   0.1200    5.0000  105.0000
 5015.0000    30.0000   2.2800   0.2600   70.0000   82.0000
 5020.0000    25.0000   2.2500   0.2800   90.0000   80.0000
"""


@pytest.fixture
def las_file(tmp_path, sample_las_content):
    """Write sample LAS content to a temp file."""
    p = tmp_path / "test_well.las"
    p.write_text(sample_las_content)
    return str(p)


@pytest.fixture
def sample_log_data():
    """Pre-built log data for evaluation tests."""
    return [
        {"md": 8000, "gr": 25, "rhob": 2.35, "nphi": 0.22, "rt": 45},
        {"md": 8005, "gr": 30, "rhob": 2.38, "nphi": 0.20, "rt": 40},
        {"md": 8010, "gr": 28, "rhob": 2.33, "nphi": 0.24, "rt": 50},
        {"md": 8015, "gr": 35, "rhob": 2.40, "nphi": 0.18, "rt": 30},
        {"md": 8020, "gr": 22, "rhob": 2.30, "nphi": 0.26, "rt": 65},
        {"md": 8025, "gr": 20, "rhob": 2.28, "nphi": 0.28, "rt": 80},
        {"md": 8030, "gr": 24, "rhob": 2.32, "nphi": 0.25, "rt": 55},
        {"md": 8035, "gr": 90, "rhob": 2.55, "nphi": 0.12, "rt": 5},
        {"md": 8040, "gr": 95, "rhob": 2.58, "nphi": 0.10, "rt": 3},
        {"md": 8045, "gr": 85, "rhob": 2.52, "nphi": 0.14, "rt": 8},
        {"md": 8050, "gr": 26, "rhob": 2.34, "nphi": 0.23, "rt": 48},
        {"md": 8055, "gr": 23, "rhob": 2.31, "nphi": 0.25, "rt": 60},
    ]


# ---------------------------------------------------------------------------
# LAS Parser Tests
# ---------------------------------------------------------------------------

class TestLASParser:
    def test_parse_las_file_returns_data(self, las_file):
        result = PetrophysicsEngine.parse_las_file(las_file)
        assert "error" not in result
        assert "well_info" in result
        assert "curves" in result
        assert "data" in result
        assert len(result["data"]) == 5

    def test_parse_las_maps_mnemonics(self, las_file):
        result = PetrophysicsEngine.parse_las_file(las_file)
        data = result["data"]
        first = data[0]
        assert "md" in first
        assert "gr" in first
        assert "rhob" in first
        assert "nphi" in first
        assert "rt" in first
        assert "dt" in first

    def test_parse_las_well_name(self, las_file):
        result = PetrophysicsEngine.parse_las_file(las_file)
        assert "VOLVE" in str(result["well_info"].get("WELL", ""))

    def test_parse_las_content_string(self, sample_las_content):
        result = PetrophysicsEngine.parse_las_content(sample_las_content)
        assert "error" not in result
        assert len(result["data"]) == 5
        assert result["data"][0]["md"] == 5000.0

    def test_parse_las_file_not_found(self):
        result = PetrophysicsEngine.parse_las_file("/nonexistent/file.las")
        assert "error" in result

    def test_parse_las_empty_content(self):
        result = PetrophysicsEngine.parse_las_content("")
        assert "error" in result

    def test_parse_las_stats_computed(self, las_file):
        result = PetrophysicsEngine.parse_las_file(las_file)
        assert "stats" in result
        assert "gr" in result["stats"]
        assert "min" in result["stats"]["gr"]
        assert "max" in result["stats"]["gr"]

    def test_parse_las_depth_range(self, las_file):
        result = PetrophysicsEngine.parse_las_file(las_file)
        dr = result["depth_range"]
        assert dr["min"] == 5000.0
        assert dr["max"] == 5020.0
        assert dr["points"] == 5

    def test_parse_las_null_handling(self, tmp_path):
        content = """~VERSION INFORMATION
 VERS.   2.0 :
 WRAP.   NO  :
~WELL INFORMATION
 NULL. -999.2500 :
~CURVE INFORMATION
 DEPT.FT  :
 GR.GAPI  :
~A DEPTH GR
 5000.0  35.0
 5005.0  -999.25
 5010.0  40.0
"""
        p = tmp_path / "null_test.las"
        p.write_text(content)
        result = PetrophysicsEngine.parse_las_file(str(p))
        assert "error" not in result
        grs = [d["gr"] for d in result["data"]]
        assert None in grs  # null value should be replaced with None


# ---------------------------------------------------------------------------
# Water Saturation Tests
# ---------------------------------------------------------------------------

class TestWaterSaturation:
    def test_archie_clean_sand(self):
        """Vsh < 0.15 → Archie model."""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.20, rt=20.0, rw=0.05, vsh=0.05, rsh=2.0,
        )
        assert result["model_used"] == "archie"
        assert 0.0 < result["sw"] < 1.0

    def test_waxman_smits_moderate_clay(self):
        """0.15 <= Vsh < 0.40 → Waxman-Smits."""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.18, rt=10.0, rw=0.05, vsh=0.25, rsh=2.0,
        )
        assert result["model_used"] == "waxman_smits"
        assert 0.0 < result["sw"] < 1.0

    def test_dual_water_high_clay(self):
        """Vsh >= 0.40 → Dual-Water."""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.15, rt=5.0, rw=0.05, vsh=0.50, rsh=1.5,
        )
        assert result["model_used"] == "dual_water"
        assert 0.0 < result["sw"] <= 1.0

    def test_manual_method_override(self):
        """Can force a specific method regardless of Vsh."""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.20, rt=20.0, rw=0.05, vsh=0.05, rsh=2.0,
            method="waxman_smits",
        )
        assert result["model_used"] == "waxman_smits"

    def test_archie_sw_physics(self):
        """Higher Rt → lower Sw (more hydrocarbon)."""
        sw_low_rt = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.20, rt=5.0, rw=0.05, vsh=0.0,
        )["sw"]
        sw_high_rt = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.20, rt=50.0, rw=0.05, vsh=0.0,
        )["sw"]
        assert sw_high_rt < sw_low_rt

    def test_archie_sw_known_value(self):
        """Archie with standard params: Sw = [(1*0.05)/(20*0.04)]^0.5 = 0.25"""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.20, rt=20.0, rw=0.05, vsh=0.0,
            a=1.0, m=2.0, n=2.0,
        )
        # phi^m = 0.2^2 = 0.04, a*Rw/(Rt*phi^m) = 0.05/0.8 = 0.0625, Sw = sqrt(0.0625) = 0.25
        assert abs(result["sw"] - 0.25) < 0.01

    def test_sw_bounded_0_1(self):
        """Sw should never exceed [0, 1]."""
        result = PetrophysicsEngine.calculate_water_saturation_advanced(
            phi=0.05, rt=0.5, rw=0.05, vsh=0.0,
        )
        assert 0.0 <= result["sw"] <= 1.0


# ---------------------------------------------------------------------------
# Pickett Plot Tests
# ---------------------------------------------------------------------------

class TestPickettPlot:
    def test_pickett_plot_data(self):
        log_data = [
            {"phi": 0.25, "rt": 10.0, "sw": 0.30},
            {"phi": 0.15, "rt": 50.0, "sw": 0.50},
            {"phi": 0.10, "rt": 200.0, "sw": 0.80},
        ]
        result = PetrophysicsEngine.generate_pickett_plot(log_data, rw=0.05)
        assert "points" in result
        assert "iso_sw_lines" in result
        assert len(result["points"]) == 3
        assert "log_phi" in result["points"][0]
        assert "log_rt" in result["points"][0]

    def test_pickett_iso_sw_lines(self):
        log_data = [{"phi": 0.20, "rt": 20.0}]
        result = PetrophysicsEngine.generate_pickett_plot(log_data)
        assert "Sw=20%" in result["iso_sw_lines"]
        assert "Sw=100%" in result["iso_sw_lines"]

    def test_pickett_regression(self):
        """With 3+ points, regression should compute slope."""
        log_data = [
            {"phi": 0.25, "rt": 10.0},
            {"phi": 0.15, "rt": 40.0},
            {"phi": 0.10, "rt": 150.0},
        ]
        result = PetrophysicsEngine.generate_pickett_plot(log_data)
        assert "slope" in result["regression"]
        assert "estimated_m" in result["regression"]

    def test_pickett_empty_data(self):
        result = PetrophysicsEngine.generate_pickett_plot([])
        assert result["points"] == []


# ---------------------------------------------------------------------------
# Crossplot Tests
# ---------------------------------------------------------------------------

class TestCrossplot:
    def test_density_neutron_crossplot(self):
        log_data = [
            {"rhob": 2.35, "nphi": 0.22, "md": 5000},
            {"rhob": 2.30, "nphi": 0.25, "md": 5005},
        ]
        result = PetrophysicsEngine.crossplot_density_neutron(log_data)
        assert len(result["points"]) == 2
        assert "lithology_lines" in result
        assert "sandstone" in result["lithology_lines"]

    def test_crossplot_gas_detection(self):
        """Gas zone: low NPHI + high phi_density → gas_flag True."""
        log_data = [
            {"rhob": 2.10, "nphi": 0.05, "md": 5000},  # gas effect
        ]
        result = PetrophysicsEngine.crossplot_density_neutron(log_data)
        assert result["gas_count"] >= 1


# ---------------------------------------------------------------------------
# Advanced Permeability Tests
# ---------------------------------------------------------------------------

class TestPermeability:
    def test_timur_permeability(self):
        result = PetrophysicsEngine.calculate_permeability_advanced(
            phi=0.25, sw_irr=0.20, method="timur",
        )
        assert result["k_md"] > 0
        assert result["method"] == "timur"
        assert "quality" in result

    def test_coates_permeability(self):
        result = PetrophysicsEngine.calculate_permeability_advanced(
            phi=0.25, sw_irr=0.20, method="coates",
        )
        assert result["k_md"] > 0
        assert result["method"] == "coates"

    def test_higher_porosity_higher_perm(self):
        low = PetrophysicsEngine.calculate_permeability_advanced(phi=0.10, sw_irr=0.30)
        high = PetrophysicsEngine.calculate_permeability_advanced(phi=0.30, sw_irr=0.30)
        assert high["k_md"] > low["k_md"]


# ---------------------------------------------------------------------------
# Full Evaluation Tests
# ---------------------------------------------------------------------------

class TestFullEvaluation:
    def test_full_evaluation_returns_all_fields(self, sample_log_data):
        result = PetrophysicsEngine.run_full_evaluation(sample_log_data)
        assert "evaluated_data" in result
        assert "summary" in result
        assert "intervals" in result
        assert len(result["evaluated_data"]) == len(sample_log_data)

    def test_evaluated_data_has_derived_properties(self, sample_log_data):
        result = PetrophysicsEngine.run_full_evaluation(sample_log_data)
        first = result["evaluated_data"][0]
        assert "vsh" in first
        assert "phi_total" in first
        assert "phi_effective" in first
        assert "sw" in first
        assert "k_md" in first
        assert "is_pay" in first

    def test_shale_points_not_pay(self, sample_log_data):
        """High-GR shale points should not be flagged as pay."""
        result = PetrophysicsEngine.run_full_evaluation(sample_log_data)
        # Points at 8035-8045 have GR=85-95 (shale)
        shale_points = [e for e in result["evaluated_data"] if e["gr"] > 80]
        for pt in shale_points:
            assert pt["is_pay"] is False

    def test_summary_stats(self, sample_log_data):
        result = PetrophysicsEngine.run_full_evaluation(sample_log_data)
        s = result["summary"]
        assert s["total_points"] == 12
        assert s["pay_points"] >= 0
        assert s["pay_points"] <= s["total_points"]
