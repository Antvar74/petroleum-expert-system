"""
Pydantic request schemas for Wellbore Cleanup routes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WellboreCleanupCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/wellbore-cleanup``."""

    event_id: Optional[int] = Field(default=None, description="Associated event ID")
    flow_rate: float = Field(default=500, description="Flow rate (gpm)")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    pv: float = Field(default=15, description="Plastic viscosity (cP)")
    yp: float = Field(default=10, description="Yield point (lbf/100ft2)")
    hole_id: float = Field(default=8.5, description="Hole inner diameter (in)")
    pipe_od: float = Field(default=5.0, description="Pipe outer diameter (in)")
    inclination: float = Field(default=0, description="Inclination (degrees)")
    rop: float = Field(default=60, description="Rate of penetration (ft/hr)")
    cutting_size: float = Field(default=0.25, description="Cutting size (in)")
    cutting_density: float = Field(default=21.0, description="Cutting density (ppg)")
    rpm: float = Field(default=0, description="Rotary speed (rpm)")
    annular_length: float = Field(default=1000, description="Annular length (ft)")
