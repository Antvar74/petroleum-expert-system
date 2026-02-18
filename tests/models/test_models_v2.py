"""
Model tests for models_v2.py — SQLAlchemy tables, JSON columns, relationships.
"""
import pytest
from sqlalchemy import inspect
from models.database import Base, Well
from models.models_v2 import (
    SurveyStation, DrillstringSection, TorqueDragResult,
    HydraulicSection, BitNozzle, HydraulicResult,
    StuckPipeAnalysis, KillSheet
)


class TestTablesExist:

    def test_all_eight_tables(self, test_engine):
        """The 8 new tables should be registered in metadata."""
        inspector = inspect(test_engine)
        table_names = inspector.get_table_names()
        expected = [
            "survey_stations", "drillstring_sections", "torque_drag_results",
            "hydraulic_sections", "bit_nozzles", "hydraulic_results",
            "stuck_pipe_analyses", "kill_sheets"
        ]
        for t in expected:
            assert t in table_names, f"Table '{t}' missing from database"


class TestSurveyStationColumns:

    def test_columns(self, test_engine):
        inspector = inspect(test_engine)
        cols = {c["name"] for c in inspector.get_columns("survey_stations")}
        for col in ("md", "inclination", "azimuth", "tvd", "north", "east", "dls"):
            assert col in cols, f"Column '{col}' missing from survey_stations"


class TestDrillstringSectionColumns:

    def test_columns(self, test_engine):
        inspector = inspect(test_engine)
        cols = {c["name"] for c in inspector.get_columns("drillstring_sections")}
        for col in ("od", "id_inner", "weight", "length", "order_from_bit"):
            assert col in cols, f"Column '{col}' missing from drillstring_sections"


class TestKillSheetJSON:

    def test_calculations_json(self, db_session, sample_well):
        """KillSheet.calculations stores and retrieves a dict."""
        ks = KillSheet(
            well_id=sample_well.id,
            depth_md=10000, depth_tvd=9500,
            original_mud_weight=10.0, casing_shoe_tvd=5000,
            calculations={"test_key": "test_value", "nested": {"a": 1}},
            status="pre-recorded"
        )
        db_session.add(ks)
        db_session.commit()
        db_session.refresh(ks)
        assert ks.calculations["test_key"] == "test_value"
        assert ks.calculations["nested"]["a"] == 1


class TestHydraulicResultJSON:

    def test_json_columns(self, db_session, sample_well):
        """result_data, bit_hydraulics, summary are all JSON."""
        hr = HydraulicResult(
            well_id=sample_well.id,
            flow_rate=400, mud_weight=10, pv=15, yp=10,
            rheology_model="bingham_plastic",
            result_data=[{"section": "dp", "dp": 100}],
            bit_hydraulics={"tfa": 0.33, "hsi": 2.5},
            summary={"total_spp": 3000}
        )
        db_session.add(hr)
        db_session.commit()
        db_session.refresh(hr)
        assert hr.result_data[0]["section"] == "dp"
        assert hr.bit_hydraulics["tfa"] == 0.33
        assert hr.summary["total_spp"] == 3000


class TestStuckPipeAnalysisJSON:

    def test_json_columns(self, db_session, sample_well):
        spa = StuckPipeAnalysis(
            well_id=sample_well.id,
            mechanism="Differential Sticking",
            decision_tree_path=[{"q": "Can circulate?", "a": "no"}],
            risk_matrix={"probability": 3, "severity": 4},
            recommended_actions={"immediate": ["work pipe"], "short_term": [], "contingency": []}
        )
        db_session.add(spa)
        db_session.commit()
        db_session.refresh(spa)
        assert spa.decision_tree_path[0]["q"] == "Can circulate?"
        assert spa.risk_matrix["probability"] == 3
        assert spa.recommended_actions["immediate"][0] == "work pipe"


class TestForeignKey:

    def test_survey_station_well_fk(self, db_session, sample_well):
        ss = SurveyStation(
            well_id=sample_well.id,
            md=1000, inclination=5, azimuth=30
        )
        db_session.add(ss)
        db_session.commit()
        db_session.refresh(ss)
        assert ss.well_id == sample_well.id


class TestRelationship:

    def test_station_well_name(self, db_session, sample_well):
        ss = SurveyStation(
            well_id=sample_well.id,
            md=1000, inclination=5, azimuth=30
        )
        db_session.add(ss)
        db_session.commit()
        db_session.refresh(ss)
        assert ss.well.name == "TEST-WELL-1"
