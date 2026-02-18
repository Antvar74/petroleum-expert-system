"""
Integration tests for Stuck Pipe API endpoints.
"""
import pytest


class TestStuckPipeApi:

    def test_diagnose_start(self, client):
        r = client.post("/stuck-pipe/diagnose/start")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "question"
        assert data["node_id"] == "start"

    def test_diagnose_answer_yes(self, client):
        r = client.post("/stuck-pipe/diagnose/answer", json={
            "node_id": "start", "answer": "yes"
        })
        assert r.status_code == 200
        assert r.json()["type"] == "question"
        assert r.json()["node_id"] == "q_rotate"

    def test_diagnose_to_result(self, client):
        """Navigate through tree to a result."""
        # Path: start→no, q_no_circ→no, q_no_circ_no_rotate→yes → Differential
        client.post("/stuck-pipe/diagnose/answer", json={"node_id": "start", "answer": "no"})
        client.post("/stuck-pipe/diagnose/answer", json={"node_id": "q_no_circ", "answer": "no"})
        r = client.post("/stuck-pipe/diagnose/answer", json={"node_id": "q_no_circ_no_rotate", "answer": "yes"})
        assert r.status_code == 200
        assert r.json()["type"] == "result"
        assert r.json()["mechanism"] == "Differential Sticking"

    def test_free_point(self, client):
        r = client.post("/stuck-pipe/free-point", json={
            "pipe_od": 5.0, "pipe_id": 4.276, "pipe_grade": "S135",
            "stretch_inches": 2.0, "pull_force_lbs": 50000
        })
        assert r.status_code == 200
        assert r.json()["free_point_depth_ft"] > 0

    def test_free_point_zero_inputs(self, client):
        r = client.post("/stuck-pipe/free-point", json={
            "pipe_od": 5.0, "pipe_id": 4.276, "pipe_grade": "S135",
            "stretch_inches": 0, "pull_force_lbs": 0
        })
        assert r.status_code == 200
        assert "error" in r.json()

    def test_risk_assessment(self, client):
        r = client.post("/stuck-pipe/risk-assessment", json={
            "mechanism": "Differential Sticking",
            "params": {"mud_weight": 14.0, "pore_pressure": 10.0}
        })
        assert r.status_code == 200
        assert "risk_level" in r.json()

    def test_full_stuck_pipe_analysis(self, client, db_session):
        """Full analysis linked to an event."""
        from models.models_v2 import Event
        from models.database import Well

        well = Well(name="SP-EVENT-WELL")
        db_session.add(well)
        db_session.commit()
        db_session.refresh(well)

        event = Event(
            well_id=well.id,
            phase="Drilling",
            family="Mechanics",
            event_type="Stuck Pipe"
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        r = client.post(f"/events/{event.id}/stuck-pipe", json={
            "answers": [
                {"node_id": "start", "answer": "no"},
                {"node_id": "q_no_circ", "answer": "no"},
                {"node_id": "q_no_circ_no_rotate", "answer": "yes"},
            ],
            "params": {"mud_weight": 14.0, "pore_pressure": 10.0}
        })
        assert r.status_code == 200
        data = r.json()
        assert "classification" in data
        assert "risk" in data
        assert "actions" in data

    def test_full_analysis_with_stretch(self, client, db_session):
        """Full analysis with free point from stretch data."""
        from models.models_v2 import Event
        from models.database import Well

        well = Well(name="SP-STRETCH-WELL")
        db_session.add(well)
        db_session.commit()
        db_session.refresh(well)

        event = Event(
            well_id=well.id, phase="Drilling",
            family="Mechanics", event_type="Stuck Pipe"
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        r = client.post(f"/events/{event.id}/stuck-pipe", json={
            "answers": [
                {"node_id": "start", "answer": "no"},
                {"node_id": "q_no_circ", "answer": "no"},
                {"node_id": "q_no_circ_no_rotate", "answer": "yes"},
            ],
            "params": {},
            "stretch_inches": 2.0,
            "pull_force_lbs": 50000,
            "pipe_od": 5.0,
            "pipe_id": 4.276,
            "pipe_grade": "S135"
        })
        assert r.status_code == 200
        assert r.json()["free_point"] is not None
        assert r.json()["free_point"]["free_point_depth_ft"] > 0
