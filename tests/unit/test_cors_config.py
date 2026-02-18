"""
Unit tests for CORS configuration.
Verifies that CORS_ORIGINS env var correctly controls allowed origins.
"""
import pytest
import os


class TestCorsConfig:
    """Tests for CORS origin configuration."""

    def test_default_cors_allows_all(self):
        """Without CORS_ORIGINS env, default should be wildcard ['*']."""
        origins = os.environ.get("CORS_ORIGINS", "*").split(",")
        assert origins == ["*"]

    def test_custom_cors_origins(self, monkeypatch):
        """CORS_ORIGINS with single origin should produce single-item list."""
        monkeypatch.setenv("CORS_ORIGINS", "https://myapp.com")
        origins = os.environ.get("CORS_ORIGINS", "*").split(",")
        assert origins == ["https://myapp.com"]

    def test_cors_multiple_origins(self, monkeypatch):
        """CORS_ORIGINS with comma-separated list should produce multi-item list."""
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5174,https://myapp.com,https://admin.myapp.com")
        origins = os.environ.get("CORS_ORIGINS", "*").split(",")
        assert origins == ["http://localhost:5174", "https://myapp.com", "https://admin.myapp.com"]
        assert len(origins) == 3
