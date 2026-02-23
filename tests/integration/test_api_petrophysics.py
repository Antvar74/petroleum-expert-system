"""Integration tests for petrophysics API routes."""
import pytest


SAMPLE_LAS = """~VERSION INFORMATION
 VERS.   2.0 :
 WRAP.   NO  :
~WELL INFORMATION
 WELL. TEST-1 :
 NULL. -999.25 :
~CURVE INFORMATION
 DEPT.FT :
 GR.GAPI :
 RHOB.G/C3 :
 NPHI.V/V :
 RT.OHMM :
~A DEPTH GR RHOB NPHI RT
 5000.0 35.0 2.32 0.22 45.0
 5005.0 40.0 2.35 0.20 38.0
 5010.0 30.0 2.28 0.26 70.0
"""


class TestParseLAS:
    def test_upload_las_content(self, client):
        resp = client.post("/calculate/petrophysics/parse-las", json={"las_content": SAMPLE_LAS})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 3
        assert "gr" in data["data"][0]
        assert data["data"][0]["md"] == 5000.0

    def test_empty_las_returns_400(self, client):
        resp = client.post("/calculate/petrophysics/parse-las", json={"las_content": ""})
        assert resp.status_code == 400


class TestAdvancedSaturation:
    def test_auto_archie(self, client):
        resp = client.post("/calculate/petrophysics/saturation", json={
            "phi": 0.20, "rt": 20.0, "rw": 0.05, "vsh": 0.05,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_used"] == "archie"
        assert 0 < data["sw"] < 1

    def test_auto_waxman_smits(self, client):
        resp = client.post("/calculate/petrophysics/saturation", json={
            "phi": 0.18, "rt": 10.0, "rw": 0.05, "vsh": 0.25, "rsh": 2.0,
        })
        assert resp.status_code == 200
        assert resp.json()["model_used"] == "waxman_smits"

    def test_auto_dual_water(self, client):
        resp = client.post("/calculate/petrophysics/saturation", json={
            "phi": 0.15, "rt": 5.0, "rw": 0.05, "vsh": 0.50, "rsh": 1.5,
        })
        assert resp.status_code == 200
        assert resp.json()["model_used"] == "dual_water"


class TestPickettPlot:
    def test_pickett_plot(self, client):
        resp = client.post("/calculate/petrophysics/pickett-plot", json={
            "log_data": [
                {"phi": 0.25, "rt": 10.0, "sw": 0.30},
                {"phi": 0.15, "rt": 50.0, "sw": 0.50},
            ],
            "rw": 0.05,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "points" in data
        assert "iso_sw_lines" in data
        assert len(data["points"]) == 2


class TestCrossplot:
    def test_density_neutron(self, client):
        resp = client.post("/calculate/petrophysics/crossplot", json={
            "log_data": [
                {"rhob": 2.35, "nphi": 0.22, "md": 5000},
                {"rhob": 2.30, "nphi": 0.25, "md": 5005},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "points" in data
        assert "lithology_lines" in data


class TestFullEvaluation:
    def test_evaluate(self, client):
        resp = client.post("/calculate/petrophysics/evaluate", json={
            "log_data": [
                {"md": 8000, "gr": 25, "rhob": 2.35, "nphi": 0.22, "rt": 45},
                {"md": 8005, "gr": 30, "rhob": 2.38, "nphi": 0.20, "rt": 40},
                {"md": 8010, "gr": 90, "rhob": 2.55, "nphi": 0.12, "rt": 5},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluated_data" in data
        assert "summary" in data
        assert len(data["evaluated_data"]) == 3
