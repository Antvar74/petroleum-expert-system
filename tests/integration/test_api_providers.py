"""
Integration tests for the /providers endpoint and provider selection in /analyze endpoints.
"""
import os
import pytest
from unittest.mock import patch


# ================================================================
# Helpers
# ================================================================

def _create_well(client, name="PROVIDER-TEST-WELL"):
    resp = client.post("/wells", params={"name": name})
    assert resp.status_code == 200
    return resp.json()


# ================================================================
# TestProvidersEndpoint
# ================================================================

class TestProvidersEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/providers")
        assert resp.status_code == 200

    def test_returns_list(self, client):
        resp = client.get("/providers")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # at least auto

    def test_always_has_auto(self, client):
        resp = client.get("/providers")
        ids = [p["id"] for p in resp.json()]
        assert "auto" in ids

    def test_each_provider_has_name_and_name_es(self, client):
        resp = client.get("/providers")
        for p in resp.json():
            assert "name" in p, f"Missing 'name' in provider {p['id']}"
            assert "name_es" in p, f"Missing 'name_es' in provider {p['id']}"


# ================================================================
# TestAnalyzeWithProvider
# ================================================================

class TestAnalyzeWithProvider:
    def test_provider_in_response(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = client.post(
            f"/wells/{well['id']}/torque-drag/analyze",
            json={"result_data": sample_td_result, "params": {}, "language": "en", "provider": "gemini"},
        )
        assert resp.status_code == 200
        assert resp.json()["provider_used"] == "gemini"

    def test_default_provider_is_auto(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = client.post(
            f"/wells/{well['id']}/torque-drag/analyze",
            json={"result_data": sample_td_result, "params": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["provider_used"] == "auto"

    def test_backward_compatible_without_provider(self, client, mock_api_coordinator, sample_hyd_result):
        well = _create_well(client, name="COMPAT-WELL")
        resp = client.post(
            f"/wells/{well['id']}/hydraulics/analyze",
            json={"result_data": sample_hyd_result, "params": {}, "language": "es"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "provider_used" in data
        assert data["provider_used"] == "auto"
