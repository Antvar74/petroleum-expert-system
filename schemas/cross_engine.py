"""
Pydantic request schemas for Cross-Engine correlation routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CementECDToCollapseRequest(BaseModel):
    """Body for ``POST /cross-engine/cement-ecd-to-collapse``."""

    casing_shoe_tvd_ft: float = Field(default=10000)
    hole_id_in: float = Field(default=12.25)
    casing_od_in: float = Field(default=9.625)
    mud_weight_ppg: float = Field(default=10.0)
    spacer_density_ppg: float = Field(default=12.0)
    lead_cement_density_ppg: float = Field(default=13.5)
    tail_cement_density_ppg: float = Field(default=16.0)
    pump_rate_bbl_min: float = Field(default=5.0)
    pv_mud: float = Field(default=25)
    yp_mud: float = Field(default=12)
    wall_thickness_in: float = Field(default=0.472)
    yield_strength_psi: float = Field(default=80000)


class CasingIDToCompletionRequest(BaseModel):
    """Body for ``POST /cross-engine/casing-id-to-completion``."""

    casing_id_in: float = Field(default=8.681)
    max_pressure_psi: float = Field(default=15000)
    max_temperature_f: float = Field(default=350)
    gun_type_filter: Optional[str] = Field(default=None)


class IPRSkinToShotRequest(BaseModel):
    """Body for ``POST /cross-engine/ipr-skin-to-shot``."""

    kh_md_ft: float = Field(default=5000)
    net_pay_ft: float = Field(default=50)
    Bo: float = Field(default=1.2)
    mu_oil_cp: float = Field(default=1.0)
    reservoir_pressure_psi: float = Field(default=4000)
    drainage_radius_ft: float = Field(default=660)
    wellbore_radius_ft: float = Field(default=0.354)
    skin: float = Field(default=0)


class VibrationsToTDRequest(BaseModel):
    """Body for ``POST /cross-engine/vibrations-to-td``."""

    wob_klb: float = Field(default=25)
    rpm: float = Field(default=120)
    rop_fph: float = Field(default=60)
    torque_ftlb: float = Field(default=15000)
    bit_diameter_in: float = Field(default=8.5)
    bha_od_in: float = Field(default=6.75)
    bha_id_in: float = Field(default=2.813)
    bha_weight_lbft: float = Field(default=83)
    bha_length_ft: float = Field(default=300)
    mud_weight_ppg: float = Field(default=10)
    hole_diameter_in: float = Field(default=8.5)
    base_friction_factor: float = Field(default=0.25)


class PackerAPBToCasingRequest(BaseModel):
    """Body for ``POST /cross-engine/packer-apb-to-casing``."""

    annular_fluid_type: str = Field(default="OBM")
    delta_t_avg: float = Field(default=150)
    annular_volume_bbl: float = Field(default=200)
    casing_od: float = Field(default=9.625)
    casing_id: float = Field(default=8.681)
    tubing_od: float = Field(default=3.5)
    tubing_id: float = Field(default=2.992)
    annular_length_ft: float = Field(default=10000)
    casing_od_in: float = Field(default=9.625)
    wall_thickness_in: float = Field(default=0.472)
    yield_strength_psi: float = Field(default=80000)


class TDToPackerLandingRequest(BaseModel):
    """Body for ``POST /cross-engine/td-to-packer-landing``."""

    tubing_sections: List[Dict[str, Any]] = Field(
        default_factory=lambda: [{"od": 3.5, "id_inner": 2.992, "length_ft": 10000, "weight_ppf": 9.3}]
    )
    survey_stations: Optional[List[Dict[str, Any]]] = Field(default=None)
    mud_weight_ppg: float = Field(default=8.34)
    friction_factor: float = Field(default=0.30)
    packer_depth_tvd_ft: float = Field(default=10000)
    set_down_weight_lbs: float = Field(default=5000)
