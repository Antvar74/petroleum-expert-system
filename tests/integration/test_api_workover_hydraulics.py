"""
Integration tests for Workover Hydraulics (CT) API endpoints.
"""
import pytest


def _create_well(client, name="WH-WELL"):
    return client.post("/wells", params={"name": name}).json()


class TestWorkoverHydraulicsApi:

    def test_calculate_workover_default_params(self, client):
        """POST with minimal data (empty body uses defaults) should return valid result."""
        well = _create_well(client, "WH-DEFAULT")
        r = client.post(f"/wells/{well['id']}/workover-hydraulics", json={})
        assert r.status_code == 200
        data = r.json()
        # Top-level keys returned by the endpoint
        assert "id" in data
        assert "well_id" in data
        assert "summary" in data
        assert "hydraulics" in data
        assert "ct_dimensions" in data
        assert "weight_analysis" in data
        assert "snubbing" in data
        assert "max_reach" in data
        assert "kill_data" in data
        assert "alerts" in data
        # Summary structure
        summary = data["summary"]
        assert "total_pressure_loss_psi" in summary
        assert "buoyed_weight_lb" in summary
        assert "max_reach_ft" in summary
        assert "pipe_light" in summary
        assert summary["total_pressure_loss_psi"] >= 0

    def test_calculate_workover_custom_params(self, client):
        """POST with custom CT parameters should reflect those values in the result."""
        well = _create_well(client, "WH-CUSTOM")
        payload = {
            "flow_rate": 120,
            "mud_weight": 9.5,
            "pv": 18,
            "yp": 12,
            "ct_od": 2.375,
            "wall_thickness": 0.190,
            "ct_length": 12000,
            "hole_id": 6.0,
            "tvd": 11000,
            "inclination": 30,
            "friction_factor": 0.30,
            "wellhead_pressure": 0,
            "reservoir_pressure": 6000,
            "yield_strength_psi": 90000,
        }
        r = client.post(f"/wells/{well['id']}/workover-hydraulics", json=payload)
        assert r.status_code == 200
        data = r.json()
        # Verify the engine used the custom CT dimensions
        ct_dims = data["ct_dimensions"]
        assert ct_dims["ct_od_in"] == 2.375
        assert ct_dims["wall_thickness_in"] == 0.190
        # CT ID should be OD - 2*wall = 2.375 - 0.380 = 1.995
        assert ct_dims["ct_id_in"] == pytest.approx(1.995, abs=0.001)
        # Parameters echoed back
        params = data["parameters"]
        assert params["flow_rate_gpm"] == 120
        assert params["mud_weight_ppg"] == 9.5
        assert params["inclination_deg"] == 30

    def test_calculate_workover_stores_result(self, client):
        """POST should persist the result; subsequent GET should retrieve it."""
        well = _create_well(client, "WH-STORE")
        # Calculate
        r_post = client.post(f"/wells/{well['id']}/workover-hydraulics", json={
            "flow_rate": 80, "mud_weight": 8.6, "ct_od": 2.0,
            "wall_thickness": 0.156, "ct_length": 10000,
            "hole_id": 4.892, "tvd": 10000
        })
        assert r_post.status_code == 200
        post_data = r_post.json()
        assert "id" in post_data

        # Retrieve
        r_get = client.get(f"/wells/{well['id']}/workover-hydraulics")
        assert r_get.status_code == 200
        get_data = r_get.json()
        assert "result_data" in get_data
        assert "summary" in get_data
        assert get_data["well_id"] == well["id"]

    def test_get_workover_no_results(self, client):
        """GET before any calculation should return 404."""
        well = _create_well(client, "WH-NORESULT")
        r = client.get(f"/wells/{well['id']}/workover-hydraulics")
        assert r.status_code == 404

    def test_calculate_workover_with_pressure(self, client):
        """POST with wellhead_pressure > 0 should trigger snubbing calculation."""
        well = _create_well(client, "WH-SNUB")
        r = client.post(f"/wells/{well['id']}/workover-hydraulics", json={
            "flow_rate": 80,
            "mud_weight": 8.6,
            "ct_od": 2.0,
            "wall_thickness": 0.156,
            "ct_length": 500,
            "hole_id": 4.892,
            "tvd": 500,
            "wellhead_pressure": 3000,
            "reservoir_pressure": 3000,
        })
        assert r.status_code == 200
        data = r.json()
        snubbing = data["snubbing"]
        assert snubbing["wellhead_pressure_psi"] == 3000
        assert snubbing["pressure_force_lb"] > 0
        # With high pressure and short/light CT, pipe should be light
        assert snubbing["pipe_light"] is True
        assert snubbing["snubbing_force_lb"] > 0

    def test_workover_alerts_generated(self, client):
        """POST with parameters known to trigger alerts should produce non-empty alerts list."""
        well = _create_well(client, "WH-ALERTS")
        # Short CT length + high wellhead pressure => pipe-light alert
        # Low mud weight + high reservoir pressure => underbalanced alert
        r = client.post(f"/wells/{well['id']}/workover-hydraulics", json={
            "flow_rate": 80,
            "mud_weight": 8.0,
            "pv": 12,
            "yp": 8,
            "ct_od": 2.0,
            "wall_thickness": 0.156,
            "ct_length": 200,
            "hole_id": 4.892,
            "tvd": 10000,
            "wellhead_pressure": 5000,
            "reservoir_pressure": 8000,
        })
        assert r.status_code == 200
        data = r.json()
        alerts = data["alerts"]
        assert isinstance(alerts, list)
        assert len(alerts) > 0
        # Verify at least one expected alert substring is present
        alert_text = " ".join(alerts).lower()
        assert "pipe-light" in alert_text or "underbalanced" in alert_text or "snubbing" in alert_text

    def test_calculate_workover_invalid_well(self, client):
        """POST to a non-existent well_id should return 404."""
        r = client.post("/wells/99999/workover-hydraulics", json={
            "flow_rate": 80, "mud_weight": 8.6, "ct_od": 2.0,
            "wall_thickness": 0.156, "ct_length": 10000,
            "hole_id": 4.892, "tvd": 10000
        })
        assert r.status_code == 404
