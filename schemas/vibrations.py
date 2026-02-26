"""
Pydantic request schemas for Vibrations routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VibrationsCalcRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/vibrations``."""

    wob_klb: float = Field(default=25, description="Weight on bit (klbs)")
    rpm: float = Field(default=120, description="RPM")
    rop_fph: float = Field(default=60, description="Rate of penetration (ft/hr)")
    torque_ftlb: float = Field(default=15000, description="Torque (ft-lb)")
    bit_diameter_in: float = Field(default=8.5, description="Bit diameter (in)")
    dp_od_in: float = Field(default=5.0, description="Drill pipe OD (in)")
    dp_id_in: float = Field(default=4.276, description="Drill pipe ID (in)")
    dp_weight_lbft: float = Field(default=19.5, description="DP weight (lb/ft)")
    bha_length_ft: float = Field(default=300, description="BHA length (ft)")
    bha_od_in: float = Field(default=6.75, description="BHA OD (in)")
    bha_id_in: float = Field(default=2.813, description="BHA ID (in)")
    bha_weight_lbft: float = Field(default=83.0, description="BHA weight (lb/ft)")
    mud_weight_ppg: float = Field(default=10.0, description="Mud weight (ppg)")
    pv_cp: Optional[float] = Field(default=None, description="Plastic viscosity (cP)")
    yp_lbf_100ft2: Optional[float] = Field(default=None, description="Yield point (lbf/100ft²)")
    flow_rate_gpm: Optional[float] = Field(default=None, description="Circulation rate (gpm)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    inclination_deg: float = Field(default=30, description="Inclination (deg)")
    friction_factor: float = Field(default=0.25, description="Friction factor")
    stabilizer_spacing_ft: Optional[float] = Field(default=None, description="Span between stabilizers (ft). If not provided, estimated as min(bha_length, 90).")
    ucs_psi: Optional[float] = Field(default=None, description="Formation unconfined compressive strength (psi). Required for MSE efficiency calculation.")
    n_blades: Optional[int] = Field(default=None, description="Number of PDC blades/cutters. Affects bit excitation frequency.")
    wellbore_sections: Optional[List[Dict[str, Any]]] = Field(default=None, description="Wellbore sections: casing, liner, open hole. Each dict has section_type, top_md_ft, bottom_md_ft, id_in.")
    total_depth_ft: Optional[float] = Field(default=None, description="Total measured depth (ft). Derived from wellbore sections max Bottom MD. Required for accurate stick-slip calculation.")


class Vibrations3DMapRequest(BaseModel):
    """Body for ``POST /vibrations/3d-map``."""

    survey_stations: List[Dict[str, Any]] = Field(default_factory=list, description="Survey stations")
    bha_od_in: float = Field(default=6.75)
    bha_id_in: float = Field(default=2.813)
    bha_weight_lbft: float = Field(default=83)
    bha_length_ft: float = Field(default=300)
    hole_diameter_in: float = Field(default=8.5)
    mud_weight_ppg: float = Field(default=10)
    rpm_range: Optional[List[float]] = Field(default=None, description="RPM range [min, max]")
    wob_klb: float = Field(default=20)


class BHAModalRequest(BaseModel):
    """Body for ``POST /vibrations/bha-modal``."""

    bha_components: List[Dict[str, Any]] = Field(default_factory=list, description="BHA component list")
    mud_weight_ppg: float = Field(default=10)
    hole_diameter_in: float = Field(default=8.5)
    boundary_conditions: str = Field(default="pinned-pinned", description="Boundary conditions")


class FatigueRequest(BaseModel):
    """Body for ``POST /vibrations/fatigue``."""

    drillstring_od: float = Field(default=5.0)
    drillstring_id: float = Field(default=4.276)
    drillstring_grade: str = Field(default="S-135")
    survey_stations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Survey for DLS")
    rpm: float = Field(default=120)
    hours_per_stand: float = Field(default=0.5)
    vibration_severity: float = Field(default=0.3)
    total_rotating_hours: float = Field(default=100)


class FEARequest(BaseModel):
    """Body for ``POST /vibrations/fea``."""

    bha_components: List[Dict[str, Any]] = Field(..., description="BHA component list")
    wob_klb: float = Field(default=20, description="Weight on bit (klbs)")
    rpm: float = Field(default=120, description="Operating RPM")
    mud_weight_ppg: float = Field(default=10, description="Mud weight (ppg)")
    pv_cp: Optional[float] = Field(default=None, description="Plastic viscosity (cP)")
    yp_lbf_100ft2: Optional[float] = Field(default=None, description="Yield point (lbf/100ft²)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    boundary_conditions: str = Field(default="pinned-pinned", description="BC: pinned-pinned, fixed-pinned, fixed-free")
    n_modes: int = Field(default=5, description="Number of modes to compute")
    include_forced_response: bool = Field(default=True, description="Include forced response analysis")
    include_campbell: bool = Field(default=True, description="Include Campbell diagram")
    n_blades: Optional[int] = Field(default=None, description="PDC blade count for blade-pass excitation")


class CampbellRequest(BaseModel):
    """Body for ``POST /vibrations/campbell``."""

    bha_components: List[Dict[str, Any]] = Field(..., description="BHA component list")
    wob_klb: float = Field(default=20, description="Weight on bit (klbs)")
    mud_weight_ppg: float = Field(default=10, description="Mud weight (ppg)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    boundary_conditions: str = Field(default="pinned-pinned", description="Boundary conditions")
    rpm_min: float = Field(default=20, description="Campbell RPM sweep start")
    rpm_max: float = Field(default=300, description="Campbell RPM sweep end")
    rpm_step: float = Field(default=5, description="Campbell RPM step")
    n_modes: int = Field(default=5, description="Number of modes")
    n_blades: Optional[int] = Field(default=None, description="PDC blade count")


class WellboreSection(BaseModel):
    """A single wellbore section (casing, liner, or open hole)."""

    section_type: str = Field(..., description="Type: surface_casing, intermediate_casing, production_casing, liner, open_hole")
    top_md_ft: float = Field(..., description="Top measured depth (ft)")
    bottom_md_ft: float = Field(..., description="Bottom measured depth (ft)")
    id_in: float = Field(..., description="Inner diameter (in)")
    shoe_depth_ft: Optional[float] = Field(default=None, description="Shoe depth (ft), typically = bottom_md_ft")
