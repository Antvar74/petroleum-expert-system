"""
Casing Design routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.casing_design_engine import CasingDesignEngine
from models.models_v2 import CasingDesignResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.casing_design import CasingDesignCalculateRequest, CombinationStringRequest, RunningLoadsRequest

router = APIRouter(tags=["casing-design"])
module_analyzer = ModuleAnalysisEngine()


@router.get("/casing-design/catalog")
async def list_catalog_ods():
    """List all available casing OD sizes in the catalog."""
    from orchestrator.casing_design_engine.constants import CASING_CATALOG
    ods = sorted([float(k) for k in CASING_CATALOG.keys()])
    return {"available_ods": ods, "count": len(ods)}


@router.get("/casing-design/catalog/{od_in}")
async def get_catalog_by_od(od_in: float, grade: str = None):
    """Get all casing options for a specific OD, optionally filtered by grade."""
    result = CasingDesignEngine.lookup_casing_catalog(od_in, grade_filter=grade)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/wells/{well_id}/casing-design")
def calculate_casing_design(well_id: int, data: CasingDesignCalculateRequest, db: Session = Depends(get_db)):
    """Run casing design calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CasingDesignEngine.calculate_full_casing_design(
        casing_od_in=data.casing_od_in,
        casing_id_in=data.casing_id_in,
        wall_thickness_in=data.wall_thickness_in,
        casing_weight_ppf=data.casing_weight_ppf,
        casing_length_ft=data.casing_length_ft,
        tvd_ft=data.tvd_ft,
        mud_weight_ppg=data.mud_weight_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg,
        fracture_gradient_ppg=data.fracture_gradient_ppg,
        gas_gradient_psi_ft=data.gas_gradient_psi_ft,
        cement_top_tvd_ft=data.cement_top_tvd_ft,
        cement_density_ppg=data.cement_density_ppg,
        bending_dls=data.bending_dls,
        overpull_lbs=data.overpull_lbs,
        sf_burst=data.sf_burst,
        sf_collapse=data.sf_collapse,
        sf_tension=data.sf_tension,
    )

    csg_result = CasingDesignResult(
        well_id=well_id,
        event_id=data.event_id,
        casing_od_in=data.casing_od_in,
        casing_weight_ppf=data.casing_weight_ppf,
        tvd_ft=data.tvd_ft,
        selected_grade=result.get("summary", {}).get("selected_grade", ""),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(csg_result)
    db.commit()
    db.refresh(csg_result)

    return {"id": csg_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/casing-design")
def get_casing_design(well_id: int, db: Session = Depends(get_db)):
    """Get latest casing design result for a well."""
    result = db.query(CasingDesignResult).filter(
        CasingDesignResult.well_id == well_id
    ).order_by(CasingDesignResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No casing design results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/casing-design/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_casing_design(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Casing Design results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_module(
        module="casing_design",
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/casing-design/combination-string")
def design_combination_string(data: CombinationStringRequest):
    """Design combination casing string (multi-grade/weight optimization)."""
    tvd = data.tvd_ft
    mud_wt = data.mud_weight_ppg
    pore_ppg = data.pore_pressure_ppg
    frac_ppg = data.frac_gradient_ppg
    casing_len = data.casing_length_ft if data.casing_length_ft is not None else tvd
    # Build default burst/collapse profiles if not provided
    default_burst = data.burst_profile if data.burst_profile is not None else [
        {"depth_ft": 0, "burst_psi": (frac_ppg - mud_wt) * 0.052 * 0},
        {"depth_ft": tvd, "burst_psi": (frac_ppg - mud_wt) * 0.052 * tvd},
    ]
    default_collapse = data.collapse_profile if data.collapse_profile is not None else [
        {"depth_ft": 0, "collapse_psi": mud_wt * 0.052 * 0},
        {"depth_ft": tvd, "collapse_psi": mud_wt * 0.052 * tvd},
    ]
    casing_weight_ppf = data.casing_weight_ppf
    default_tension = data.tension_at_surface_lbs if data.tension_at_surface_lbs is not None else casing_weight_ppf * casing_len * 0.817
    return CasingDesignEngine.design_combination_string(
        tvd_ft=tvd,
        casing_od_in=data.casing_od_in if data.casing_od is None else data.casing_od,
        burst_profile=default_burst,
        collapse_profile=default_collapse,
        tension_at_surface_lbs=default_tension,
        casing_length_ft=casing_len,
        mud_weight_ppg=mud_wt,
        sf_burst=data.sf_burst,
        sf_collapse=data.sf_collapse,
        sf_tension=data.sf_tension,
    )


@router.post("/casing-design/running-loads")
def calculate_running_loads(data: RunningLoadsRequest):
    """Calculate casing running loads (hookload, shock, bending)."""
    casing_length = data.casing_length_ft if data.casing_length_ft is not None else (data.total_length_ft if data.total_length_ft is not None else 10000)
    casing_od = data.casing_od_in if data.casing_od_in is not None else (data.casing_od if data.casing_od is not None else 9.625)
    return CasingDesignEngine.calculate_running_loads(
        casing_weight_ppf=data.casing_weight_ppf,
        casing_length_ft=casing_length,
        casing_od_in=casing_od,
        casing_id_in=data.casing_id_in,
        mud_weight_ppg=data.mud_weight_ppg,
        survey=data.survey,
        friction_factor=data.friction_factor,
    )
