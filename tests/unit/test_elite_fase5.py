"""
Phase 5 Elite Tests — API Endpoints for Phases 1-4.

Tests the new REST API endpoints that expose Phase 1-4 engine features.
Uses FastAPI TestClient for endpoint testing.
"""

import pytest
from fastapi.testclient import TestClient

# Import the app
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from api_main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════
# Well Control Endpoints
# ═══════════════════════════════════════════════════════════════

class TestKickToleranceEndpoint:
    """Test /well-control/kick-tolerance endpoint."""

    def test_returns_200(self):
        resp = client.post("/well-control/kick-tolerance", json={
            "mud_weight": 10.0, "shoe_tvd": 5000, "lot_emw": 14.0,
            "well_depth_tvd": 10000
        })
        assert resp.status_code == 200

    def test_result_has_kt_bbl(self):
        resp = client.post("/well-control/kick-tolerance", json={
            "mud_weight": 10.0, "shoe_tvd": 5000, "lot_emw": 14.0,
            "well_depth_tvd": 10000
        })
        data = resp.json()
        assert "kick_tolerance_bbl" in data
        assert data["kick_tolerance_bbl"] > 0


class TestBariteEndpoint:
    """Test /well-control/barite-requirements endpoint."""

    def test_returns_200(self):
        resp = client.post("/well-control/barite-requirements", json={
            "current_mud_weight": 10.0, "target_mud_weight": 12.0,
            "system_volume_bbl": 500
        })
        assert resp.status_code == 200

    def test_result_has_sacks(self):
        resp = client.post("/well-control/barite-requirements", json={
            "current_mud_weight": 10.0, "target_mud_weight": 12.0,
            "system_volume_bbl": 500
        })
        data = resp.json()
        assert "barite_sacks" in data
        assert data["barite_sacks"] > 0


class TestZFactorEndpoint:
    """Test /well-control/z-factor endpoint."""

    def test_returns_200(self):
        resp = client.post("/well-control/z-factor", json={
            "pressure": 5000, "temperature": 200
        })
        assert resp.status_code == 200

    def test_z_in_range(self):
        resp = client.post("/well-control/z-factor", json={
            "pressure": 5000, "temperature": 200
        })
        data = resp.json()
        assert "z_factor" in data
        assert 0.5 < data["z_factor"] < 1.5


# ═══════════════════════════════════════════════════════════════
# Hydraulics Endpoints
# ═══════════════════════════════════════════════════════════════

class TestBHABreakdownEndpoint:
    """Test /hydraulics/bha-breakdown endpoint."""

    def test_returns_200(self):
        resp = client.post("/hydraulics/bha-breakdown", json={
            "bha_tools": [
                {"tool_name": "DC", "tool_type": "collar",
                 "od": 6.75, "id_inner": 2.81, "length": 90, "loss_coefficient": 1.0}
            ],
            "flow_rate": 400, "mud_weight": 12.0, "pv": 20, "yp": 12
        })
        assert resp.status_code == 200

    def test_has_breakdown(self):
        resp = client.post("/hydraulics/bha-breakdown", json={
            "bha_tools": [
                {"tool_name": "DC", "tool_type": "collar",
                 "od": 6.75, "id_inner": 2.81, "length": 90, "loss_coefficient": 1.0}
            ],
            "flow_rate": 400, "mud_weight": 12.0, "pv": 20, "yp": 12
        })
        data = resp.json()
        assert "tools_breakdown" in data
        assert len(data["tools_breakdown"]) == 1


class TestFitHBEndpoint:
    """Test /hydraulics/fit-herschel-bulkley endpoint."""

    def test_returns_200(self):
        resp = client.post("/hydraulics/fit-herschel-bulkley", json={
            "fann_readings": {"r600": 68, "r300": 42, "r200": 34,
                              "r100": 24, "r6": 8, "r3": 6}
        })
        assert resp.status_code == 200

    def test_has_parameters(self):
        resp = client.post("/hydraulics/fit-herschel-bulkley", json={
            "fann_readings": {"r600": 68, "r300": 42, "r200": 34,
                              "r100": 24, "r6": 8, "r3": 6}
        })
        data = resp.json()
        assert "tau_0" in data
        assert "k_hb" in data
        assert "n_hb" in data


# ═══════════════════════════════════════════════════════════════
# Stuck Pipe Endpoints
# ═══════════════════════════════════════════════════════════════

class TestDiffStickingEndpoint:
    """Test /stuck-pipe/differential-sticking endpoint."""

    def test_returns_200(self):
        resp = client.post("/stuck-pipe/differential-sticking", json={
            "ecd_ppg": 13.0, "pore_pressure_ppg": 10.0,
            "contact_length_ft": 30, "pipe_od_in": 5.0, "tvd_ft": 10000
        })
        assert resp.status_code == 200

    def test_has_sticking_force(self):
        resp = client.post("/stuck-pipe/differential-sticking", json={
            "ecd_ppg": 13.0, "pore_pressure_ppg": 10.0,
            "contact_length_ft": 30, "pipe_od_in": 5.0, "tvd_ft": 10000
        })
        data = resp.json()
        assert "sticking_force_lbs" in data
        assert data["sticking_force_lbs"] > 0


class TestPackoffRiskEndpoint:
    """Test /stuck-pipe/packoff-risk endpoint."""

    def test_returns_200(self):
        resp = client.post("/stuck-pipe/packoff-risk", json={
            "hci": 0.5, "cuttings_concentration_pct": 6.0, "inclination": 60
        })
        assert resp.status_code == 200

    def test_has_risk_level(self):
        resp = client.post("/stuck-pipe/packoff-risk", json={
            "hci": 0.5, "cuttings_concentration_pct": 6.0, "inclination": 60
        })
        data = resp.json()
        assert "risk_level" in data
        assert data["risk_level"] in ("LOW", "MODERATE", "HIGH")


# ═══════════════════════════════════════════════════════════════
# Workover Endpoints
# ═══════════════════════════════════════════════════════════════

class TestCTElongationEndpoint:
    """Test /workover/ct-elongation endpoint."""

    def test_returns_200(self):
        resp = client.post("/workover/ct-elongation", json={
            "ct_od": 2.0, "ct_id": 1.688, "ct_length": 15000,
            "weight_per_ft": 3.24, "mud_weight": 8.6,
            "delta_p_internal": 3000, "delta_t": 100
        })
        assert resp.status_code == 200

    def test_has_total(self):
        resp = client.post("/workover/ct-elongation", json={
            "ct_od": 2.0, "ct_id": 1.688, "ct_length": 15000,
            "weight_per_ft": 3.24, "mud_weight": 8.6,
            "delta_p_internal": 3000, "delta_t": 100
        })
        data = resp.json()
        assert "dL_total_ft" in data


class TestCTFatigueEndpoint:
    """Test /workover/ct-fatigue endpoint."""

    def test_returns_200(self):
        resp = client.post("/workover/ct-fatigue", json={
            "ct_od": 2.0, "wall_thickness": 0.156,
            "reel_diameter": 72, "internal_pressure": 5000
        })
        assert resp.status_code == 200

    def test_has_cycles(self):
        resp = client.post("/workover/ct-fatigue", json={
            "ct_od": 2.0, "wall_thickness": 0.156,
            "reel_diameter": 72, "internal_pressure": 5000
        })
        data = resp.json()
        assert "cycles_to_failure" in data
        assert data["cycles_to_failure"] > 0
