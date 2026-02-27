"""
Pydantic request schemas for Casing Design routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CasingDesignCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/casing-design``."""

    event_id: Optional[int] = Field(default=None, description="Associated event ID")
    casing_od_in: float = Field(default=9.625, description="Casing outer diameter (in)")
    casing_id_in: float = Field(default=8.681, description="Casing inner diameter (in)")
    wall_thickness_in: float = Field(default=0.472, description="Wall thickness (in)")
    casing_weight_ppf: float = Field(default=47.0, description="Casing weight (ppf)")
    casing_length_ft: float = Field(default=10000.0, description="Casing length (ft)")
    tvd_ft: float = Field(default=9500.0, description="True vertical depth (ft)")
    mud_weight_ppg: float = Field(default=10.5, description="Mud weight (ppg)")
    pore_pressure_ppg: float = Field(default=9.0, description="Pore pressure (ppg)")
    fracture_gradient_ppg: float = Field(default=16.5, description="Fracture gradient (ppg)")
    gas_gradient_psi_ft: float = Field(default=0.1, description="Gas gradient (psi/ft)")
    cement_top_tvd_ft: float = Field(default=5000.0, description="Cement top TVD (ft)")
    cement_density_ppg: float = Field(default=16.0, description="Cement density (ppg)")
    bending_dls: float = Field(default=3.0, description="Bending dogleg severity (deg/100ft)")
    overpull_lbs: float = Field(default=50000.0, description="Overpull (lbs)")
    sf_burst: float = Field(default=1.10, description="Safety factor for burst")
    sf_collapse: float = Field(default=1.00, description="Safety factor for collapse")
    sf_tension: float = Field(default=1.60, description="Safety factor for tension")

    # Tier 1 parameters
    connection_type: str = Field(default="BTC", description="Connection type: STC, LTC, BTC, PREMIUM")
    wear_pct: float = Field(default=0.0, description="Casing wear percentage (%)")
    corrosion_rate_in_yr: float = Field(default=0.0, description="Corrosion rate (in/yr)")
    design_life_years: float = Field(default=20.0, description="Design life (years)")
    bottomhole_temp_f: float = Field(default=200.0, description="Bottomhole temperature (°F)")
    tubing_pressure_psi: float = Field(default=0.0, description="Tubing head pressure for leak scenario (psi)")
    internal_fluid_density_ppg: float = Field(default=0.0, description="Internal fluid density (ppg), 0 = use mud weight")
    evacuation_level_ft: float = Field(default=-1.0, description="Evacuation fluid level (ft). -1=full evacuation, 0=no evacuation, >0=partial")


class CombinationStringRequest(BaseModel):
    """Body for ``POST /casing-design/combination-string``."""

    tvd_ft: float = Field(default=12000, description="True vertical depth (ft)")
    mud_weight_ppg: float = Field(default=12.0, description="Mud weight (ppg)")
    pore_pressure_ppg: float = Field(default=9.0, description="Pore pressure (ppg)")
    frac_gradient_ppg: float = Field(default=15.0, description="Fracture gradient (ppg)")
    casing_length_ft: Optional[float] = Field(default=None, description="Casing length (ft), defaults to tvd_ft")
    burst_profile: Optional[List[Dict[str, Any]]] = Field(default=None, description="Burst pressure profile")
    collapse_profile: Optional[List[Dict[str, Any]]] = Field(default=None, description="Collapse pressure profile")
    casing_weight_ppf: float = Field(default=47.0, description="Casing weight (ppf)")
    tension_at_surface_lbs: Optional[float] = Field(default=None, description="Tension at surface (lbs)")
    casing_od_in: float = Field(default=9.625, description="Casing OD (in)")
    casing_od: Optional[float] = Field(default=None, description="Casing OD alias (in)")
    sf_burst: float = Field(default=1.1, description="Safety factor for burst")
    sf_collapse: float = Field(default=1.0, description="Safety factor for collapse")
    sf_tension: float = Field(default=1.6, description="Safety factor for tension")


class RunningLoadsRequest(BaseModel):
    """Body for ``POST /casing-design/running-loads``."""

    casing_weight_ppf: float = Field(default=47, description="Casing weight (ppf)")
    casing_length_ft: Optional[float] = Field(default=None, description="Casing length (ft)")
    total_length_ft: Optional[float] = Field(default=None, description="Total length alias (ft)")
    casing_od_in: Optional[float] = Field(default=None, description="Casing OD (in)")
    casing_od: Optional[float] = Field(default=None, description="Casing OD alias (in)")
    casing_id_in: float = Field(default=8.535, description="Casing ID (in)")
    mud_weight_ppg: float = Field(default=10.0, description="Mud weight (ppg)")
    survey: Optional[List[Dict[str, Any]]] = Field(default=None, description="Survey stations")
    friction_factor: float = Field(default=0.30, description="Friction factor")
