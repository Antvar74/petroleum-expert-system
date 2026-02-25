from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import WorkoverHydraulicsResult
from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.workover import CTElongationRequest, CTFatigueRequest, WorkoverHydraulicsCalculateRequest

router = APIRouter(tags=["Workover"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/workover/ct-elongation")
def calculate_ct_elongation(data: CTElongationRequest):
    """Calculate coiled tubing elongation (weight, temp, ballooning, Bourdon)."""
    return WorkoverHydraulicsEngine.calculate_ct_elongation(
        ct_od=data.ct_od,
        ct_id=data.ct_id,
        ct_length=data.ct_length,
        weight_per_ft=data.weight_per_ft,
        mud_weight=data.mud_weight,
        delta_p_internal=data.delta_p_internal,
        delta_t=data.delta_t,
        wellhead_pressure=data.wellhead_pressure
    )


@router.post("/workover/ct-fatigue")
def calculate_ct_fatigue(data: CTFatigueRequest):
    """Calculate coiled tubing fatigue life (API RP 5C7, Miner's rule)."""
    return WorkoverHydraulicsEngine.calculate_ct_fatigue(
        ct_od=data.ct_od,
        wall_thickness=data.wall_thickness,
        reel_diameter=data.reel_diameter,
        internal_pressure=data.internal_pressure,
        yield_strength_psi=data.yield_strength_psi,
        trips_history=data.trips_history
    )


@router.post("/wells/{well_id}/workover-hydraulics")
def calculate_workover_hydraulics(well_id: int, data: WorkoverHydraulicsCalculateRequest, db: Session = Depends(get_db)):
    """Run workover/CT hydraulics calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WorkoverHydraulicsEngine.calculate_full_workover(
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        ct_od=data.ct_od,
        wall_thickness=data.wall_thickness,
        ct_length=data.ct_length,
        hole_id=data.hole_id,
        tvd=data.tvd,
        inclination=data.inclination,
        friction_factor=data.friction_factor,
        wellhead_pressure=data.wellhead_pressure,
        reservoir_pressure=data.reservoir_pressure,
        yield_strength_psi=data.yield_strength_psi
    )

    wh_result = WorkoverHydraulicsResult(
        well_id=well_id,
        ct_od=data.ct_od,
        wall_thickness=data.wall_thickness,
        ct_length=data.ct_length,
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        hole_id=data.hole_id,
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(wh_result)
    db.commit()
    db.refresh(wh_result)

    return {"id": wh_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/workover-hydraulics")
def get_workover_hydraulics(well_id: int, db: Session = Depends(get_db)):
    """Get latest workover hydraulics result for a well."""
    result = db.query(WorkoverHydraulicsResult).filter(
        WorkoverHydraulicsResult.well_id == well_id
    ).order_by(WorkoverHydraulicsResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No workover hydraulics results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/workover-hydraulics/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_workover_hydraulics(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Workover Hydraulics results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_workover_hydraulics(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
