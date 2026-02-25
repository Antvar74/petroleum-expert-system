"""
Pydantic request schemas for Stuck Pipe routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiagnosisAnswerRequest(BaseModel):
    """Body for ``POST /stuck-pipe/diagnose/answer``."""

    node_id: str = Field(default="start", description="Current decision-tree node")
    answer: str = Field(default="yes", description="Selected answer")


class FreePointRequest(BaseModel):
    """Body for ``POST /stuck-pipe/free-point``."""

    pipe_od: float = Field(default=5.0, description="Pipe OD (in)")
    pipe_id: float = Field(default=4.276, description="Pipe ID (in)")
    pipe_grade: str = Field(default="S135", description="Pipe grade")
    stretch_inches: float = Field(default=0, description="Measured stretch (in)")
    pull_force_lbs: float = Field(default=0, description="Applied pull force (lbs)")


class RiskAssessmentRequest(BaseModel):
    """Body for ``POST /stuck-pipe/risk-assessment``."""

    mechanism: str = Field(default="", description="Stuck mechanism classification")
    params: Dict[str, Any] = Field(default_factory=dict, description="Context parameters")


class FullStuckPipeRequest(BaseModel):
    """Body for ``POST /events/{event_id}/stuck-pipe``."""

    answers: List[Dict[str, str]] = Field(default_factory=list, description="Decision tree answers")
    params: Dict[str, Any] = Field(default_factory=dict, description="Context parameters for risk")
    stretch_inches: Optional[float] = Field(default=None, description="Pipe stretch (in)")
    pull_force_lbs: Optional[float] = Field(default=None, description="Pull force (lbs)")
    pipe_od: float = Field(default=5.0, description="Pipe OD (in)")
    pipe_id: float = Field(default=4.276, description="Pipe ID (in)")
    pipe_grade: str = Field(default="S135", description="Pipe grade")


class DifferentialStickingRequest(BaseModel):
    """Body for ``POST /stuck-pipe/differential-sticking``."""

    ecd_ppg: float = Field(default=12.5, description="ECD (ppg)")
    pore_pressure_ppg: float = Field(default=10.0, description="Pore pressure (ppg)")
    contact_length_ft: float = Field(default=30, description="Contact length (ft)")
    pipe_od_in: float = Field(default=5.0, description="Pipe OD (in)")
    filter_cake_thickness_in: float = Field(default=0.25, description="Filter cake thickness (in)")
    friction_coefficient_cake: float = Field(default=0.10, description="Cake friction coefficient")
    tvd_ft: float = Field(default=10000, description="TVD (ft)")


class PackoffRiskRequest(BaseModel):
    """Body for ``POST /stuck-pipe/packoff-risk``."""

    hci: float = Field(default=0.8, description="Hole cleaning index")
    cuttings_concentration_pct: float = Field(default=3.0, description="Cuttings concentration (%)")
    inclination: float = Field(default=0.0, description="Inclination (deg)")
    annular_velocity_ftmin: float = Field(default=150.0, description="Annular velocity (ft/min)")
