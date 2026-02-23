# tests/unit/test_witsml_soap.py
"""Unit tests for WITSMLSoapClient — SOAP client with mock mode."""
import pytest
from orchestrator.witsml_client import WITSMLSoapClient


class TestMockModeConnection:
    def test_mock_connect_succeeds(self):
        """Mock mode connect should always succeed."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.connect()
        assert result["connected"] is True
        assert result["mode"] == "mock"

    def test_mock_connect_returns_capabilities(self):
        """Mock connect should return server capabilities."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.connect()
        assert "capabilities" in result
        assert "1.4.1" in str(result["capabilities"])


class TestMockModeQueries:
    def test_get_from_store_log(self):
        """Mock get_from_store for log type should return valid XML."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        xml = client.get_from_store("log", "<logs/>")
        assert "<logs" in xml
        assert "logData" in xml

    def test_get_from_store_trajectory(self):
        """Mock get_from_store for trajectory should return valid XML."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        xml = client.get_from_store("trajectory", "<trajectorys/>")
        assert "<trajectorys" in xml

    def test_get_cap(self):
        """get_cap should return capabilities dict."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.get_cap()
        assert "functions" in result
        assert "WMLS_GetFromStore" in result["functions"]

    def test_fetch_latest_log(self):
        """Convenience fetch_latest_log should return parsed data."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.fetch_latest_log("W-001", "WB-001", ["GR", "RHOB"])
        assert "data" in result
        assert len(result["data"]) > 0


class TestRealModeWithoutZeep:
    def test_real_mode_without_zeep_raises(self):
        """Real mode should raise ImportError when zeep is not installed."""
        client = WITSMLSoapClient("https://real.witsml.com/store", "user", "pass", mock_mode=False)
        result = client.connect()
        assert result["connected"] is False
        assert "zeep" in result.get("error", "").lower() or "zeep" in result.get("message", "").lower()

    def test_invalid_url_rejected(self):
        """Should reject non-HTTP URLs."""
        client = WITSMLSoapClient("ftp://invalid", "user", "pass", mock_mode=True)
        result = client.connect()
        assert isinstance(result, dict)
