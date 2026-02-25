from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone


def _utcnow():
    """Timezone-aware UTC timestamp for SQLAlchemy column defaults."""
    return datetime.now(timezone.utc)
import os

# Base directory for database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build_database_url() -> str:
    """Resolve database URL from environment or defaults.

    Priority:
    1. DATABASE_URL env var (supports PostgreSQL, MySQL, SQLite, etc.)
    2. VERCEL env var → ephemeral SQLite in /tmp
    3. Local SQLite file in project root
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/petroleum_expert.db"
    return f"sqlite:///{os.path.join(BASE_DIR, 'petroleum_expert.db')}"


DATABASE_URL = _build_database_url()

# SQLite requires check_same_thread=False for FastAPI; other DBs don't need it
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

Base = declarative_base()

class Well(Base):
    __tablename__ = "wells"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    
    problems = relationship("Problem", back_populates="well", cascade="all, delete-orphan")
    programs = relationship("Program", back_populates="well", cascade="all, delete-orphan")

class Problem(Base):
    __tablename__ = "problems"
    
    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    depth_md = Column(Float, nullable=False)
    depth_tvd = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    operation = Column(String, nullable=False)
    formation = Column(String, nullable=True)
    mud_weight = Column(Float, nullable=True)
    inclination = Column(Float, nullable=True)
    azimuth = Column(Float, nullable=True)
    torque = Column(Float, nullable=True)
    drag = Column(Float, nullable=True)
    overpull = Column(Float, nullable=True)
    string_weight = Column(Float, nullable=True)
    additional_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    
    well = relationship("Well", back_populates="problems")
    analyses = relationship("Analysis", back_populates="problem", cascade="all, delete-orphan")

class Program(Base):
    __tablename__ = "programs"
    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    type = Column(String) # 'drilling', 'completion', 'workover'
    status = Column(String, default="draft")
    content = Column(JSON, nullable=True) # Full structured plan
    created_at = Column(DateTime, default=_utcnow)
    
    well = relationship("Well", back_populates="programs")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    workflow_used = Column(JSON, nullable=False) # List of agent names
    confidence_summary = Column(JSON, nullable=True)
    overall_confidence = Column(String, nullable=True)
    individual_analyses = Column(JSON, nullable=True) # List of dicts
    final_synthesis = Column(JSON, nullable=True)
    leader_agent_id = Column(String, nullable=True) # ID of the agent leading the investigation
    created_at = Column(DateTime, default=_utcnow)
    
    problem = relationship("Problem", back_populates="analyses")

# Database connection
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # NOTE: Schema migrations are now managed by Alembic.
    # Run: alembic upgrade head

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
