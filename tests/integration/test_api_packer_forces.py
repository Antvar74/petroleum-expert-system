"""
Integration tests for Packer Forces API endpoints.
"""
import pytest


def _create_well(client, name="PF-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _standard_packer_input():
    return {
        "tubing_od": 2.875,
        "tubing_id": 2.441,
        "tubing_weight": 6.5,
        "tubing_length": 10000,
        "seal_bore_id": 3.25,
        "initial_tubing_pressure": 0,
        "final_tubing_pressure": 3000,
        "initial_annulus_pressure": 0,
        "final_annulus_pressure": 0,
        "initial_temperature": 80,
        "final_temperature": 250,
        "packer_depth_tvd": 10000,
    }


class TestPackerForcesApi:

    def test_calculate_packer_forces(self, client):
        """POST with standard params should return valid result."""
        well = _create_well(client, "PF-CALC")
        r = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "force_components" in data
        assert "movements" in data

    def test_force_direction(self, client):
        """Result should indicate Tension or Compression."""
        well = _create_well(client, "PF-DIR")
        r = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        assert r.json()["summary"]["force_direction"] in ("Tension", "Compression")

    def test_buckling_status(self, client):
        """Buckling status should be valid."""
        well = _create_well(client, "PF-BUCK")
        r = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        assert r.json()["summary"]["buckling_status"] in ("OK", "Sinusoidal Buckling", "Helical Buckling")

    def test_get_packer_forces(self, client):
        """GET should return saved result."""
        well = _create_well(client, "PF-GET")
        client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        r = client.get(f"/wells/{well['id']}/packer-forces")
        assert r.status_code == 200
        assert "result_data" in r.json()

    def test_get_not_found(self, client):
        """GET without prior calculation → 404."""
        well = _create_well(client, "PF-NOTFOUND")
        r = client.get(f"/wells/{well['id']}/packer-forces")
        assert r.status_code == 404

    def test_well_not_found(self, client):
        """Non-existent well → 404."""
        r = client.post("/wells/99999/packer-forces", json=_standard_packer_input())
        assert r.status_code == 404

    def test_no_pressure_change_minimal(self, client):
        """No changes should produce minimal forces."""
        well = _create_well(client, "PF-MINIMAL")
        params = _standard_packer_input()
        params["final_tubing_pressure"] = 0
        params["final_temperature"] = 80
        r = client.post(f"/wells/{well['id']}/packer-forces", json=params)
        assert r.status_code == 200
        total = r.json()["summary"]["total_force_lbs"]
        assert abs(total) < 500  # minimal force

    def test_force_components_present(self, client):
        """Force components should include piston, ballooning, temperature."""
        well = _create_well(client, "PF-COMPONENTS")
        r = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        fc = r.json()["force_components"]
        assert "piston" in fc
        assert "ballooning" in fc
        assert "temperature" in fc
        assert "total" in fc

    def test_movements_present(self, client):
        """Movements should include all components."""
        well = _create_well(client, "PF-MOVEMENTS")
        r = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        mv = r.json()["movements"]
        assert "piston_in" in mv
        assert "ballooning_in" in mv
        assert "thermal_in" in mv
        assert "total_in" in mv

    def test_result_is_saved(self, client):
        """Multiple calculations should save results."""
        well = _create_well(client, "PF-SAVE")
        r1 = client.post(f"/wells/{well['id']}/packer-forces", json=_standard_packer_input())
        assert r1.status_code == 200
        assert "id" in r1.json()
