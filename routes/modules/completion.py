"""
Completion Design routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.completion_design_engine import CompletionDesignEngine
from models.models_v2 import CompletionDesignResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.completion import CompletionDesignCalculateRequest, IPRRequest, NodalAnalysisRequest

router = APIRouter(tags=["completion-design"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/completion-design")
def calculate_completion_design(well_id: int, data: CompletionDesignCalculateRequest, db: Session = Depends(get_db)):
    """Run completion design calculations (perforating, fracture, productivity)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CompletionDesignEngine.calculate_full_completion_design(
        casing_id_in=data.casing_id_in,
        formation_permeability_md=data.formation_permeability_md,
        formation_thickness_ft=data.formation_thickness_ft,
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        wellbore_pressure_psi=data.wellbore_pressure_psi,
        depth_tvd_ft=data.depth_tvd_ft,
        overburden_stress_psi=data.overburden_stress_psi,
        pore_pressure_psi=data.pore_pressure_psi,
        sigma_min_psi=data.sigma_min_psi,
        sigma_max_psi=data.sigma_max_psi,
        tensile_strength_psi=data.tensile_strength_psi,
        poisson_ratio=data.poisson_ratio,
        penetration_berea_in=data.penetration_berea_in,
        effective_stress_psi=data.effective_stress_psi,
        temperature_f=data.temperature_f,
        completion_fluid=data.completion_fluid,
        wellbore_radius_ft=data.wellbore_radius_ft,
        kv_kh_ratio=data.kv_kh_ratio,
        tubing_od_in=data.tubing_od_in,
        damage_radius_ft=data.damage_radius_ft,
        damage_permeability_md=data.damage_permeability_md,
        formation_type=data.formation_type,
    )

    cd_result = CompletionDesignResult(
        well_id=well_id,
        casing_id_in=data.casing_id_in,
        formation_permeability_md=data.formation_permeability_md,
        depth_tvd_ft=data.depth_tvd_ft,
        penetration_berea_in=data.penetration_berea_in,
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(cd_result)
    db.commit()
    db.refresh(cd_result)

    return {"id": cd_result.id, "well_id": well_id, **result}


@router.get("/wells/{well_id}/completion-design")
def get_completion_design(well_id: int, db: Session = Depends(get_db)):
    """Get latest completion design result for a well."""
    result = db.query(CompletionDesignResult).filter(
        CompletionDesignResult.well_id == well_id
    ).order_by(CompletionDesignResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No completion design results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/completion-design/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_completion_design(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Completion Design results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_module(
        module="completion_design",
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/completion/ipr")
def calculate_ipr(data: IPRRequest):
    """Calculate IPR curve (Vogel, Fetkovich, or Darcy)."""
    model = data.model
    if model == "vogel":
        return CompletionDesignEngine.calculate_ipr_vogel(
            reservoir_pressure_psi=data.reservoir_pressure_psi,
            bubble_point_psi=data.bubble_point_psi,
            productivity_index_above_pb=data.productivity_index,
        )
    elif model == "fetkovich":
        return CompletionDesignEngine.calculate_ipr_fetkovich(
            reservoir_pressure_psi=data.reservoir_pressure_psi,
            C_coefficient=data.C_coefficient,
            n_exponent=data.n_exponent,
        )
    else:
        return CompletionDesignEngine.calculate_ipr_darcy(
            permeability_md=data.permeability_md,
            net_pay_ft=data.net_pay_ft,
            Bo=data.Bo, mu_oil_cp=data.mu_oil_cp,
            reservoir_pressure_psi=data.reservoir_pressure_psi,
            drainage_radius_ft=data.drainage_radius_ft,
            wellbore_radius_ft=data.wellbore_radius_ft,
            skin=data.skin,
        )


@router.post("/completion/nodal-analysis")
def calculate_nodal(data: NodalAnalysisRequest):
    """Calculate nodal analysis (IPR-VLP intersection)."""
    ipr = data.ipr_data
    vlp = data.vlp_data
    return CompletionDesignEngine.calculate_nodal_analysis(
        ipr_Pwf=ipr.get("Pwf", []),
        ipr_q=ipr.get("q", []),
        vlp_q_range=vlp.get("q_range", []),
        vlp_Pwf=vlp.get("Pwf", []),
    )
