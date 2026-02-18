"""
Integration tests for AI analysis endpoints.
Tests the 4 /wells/{id}/<module>/analyze routes with mocked LLM.
"""
import pytest
from datetime import datetime


# ================================================================
# Helpers
# ================================================================

def _create_well(client, name="AI-TEST-WELL"):
    resp = client.post("/wells", params={"name": name})
    assert resp.status_code == 200
    return resp.json()


def _post_analyze(client, well_id, module_path, result_data, language="en"):
    return client.post(
        f"/wells/{well_id}/{module_path}/analyze",
        json={"result_data": result_data, "params": {}, "language": language},
    )


REQUIRED_FIELDS = {"module", "timestamp", "analysis", "confidence", "agent_used",
                    "agent_role", "key_metrics", "well_name", "language", "provider_used"}


# ================================================================
# TestTorqueDragAnalyze
# ================================================================

class TestTorqueDragAnalyze:
    def test_returns_200(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        assert resp.status_code == 200

    def test_404_well_not_found(self, client, mock_api_coordinator, sample_td_result):
        resp = _post_analyze(client, 99999, "torque-drag", sample_td_result, "en")
        assert resp.status_code == 404

    def test_response_structure(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        data = resp.json()
        assert REQUIRED_FIELDS == set(data.keys())

    def test_language_es_in_response(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "es")
        assert resp.json()["language"] == "es"


# ================================================================
# TestHydraulicsAnalyze
# ================================================================

class TestHydraulicsAnalyze:
    def test_returns_200(self, client, mock_api_coordinator, sample_hyd_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "hydraulics", sample_hyd_result, "en")
        assert resp.status_code == 200

    def test_404_well_not_found(self, client, mock_api_coordinator, sample_hyd_result):
        resp = _post_analyze(client, 99999, "hydraulics", sample_hyd_result, "en")
        assert resp.status_code == 404

    def test_response_structure(self, client, mock_api_coordinator, sample_hyd_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "hydraulics", sample_hyd_result, "en")
        assert REQUIRED_FIELDS == set(resp.json().keys())

    def test_language_es_in_response(self, client, mock_api_coordinator, sample_hyd_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "hydraulics", sample_hyd_result, "es")
        assert resp.json()["language"] == "es"


# ================================================================
# TestStuckPipeAnalyze
# ================================================================

class TestStuckPipeAnalyze:
    def test_returns_200(self, client, mock_api_coordinator, sample_sp_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "stuck-pipe", sample_sp_result, "en")
        assert resp.status_code == 200

    def test_404_well_not_found(self, client, mock_api_coordinator, sample_sp_result):
        resp = _post_analyze(client, 99999, "stuck-pipe", sample_sp_result, "en")
        assert resp.status_code == 404

    def test_response_structure(self, client, mock_api_coordinator, sample_sp_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "stuck-pipe", sample_sp_result, "en")
        assert REQUIRED_FIELDS == set(resp.json().keys())

    def test_language_es_in_response(self, client, mock_api_coordinator, sample_sp_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "stuck-pipe", sample_sp_result, "es")
        assert resp.json()["language"] == "es"


# ================================================================
# TestWellControlAnalyze
# ================================================================

class TestWellControlAnalyze:
    def test_returns_200(self, client, mock_api_coordinator, sample_wc_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "well-control", sample_wc_result, "en")
        assert resp.status_code == 200

    def test_404_well_not_found(self, client, mock_api_coordinator, sample_wc_result):
        resp = _post_analyze(client, 99999, "well-control", sample_wc_result, "en")
        assert resp.status_code == 404

    def test_response_structure(self, client, mock_api_coordinator, sample_wc_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "well-control", sample_wc_result, "en")
        assert REQUIRED_FIELDS == set(resp.json().keys())

    def test_language_es_in_response(self, client, mock_api_coordinator, sample_wc_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "well-control", sample_wc_result, "es")
        assert resp.json()["language"] == "es"


# ================================================================
# TestLanguageToggle (cross-module)
# ================================================================

class TestLanguageToggle:
    def test_default_language_is_english(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = client.post(
            f"/wells/{well['id']}/torque-drag/analyze",
            json={"result_data": sample_td_result, "params": {}},
        )
        assert resp.json()["language"] == "en"

    def test_english_td_metrics_have_english_labels(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        labels = [m["label"] for m in resp.json()["key_metrics"]]
        assert "Hookload" in labels

    def test_spanish_td_metrics_have_spanish_labels(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "es")
        labels = [m["label"] for m in resp.json()["key_metrics"]]
        assert "Carga en Gancho" in labels

    def test_spanish_wc_kmw_translated_to_pmm(self, client, mock_api_coordinator, sample_wc_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "well-control", sample_wc_result, "es")
        labels = [m["label"] for m in resp.json()["key_metrics"]]
        assert "PMM" in labels

    def test_key_metrics_is_nonempty_list(self, client, mock_api_coordinator, sample_hyd_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "hydraulics", sample_hyd_result, "en")
        metrics = resp.json()["key_metrics"]
        assert isinstance(metrics, list)
        assert len(metrics) > 0


# ================================================================
# TestResponseFields
# ================================================================

class TestResponseFields:
    def test_module_field_correct(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        assert resp.json()["module"] == "torque_drag"

    def test_timestamp_valid_iso(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        ts = resp.json()["timestamp"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.year >= 2024

    def test_agent_role_populated(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client)
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        assert resp.json()["agent_role"] != ""

    def test_well_name_matches(self, client, mock_api_coordinator, sample_td_result):
        well = _create_well(client, name="MY-SPECIAL-WELL")
        resp = _post_analyze(client, well["id"], "torque-drag", sample_td_result, "en")
        assert resp.json()["well_name"] == "MY-SPECIAL-WELL"
