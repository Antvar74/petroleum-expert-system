# tests/unit/test_data_ingest.py
"""Unit tests for DataIngestionService — unified LAS/DLIS data pipeline."""
import pytest
from orchestrator.data_ingest import DataIngestionService


# ── Sample LAS content for testing ──────────────────────────────
SAMPLE_LAS = """~VERSION INFORMATION
VERS.  2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
WRAP.  NO  :
~WELL INFORMATION
WELL.  TEST-1  : Well name
~CURVE INFORMATION
DEPT .FT     : Measured Depth
GR   .GAPI   : Gamma Ray
RHOB .G/CC   : Bulk Density
NPHI .V/V    : Neutron Porosity
ILD  .OHMM   : Deep Resistivity
~A
1000.0  55.0  2.35  0.20  10.0
1001.0  60.0  2.40  0.18  12.0
1002.0  80.0  2.50  0.15  8.0
"""


class TestParseLAS:
    def test_parse_las_returns_data(self):
        """LAS parse should return curves and data."""
        result = DataIngestionService.parse_las(SAMPLE_LAS)
        assert "data" in result
        assert "curves" in result
        assert len(result["data"]) == 3

    def test_parse_las_has_well_info(self):
        """Should extract well name."""
        result = DataIngestionService.parse_las(SAMPLE_LAS)
        assert "well_info" in result

    def test_parse_las_empty_content(self):
        """Empty input should return error."""
        result = DataIngestionService.parse_las("")
        assert "error" in result

    def test_parse_las_invalid_content(self):
        """Garbage input should return error, not crash."""
        result = DataIngestionService.parse_las("this is not a LAS file")
        assert "error" in result


class TestNormalize:
    def test_normalize_maps_standard_mnemonics(self):
        """DEPT -> md, GR -> gr, RHOB -> rhob, ILD -> rt."""
        raw = [{"DEPT": 1000, "GR": 55, "RHOB": 2.35, "ILD": 10.0}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["md"] == 1000
        assert result[0]["gr"] == 55
        assert result[0]["rhob"] == 2.35
        assert result[0]["rt"] == 10.0

    def test_normalize_case_insensitive(self):
        """Should handle mixed case mnemonics."""
        raw = [{"Dept": 1000, "gr": 55}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["md"] == 1000
        assert result[0]["gr"] == 55

    def test_normalize_unknown_mnemonic_kept_lowercase(self):
        """Unknown mnemonics are lowercased, not dropped."""
        raw = [{"DEPT": 1000, "CUSTOM_CURVE": 99}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["custom_curve"] == 99

    def test_normalize_empty_input(self):
        """Empty list returns empty list."""
        result = DataIngestionService.normalize([])
        assert result == []


class TestParseDLIS:
    def test_parse_dlis_without_dlisio(self):
        """Should return clear error when dlisio is not installed."""
        result = DataIngestionService.parse_dlis("/fake/path.dlis")
        assert "error" in result
        assert "dlisio" in result["error"].lower()

    def test_parse_dlis_file_not_found(self):
        """Should handle missing file gracefully."""
        result = DataIngestionService.parse_dlis("/nonexistent/file.dlis")
        assert "error" in result
