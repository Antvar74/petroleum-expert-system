"""
Shared fixtures for Petroleum Expert System test suite.
Provides in-memory SQLite DB, TestClient, and petroleum engineering test data.
"""
import sys
import os
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base, get_db, Well
from middleware.auth import verify_api_key


# ============================================================
# Database Fixtures
# ============================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create a test engine with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Import all models so Base.metadata knows about them
    import models.models_v2  # noqa: F401
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Per-test DB session with rollback for isolation."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with DB override → in-memory."""
    from fastapi.testclient import TestClient
    from api_main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_auth():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_api_key] = override_auth
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ============================================================
# Sample DB Records
# ============================================================

@pytest.fixture
def sample_well(db_session):
    """Insert and return a test well."""
    well = Well(name="TEST-WELL-1", location="Test Location")
    db_session.add(well)
    db_session.commit()
    db_session.refresh(well)
    return well


# ============================================================
# Petroleum Engineering Data Fixtures
# ============================================================

@pytest.fixture
def vertical_survey():
    """11 stations, 0-10,000ft MD, vertical (inc=0°, azi=0°)."""
    return [
        {"md": i * 1000.0, "inclination": 0.0, "azimuth": 0.0}
        for i in range(11)
    ]


@pytest.fixture
def directional_survey():
    """
    S-type well: vertical to KOP@2000ft, build 2°/100ft to 40°, tangent to TD.
    Approximately 23 stations.
    """
    stations = []
    # Vertical section: 0 → 2000 ft
    for md in range(0, 2500, 500):
        stations.append({"md": float(md), "inclination": 0.0, "azimuth": 45.0})

    # Build section: 2000 → 4000 ft, 2°/100ft → 40° at 4000ft
    for md in range(2500, 4500, 500):
        inc = (md - 2000) * 2.0 / 100.0
        inc = min(inc, 40.0)
        stations.append({"md": float(md), "inclination": inc, "azimuth": 45.0})

    # Tangent: 4000 → 10000 ft at 40°
    for md in range(4500, 10500, 500):
        stations.append({"md": float(md), "inclination": 40.0, "azimuth": 45.0})

    return stations


@pytest.fixture
def standard_drillstring():
    """Standard drillstring: DP + HWDP + DC."""
    return [
        {"section_name": "Drill Pipe", "od": 5.0, "id_inner": 4.276, "weight": 19.5, "length": 9500.0, "order_from_bit": 3},
        {"section_name": "HWDP", "od": 5.0, "id_inner": 3.0, "weight": 49.3, "length": 300.0, "order_from_bit": 2},
        {"section_name": "Drill Collar", "od": 6.5, "id_inner": 2.813, "weight": 91.0, "length": 200.0, "order_from_bit": 1},
    ]


@pytest.fixture
def standard_hydraulic_sections():
    """5 hydraulic circuit sections: DP + HWDP + DC + annulus_dc + annulus_dp."""
    return [
        {"section_type": "drill_pipe", "length": 9500.0, "od": 5.0, "id_inner": 4.276},
        {"section_type": "hwdp", "length": 300.0, "od": 5.0, "id_inner": 3.0},
        {"section_type": "collar", "length": 200.0, "od": 6.5, "id_inner": 2.813},
        {"section_type": "annulus_dc", "length": 200.0, "od": 8.5, "id_inner": 6.5},
        {"section_type": "annulus_dp", "length": 9800.0, "od": 8.5, "id_inner": 5.0},
    ]


@pytest.fixture
def standard_nozzles():
    """3 × 12/32 inch nozzles."""
    return [12, 12, 12]


@pytest.fixture
def standard_mud_properties():
    """MW=10.0 ppg, PV=15 cP, YP=10 lb/100ft²."""
    return {"mud_weight": 10.0, "pv": 15, "yp": 10}


@pytest.fixture
def standard_well_geometry():
    """MD=10,000ft, TVD=9,500ft, shoe=5,000ft, hole=8.5in."""
    return {
        "depth_md": 10000.0,
        "depth_tvd": 9500.0,
        "casing_shoe_tvd": 5000.0,
        "hole_size": 8.5,
    }


# ============================================================
# AI Analysis / Module Analysis Engine Fixtures
# ============================================================

@pytest.fixture
def mock_coordinator_response():
    """Standard mock response from APICoordinator.run_automated_step."""
    return {
        "agent": "well_engineer",
        "role": "Well Engineer",
        "analysis": "1. EXECUTIVE SUMMARY\nMock analysis text.\n\n2. KEY FINDINGS\n- Finding 1\n- Finding 2",
        "confidence": "HIGH",
    }


@pytest.fixture
def mock_api_coordinator(monkeypatch, mock_coordinator_response):
    """Patch run_automated_step to avoid LLM calls."""
    async def mock_run(self, agent_id, problem, context=None, provider="auto"):
        return {**mock_coordinator_response, "agent": agent_id}
    monkeypatch.setattr(
        "orchestrator.module_analysis_engine.APICoordinator.run_automated_step",
        mock_run,
    )


@pytest.fixture
def sample_td_result():
    """Sample Torque & Drag calculation result."""
    return {
        "summary": {
            "surface_hookload_klb": 250.5,
            "surface_torque_ftlb": 15000,
            "max_side_force_lb": 8500,
            "buoyancy_factor": 0.867,
            "buoyed_weight_klb": 217.3,
            "alerts": ["High torque at 8500 ft"],
        },
        "station_results": [
            {"md": 0, "axial_force": 250500, "torque": 0, "normal_force": 0, "buckling_status": "OK"},
            {"md": 10000, "axial_force": 50000, "torque": 15000, "normal_force": 5000, "buckling_status": "SINUSOIDAL"},
        ],
    }


@pytest.fixture
def sample_hyd_result():
    """Sample Hydraulics/ECD calculation result."""
    return {
        "hydraulics": {
            "summary": {
                "total_system_pressure_psi": 2850,
                "ecd_at_td_ppg": 10.45,
                "annular_pressure_loss_psi": 450,
                "hsi": 3.2,
                "percent_at_bit": 45.5,
            },
            "bit_hydraulics": {"bit_pressure_drop_psi": 1300, "jet_velocity_fps": 385},
            "section_results": [],
        },
        "surge": {
            "surge_ecd_ppg": 11.2,
            "swab_ecd_ppg": 9.8,
            "surge_margin": "Normal",
            "swab_margin": "Acceptable",
        },
    }


@pytest.fixture
def sample_sp_result():
    """Sample Stuck Pipe calculation result."""
    return {
        "diagnosis": {
            "mechanism": "Differential Sticking",
            "confidence": "HIGH",
            "decision_path": ["permeable_zone", "high_overbalance"],
        },
        "risk": {
            "risk_level": "HIGH",
            "risk_score": 85,
            "contributing_factors": {"overbalance": 500},
            "recommended_actions": ["Spot pill"],
        },
        "freePoint": {
            "free_point_depth_ft": 8500,
            "stretch_inches": 12.5,
            "pull_force_lbs": 75000,
            "percent_yield": 45.2,
        },
    }


@pytest.fixture
def sample_wc_result():
    """Sample Well Control calculation result."""
    return {
        "kill": {
            "formation_pressure_psi": 5720,
            "kill_mud_weight_ppg": 11.2,
            "icp_psi": 850,
            "fcp_psi": 1200,
            "maasp_psi": 1500,
            "influx_type": "Gas",
            "influx_gradient_psi_ft": 0.1,
            "alerts": [],
            "method_detail": {},
        },
        "volumetric": {
            "method": "Volumetric",
            "cycles": [],
            "initial_conditions": {"working_pressure_psi": 850},
        },
        "bullhead": {
            "shoe_integrity": {"safe": True},
            "calculations": {"required_pump_pressure_psi": 1200},
            "warnings": [],
        },
    }
