"""
Integration tests for Well Control / Kill Sheet API endpoints.
"""
import pytest


def _create_well(client, name="WC-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _pre_record(client, well_id):
    return client.post(f"/wells/{well_id}/kill-sheet/pre-record", json={
        "depth_md": 10000, "depth_tvd": 9500,
        "original_mud_weight": 10.0, "casing_shoe_tvd": 5000,
        "casing_id": 8.681, "dp_od": 5.0, "dp_id": 4.276, "dp_length": 9800,
        "dc_od": 6.5, "dc_id": 2.813, "dc_length": 200,
        "scr_pressure": 800, "scr_rate": 30, "lot_emw": 14.0,
        "pump_output": 0.1, "hole_size": 8.5
    })


class TestWellControlApi:

    def test_pre_record(self, client):
        well = _create_well(client, "WC-PR-1")
        r = _pre_record(client, well["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "pre-recorded"

    def test_pre_record_nonexistent_well(self, client):
        r = client.post("/wells/99999/kill-sheet/pre-record", json={
            "depth_md": 10000, "depth_tvd": 9500
        })
        assert r.status_code == 404

    def test_get_kill_sheet_after_pre_record(self, client):
        well = _create_well(client, "WC-GET-1")
        _pre_record(client, well["id"])
        r = client.get(f"/wells/{well['id']}/kill-sheet")
        assert r.status_code == 200
        data = r.json()
        assert data["well_id"] == well["id"]
        assert data["status"] == "pre-recorded"

    def test_get_kill_sheet_no_record_404(self, client):
        well = _create_well(client, "WC-NORECORD")
        r = client.get(f"/wells/{well['id']}/kill-sheet")
        assert r.status_code == 404

    def test_calculate_no_pre_record_400(self, client):
        well = _create_well(client, "WC-NOPRE")
        r = client.post(f"/wells/{well['id']}/kill-sheet/calculate", json={
            "sidpp": 200, "sicp": 350, "pit_gain": 20
        })
        assert r.status_code == 400

    def test_calculate_wait_weight(self, client):
        well = _create_well(client, "WC-WW")
        _pre_record(client, well["id"])
        r = client.post(f"/wells/{well['id']}/kill-sheet/calculate", json={
            "sidpp": 200, "sicp": 350, "pit_gain": 20,
            "kill_method": "wait_weight"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["kill_mud_weight_ppg"] > 10.0
        assert data["icp_psi"] > 0
        assert data["fcp_psi"] > 0

    def test_calculate_drillers(self, client):
        well = _create_well(client, "WC-DM")
        _pre_record(client, well["id"])
        r = client.post(f"/wells/{well['id']}/kill-sheet/calculate", json={
            "sidpp": 200, "sicp": 350, "pit_gain": 20,
            "kill_method": "drillers"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["method_detail"]["method"] == "Driller's Method"

    def test_volumetric(self, client):
        r = client.post("/kill-sheet/volumetric", json={
            "mud_weight": 10, "sicp": 200, "tvd": 10000,
            "annular_capacity": 0.05, "lot_emw": 14.0, "casing_shoe_tvd": 5000
        })
        assert r.status_code == 200
        data = r.json()
        assert "cycles" in data
        assert len(data["cycles"]) > 0

    def test_bullhead(self, client):
        r = client.post("/kill-sheet/bullhead", json={
            "mud_weight": 10, "kill_mud_weight": 11, "depth_tvd": 10000,
            "casing_shoe_tvd": 5000, "lot_emw": 14.0,
            "dp_capacity": 0.018, "depth_md": 10000, "formation_pressure": 5720
        })
        assert r.status_code == 200
        data = r.json()
        assert "shoe_integrity" in data
