"""
Pydantic request schemas for Torque & Drag routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SurveyStationInput(BaseModel):
    """A single survey station record."""

    md: float
    inclination: float
    azimuth: float
    tvd: Optional[float] = None
    north: Optional[float] = None
    east: Optional[float] = None
    dls: Optional[float] = None


class DrillstringSectionInput(BaseModel):
    """A single drillstring section record."""

    section_name: str = "Unknown"
    od: float
    id_inner: float
    weight: float
    length: float
    order_from_bit: int = 0


class TorqueDragCalcRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/torque-drag``."""

    friction_cased: float = Field(default=0.25, description="Friction factor in cased hole")
    friction_open: float = Field(default=0.35, description="Friction factor in open hole")
    operation: str = Field(default="trip_out", description="Operation type")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    wob: float = Field(default=0.0, description="Weight on bit (klbs)")
    rpm: float = Field(default=0.0, description="RPM")
    casing_shoe_md: float = Field(default=0.0, description="Casing shoe MD (ft)")
    event_id: Optional[int] = Field(default=None, description="Event ID to link result")


class BackCalculateRequest(BaseModel):
    """Body for ``POST /torque-drag/back-calculate``."""

    well_id: int = Field(..., description="Well ID to fetch survey/drillstring")
    measured_hookload: float = Field(default=0, description="Measured hookload (klbs)")
    operation: str = Field(default="trip_out", description="Operation type")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    wob: float = Field(default=0.0, description="WOB (klbs)")
    casing_shoe_md: float = Field(default=0.0, description="Casing shoe MD (ft)")


class TDCompareRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/torque-drag/compare``."""

    operations: List[str] = Field(
        default=["trip_out", "trip_in", "rotating", "sliding", "lowering"],
        description="Operations to compare",
    )
    friction_cased: float = Field(default=0.25)
    friction_open: float = Field(default=0.35)
    mud_weight: float = Field(default=10.0)
    wob: float = Field(default=0.0)
    rpm: float = Field(default=0.0)
    casing_shoe_md: float = Field(default=0.0)
