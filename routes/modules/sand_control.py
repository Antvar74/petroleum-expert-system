"""
Sand Control routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.sand_control_engine import SandControlEngine
from models.models_v2 import SandControlResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.sand_control import SandControlCalculateRequest

router = APIRouter(tags=["sand-control"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/sand-control")
def calculate_sand_control(well_id: int, data: SandControlCalculateRequest, db: Session = Depends(get_db)):
    """Run sand control analysis calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = SandControlEngine.calculate_full_sand_control(
        sieve_sizes_mm=data.sieve_sizes_mm,
        cumulative_passing_pct=data.cumulative_passing_pct,
        hole_id=data.hole_id,
        screen_od=data.screen_od,
        interval_length=data.interval_length,
        ucs_psi=data.ucs_psi,
        friction_angle_deg=data.friction_angle_deg,
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        overburden_stress_psi=data.overburden_stress_psi,
        formation_permeability_md=data.formation_permeability_md,
        wellbore_radius_ft=data.wellbore_radius_ft,
        wellbore_type=data.wellbore_type,
        gravel_permeability_md=data.gravel_permeability_md,
        pack_factor=data.pack_factor,
        washout_factor=data.washout_factor
    )

    sc_result = SandControlResult(
        well_id=well_id,
        d50_mm=result.get("psd", {}).get("d50_mm", 0),
        uniformity_coefficient=result.get("psd", {}).get("uniformity_coefficient", 0),
        ucs_psi=data.ucs_psi,
        interval_length=data.interval_length,
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(sc_result)
    db.commit()
    db.refresh(sc_result)

    return {"id": sc_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/sand-control")
def get_sand_control(well_id: int, db: Session = Depends(get_db)):
    """Get latest sand control result for a well."""
    result = db.query(SandControlResult).filter(
        SandControlResult.well_id == well_id
    ).order_by(SandControlResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No sand control results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/sand-control/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_sand_control(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Sand Control results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_sand_control(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
