"""
Unit tests for path traversal prevention.
Tests safe_path.py resolver and DLIS endpoint path restriction.
"""
import os
import pytest

from utils.safe_path import resolve_safe_data_path, DATA_DIR


class TestSafePathResolver:
    """Tests for resolve_safe_data_path utility."""

    def test_rejects_parent_traversal(self):
        """../../etc/passwd must be rejected (basename 'passwd' has no extension)."""
        with pytest.raises(ValueError):
            resolve_safe_data_path("../../etc/passwd")

    def test_rejects_deep_traversal(self):
        """Deep traversal like ../../../.env must be rejected (unsupported ext)."""
        with pytest.raises(ValueError):
            resolve_safe_data_path("../../../.env")

    def test_rejects_absolute_path(self):
        """/etc/passwd (absolute) must be rejected."""
        with pytest.raises(ValueError):
            resolve_safe_data_path("/etc/passwd")

    def test_rejects_disallowed_extension(self):
        """Python script extension must be rejected."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            resolve_safe_data_path("script.py")

    def test_rejects_shell_scripts(self):
        """.sh extension must be rejected."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            resolve_safe_data_path("malicious.sh")

    def test_rejects_no_extension(self):
        """Files without extension must be rejected."""
        with pytest.raises(ValueError, match="no extension"):
            resolve_safe_data_path("passwd")

    def test_rejects_empty_filename(self):
        """Empty string must be rejected."""
        with pytest.raises(ValueError, match="Invalid filename"):
            resolve_safe_data_path("")

    def test_rejects_only_slashes(self):
        """Only directory separators must be rejected."""
        with pytest.raises(ValueError, match="Invalid filename"):
            resolve_safe_data_path("../../")

    def test_accepts_valid_pdf(self):
        """Valid PDF filename resolves to data/ directory."""
        path = resolve_safe_data_path("report.pdf")
        assert path.endswith(os.path.join("data", "report.pdf"))
        assert os.path.realpath(path).startswith(DATA_DIR)

    def test_accepts_valid_csv(self):
        """Valid CSV filename resolves correctly."""
        path = resolve_safe_data_path("welldata.csv")
        assert path.endswith(os.path.join("data", "welldata.csv"))

    def test_accepts_valid_txt(self):
        """Valid TXT filename resolves correctly."""
        path = resolve_safe_data_path("notes.txt")
        assert path.endswith(os.path.join("data", "notes.txt"))

    def test_accepts_valid_md(self):
        """Valid Markdown filename resolves correctly."""
        path = resolve_safe_data_path("README.md")
        assert path.endswith(os.path.join("data", "README.md"))

    def test_strips_directory_components(self):
        """Subdir/file.pdf must strip to just file.pdf in data/."""
        path = resolve_safe_data_path("subdir/report.pdf")
        assert os.path.basename(path) == "report.pdf"
        assert os.path.realpath(path).startswith(DATA_DIR)

    def test_traversal_with_allowed_extension(self):
        """../../secret.pdf — traversal even with allowed extension is neutered."""
        path = resolve_safe_data_path("../../secret.pdf")
        # basename() strips traversal, result is data/secret.pdf
        assert os.path.basename(path) == "secret.pdf"
        assert os.path.realpath(path).startswith(DATA_DIR)


class TestDlisPathRestriction:
    """Tests for DLIS endpoint path restriction via API."""

    def test_dlis_rejects_traversal(self, client):
        """DLIS with ../../etc/passwd must return 403."""
        resp = client.post("/data/ingest/dlis", json={"file_path": "../../etc/passwd"})
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_dlis_rejects_absolute_path(self, client):
        """DLIS with absolute path must return 403."""
        resp = client.post("/data/ingest/dlis", json={"file_path": "/etc/passwd"})
        assert resp.status_code == 403

    def test_dlis_rejects_dotenv(self, client):
        """DLIS trying to read .env must return 403."""
        resp = client.post("/data/ingest/dlis", json={"file_path": "../.env"})
        assert resp.status_code == 403

    def test_dlis_missing_path(self, client):
        """DLIS without file_path must return 4xx (422 via Pydantic validation)."""
        resp = client.post("/data/ingest/dlis", json={})
        assert resp.status_code in (400, 422)


class TestDataLoaderDefenseInDepth:
    """Tests for data_loader.py path restriction."""

    def test_rejects_path_outside_data_dir(self):
        """load_data_context rejects paths outside data/."""
        from utils.data_loader import load_data_context
        result = load_data_context("/etc/passwd")
        assert "Access denied" in result

    def test_rejects_traversal(self):
        """load_data_context rejects traversal paths."""
        from utils.data_loader import load_data_context
        result = load_data_context("../../.env")
        assert "Access denied" in result
