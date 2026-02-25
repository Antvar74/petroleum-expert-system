"""
Wellbore Cleanup routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine
from models.models_v2 import WellboreCleanupResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.wellbore_cleanup import WellboreCleanupCalculateRequest

router = APIRouter(tags=["wellbore-cleanup"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/wellbore-cleanup")
def calculate_wellbore_cleanup(well_id: int, data: WellboreCleanupCalculateRequest, db: Session = Depends(get_db)):
    """Run wellbore cleanup / hole cleaning calculation."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WellboreCleanupEngine.calculate_full_cleanup(
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        hole_id=data.hole_id,
        pipe_od=data.pipe_od,
        inclination=data.inclination,
        rop=data.rop,
        cutting_size=data.cutting_size,
        cutting_density=data.cutting_density,
        rpm=data.rpm,
        annular_length=data.annular_length
    )

    # Save result
    cu_result = WellboreCleanupResult(
        well_id=well_id,
        event_id=data.event_id,
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        hole_id=data.hole_id,
        pipe_od=data.pipe_od,
        inclination=data.inclination,
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(cu_result)
    db.commit()
    db.refresh(cu_result)

    return {"id": cu_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/wellbore-cleanup")
def get_wellbore_cleanup(well_id: int, db: Session = Depends(get_db)):
    """Get latest wellbore cleanup result for a well."""
    result = db.query(WellboreCleanupResult).filter(
        WellboreCleanupResult.well_id == well_id
    ).order_by(WellboreCleanupResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No cleanup results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/wellbore-cleanup/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_wellbore_cleanup(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Wellbore Cleanup results via mud_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_wellbore_cleanup(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
