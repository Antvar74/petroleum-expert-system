"""
Pydantic request schemas for Completion Design routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CompletionDesignCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/completion-design``."""

    casing_id_in: float = Field(default=6.276, description="Casing inner diameter (in)")
    formation_permeability_md: float = Field(default=100, description="Formation permeability (mD)")
    formation_thickness_ft: float = Field(default=30, description="Formation thickness (ft)")
    reservoir_pressure_psi: float = Field(default=5000, description="Reservoir pressure (psi)")
    wellbore_pressure_psi: float = Field(default=4200, description="Wellbore pressure (psi)")
    depth_tvd_ft: float = Field(default=10000, description="Depth TVD (ft)")
    overburden_stress_psi: float = Field(default=10000, description="Overburden stress (psi)")
    pore_pressure_psi: float = Field(default=4500, description="Pore pressure (psi)")
    sigma_min_psi: float = Field(default=6000, description="Minimum horizontal stress (psi)")
    sigma_max_psi: float = Field(default=8000, description="Maximum horizontal stress (psi)")
    tensile_strength_psi: float = Field(default=500, description="Tensile strength (psi)")
    poisson_ratio: float = Field(default=0.25, description="Poisson ratio")
    penetration_berea_in: float = Field(default=12.0, description="Penetration in Berea sandstone (in)")
    effective_stress_psi: float = Field(default=3000, description="Effective stress (psi)")
    temperature_f: float = Field(default=200, description="Temperature (F)")
    completion_fluid: str = Field(default="brine", description="Completion fluid type")
    wellbore_radius_ft: float = Field(default=0.354, description="Wellbore radius (ft)")
    kv_kh_ratio: float = Field(default=0.5, description="Kv/Kh ratio")
    tubing_od_in: float = Field(default=0.0, description="Tubing OD (in)")
    damage_radius_ft: float = Field(default=0.5, description="Damage radius (ft)")
    damage_permeability_md: float = Field(default=50.0, description="Damage zone permeability (mD)")
    formation_type: str = Field(default="sandstone", description="Formation type")


class IPRRequest(BaseModel):
    """Body for ``POST /completion/ipr``."""

    model: str = Field(default="vogel", description="IPR model: vogel | fetkovich | darcy")
    # Vogel params
    reservoir_pressure_psi: float = Field(default=4000, description="Reservoir pressure (psi)")
    bubble_point_psi: float = Field(default=2500, description="Bubble point pressure (psi)")
    productivity_index: float = Field(default=5.0, description="Productivity index (bbl/d/psi)")
    # Fetkovich params
    C_coefficient: float = Field(default=0.001, description="Fetkovich C coefficient")
    n_exponent: float = Field(default=0.8, description="Fetkovich n exponent")
    # Darcy params
    permeability_md: float = Field(default=100, description="Permeability (mD)")
    net_pay_ft: float = Field(default=50, description="Net pay thickness (ft)")
    Bo: float = Field(default=1.2, description="Oil formation volume factor")
    mu_oil_cp: float = Field(default=1.0, description="Oil viscosity (cP)")
    drainage_radius_ft: float = Field(default=660, description="Drainage radius (ft)")
    wellbore_radius_ft: float = Field(default=0.354, description="Wellbore radius (ft)")
    skin: float = Field(default=0, description="Skin factor")


class NodalAnalysisRequest(BaseModel):
    """Body for ``POST /completion/nodal-analysis``."""

    ipr_data: Dict[str, Any] = Field(default_factory=dict, description="IPR data with Pwf and q arrays")
    vlp_data: Dict[str, Any] = Field(default_factory=dict, description="VLP data with q_range and Pwf arrays")
