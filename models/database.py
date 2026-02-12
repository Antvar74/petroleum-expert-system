from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Base directory for database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/petroleum_expert.db"
else:
    DB_PATH = os.path.join(BASE_DIR, "petroleum_expert.db")

Base = declarative_base()

class Well(Base):
    __tablename__ = "wells"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    well = relationship("Well", back_populates="problems")
    analyses = relationship("Analysis", back_populates="problem", cascade="all, delete-orphan")

class Program(Base):
    __tablename__ = "programs"
    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    type = Column(String) # 'drilling', 'completion', 'workover'
    status = Column(String, default="draft")
    content = Column(JSON, nullable=True) # Full structured plan
    created_at = Column(DateTime, default=datetime.utcnow)
    
    well = relationship("Well", back_populates="programs")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    workflow_used = Column(JSON, nullable=False) # List of agent names
    confidence_summary = Column(JSON, nullable=True)
    overall_confidence = Column(String, nullable=True)
    individual_analyses = Column(JSON, nullable=True) # List of dicts
    final_synthesis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    problem = relationship("Problem", back_populates="analyses")

# Database connection
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
