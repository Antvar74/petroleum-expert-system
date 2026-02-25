"""
Pydantic request schemas for Cementing routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CementingCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/cementing``."""

    event_id: Optional[int] = Field(default=None, description="Associated event ID")
    casing_od_in: float = Field(default=9.625, description="Casing outer diameter (in)")
    casing_id_in: float = Field(default=8.681, description="Casing inner diameter (in)")
    hole_id_in: float = Field(default=12.25, description="Hole inner diameter (in)")
    casing_shoe_md_ft: float = Field(default=10000.0, description="Casing shoe measured depth (ft)")
    casing_shoe_tvd_ft: float = Field(default=9500.0, description="Casing shoe TVD (ft)")
    toc_md_ft: float = Field(default=5000.0, description="Top of cement MD (ft)")
    toc_tvd_ft: float = Field(default=4750.0, description="Top of cement TVD (ft)")
    float_collar_md_ft: float = Field(default=9900.0, description="Float collar MD (ft)")
    mud_weight_ppg: float = Field(default=10.5, description="Mud weight (ppg)")
    spacer_density_ppg: float = Field(default=11.5, description="Spacer density (ppg)")
    lead_cement_density_ppg: float = Field(default=13.5, description="Lead cement density (ppg)")
    tail_cement_density_ppg: float = Field(default=16.0, description="Tail cement density (ppg)")
    tail_length_ft: float = Field(default=500.0, description="Tail cement length (ft)")
    spacer_volume_bbl: float = Field(default=25.0, description="Spacer volume (bbl)")
    excess_pct: float = Field(default=50.0, description="Cement excess percentage")
    rat_hole_ft: float = Field(default=50.0, description="Rat hole length (ft)")
    pump_rate_bbl_min: float = Field(default=5.0, description="Pump rate (bbl/min)")
    pv_mud: float = Field(default=15.0, description="Plastic viscosity of mud (cP)")
    yp_mud: float = Field(default=10.0, description="Yield point of mud (lbf/100ft2)")
    fracture_gradient_ppg: float = Field(default=16.5, description="Fracture gradient (ppg)")
    pore_pressure_ppg: float = Field(default=9.0, description="Pore pressure (ppg)")


class GasMigrationRequest(BaseModel):
    """Body for ``POST /cementing/gas-migration``."""

    cement_top_tvd_ft: float = Field(default=5000, description="Cement top TVD (ft)")
    cement_base_tvd_ft: float = Field(default=10000, description="Cement base TVD (ft)")
    reservoir_pressure_psi: float = Field(default=5000, description="Reservoir pressure (psi)")
    slurry_density_ppg: float = Field(default=16.0, description="Slurry density (ppg)")
    pore_pressure_ppg: float = Field(default=9.0, description="Pore pressure (ppg)")
    sgs_time_hr: float = Field(default=4.0, description="SGS transition time (hr)")
    thickening_time_hr: float = Field(default=6.0, description="Thickening time (hr)")
    sgs_10min_lbf_100sqft: float = Field(default=20.0, description="SGS at 10 min (lbf/100sqft)")


class CentralizerDesignRequest(BaseModel):
    """Body for ``POST /cementing/centralizer-design``."""

    casing_od_in: float = Field(default=9.625, description="Casing OD (in)")
    hole_id_in: float = Field(default=12.25, description="Hole ID (in)")
    casing_weight_ppf: float = Field(default=47, description="Casing weight (ppf)")
    inclination_profile: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"md": 0, "inclination": 0},
            {"md": 2500, "inclination": 15},
            {"md": 5000, "inclination": 30},
            {"md": 7500, "inclination": 45},
            {"md": 10000, "inclination": 60},
        ],
        description="Inclination profile: list of {md, inclination} dicts",
    )
    centralizer_type: str = Field(default="bow_spring", description="Centralizer type: bow_spring | rigid")
