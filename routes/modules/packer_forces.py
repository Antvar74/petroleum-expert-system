"""
Packer Forces routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.packer_forces_engine import PackerForcesEngine
from models.models_v2 import PackerForcesResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.packer_forces import (
    PackerForcesCalculateRequest,
    APBRequest,
    LandingConditionsRequest,
    BucklingLengthRequest,
)

router = APIRouter(tags=["packer-forces"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/packer-forces")
def calculate_packer_forces(well_id: int, data: PackerForcesCalculateRequest, db: Session = Depends(get_db)):
    """Run packer forces calculation."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = PackerForcesEngine.calculate_total_packer_force(
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        tubing_weight=data.tubing_weight,
        tubing_length=data.tubing_length,
        seal_bore_id=data.seal_bore_id,
        initial_tubing_pressure=data.initial_tubing_pressure,
        final_tubing_pressure=data.final_tubing_pressure,
        initial_annulus_pressure=data.initial_annulus_pressure,
        final_annulus_pressure=data.final_annulus_pressure,
        initial_temperature=data.initial_temperature,
        final_temperature=data.final_temperature,
        packer_depth_tvd=data.packer_depth_tvd,
        mud_weight_tubing=data.mud_weight_tubing,
        mud_weight_annulus=data.mud_weight_annulus,
        poisson_ratio=data.poisson_ratio,
        thermal_expansion=data.thermal_expansion
    )

    # Save result
    pf_result = PackerForcesResult(
        well_id=well_id,
        event_id=data.event_id,
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        tubing_weight=data.tubing_weight,
        packer_depth_tvd=data.packer_depth_tvd,
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(pf_result)
    db.commit()
    db.refresh(pf_result)

    return {"id": pf_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/packer-forces")
def get_packer_forces(well_id: int, db: Session = Depends(get_db)):
    """Get latest packer forces result for a well."""
    result = db.query(PackerForcesResult).filter(
        PackerForcesResult.well_id == well_id
    ).order_by(PackerForcesResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No packer forces results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/packer-forces/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_packer_forces(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Packer Forces results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_packer_forces(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/packer/apb")
def calculate_packer_apb(data: APBRequest):
    """Calculate Annular Pressure Buildup (APB) for trapped annulus."""
    return PackerForcesEngine.calculate_apb(
        annular_fluid_type=data.annular_fluid_type,
        delta_t_avg=data.delta_t_avg,
        annular_volume_bbl=data.annular_volume_bbl,
        casing_od=data.casing_od,
        casing_id=data.casing_id,
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        annular_length_ft=data.annular_length_ft,
        initial_pressure_psi=data.initial_pressure_psi,
    )


@router.post("/packer/landing-conditions")
def calculate_packer_landing(data: LandingConditionsRequest):
    """Calculate tubing landing conditions for packer installation."""
    return PackerForcesEngine.calculate_landing_conditions(
        tubing_sections=data.tubing_sections,
        survey_stations=data.survey_stations,
        mud_weight_ppg=data.mud_weight_ppg,
        friction_factor=data.friction_factor,
        packer_depth_tvd_ft=data.packer_depth_tvd_ft,
        set_down_weight_lbs=data.set_down_weight_lbs,
    )


@router.post("/packer/buckling-length")
def calculate_packer_buckling_length(data: BucklingLengthRequest):
    """Calculate tubing buckling length and effects."""
    return PackerForcesEngine.calculate_buckling_length(
        axial_force=data.axial_force,
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        tubing_weight_ppf=data.tubing_weight_ppf,
        casing_id=data.casing_id,
        inclination_deg=data.inclination_deg,
        mud_weight_ppg=data.mud_weight_ppg,
    )
