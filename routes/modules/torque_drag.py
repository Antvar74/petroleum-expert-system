from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import SurveyStation, DrillstringSection, TorqueDragResult
from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.torque_drag import (
    TorqueDragCalcRequest, BackCalculateRequest, TDCompareRequest,
)

router = APIRouter(tags=["Torque & Drag"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/survey")
def upload_survey(well_id: int, stations: List[Dict[str, Any]] = Body(...), db: Session = Depends(get_db)):
    """Upload survey stations and compute derived values (TVD, N, E, DLS)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    # Clear existing survey for this well
    db.query(SurveyStation).filter(SurveyStation.well_id == well_id).delete()

    # Compute derived values
    computed = TorqueDragEngine.compute_survey_derived(stations)

    # Save to DB
    for s in computed:
        db.add(SurveyStation(
            well_id=well_id,
            md=s["md"], inclination=s["inclination"], azimuth=s["azimuth"],
            tvd=s.get("tvd"), north=s.get("north"), east=s.get("east"), dls=s.get("dls")
        ))

    db.commit()
    return {"well_id": well_id, "stations_count": len(computed), "stations": computed}


@router.get("/wells/{well_id}/survey")
def get_survey(well_id: int, db: Session = Depends(get_db)):
    """Get survey stations for a well."""
    stations = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    return [
        {"id": s.id, "md": s.md, "inclination": s.inclination, "azimuth": s.azimuth,
         "tvd": s.tvd, "north": s.north, "east": s.east, "dls": s.dls}
        for s in stations
    ]


@router.post("/wells/{well_id}/drillstring")
def upload_drillstring(well_id: int, sections: List[Dict[str, Any]] = Body(...), db: Session = Depends(get_db)):
    """Define drillstring sections for a well."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    db.query(DrillstringSection).filter(DrillstringSection.well_id == well_id).delete()

    for sec in sections:
        db.add(DrillstringSection(
            well_id=well_id,
            section_name=sec.get("section_name", "Unknown"),
            od=sec["od"], id_inner=sec["id_inner"],
            weight=sec["weight"], length=sec["length"],
            order_from_bit=sec.get("order_from_bit", 0)
        ))

    db.commit()
    return {"well_id": well_id, "sections_count": len(sections)}


@router.get("/wells/{well_id}/drillstring")
def get_drillstring(well_id: int, db: Session = Depends(get_db)):
    """Get drillstring sections for a well."""
    sections = db.query(DrillstringSection).filter(
        DrillstringSection.well_id == well_id
    ).order_by(DrillstringSection.order_from_bit).all()
    return [
        {"id": s.id, "section_name": s.section_name, "od": s.od, "id_inner": s.id_inner,
         "weight": s.weight, "length": s.length, "order_from_bit": s.order_from_bit}
        for s in sections
    ]


@router.post("/wells/{well_id}/torque-drag")
def calculate_torque_drag(well_id: int, data: TorqueDragCalcRequest, db: Session = Depends(get_db)):
    """Run Torque & Drag calculation for a well."""
    # Get survey
    survey_rows = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    if len(survey_rows) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 survey stations")

    survey = [{"md": s.md, "inclination": s.inclination, "azimuth": s.azimuth, "tvd": s.tvd} for s in survey_rows]

    # Get drillstring
    ds_rows = db.query(DrillstringSection).filter(DrillstringSection.well_id == well_id).order_by(DrillstringSection.order_from_bit).all()
    if not ds_rows:
        raise HTTPException(status_code=400, detail="No drillstring defined")

    drillstring = [{"od": s.od, "id_inner": s.id_inner, "weight": s.weight,
                    "length": s.length, "order_from_bit": s.order_from_bit} for s in ds_rows]

    result = TorqueDragEngine.compute_torque_drag(
        survey=survey,
        drillstring=drillstring,
        friction_cased=data.friction_cased,
        friction_open=data.friction_open,
        operation=data.operation,
        mud_weight=data.mud_weight,
        wob=data.wob,
        rpm=data.rpm,
        casing_shoe_md=data.casing_shoe_md
    )

    # Save result
    td_result = TorqueDragResult(
        well_id=well_id,
        event_id=data.event_id,
        operation=data.operation,
        friction_cased=data.friction_cased,
        friction_open=data.friction_open,
        wob=data.wob,
        rpm=data.rpm,
        result_data=result.get("station_results"),
        summary=result.get("summary")
    )
    db.add(td_result)
    db.commit()

    return result


@router.post("/torque-drag/back-calculate")
def back_calculate_friction(data: BackCalculateRequest, db: Session = Depends(get_db)):
    """Back-calculate friction factor from measured hookload."""
    well_id = data.well_id

    survey_rows = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    survey = [{"md": s.md, "inclination": s.inclination, "azimuth": s.azimuth, "tvd": s.tvd} for s in survey_rows]

    ds_rows = db.query(DrillstringSection).filter(DrillstringSection.well_id == well_id).order_by(DrillstringSection.order_from_bit).all()
    drillstring = [{"od": s.od, "id_inner": s.id_inner, "weight": s.weight,
                    "length": s.length, "order_from_bit": s.order_from_bit} for s in ds_rows]

    result = TorqueDragEngine.back_calculate_friction(
        survey=survey,
        drillstring=drillstring,
        measured_hookload=data.measured_hookload,
        operation=data.operation,
        mud_weight=data.mud_weight,
        wob=data.wob,
        casing_shoe_md=data.casing_shoe_md
    )

    return result


@router.post("/wells/{well_id}/torque-drag/compare")
def compare_torque_drag(well_id: int, data: TDCompareRequest = TDCompareRequest(), db: Session = Depends(get_db)):
    """Run T&D for multiple operations and return combined results for overlay chart."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    survey_rows = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    if not survey_rows:
        raise HTTPException(status_code=400, detail="No survey data for well")
    survey = [{"md": s.md, "inclination": s.inclination, "azimuth": s.azimuth, "tvd": s.tvd} for s in survey_rows]

    ds_rows = db.query(DrillstringSection).filter(DrillstringSection.well_id == well_id).order_by(DrillstringSection.order_from_bit).all()
    if not ds_rows:
        raise HTTPException(status_code=400, detail="No drillstring data for well")
    drillstring = [{"od": s.od, "id_inner": s.id_inner, "weight": s.weight,
                    "length": s.length, "order_from_bit": s.order_from_bit} for s in ds_rows]

    operations = data.operations
    friction_cased = data.friction_cased
    friction_open = data.friction_open
    mud_weight = data.mud_weight
    wob = data.wob
    rpm = data.rpm
    casing_shoe_md = data.casing_shoe_md

    results = {}
    summary_comparison = []

    for op in operations:
        try:
            result = TorqueDragEngine.compute_torque_drag(
                survey=survey,
                drillstring=drillstring,
                friction_cased=friction_cased,
                friction_open=friction_open,
                mud_weight=mud_weight,
                operation=op,
                wob=wob,
                rpm=rpm,
                casing_shoe_md=casing_shoe_md,
            )
            results[op] = result.get("station_results", [])
            summary_comparison.append({
                "operation": op,
                "hookload_klb": result.get("summary", {}).get("surface_hookload_klb", 0),
                "torque_ftlb": result.get("summary", {}).get("surface_torque_ftlb", 0),
            })
        except Exception:
            results[op] = []
            summary_comparison.append({"operation": op, "hookload_klb": 0, "torque_ftlb": 0})

    # Build combined data array -- one row per MD with all operations
    combined = []
    if results.get(operations[0]):
        for i, station in enumerate(results[operations[0]]):
            row = {"md": station.get("md", 0)}
            for op in operations:
                op_stations = results.get(op, [])
                if i < len(op_stations):
                    row[op] = op_stations[i].get("axial_force", 0)
            combined.append(row)

    return {
        "operations": results,
        "combined": combined,
        "summary_comparison": summary_comparison,
    }


@router.post("/wells/{well_id}/torque-drag/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_torque_drag(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Torque & Drag results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_torque_drag(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
