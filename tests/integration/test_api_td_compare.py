"""
Integration tests for Torque & Drag Compare API endpoint.
Tests: POST /wells/{well_id}/torque-drag/compare
"""
import pytest


def _create_well(client, name="TDC-WELL"):
    return client.post("/wells", params={"name": name}).json()


def _upload_survey(client, well_id):
    """Directional survey for meaningful friction differences between operations."""
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


def _setup_well(client, name="TDC-FULL"):
    """Create well with survey + drillstring, return well dict."""
    well = _create_well(client, name)
    _upload_survey(client, well["id"])
    _upload_drillstring(client, well["id"])
    return well


class TestTorqueDragCompare:

    # ----------------------------------------------------------------
    # Happy path
    # ----------------------------------------------------------------

    def test_compare_returns_200(self, client):
        well = _setup_well(client, "TDC-200")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "trip_in"]
        })
        assert r.status_code == 200

    def test_compare_default_operations(self, client):
        """POST with empty body uses default 5 operations."""
        well = _setup_well(client, "TDC-DEFAULT")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={})
        assert r.status_code == 200
        data = r.json()
        ops = data["operations"]
        for expected_op in ["trip_out", "trip_in", "rotating", "sliding", "lowering"]:
            assert expected_op in ops, f"Missing default operation: {expected_op}"

    def test_compare_response_structure(self, client):
        """Response must have operations (dict), combined (list), summary_comparison (list)."""
        well = _setup_well(client, "TDC-STRUCT")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "trip_in"]
        })
        data = r.json()
        assert isinstance(data["operations"], dict)
        assert isinstance(data["combined"], list)
        assert isinstance(data["summary_comparison"], list)

        # operations keys match requested
        assert "trip_out" in data["operations"]
        assert "trip_in" in data["operations"]

        # summary_comparison has one entry per operation
        assert len(data["summary_comparison"]) == 2
        for entry in data["summary_comparison"]:
            assert "operation" in entry
            assert "hookload_klb" in entry
            assert "torque_ftlb" in entry

    def test_compare_combined_has_md_and_forces(self, client):
        """Each row in combined[] should have md plus force values per operation."""
        well = _setup_well(client, "TDC-COMBINED")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "trip_in"]
        })
        data = r.json()
        assert len(data["combined"]) > 0
        for row in data["combined"]:
            assert "md" in row
            assert isinstance(row["md"], (int, float))
            # At least one operation should have a force value
            has_force = "trip_out" in row or "trip_in" in row
            assert has_force

    def test_compare_summary_hookload_positive(self, client):
        """Hookload should be positive for all standard operations."""
        well = _setup_well(client, "TDC-HOOKPOS")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "trip_in", "rotating"]
        })
        data = r.json()
        for entry in data["summary_comparison"]:
            assert entry["hookload_klb"] > 0, \
                f"Hookload should be positive for {entry['operation']}"

    def test_compare_trip_out_gt_trip_in(self, client):
        """In a directional well, trip_out hookload > trip_in hookload."""
        well = _setup_well(client, "TDC-OUTGTIN")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "trip_in"]
        })
        data = r.json()
        summary = {e["operation"]: e for e in data["summary_comparison"]}
        assert summary["trip_out"]["hookload_klb"] > summary["trip_in"]["hookload_klb"]

    def test_compare_custom_operations(self, client):
        """Only requested operations appear in response."""
        well = _setup_well(client, "TDC-CUSTOM")
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out", "rotating"]
        })
        data = r.json()
        assert set(data["operations"].keys()) == {"trip_out", "rotating"}
        assert len(data["summary_comparison"]) == 2

    def test_compare_custom_friction(self, client):
        """Different friction factors should produce different hookloads."""
        well = _setup_well(client, "TDC-FRICTION")

        r_low = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out"],
            "friction_cased": 0.15, "friction_open": 0.20
        })
        r_high = client.post(f"/wells/{well['id']}/torque-drag/compare", json={
            "operations": ["trip_out"],
            "friction_cased": 0.40, "friction_open": 0.50
        })

        hl_low = r_low.json()["summary_comparison"][0]["hookload_klb"]
        hl_high = r_high.json()["summary_comparison"][0]["hookload_klb"]
        assert hl_high > hl_low, "Higher friction should produce higher trip-out hookload"

    # ----------------------------------------------------------------
    # Error handling
    # ----------------------------------------------------------------

    def test_compare_no_survey_400(self, client):
        """Well without survey → 400."""
        well = _create_well(client, "TDC-NOSURV")
        _upload_drillstring(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={})
        assert r.status_code == 400

    def test_compare_no_drillstring_400(self, client):
        """Well without drillstring → 400."""
        well = _create_well(client, "TDC-NODS")
        _upload_survey(client, well["id"])
        r = client.post(f"/wells/{well['id']}/torque-drag/compare", json={})
        assert r.status_code == 400

    def test_compare_nonexistent_well_404(self, client):
        """Nonexistent well → 404."""
        r = client.post("/wells/99999/torque-drag/compare", json={})
        assert r.status_code == 404
