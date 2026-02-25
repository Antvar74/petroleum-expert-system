"""
Cementing routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.cementing_engine import CementingEngine
from models.models_v2 import CementingResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.cementing import CementingCalculateRequest, GasMigrationRequest, CentralizerDesignRequest

router = APIRouter(tags=["cementing"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/cementing")
def calculate_cementing(well_id: int, data: CementingCalculateRequest, db: Session = Depends(get_db)):
    """Run cementing simulation calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CementingEngine.calculate_full_cementing(
        casing_od_in=data.casing_od_in,
        casing_id_in=data.casing_id_in,
        hole_id_in=data.hole_id_in,
        casing_shoe_md_ft=data.casing_shoe_md_ft,
        casing_shoe_tvd_ft=data.casing_shoe_tvd_ft,
        toc_md_ft=data.toc_md_ft,
        toc_tvd_ft=data.toc_tvd_ft,
        float_collar_md_ft=data.float_collar_md_ft,
        mud_weight_ppg=data.mud_weight_ppg,
        spacer_density_ppg=data.spacer_density_ppg,
        lead_cement_density_ppg=data.lead_cement_density_ppg,
        tail_cement_density_ppg=data.tail_cement_density_ppg,
        tail_length_ft=data.tail_length_ft,
        spacer_volume_bbl=data.spacer_volume_bbl,
        excess_pct=data.excess_pct,
        rat_hole_ft=data.rat_hole_ft,
        pump_rate_bbl_min=data.pump_rate_bbl_min,
        pv_mud=data.pv_mud,
        yp_mud=data.yp_mud,
        fracture_gradient_ppg=data.fracture_gradient_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg,
    )

    cem_result = CementingResult(
        well_id=well_id,
        event_id=data.event_id,
        casing_od_in=data.casing_od_in,
        hole_id_in=data.hole_id_in,
        casing_shoe_md_ft=data.casing_shoe_md_ft,
        cement_density_ppg=data.tail_cement_density_ppg,
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(cem_result)
    db.commit()
    db.refresh(cem_result)

    return {"id": cem_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/cementing")
def get_cementing(well_id: int, db: Session = Depends(get_db)):
    """Get latest cementing result for a well."""
    result = db.query(CementingResult).filter(
        CementingResult.well_id == well_id
    ).order_by(CementingResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No cementing results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/cementing/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_cementing(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Cementing results via cementing_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_module(
        module="cementing",
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/cementing/gas-migration")
def calculate_gas_migration(data: GasMigrationRequest):
    """Assess gas migration risk post-cementacion (API RP 65-2)."""
    cement_top = data.cement_top_tvd_ft
    cement_base = data.cement_base_tvd_ft
    return CementingEngine.calculate_gas_migration_risk(
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        cement_column_height_ft=cement_base - cement_top,
        slurry_density_ppg=data.slurry_density_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg,
        tvd_ft=cement_base,
        transition_time_hr=data.sgs_time_hr,
        thickening_time_hr=data.thickening_time_hr,
        sgs_10min_lbf_100sqft=data.sgs_10min_lbf_100sqft,
    )


@router.post("/cementing/centralizer-design")
def design_centralizers(data: CentralizerDesignRequest):
    """Design centralizer spacing and standoff (API RP 10D-2)."""
    return CementingEngine.design_centralizers(
        casing_od_in=data.casing_od_in,
        hole_id_in=data.hole_id_in,
        casing_weight_ppf=data.casing_weight_ppf,
        inclination_profile=data.inclination_profile,
        centralizer_type=data.centralizer_type,
    )
