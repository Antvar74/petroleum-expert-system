"""
Pydantic request schemas for Shot Efficiency routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ShotEfficiencyCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/shot-efficiency``."""

    log_entries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Log data entries (list of dicts with MD, GR, RHOB, NPHI, Rt, etc.)",
    )
    archie_params: Dict[str, Any] = Field(
        default_factory=lambda: {"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05},
        description="Archie equation parameters",
    )
    matrix_params: Dict[str, Any] = Field(
        default_factory=lambda: {"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120},
        description="Matrix parameters for porosity/Vsh calculations",
    )
    cutoffs: Dict[str, Any] = Field(
        default_factory=lambda: {"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40, "min_thickness_ft": 2.0},
        description="Net pay cutoff values",
    )
    perf_params: Dict[str, Any] = Field(
        default_factory=lambda: {"spf": 6, "phasing_deg": 60, "perf_length_in": 10, "tunnel_radius_in": 0.2},
        description="Perforation parameters",
    )
    reservoir_params: Dict[str, Any] = Field(
        default_factory=lambda: {"k_h": 100, "kv_kh": 0.5, "wellbore_radius_ft": 0.354},
        description="Reservoir parameters",
    )
    sw_model: str = Field(
        default="auto",
        description="Water saturation model: auto | archie | simandoux | indonesia",
    )
    rsh: float = Field(default=5.0, description="Shale resistivity (ohm-m)")
    estimate_permeability: bool = Field(
        default=False, description="Whether to estimate permeability"
    )
    sw_irreducible: float = Field(
        default=0.25, description="Irreducible water saturation"
    )
