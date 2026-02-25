"""
Pydantic request schemas for Sand Control routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SandControlCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/sand-control``."""

    sieve_sizes_mm: List[float] = Field(
        default_factory=lambda: [2.0, 0.85, 0.425, 0.25, 0.15, 0.075],
        description="Sieve sizes (mm)",
    )
    cumulative_passing_pct: List[float] = Field(
        default_factory=lambda: [100, 95, 70, 40, 15, 2],
        description="Cumulative passing percentage",
    )
    hole_id: float = Field(default=8.5, description="Hole inner diameter (in)")
    screen_od: float = Field(default=5.5, description="Screen outer diameter (in)")
    interval_length: float = Field(default=50, description="Interval length (ft)")
    ucs_psi: float = Field(default=500, description="Unconfined compressive strength (psi)")
    friction_angle_deg: float = Field(default=30, description="Friction angle (degrees)")
    reservoir_pressure_psi: float = Field(default=4500, description="Reservoir pressure (psi)")
    overburden_stress_psi: float = Field(default=10000, description="Overburden stress (psi)")
    formation_permeability_md: float = Field(default=500, description="Formation permeability (mD)")
    wellbore_radius_ft: float = Field(default=0.354, description="Wellbore radius (ft)")
    wellbore_type: str = Field(default="cased", description="Wellbore type: cased | openhole")
    gravel_permeability_md: float = Field(default=80000, description="Gravel permeability (mD)")
    pack_factor: float = Field(default=1.4, description="Gravel pack factor")
    washout_factor: float = Field(default=1.1, description="Washout factor")
