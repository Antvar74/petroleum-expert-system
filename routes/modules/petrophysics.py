"""
Petrophysics routes for PETROEXPERT.

Provides:
  POST /calculate/petrophysics/parse-las    — parse LAS content
  POST /calculate/petrophysics/saturation   — advanced Sw calculation
  POST /calculate/petrophysics/pickett-plot  — Pickett plot data
  POST /calculate/petrophysics/crossplot     — Density-Neutron crossplot
  POST /calculate/petrophysics/evaluate      — full petrophysical evaluation
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any

from orchestrator.petrophysics_engine import PetrophysicsEngine

from schemas.petrophysics import (
    ParseLASRequest,
    SaturationRequest,
    PickettPlotRequest,
    CrossplotRequest,
    PetroEvaluationRequest,
)

router = APIRouter(tags=["petrophysics"])


@router.post("/calculate/petrophysics/parse-las")
def standalone_parse_las(data: ParseLASRequest):
    """Parse LAS 2.0/3.0 content string and return structured log data."""
    content = data.las_content
    if not content:
        raise HTTPException(status_code=400, detail="las_content is required")
    result = PetrophysicsEngine.parse_las_content(content)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/calculate/petrophysics/saturation")
def standalone_advanced_saturation(data: SaturationRequest):
    """Calculate Sw with auto-model selection (Archie / Waxman-Smits / Dual-Water)."""
    return PetrophysicsEngine.calculate_water_saturation_advanced(
        phi=data.phi, rt=data.rt,
        rw=data.rw, vsh=data.vsh,
        rsh=data.rsh, a=data.a,
        m=data.m, n=data.n,
        method=data.method,
    )


@router.post("/calculate/petrophysics/pickett-plot")
def standalone_pickett_plot(data: PickettPlotRequest):
    """Generate Pickett plot data with iso-Sw lines."""
    return PetrophysicsEngine.generate_pickett_plot(
        log_data=data.log_data,
        rw=data.rw,
        a=data.a, m=data.m, n=data.n,
    )


@router.post("/calculate/petrophysics/crossplot")
def standalone_crossplot(data: CrossplotRequest):
    """Generate Density-Neutron crossplot with lithology lines and gas detection."""
    return PetrophysicsEngine.crossplot_density_neutron(
        log_data=data.log_data,
        rho_fluid=data.rho_fluid,
    )


@router.post("/calculate/petrophysics/evaluate")
def standalone_petro_evaluation(data: PetroEvaluationRequest):
    """Run full petrophysical evaluation — Vsh, porosity, Sw, permeability, net pay."""
    return PetrophysicsEngine.run_full_evaluation(
        log_data=data.log_data,
        archie_params=data.archie_params,
        matrix_params=data.matrix_params,
        cutoffs=data.cutoffs,
    )
