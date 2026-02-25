"""
Structured event routes for PETROEXPERT.

Provides:
  POST /events/extract              — extract parameters from uploaded files
  POST /events                      — create a new structured event
  POST /events/{id}/analysis/init   — initialize event-based analysis
  POST /events/{id}/calculate       — run physics engine on event
  POST /events/{id}/rca             — generate structured RCA
  GET  /events/{id}/rca             — get existing RCA report
  DELETE /events/{id}/rca           — delete RCA report
  POST /events/{id}/stuck-pipe      — event-based stuck pipe analysis
"""
import os
import re
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from models import get_db, Well, Problem, Analysis
from models.models_v2 import Event, ParameterSet, RCAReport
from orchestrator.calculation_engine import CalculationEngine
from agents.data_extractor import DataExtractionAgent
from agents.rca_synthesizer import RCASynthesizerAgent
from routes.dependencies import get_coordinator
from schemas.events import CreateEventRequest, EventAnalysisInitRequest
from utils.logger import get_logger
from utils.upload_validation import validate_upload

logger = get_logger("routes.events")

router = APIRouter(tags=["events"])

data_extractor = DataExtractionAgent()
calc_engine = CalculationEngine()
rca_agent = RCASynthesizerAgent()


@router.post("/events/extract")
async def extract_event_parameters(files: List[UploadFile] = File(...)):
    """
    Extracts structured parameters from uploaded files (PDF/CSV/TXT/MD).
    Accepts multiple files and combines their content.
    """
    try:
        combined_text = ""

        for file in files:
            safe_name = os.path.basename(file.filename or "upload.txt")
            _, ext = os.path.splitext(safe_name)
            ext = ext if ext else ".txt"

            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            try:
                validated_content = await validate_upload(file, allowed_extensions=[".pdf", ".csv", ".txt", ".md"])
                tmp.write(validated_content)
                tmp.close()

                from utils.data_loader import load_data_context
                text_content = load_data_context(tmp.name)

                combined_text += f"\n\n--- BEGIN FILE: {safe_name} ---\n{text_content}\n--- END FILE: {safe_name} ---\n"
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)

        extracted_data = await data_extractor.extract_parameters(combined_text)
        return extracted_data

    except Exception as e:
        logger.exception("Event parameter extraction failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/events")
def create_event(event_data: CreateEventRequest, db: Session = Depends(get_db)):
    """Creates a new Structured Event with Parameters."""
    try:
        def safe_float(val, default=0.0):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                match = re.search(r"[-+]?\d*\.?\d+", val)
                if match:
                    return float(match.group())
            return default

        new_event = Event(
            well_id=event_data.well_id,
            phase=event_data.phase,
            family=event_data.family,
            event_type=event_data.event_type,
            description=event_data.parameters.get("operation_summary", "No description"),
            status="analyzing"
        )
        db.add(new_event)
        db.flush()

        params = event_data.parameters
        valid_keys = [c.name for c in ParameterSet.__table__.columns if c.name not in ['id', 'event_id']]

        filtered_params = {}
        for k, v in params.items():
            if k in valid_keys:
                col = ParameterSet.__table__.columns[k]
                if str(col.type) == 'FLOAT' or str(col.type) == 'INTEGER':
                    filtered_params[k] = safe_float(v, default=None)
                else:
                    filtered_params[k] = v

        new_params = ParameterSet(event_id=new_event.id, **filtered_params)
        db.add(new_params)

        legacy_problem = Problem(
            well_id=event_data.well_id,
            depth_md=safe_float(params.get("depth_md"), 0),
            depth_tvd=safe_float(params.get("depth_tvd"), 0),
            description=f"[{(event_data.family or 'UNKNOWN').upper()}] {params.get('operation_summary', '')}",
            operation=event_data.phase,
            formation="Unknown",
            mud_weight=safe_float(params.get("mud_weight"), None),
            inclination=safe_float(params.get("inclination"), None),
            azimuth=safe_float(params.get("azimuth"), None),
            torque=safe_float(params.get("torque"), None),
            overpull=safe_float(params.get("overpull"), None),
            string_weight=safe_float(params.get("hook_load"), None),
            additional_data={"event_id": new_event.id}
        )
        db.add(legacy_problem)
        db.commit()

        return {
            "id": new_event.id,
            "problem_id": legacy_problem.id,
            "message": "Event created successfully"
        }

    except Exception as e:
        db.rollback()
        logger.exception("Event creation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/events/{event_id}/analysis/init")
def init_event_analysis(
    event_id: int,
    body: EventAnalysisInitRequest = EventAnalysisInitRequest(),
    db: Session = Depends(get_db),
):
    """Initialize analysis directly from an Event (no Problem bridge needed)."""
    coordinator = get_coordinator()

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    workflow = body.workflow
    leader = body.leader

    if isinstance(workflow, list):
        agent_ids = workflow
        valid_agents = list(coordinator.agents.keys())
        for aid in agent_ids:
            if aid not in valid_agents:
                raise HTTPException(status_code=400, detail=f"Invalid agent: {aid}")
    else:
        agent_ids = coordinator.get_workflow(workflow)

    new_analysis = Analysis(
        problem_id=None,
        event_id=event_id,
        workflow_used=agent_ids,
        leader_agent_id=leader,
        individual_analyses=[],
        overall_confidence="PENDING"
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)

    return {
        "id": new_analysis.id,
        "analysis_id": new_analysis.id,
        "event_id": event_id,
        "workflow": agent_ids,
        "leader": leader,
        "current_agent_index": 0
    }


@router.post("/events/{event_id}/calculate")
def calculate_event_physics(event_id: int, db: Session = Depends(get_db)):
    """Run Physics Engine on the event parameters."""
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        params = db.query(ParameterSet).filter(ParameterSet.event_id == event_id).first()
        if not params:
            raise HTTPException(status_code=404, detail="Parameters not found for this event")

        param_dict = {c.name: getattr(params, c.name) for c in params.__table__.columns}
        results = calc_engine.calculate_all(param_dict)

        return {"event_id": event_id, "physics_results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Event calculation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/events/{event_id}/rca")
async def generate_structured_rca(event_id: int, db: Session = Depends(get_db)):
    """Triggers Structured RCA using Event Data + Physics Results."""
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        params = db.query(ParameterSet).filter(ParameterSet.event_id == event_id).first()
        if not params:
            raise HTTPException(status_code=400, detail="Parameters not found. Run extraction first.")

        existing_rca = db.query(RCAReport).filter(RCAReport.event_id == event_id).first()
        if existing_rca:
            return {
                "root_cause_category": existing_rca.root_cause_category,
                "root_cause_description": existing_rca.root_cause_description,
                "five_whys": existing_rca.five_whys,
                "fishbone_factors": existing_rca.fishbone_factors,
                "corrective_actions": existing_rca.corrective_actions,
                "prevention_actions": existing_rca.prevention_actions,
                "confidence_score": existing_rca.confidence_score,
                "cached": True
            }

        param_dict = {c.name: getattr(params, c.name) for c in params.__table__.columns}
        physics_results = calc_engine.calculate_all(param_dict)

        event_details = {
            "phase": event.phase,
            "family": event.family,
            "event_type": event.event_type,
            "description": event.description
        }

        rca_output = await rca_agent.perform_structured_rca(
            event_details=event_details,
            parameters=param_dict,
            physics_results=physics_results
        )

        new_report = RCAReport(
            event_id=event_id,
            root_cause_category=rca_output.get("root_cause_category"),
            root_cause_description=rca_output.get("root_cause_description"),
            five_whys=rca_output.get("five_whys"),
            fishbone_factors=rca_output.get("fishbone_factors"),
            corrective_actions=rca_output.get("corrective_actions"),
            prevention_actions=rca_output.get("prevention_actions"),
            confidence_score=rca_output.get("confidence_score")
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return rca_output

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RCA generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/events/{event_id}/rca")
def get_existing_rca(event_id: int, db: Session = Depends(get_db)):
    """Get existing RCA report for an event without regenerating."""
    report = db.query(RCAReport).filter(RCAReport.event_id == event_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No RCA report found for this event")
    return {
        "root_cause_category": report.root_cause_category,
        "root_cause_description": report.root_cause_description,
        "five_whys": report.five_whys,
        "fishbone_factors": report.fishbone_factors,
        "corrective_actions": report.corrective_actions,
        "prevention_actions": report.prevention_actions,
        "confidence_score": report.confidence_score
    }


@router.delete("/events/{event_id}/rca")
def delete_rca_report(event_id: int, db: Session = Depends(get_db)):
    """Delete existing RCA report to allow regeneration."""
    report = db.query(RCAReport).filter(RCAReport.event_id == event_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No RCA report found")
    db.delete(report)
    db.commit()
    return {"message": "RCA report deleted. You can now regenerate."}
