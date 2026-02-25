"""
Pydantic request schemas for Petrophysics routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParseLASRequest(BaseModel):
    """Body for ``POST /calculate/petrophysics/parse-las``."""

    las_content: str = Field(default="", description="LAS 2.0/3.0 content string")


class SaturationRequest(BaseModel):
    """Body for ``POST /calculate/petrophysics/saturation``."""

    phi: float = Field(default=0.20, description="Porosity (fraction)")
    rt: float = Field(default=20.0, description="True resistivity (ohm-m)")
    rw: float = Field(default=0.05, description="Water resistivity (ohm-m)")
    vsh: float = Field(default=0.0, description="Shale volume (fraction)")
    rsh: float = Field(default=2.0, description="Shale resistivity (ohm-m)")
    a: float = Field(default=1.0, description="Archie tortuosity factor")
    m: float = Field(default=2.0, description="Archie cementation exponent")
    n: float = Field(default=2.0, description="Archie saturation exponent")
    method: str = Field(default="auto", description="Method: auto | archie | waxman_smits | dual_water")


class PickettPlotRequest(BaseModel):
    """Body for ``POST /calculate/petrophysics/pickett-plot``."""

    log_data: List[Dict[str, Any]] = Field(default_factory=list, description="Log data points")
    rw: float = Field(default=0.05, description="Water resistivity (ohm-m)")
    a: float = Field(default=1.0, description="Archie tortuosity factor")
    m: float = Field(default=2.0, description="Archie cementation exponent")
    n: float = Field(default=2.0, description="Archie saturation exponent")


class CrossplotRequest(BaseModel):
    """Body for ``POST /calculate/petrophysics/crossplot``."""

    log_data: List[Dict[str, Any]] = Field(default_factory=list, description="Log data points")
    rho_fluid: float = Field(default=1.0, description="Fluid density (g/cc)")


class PetroEvaluationRequest(BaseModel):
    """Body for ``POST /calculate/petrophysics/evaluate``."""

    log_data: List[Dict[str, Any]] = Field(default_factory=list, description="Log data points")
    archie_params: Optional[Dict[str, Any]] = Field(default=None, description="Archie equation parameters")
    matrix_params: Optional[Dict[str, Any]] = Field(default=None, description="Matrix parameters")
    cutoffs: Optional[Dict[str, Any]] = Field(default=None, description="Net pay cutoff values")
