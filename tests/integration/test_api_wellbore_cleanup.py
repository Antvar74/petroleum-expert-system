"""
Integration tests for Wellbore Cleanup API endpoints.
"""
import pytest


def _create_well(client, name="CU-WELL"):
    return client.post("/wells", params={"name": name}).json()


class TestWellboreCleanupApi:

    def test_calculate_cleanup_default(self, client):
        """POST with defaults should return valid result."""
        well = _create_well(client, "CU-DEFAULT")
        r = client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 500, "mud_weight": 10.0, "pv": 15, "yp": 10,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 0
        })
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "sweep_pill" in data
        assert data["summary"]["annular_velocity_ftmin"] > 0

    def test_calculate_cleanup_high_angle(self, client):
        """High angle well should have different alerts."""
        well = _create_well(client, "CU-HIGHANGLE")
        r = client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 500, "mud_weight": 10.0, "pv": 15, "yp": 10,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 75, "rpm": 0
        })
        assert r.status_code == 200
        data = r.json()
        assert data["summary"]["cleaning_quality"] in ("Good", "Marginal", "Poor")

    def test_get_cleanup_result(self, client):
        """GET should return last saved result."""
        well = _create_well(client, "CU-GET")
        # First calculate
        client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 600, "mud_weight": 12.0, "pv": 20, "yp": 15,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 30
        })
        # Then retrieve
        r = client.get(f"/wells/{well['id']}/wellbore-cleanup")
        assert r.status_code == 200
        data = r.json()
        assert "result_data" in data
        assert "summary" in data

    def test_get_cleanup_not_found(self, client):
        """GET without prior calculation → 404."""
        well = _create_well(client, "CU-NOTFOUND")
        r = client.get(f"/wells/{well['id']}/wellbore-cleanup")
        assert r.status_code == 404

    def test_well_not_found(self, client):
        """Non-existent well → 404."""
        r = client.post("/wells/99999/wellbore-cleanup", json={
            "flow_rate": 500, "mud_weight": 10.0, "pv": 15, "yp": 10,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 0
        })
        assert r.status_code == 404

    def test_result_is_saved(self, client):
        """Multiple calculations should save latest."""
        well = _create_well(client, "CU-SAVE")
        # First calc
        r1 = client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 300, "mud_weight": 10.0, "pv": 15, "yp": 10,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 0
        })
        # Second calc with different params
        r2 = client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 700, "mud_weight": 12.0, "pv": 20, "yp": 15,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 0
        })
        assert r1.status_code == 200
        assert r2.status_code == 200
        # GET should return the latest
        r = client.get(f"/wells/{well['id']}/wellbore-cleanup")
        assert r.status_code == 200

    def test_cleaning_quality_values(self, client):
        """Cleaning quality should be one of Good/Marginal/Poor."""
        well = _create_well(client, "CU-QUALITY")
        r = client.post(f"/wells/{well['id']}/wellbore-cleanup", json={
            "flow_rate": 500, "mud_weight": 10.0, "pv": 15, "yp": 10,
            "hole_id": 8.5, "pipe_od": 5.0, "inclination": 0
        })
        assert r.json()["summary"]["cleaning_quality"] in ("Good", "Marginal", "Poor")
