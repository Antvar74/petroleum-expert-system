"""
Integration tests for Sand Control API endpoints.
"""
import pytest


def _create_well(client, name="SC-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _standard_sand_control_input():
    """Minimal payload — relies on API defaults for most fields."""
    return {
        "ucs_psi": 500,
        "friction_angle_deg": 30,
        "reservoir_pressure_psi": 4500,
        "overburden_stress_psi": 10000,
        "formation_permeability_md": 500,
    }


def _custom_psd_input():
    """Payload with explicitly specified sieve/PSD data."""
    return {
        "sieve_sizes_mm": [4.75, 2.0, 0.85, 0.425, 0.25, 0.15, 0.075],
        "cumulative_passing_pct": [100, 98, 85, 55, 30, 10, 1],
        "hole_id": 8.5,
        "screen_od": 5.5,
        "interval_length": 75,
        "ucs_psi": 800,
        "friction_angle_deg": 35,
        "reservoir_pressure_psi": 5000,
        "overburden_stress_psi": 12000,
        "formation_permeability_md": 1000,
        "wellbore_type": "openhole",
    }


class TestSandControlApi:

    def test_calculate_sand_control_default(self, client):
        """POST with minimal params should return 200 and valid structure."""
        well = _create_well(client, "SC-DEFAULT")
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "psd" in data
        assert "gravel" in data
        assert "screen" in data
        assert "drawdown" in data
        assert "volume" in data
        assert "skin" in data
        assert "completion" in data
        assert "alerts" in data

    def test_calculate_sand_control_custom_psd(self, client):
        """POST with custom sieve data should return 200 and reflect custom PSD."""
        well = _create_well(client, "SC-CUSTOMPSD")
        payload = _custom_psd_input()
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=payload,
        )
        assert r.status_code == 200
        data = r.json()
        psd = data["psd"]
        # Custom data has 7 sieve points
        assert psd["sieve_count"] == 7
        # d50 should differ from the default PSD
        assert psd["d50_mm"] > 0

    def test_calculate_stores_result(self, client):
        """POST then GET should return the stored result."""
        well = _create_well(client, "SC-STORE")
        post_r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert post_r.status_code == 200
        post_id = post_r.json()["id"]

        get_r = client.get(f"/wells/{well['id']}/sand-control")
        assert get_r.status_code == 200
        get_data = get_r.json()
        assert "result_data" in get_data
        assert get_data["id"] == post_id

    def test_get_sand_control_no_results(self, client):
        """GET without prior POST should return 404."""
        well = _create_well(client, "SC-NORESULT")
        r = client.get(f"/wells/{well['id']}/sand-control")
        assert r.status_code == 404

    def test_psd_analysis_present(self, client):
        """PSD section should contain d50, d10, d90, and Cu."""
        well = _create_well(client, "SC-PSD")
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 200
        psd = r.json()["psd"]
        assert "d50_mm" in psd
        assert "d10_mm" in psd
        assert "d90_mm" in psd
        assert "uniformity_coefficient" in psd
        assert psd["d50_mm"] > 0
        assert psd["d10_mm"] > 0
        assert psd["d90_mm"] > 0
        assert psd["uniformity_coefficient"] > 0

    def test_gravel_selection_present(self, client):
        """Gravel section should contain recommended_pack."""
        well = _create_well(client, "SC-GRAVEL")
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 200
        gravel = r.json()["gravel"]
        assert "recommended_pack" in gravel
        assert "gravel_min_mm" in gravel
        assert "gravel_max_mm" in gravel
        assert gravel["recommended_pack"]  # non-empty string

    def test_drawdown_analysis_present(self, client):
        """Drawdown section should contain critical_drawdown_psi and sanding_risk."""
        well = _create_well(client, "SC-DRAWDOWN")
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 200
        dd = r.json()["drawdown"]
        assert "critical_drawdown_psi" in dd
        assert "sanding_risk" in dd
        assert dd["critical_drawdown_psi"] >= 0
        assert dd["sanding_risk"] in (
            "Very High", "High", "Moderate", "Low", "Very Low"
        )

    def test_completion_evaluation_present(self, client):
        """Completion section should contain a recommended method."""
        well = _create_well(client, "SC-COMPLETION")
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 200
        comp = r.json()["completion"]
        assert "recommended" in comp
        assert "methods" in comp
        assert len(comp["methods"]) > 0

    def test_sand_control_alerts(self, client):
        """Weak formation with low effective stress should trigger sanding alerts."""
        well = _create_well(client, "SC-ALERTS")
        payload = _standard_sand_control_input()
        payload["ucs_psi"] = 50  # very weak formation
        payload["reservoir_pressure_psi"] = 7000  # high pore pressure
        payload["overburden_stress_psi"] = 7500   # low effective stress
        r = client.post(
            f"/wells/{well['id']}/sand-control",
            json=payload,
        )
        assert r.status_code == 200
        data = r.json()
        alerts = data["alerts"]
        assert isinstance(alerts, list)
        assert len(alerts) > 0
        # At least one alert should mention sanding risk or weak formation
        combined = " ".join(alerts).lower()
        assert "sanding" in combined or "weak" in combined or "risk" in combined

    def test_invalid_well(self, client):
        """POST to nonexistent well_id should return 404."""
        r = client.post(
            "/wells/99999/sand-control",
            json=_standard_sand_control_input(),
        )
        assert r.status_code == 404
