"""
Pydantic request schemas for Packer Forces routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PackerForcesCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/packer-forces``."""

    event_id: Optional[int] = Field(default=None, description="Associated event ID")
    tubing_od: float = Field(default=2.875, description="Tubing outer diameter (in)")
    tubing_id: float = Field(default=2.441, description="Tubing inner diameter (in)")
    tubing_weight: float = Field(default=6.5, description="Tubing weight (ppf)")
    tubing_length: float = Field(default=10000, description="Tubing length (ft)")
    seal_bore_id: float = Field(default=3.25, description="Seal bore inner diameter (in)")
    initial_tubing_pressure: float = Field(default=0, description="Initial tubing pressure (psi)")
    final_tubing_pressure: float = Field(default=3000, description="Final tubing pressure (psi)")
    initial_annulus_pressure: float = Field(default=0, description="Initial annulus pressure (psi)")
    final_annulus_pressure: float = Field(default=0, description="Final annulus pressure (psi)")
    initial_temperature: float = Field(default=80, description="Initial temperature (F)")
    final_temperature: float = Field(default=250, description="Final temperature (F)")
    packer_depth_tvd: float = Field(default=10000, description="Packer depth TVD (ft)")
    mud_weight_tubing: float = Field(default=8.34, description="Mud weight in tubing (ppg)")
    mud_weight_annulus: float = Field(default=8.34, description="Mud weight in annulus (ppg)")
    poisson_ratio: float = Field(default=0.30, description="Poisson ratio")
    thermal_expansion: float = Field(default=6.9e-6, description="Thermal expansion coefficient (1/F)")


class APBRequest(BaseModel):
    """Body for ``POST /packer/apb``."""

    annular_fluid_type: str = Field(default="WBM", description="Annular fluid type")
    delta_t_avg: float = Field(default=100, description="Average temperature change (F)")
    annular_volume_bbl: float = Field(default=200, description="Annular volume (bbl)")
    casing_od: float = Field(default=9.625, description="Casing OD (in)")
    casing_id: float = Field(default=8.681, description="Casing ID (in)")
    tubing_od: float = Field(default=3.5, description="Tubing OD (in)")
    tubing_id: float = Field(default=2.992, description="Tubing ID (in)")
    annular_length_ft: float = Field(default=10000, description="Annular length (ft)")
    initial_pressure_psi: float = Field(default=0, description="Initial pressure (psi)")


class LandingConditionsRequest(BaseModel):
    """Body for ``POST /packer/landing-conditions``."""

    tubing_sections: List[Dict[str, Any]] = Field(default_factory=list, description="Tubing sections")
    survey_stations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Survey stations")
    mud_weight_ppg: float = Field(default=8.34, description="Mud weight (ppg)")
    friction_factor: float = Field(default=0.30, description="Friction factor")
    packer_depth_tvd_ft: float = Field(default=10000, description="Packer depth TVD (ft)")
    set_down_weight_lbs: float = Field(default=5000, description="Set-down weight (lbs)")


class BucklingLengthRequest(BaseModel):
    """Body for ``POST /packer/buckling-length``."""

    axial_force: float = Field(default=-50000, description="Axial force (lbs, negative = compression)")
    tubing_od: float = Field(default=3.5, description="Tubing OD (in)")
    tubing_id: float = Field(default=2.992, description="Tubing ID (in)")
    tubing_weight_ppf: float = Field(default=9.3, description="Tubing weight (ppf)")
    casing_id: float = Field(default=6.276, description="Casing ID (in)")
    inclination_deg: float = Field(default=0, description="Inclination (degrees)")
    mud_weight_ppg: float = Field(default=8.34, description="Mud weight (ppg)")
