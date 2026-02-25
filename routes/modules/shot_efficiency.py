"""
Shot Efficiency routes for PETROEXPERT.
"""
import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine
from models.models_v2 import ShotEfficiencyResult
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.shot_efficiency import ShotEfficiencyCalculateRequest
from utils.upload_validation import validate_upload

router = APIRouter(tags=["shot-efficiency"])
module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/shot-efficiency")
def calculate_shot_efficiency(well_id: int, data: ShotEfficiencyCalculateRequest, db: Session = Depends(get_db)):
    """Run shot efficiency analysis (petrophysics + interval ranking)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = ShotEfficiencyEngine.calculate_full_shot_efficiency(
        log_entries=data.log_entries,
        archie_params=data.archie_params,
        matrix_params=data.matrix_params,
        cutoffs=data.cutoffs,
        perf_params=data.perf_params,
        reservoir_params=data.reservoir_params,
    )

    se_result = ShotEfficiencyResult(
        well_id=well_id,
        log_points_count=result.get("summary", {}).get("total_log_points", 0),
        net_pay_intervals=result.get("summary", {}).get("net_pay_intervals_count", 0),
        total_net_pay_ft=result.get("summary", {}).get("total_net_pay_ft", 0),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(se_result)
    db.commit()
    db.refresh(se_result)

    return {"id": se_result.id, "well_id": well_id, **result}


@router.post("/wells/{well_id}/shot-efficiency/upload-csv")
async def upload_log_csv(well_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload CSV with log data (columns: MD, GR, RHOB, NPHI, Rt, Caliper)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    contents = await validate_upload(file, allowed_extensions=[".csv"])
    try:
        df = pd.read_csv(io.BytesIO(contents))
        # Normalize column names
        col_map = {}
        for col in df.columns:
            cl = col.strip().lower()
            if cl in ("md", "depth", "prof"):
                col_map[col] = "md"
            elif cl in ("gr", "gamma_ray", "gamma"):
                col_map[col] = "gr"
            elif cl in ("rhob", "density", "den"):
                col_map[col] = "rhob"
            elif cl in ("nphi", "neutron", "neu"):
                col_map[col] = "nphi"
            elif cl in ("rt", "resistivity", "res", "ild"):
                col_map[col] = "rt"
            elif cl in ("caliper", "cali", "cal"):
                col_map[col] = "caliper"
        df = df.rename(columns=col_map)

        required = ["md", "gr", "rhob", "nphi", "rt"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

        log_entries = df.fillna(0).to_dict(orient="records")
        return {"status": "ok", "rows": len(log_entries), "columns": list(df.columns), "log_entries": log_entries}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


@router.get("/wells/{well_id}/shot-efficiency")
def get_shot_efficiency(well_id: int, db: Session = Depends(get_db)):
    """Get latest shot efficiency result for a well."""
    result = db.query(ShotEfficiencyResult).filter(
        ShotEfficiencyResult.well_id == well_id
    ).order_by(ShotEfficiencyResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No shot efficiency results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


@router.post("/wells/{well_id}/shot-efficiency/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_shot_efficiency(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Shot Efficiency results via geologist agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_module(
        module="shot_efficiency",
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
