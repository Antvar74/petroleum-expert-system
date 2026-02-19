from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Event(Base):
    """
    Represents a structured operational event (Phase 1: Identification)
    Replaces/Augments the legacy 'Problem' model.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    
    # Classification
    phase = Column(String, nullable=False) # Drilling, Completion, Workover
    family = Column(String, nullable=False) # Well, Fluids, Mechanics, Control, Human
    event_type = Column(String, nullable=True) # Specific type (e.g. "Stuck Pipe", "Kick")
    
    # Metadata
    description = Column(Text, nullable=True) 
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="open") # open, analyzing, resolved
    
    # Relationships
    well = relationship("Well") # defined in database.py, we just link to it
    parameters = relationship("ParameterSet", back_populates="event", uselist=False, cascade="all, delete-orphan")
    rca_analysis = relationship("RCAReport", back_populates="event", uselist=False, cascade="all, delete-orphan")

class ParameterSet(Base):
    """
    Stores the 'Non-Negotiable' Minimum Data Set (Phase 2: Capture)
    """
    __tablename__ = "parameter_sets"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    
    # 1. General Well Params
    depth_md = Column(Float, nullable=True)
    depth_tvd = Column(Float, nullable=True)
    inclination = Column(Float, nullable=True)
    azimuth = Column(Float, nullable=True)
    
    # 2. Fluid Params
    mud_weight = Column(Float, nullable=True) # ppg
    viscosity_pv = Column(Float, nullable=True)
    viscosity_yp = Column(Float, nullable=True)
    temperature_out = Column(Float, nullable=True)
    
    # 3. Hydraulics & Operation
    flow_rate = Column(Float, nullable=True) # gpm
    spp = Column(Float, nullable=True) # psi
    operation_code = Column(String, nullable=True) # e.g. "Drilling", "Tripping"
    
    # 4. Drilling / Mechanics
    wob = Column(Float, nullable=True) # klb
    rpm = Column(Float, nullable=True)
    rop = Column(Float, nullable=True) # ft/hr
    torque = Column(Float, nullable=True) # ft-lb
    hook_load = Column(Float, nullable=True) # klb
    overpull = Column(Float, nullable=True) # klb
    
    # 5. Kick / Control (Optional)
    pit_gain = Column(Float, nullable=True) # bbl
    sidpp = Column(Float, nullable=True) # psi
    sicp = Column(Float, nullable=True) # psi
    
    # Metada
    source = Column(String, default="manual") # manual, ai_extracted
    
    event = relationship("Event", back_populates="parameters")

class RCAReport(Base):
    """
    Stores the structured RCA Output (Phase 4: Synthesis)
    API RP 585 Compliant
    """
    __tablename__ = "rca_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    
    # Core Analysis
    root_cause_category = Column(String, nullable=True) # e.g. "Procedural"
    root_cause_description = Column(Text, nullable=True)
    
    # Structured Data
    five_whys = Column(JSON, nullable=True) # List of questions/answers
    fishbone_factors = Column(JSON, nullable=True) # Dict of categories
    
    # Recommendations
    corrective_actions = Column(JSON, nullable=True) # List of actions
    prevention_actions = Column(JSON, nullable=True)
    
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="rca_analysis")


# ============================================================
# MODULE 1: Torque & Drag Models
# ============================================================

class SurveyStation(Base):
    """Survey station for wellbore trajectory (minimum curvature input)."""
    __tablename__ = "survey_stations"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    md = Column(Float, nullable=False)           # ft
    inclination = Column(Float, nullable=False)   # degrees
    azimuth = Column(Float, nullable=False)       # degrees
    tvd = Column(Float, nullable=True)            # ft (computed)
    north = Column(Float, nullable=True)          # ft (computed)
    east = Column(Float, nullable=True)           # ft (computed)
    dls = Column(Float, nullable=True)            # deg/100ft (computed)

    well = relationship("Well")


class DrillstringSection(Base):
    """Drillstring section description for T&D calculations."""
    __tablename__ = "drillstring_sections"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    section_name = Column(String)      # "Drill Pipe", "HWDP", "Drill Collar", "BHA"
    od = Column(Float)                 # inches
    id_inner = Column(Float)           # inches
    weight = Column(Float)             # lb/ft (nominal)
    length = Column(Float)             # ft
    order_from_bit = Column(Integer)   # 1 = bit, 2 = next section up, etc.

    well = relationship("Well")


class TorqueDragResult(Base):
    """Stores results from torque & drag calculations."""
    __tablename__ = "torque_drag_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    operation = Column(String)         # rotating, sliding, trip_in, trip_out, back_ream
    friction_cased = Column(Float)
    friction_open = Column(Float)
    wob = Column(Float, nullable=True)
    rpm = Column(Float, nullable=True)
    result_data = Column(JSON)         # per-station results array
    summary = Column(JSON)             # surface hookload, torque, alerts
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 2: Hydraulics / ECD Dynamic Models
# ============================================================

class HydraulicSection(Base):
    """Hydraulic circuit section geometry."""
    __tablename__ = "hydraulic_sections"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    section_type = Column(String)      # surface_equip, drill_pipe, hwdp, collar, annulus_dp, annulus_dc
    length = Column(Float)             # ft
    od = Column(Float)                 # inches (pipe OD or hole ID for annulus)
    id_inner = Column(Float)           # inches (pipe ID or pipe OD for annulus)

    well = relationship("Well")


class BitNozzle(Base):
    """Bit nozzle configuration."""
    __tablename__ = "bit_nozzles"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    nozzle_count = Column(Integer)
    nozzle_sizes = Column(JSON)        # list of sizes in 32nds of an inch
    tfa = Column(Float, nullable=True) # total flow area in^2 (computed)
    bit_diameter = Column(Float, nullable=True)  # inches

    well = relationship("Well")


class HydraulicResult(Base):
    """Stores results from hydraulic calculations."""
    __tablename__ = "hydraulic_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    flow_rate = Column(Float)
    mud_weight = Column(Float)
    pv = Column(Float)
    yp = Column(Float)
    rheology_model = Column(String)    # bingham_plastic | power_law
    result_data = Column(JSON)         # per-section pressure losses + ECD profile
    bit_hydraulics = Column(JSON)      # TFA, HSI, impact force, jet velocity
    surge_swab = Column(JSON, nullable=True)
    summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 3: Stuck Pipe Analyzer Models
# ============================================================

class StuckPipeAnalysis(Base):
    """Stores stuck pipe diagnosis and analysis results."""
    __tablename__ = "stuck_pipe_analyses"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    well_id = Column(Integer, ForeignKey("wells.id"))

    mechanism = Column(String)                # differential, mechanical, hole_cleaning, etc.
    decision_tree_path = Column(JSON)         # list of Q&A pairs
    free_point_depth = Column(Float, nullable=True)
    pipe_stretch_inches = Column(Float, nullable=True)
    pull_force_lbs = Column(Float, nullable=True)
    risk_matrix = Column(JSON, nullable=True) # {probability, severity, risk_level, factors}
    recommended_actions = Column(JSON)        # ordered list of actions

    created_at = Column(DateTime, default=datetime.utcnow)
    well = relationship("Well")


# ============================================================
# MODULE 4: Well Control / Kill Sheet Models
# ============================================================

class KillSheet(Base):
    """Pre-recorded and active kill sheet data."""
    __tablename__ = "kill_sheets"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    # Pre-recorded static data
    well_name = Column(String, nullable=True)
    depth_md = Column(Float)
    depth_tvd = Column(Float)
    original_mud_weight = Column(Float)  # ppg
    casing_shoe_tvd = Column(Float)
    casing_id = Column(Float, nullable=True)  # inches
    dp_capacity = Column(Float, nullable=True)  # bbl/ft
    annular_capacity = Column(Float, nullable=True)  # bbl/ft

    # Kick data (filled when kick occurs)
    sidpp = Column(Float, nullable=True)  # psi
    sicp = Column(Float, nullable=True)   # psi
    pit_gain = Column(Float, nullable=True)  # bbl

    # Circulation data
    scr_pressure = Column(Float, nullable=True)  # psi
    scr_rate = Column(Float, nullable=True)       # spm
    strokes_surface_to_bit = Column(Float, nullable=True)
    strokes_bit_to_surface = Column(Float, nullable=True)
    total_strokes = Column(Float, nullable=True)

    # LOT/FIT data
    lot_emw = Column(Float, nullable=True)  # ppg

    # Calculated results
    calculations = Column(JSON, nullable=True)
    pressure_schedule = Column(JSON, nullable=True)
    kill_method = Column(String, nullable=True)  # drillers, wait_weight, volumetric, bullhead

    status = Column(String, default="pre-recorded")  # pre-recorded, active, completed
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 5: Wellbore Cleanup (Hole Cleaning) Models
# ============================================================

class WellboreCleanupResult(Base):
    """Stores results from wellbore cleanup / hole cleaning calculations."""
    __tablename__ = "wellbore_cleanup_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    flow_rate = Column(Float)              # gpm
    mud_weight = Column(Float)             # ppg
    pv = Column(Float)                     # cP
    yp = Column(Float)                     # lb/100ft²
    hole_id = Column(Float)                # inches
    pipe_od = Column(Float)                # inches
    inclination = Column(Float)            # degrees

    result_data = Column(JSON)             # full calculation results
    summary = Column(JSON)                 # summary metrics + alerts
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 6: Packer Forces Models
# ============================================================

class PackerForcesResult(Base):
    """Stores results from packer forces calculations."""
    __tablename__ = "packer_forces_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    tubing_od = Column(Float)              # inches
    tubing_id = Column(Float)              # inches
    tubing_weight = Column(Float)          # lb/ft
    packer_depth_tvd = Column(Float)       # ft

    result_data = Column(JSON)             # full calculation results
    summary = Column(JSON)                 # summary metrics + alerts
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 7: Workover Hydraulics Models
# ============================================================

class WorkoverHydraulicsResult(Base):
    """Stores results from workover/CT hydraulics calculations."""
    __tablename__ = "workover_hydraulics_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    ct_od = Column(Float)                  # inches
    wall_thickness = Column(Float)         # inches
    ct_length = Column(Float)              # ft
    flow_rate = Column(Float)              # gpm
    mud_weight = Column(Float)             # ppg
    hole_id = Column(Float)               # inches

    result_data = Column(JSON)             # full calculation results
    summary = Column(JSON)                 # summary metrics + alerts
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 8: Sand Control Models
# ============================================================

class SandControlResult(Base):
    """Stores results from sand control analysis calculations."""
    __tablename__ = "sand_control_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    d50_mm = Column(Float)                 # median grain size
    uniformity_coefficient = Column(Float) # Cu = D60/D10
    ucs_psi = Column(Float)               # unconfined compressive strength
    interval_length = Column(Float)        # ft

    result_data = Column(JSON)             # full calculation results
    summary = Column(JSON)                 # summary metrics + alerts
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 9: Completion Design Models
# ============================================================

class CompletionDesignResult(Base):
    """Stores results from completion design calculations."""
    __tablename__ = "completion_design_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    casing_id_in = Column(Float)
    formation_permeability_md = Column(Float)
    depth_tvd_ft = Column(Float)
    penetration_berea_in = Column(Float)

    result_data = Column(JSON)
    summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 10: Shot Efficiency Models
# ============================================================

class ShotEfficiencyResult(Base):
    """Stores results from shot efficiency / petrophysical analysis."""
    __tablename__ = "shot_efficiency_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    log_points_count = Column(Integer)
    net_pay_intervals = Column(Integer)
    total_net_pay_ft = Column(Float)

    result_data = Column(JSON)
    summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")


# ============================================================
# MODULE 11: Vibrations / Stability Models
# ============================================================

class VibrationsResult(Base):
    """Stores results from vibrations/stability calculations."""
    __tablename__ = "vibrations_results"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    wob_klb = Column(Float)
    rpm = Column(Float)
    bit_diameter_in = Column(Float)

    result_data = Column(JSON)
    summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    well = relationship("Well")
