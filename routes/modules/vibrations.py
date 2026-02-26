"""
Vibrations routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.vibrations_engine import VibrationsEngine
from models.models_v2 import VibrationsResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.vibrations import (
    VibrationsCalcRequest, Vibrations3DMapRequest, BHAModalRequest, FatigueRequest,
    FEARequest, CampbellRequest,
)

router = APIRouter(tags=["vibrations"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/vibrations")
def calculate_vibrations(well_id: int, data: VibrationsCalcRequest, db: Session = Depends(get_db)):
    """Run vibrations/stability analysis."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = VibrationsEngine.calculate_full_vibration_analysis(
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        rop_fph=data.rop_fph,
        torque_ftlb=data.torque_ftlb,
        bit_diameter_in=data.bit_diameter_in,
        dp_od_in=data.dp_od_in,
        dp_id_in=data.dp_id_in,
        dp_weight_lbft=data.dp_weight_lbft,
        bha_length_ft=data.bha_length_ft,
        bha_od_in=data.bha_od_in,
        bha_id_in=data.bha_id_in,
        bha_weight_lbft=data.bha_weight_lbft,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        inclination_deg=data.inclination_deg,
        friction_factor=data.friction_factor,
        stabilizer_spacing_ft=data.stabilizer_spacing_ft,
        ucs_psi=data.ucs_psi,
        total_depth_ft=data.total_depth_ft,
        n_blades=data.n_blades,
        bha_components=data.bha_components,
    )

    vib_result = VibrationsResult(
        well_id=well_id,
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        bit_diameter_in=data.bit_diameter_in,
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(vib_result)
    db.commit()
    db.refresh(vib_result)

    return {"id": vib_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/vibrations")
def get_vibrations(well_id: int, db: Session = Depends(get_db)):
    """Get latest vibrations result for a well."""
    result = db.query(VibrationsResult).filter(
        VibrationsResult.well_id == well_id
    ).order_by(VibrationsResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No vibrations results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/vibrations/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_vibrations(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Vibrations results via optimization_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_module(
        module="vibrations",
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/vibrations/3d-map")
def calculate_vibrations_3d_map(data: Vibrations3DMapRequest):
    """Generate 3D vibration risk map (MD vs RPM heatmap)."""
    return VibrationsEngine.calculate_vibration_map_3d(
        survey_stations=data.survey_stations,
        bha_od_in=data.bha_od_in,
        bha_id_in=data.bha_id_in,
        bha_weight_lbft=data.bha_weight_lbft,
        bha_length_ft=data.bha_length_ft,
        hole_diameter_in=data.hole_diameter_in,
        mud_weight_ppg=data.mud_weight_ppg,
        rpm_range=data.rpm_range,
        wob_klb=data.wob_klb,
    )


@router.post("/vibrations/bha-modal")
def calculate_bha_modal(data: BHAModalRequest):
    """Multi-component BHA modal analysis (Transfer Matrix Method)."""
    return VibrationsEngine.calculate_critical_rpm_lateral_multi(
        bha_components=data.bha_components,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        boundary_conditions=data.boundary_conditions,
    )


@router.post("/vibrations/fatigue")
def calculate_vibrations_fatigue(data: FatigueRequest):
    """Calculate drillstring fatigue damage (Miner's rule)."""
    return VibrationsEngine.calculate_fatigue_damage(
        drillstring_od=data.drillstring_od,
        drillstring_id=data.drillstring_id,
        drillstring_grade=data.drillstring_grade,
        survey_stations=data.survey_stations,
        rpm=data.rpm,
        hours_per_stand=data.hours_per_stand,
        vibration_severity=data.vibration_severity,
        total_rotating_hours=data.total_rotating_hours,
    )


@router.post("/vibrations/fea")
def calculate_fea(data: FEARequest):
    """Finite Element Analysis of BHA lateral vibrations."""
    return VibrationsEngine.run_fea_analysis(
        bha_components=data.bha_components,
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        bc=data.boundary_conditions,
        n_modes=data.n_modes,
        include_forced_response=data.include_forced_response,
        include_campbell=data.include_campbell,
        n_blades=data.n_blades,
        pv_cp=data.pv_cp,
        yp_lbf_100ft2=data.yp_lbf_100ft2,
    )


@router.post("/vibrations/campbell")
def calculate_campbell(data: CampbellRequest):
    """Generate Campbell diagram data for BHA."""
    return VibrationsEngine.generate_campbell_diagram(
        bha_components=data.bha_components,
        wob_klb=data.wob_klb,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        bc=data.boundary_conditions,
        rpm_min=data.rpm_min,
        rpm_max=data.rpm_max,
        rpm_step=data.rpm_step,
        n_modes=data.n_modes,
        n_blades=data.n_blades,
    )
