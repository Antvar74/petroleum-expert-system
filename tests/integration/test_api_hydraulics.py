"""
Integration tests for Hydraulics / ECD API endpoints.
"""
import pytest


def _create_well(client, name="HYD-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _upload_hyd_sections(client, well_id):
    sections = [
        {"section_type": "drill_pipe", "length": 9500, "od": 5.0, "id_inner": 4.276},
        {"section_type": "collar", "length": 200, "od": 6.5, "id_inner": 2.813},
        {"section_type": "annulus_dc", "length": 200, "od": 8.5, "id_inner": 6.5},
        {"section_type": "annulus_dp", "length": 9500, "od": 8.5, "id_inner": 5.0},
    ]
    return client.post(f"/wells/{well_id}/hydraulic-sections", json=sections)


def _upload_nozzles(client, well_id):
    return client.post(f"/wells/{well_id}/bit-nozzles", json={
        "nozzle_sizes": [12, 12, 12],
        "bit_diameter": 8.5
    })


class TestHydraulicsApi:

    def test_upload_sections(self, client):
        well = _create_well(client, "HYD-SEC-1")
        r = _upload_hyd_sections(client, well["id"])
        assert r.status_code == 200
        assert r.json()["sections_count"] == 4

    def test_upload_nozzles_tfa(self, client):
        well = _create_well(client, "HYD-NOZ-1")
        r = _upload_nozzles(client, well["id"])
        assert r.status_code == 200
        assert r.json()["tfa"] > 0

    def test_calculate_no_sections_400(self, client):
        well = _create_well(client, "HYD-NOSEC")
        r = client.post(f"/wells/{well['id']}/hydraulics/calculate", json={
            "flow_rate": 400, "mud_weight": 10, "tvd": 10000
        })
        assert r.status_code == 400

    def test_calculate_bingham(self, client):
        well = _create_well(client, "HYD-BING")
        _upload_hyd_sections(client, well["id"])
        _upload_nozzles(client, well["id"])
        r = client.post(f"/wells/{well['id']}/hydraulics/calculate", json={
            "flow_rate": 400, "mud_weight": 10, "pv": 15, "yp": 10, "tvd": 10000,
            "rheology_model": "bingham_plastic"
        })
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "ecd" in data
        assert data["summary"]["total_spp_psi"] > 0

    def test_calculate_power_law(self, client):
        well = _create_well(client, "HYD-PL")
        _upload_hyd_sections(client, well["id"])
        _upload_nozzles(client, well["id"])
        r = client.post(f"/wells/{well['id']}/hydraulics/calculate", json={
            "flow_rate": 400, "mud_weight": 10, "tvd": 10000,
            "rheology_model": "power_law", "n": 0.5, "k": 300
        })
        assert r.status_code == 200

    def test_surge_swab(self, client):
        well = _create_well(client, "HYD-SS")
        r = client.post(f"/wells/{well['id']}/hydraulics/surge-swab", json={
            "mud_weight": 10, "pv": 15, "yp": 10, "tvd": 10000,
            "pipe_od": 5.0, "pipe_id": 4.276, "hole_id": 8.5,
            "pipe_velocity_fpm": 90
        })
        assert r.status_code == 200
        data = r.json()
        assert data["surge_ecd_ppg"] >= 10.0
        assert data["swab_ecd_ppg"] <= 10.0

    def test_result_saved_in_db(self, client, db_session):
        """After calculation, a HydraulicResult should be saved in DB."""
        from models.models_v2 import HydraulicResult

        well = _create_well(client, "HYD-DBCHECK")
        _upload_hyd_sections(client, well["id"])
        _upload_nozzles(client, well["id"])
        client.post(f"/wells/{well['id']}/hydraulics/calculate", json={
            "flow_rate": 400, "mud_weight": 10, "pv": 15, "yp": 10, "tvd": 10000
        })
        results = db_session.query(HydraulicResult).filter(
            HydraulicResult.well_id == well["id"]
        ).all()
        assert len(results) >= 1
