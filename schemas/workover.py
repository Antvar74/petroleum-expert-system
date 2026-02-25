"""
Pydantic request schemas for Workover Hydraulics routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CTElongationRequest(BaseModel):
    """Body for ``POST /workover/ct-elongation``."""

    ct_od: float = Field(default=2.0, description="Coiled tubing OD (in)")
    ct_id: float = Field(default=1.688, description="Coiled tubing ID (in)")
    ct_length: float = Field(default=15000, description="Coiled tubing length (ft)")
    weight_per_ft: float = Field(default=3.24, description="Weight per foot (lbs/ft)")
    mud_weight: float = Field(default=8.6, description="Mud weight (ppg)")
    delta_p_internal: float = Field(default=3000, description="Internal pressure differential (psi)")
    delta_t: float = Field(default=100, description="Temperature change (F)")
    wellhead_pressure: float = Field(default=500, description="Wellhead pressure (psi)")


class CTFatigueRequest(BaseModel):
    """Body for ``POST /workover/ct-fatigue``."""

    ct_od: float = Field(default=2.0, description="Coiled tubing OD (in)")
    wall_thickness: float = Field(default=0.156, description="Wall thickness (in)")
    reel_diameter: float = Field(default=72, description="Reel diameter (in)")
    internal_pressure: float = Field(default=5000, description="Internal pressure (psi)")
    yield_strength_psi: float = Field(default=80000, description="Yield strength (psi)")
    trips_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Historical trips data")


class WorkoverHydraulicsCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/workover-hydraulics``."""

    flow_rate: float = Field(default=80, description="Flow rate (gpm)")
    mud_weight: float = Field(default=8.6, description="Mud weight (ppg)")
    pv: float = Field(default=12, description="Plastic viscosity (cP)")
    yp: float = Field(default=8, description="Yield point (lbf/100ft2)")
    ct_od: float = Field(default=2.0, description="Coiled tubing OD (in)")
    wall_thickness: float = Field(default=0.156, description="Wall thickness (in)")
    ct_length: float = Field(default=10000, description="Coiled tubing length (ft)")
    hole_id: float = Field(default=4.892, description="Hole inner diameter (in)")
    tvd: float = Field(default=10000, description="True vertical depth (ft)")
    inclination: float = Field(default=0, description="Inclination (degrees)")
    friction_factor: float = Field(default=0.25, description="Friction factor")
    wellhead_pressure: float = Field(default=0, description="Wellhead pressure (psi)")
    reservoir_pressure: float = Field(default=5200, description="Reservoir pressure (psi)")
    yield_strength_psi: float = Field(default=80000, description="Yield strength (psi)")
