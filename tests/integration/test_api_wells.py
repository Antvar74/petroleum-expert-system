"""
Integration tests for base Wells CRUD endpoints.
"""
import pytest


class TestWellsCrud:

    def test_create_well(self, client):
        r = client.post("/wells", params={"name": "INTEGRATION-WELL-1"})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "INTEGRATION-WELL-1"

    def test_create_duplicate_well(self, client):
        client.post("/wells", params={"name": "DUP-WELL"})
        r2 = client.post("/wells", params={"name": "DUP-WELL"})
        assert r2.status_code in (400, 409, 500)

    def test_get_wells(self, client):
        client.post("/wells", params={"name": "LIST-WELL"})
        r = client.get("/wells")
        assert r.status_code == 200
        wells = r.json()
        assert any(w["name"] == "LIST-WELL" for w in wells)

    def test_delete_well(self, client):
        cr = client.post("/wells", params={"name": "DEL-WELL"})
        well_id = cr.json()["id"]
        r = client.delete(f"/wells/{well_id}")
        assert r.status_code == 200

    def test_delete_nonexistent_well(self, client):
        r = client.delete("/wells/99999")
        assert r.status_code in (404, 200)
