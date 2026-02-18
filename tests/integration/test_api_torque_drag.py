"""
Integration tests for Torque & Drag API endpoints.
"""
import pytest


def _create_well(client, name="TD-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _upload_survey(client, well_id):
    stations = [
        {"md": 0, "inclination": 0, "azimuth": 0},
        {"md": 3000, "inclination": 0, "azimuth": 0},
        {"md": 6000, "inclination": 30, "azimuth": 45},
        {"md": 10000, "inclination": 30, "azimuth": 45},
    ]
    return client.post(f"/wells/{well_id}/survey", json=stations)


def _upload_drillstring(client, well_id):
    sections = [
        {"section_name": "DP", "od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9800, "order_from_bit": 2},
        {"section_name": "DC", "od": 6.5, "id_inner": 2.813, "weight": 91.0, "length": 200, "order_from_bit": 1},
    ]
    return client.post(f"/wells/{well_id}/drillstring", json=sections)


class TestTorqueDragApi:

    def test_upload_survey(self, client):
        well = _create_well(client, "TD-SURVEY-1")
        r = _upload_survey(client, well["id"])
        assert r.status_code == 200
        data = r.json()
        assert data["stations_count"] == 4
        # Stations should have computed TVD/DLS
        for s in data["stations"]:
            assert "tvd" in s
            assert "dls" in s

    def test_get_survey(self, client):
        well = _create_well(client, "TD-GETSURVEY")
        _upload_survey(client, well["id"])
        r = client.get(f"/wells/{well['id']}/survey")
        assert r.status_code == 200
        stations = r.json()
        assert len(stations) == 4
        # Ordered by MD
        mds = [s["md"] for s in stations]
        assert mds == sorted(mds)

    def test_upload_drillstring(self, client):
        well = _create_well(client, "TD-DS-1")
        r = _upload_drillstring(client, well["id"])
        assert r.status_code == 200
        assert r.json()["sections_count"] == 2

    def test_get_drillstring(self, client):
        well = _create_well(client, "TD-GETDS")
        _upload_drillstring(client, well["id"])
        r = client.get(f"/wells/{well['id']}/drillstring")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_td_no_survey_400(self, client):
        well = _create_well(client, "TD-NOSURVEY")
        _upload_drillstring(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag", json={"operation": "trip_out"})
        assert r.status_code == 400

    def test_td_no_drillstring_400(self, client):
        well = _create_well(client, "TD-NODS")
        _upload_survey(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag", json={"operation": "trip_out"})
        assert r.status_code == 400

    def test_td_trip_out(self, client):
        well = _create_well(client, "TD-TRIPOUT")
        _upload_survey(client, well["id"])
        _upload_drillstring(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag", json={
            "operation": "trip_out", "mud_weight": 10.0
        })
        assert r.status_code == 200
        data = r.json()
        assert "station_results" in data
        assert "summary" in data

    def test_td_rotating_torque(self, client):
        well = _create_well(client, "TD-ROT")
        _upload_survey(client, well["id"])
        _upload_drillstring(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag", json={
            "operation": "rotating", "mud_weight": 10.0, "wob": 15, "rpm": 120
        })
        assert r.status_code == 200
        assert r.json()["summary"]["surface_torque_ftlb"] > 0

    def test_td_nonexistent_well_404(self, client):
        r = client.post("/wells/99999/torque-drag", json={"operation": "trip_out"})
        assert r.status_code in (400, 404)

    def test_back_calculate_friction(self, client):
        well = _create_well(client, "TD-BACKCALC")
        _upload_survey(client, well["id"])
        _upload_drillstring(client, well["id"])
        r = client.post("/torque-drag/back-calculate", json={
            "well_id": well["id"],
            "measured_hookload": 200.0,
            "operation": "trip_out",
            "mud_weight": 10.0
        })
        assert r.status_code == 200
        data = r.json()
        assert "friction_factor" in data
