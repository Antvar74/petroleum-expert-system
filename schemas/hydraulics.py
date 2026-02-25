"""
Pydantic request schemas for Hydraulics routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HydraulicSectionInput(BaseModel):
    """A single hydraulic circuit section."""

    section_type: str
    length: float
    od: float
    id_inner: float


class BitNozzlesRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/bit-nozzles``."""

    nozzle_sizes: List[float] = Field(default_factory=list, description="Nozzle sizes in 32nds of an inch")
    bit_diameter: Optional[float] = Field(default=None, description="Bit diameter (in)")


class HydraulicsCalcRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/hydraulics/calculate``."""

    flow_rate: float = Field(default=400, description="Flow rate (gpm)")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    pv: float = Field(default=15, description="Plastic viscosity (cP)")
    yp: float = Field(default=10, description="Yield point (lbf/100sqft)")
    tvd: float = Field(default=10000, description="True vertical depth (ft)")
    rheology_model: str = Field(default="bingham_plastic", description="Rheology model")
    n: float = Field(default=0.5, description="Power-law n index")
    k: float = Field(default=300, description="Power-law K consistency index")
    surface_equipment_loss: float = Field(default=80.0, description="Surface equipment pressure loss (psi)")
    nozzle_sizes: Optional[List[float]] = Field(default=None, description="Override nozzle sizes")
    event_id: Optional[int] = Field(default=None, description="Event ID to link result")


class SurgeSwabRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/hydraulics/surge-swab``."""

    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    pv: float = Field(default=15, description="Plastic viscosity (cP)")
    yp: float = Field(default=10, description="Yield point (lbf/100sqft)")
    tvd: float = Field(default=10000, description="TVD (ft)")
    pipe_od: float = Field(default=5.0, description="Pipe OD (in)")
    pipe_id: float = Field(default=4.276, description="Pipe ID (in)")
    hole_id: float = Field(default=8.5, description="Hole ID (in)")
    pipe_velocity_fpm: float = Field(default=90, description="Pipe velocity (ft/min)")
    pipe_open: bool = Field(default=True, description="Is pipe open-ended?")


class BHABreakdownRequest(BaseModel):
    """Body for ``POST /hydraulics/bha-breakdown``."""

    bha_tools: List[Dict[str, Any]] = Field(default_factory=list, description="BHA tool list")
    flow_rate: float = Field(default=400, description="Flow rate (gpm)")
    mud_weight: float = Field(default=12.0, description="Mud weight (ppg)")
    pv: float = Field(default=20, description="Plastic viscosity (cP)")
    yp: float = Field(default=12, description="Yield point (lbf/100sqft)")
    rheology_model: str = Field(default="bingham_plastic", description="Rheology model")
    n: float = Field(default=0.5, description="Power-law n")
    k: float = Field(default=300.0, description="Power-law K")
    tau_0: float = Field(default=0.0, description="HB yield stress")
    k_hb: float = Field(default=0.0, description="HB K")
    n_hb: float = Field(default=0.5, description="HB n")


class PressureWaterfallRequest(BaseModel):
    """Body for ``POST /hydraulics/pressure-waterfall``."""

    circuit_result: Dict[str, Any] = Field(default_factory=dict, description="Circuit result data")
    bha_breakdown: Optional[Dict[str, Any]] = Field(default=None, description="BHA breakdown data")


class HerschelBulkleyFitRequest(BaseModel):
    """Body for ``POST /hydraulics/fit-herschel-bulkley``."""

    fann_readings: Dict[str, Any] = Field(default_factory=dict, description="FANN viscometer readings")
