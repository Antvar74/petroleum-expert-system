"""
Analysis workflow routes for PETROEXPERT.

Provides:
  GET  /agents                                     — list specialist agents
  GET+POST /problems/{id}/analysis/init            — initialize analysis session
  GET  /analysis/{id}                              — get analysis details
  GET  /analysis/{id}/agent/{id}/query             — get agent prompt
  POST /analysis/{id}/agent/{id}/response          — submit agent response
  GET  /analysis/{id}/synthesis/query              — get synthesis prompt
  POST /analysis/{id}/synthesis/response           — submit synthesis response
  POST /analysis/{id}/agent/{id}/auto              — auto-run analysis step
  POST /analysis/{id}/synthesis/auto               — auto-run synthesis
  POST /analysis/{id}/rca/generate                 — generate RCA report
"""
import re
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union

from middleware.rate_limit import limiter, LLM_LIMIT

from models import get_db, Problem, Analysis, OperationalProblem
from models.models_v2 import Event, ParameterSet
from routes.dependencies import get_coordinator
from schemas.common import AnalysisInitRequest, TextResponseBody
from schemas.analysis import RCAGenerateRequest
from utils.logger import get_logger

logger = get_logger("routes.analysis")

router = APIRouter(tags=["analysis"])


@router.get("/agents", response_model=List[Dict[str, str]])
def list_agents():
    """List all available specialist agents"""
    coordinator = get_coordinator()
    agents_list = []
    for agent_id, agent in coordinator.agents.items():
        agents_list.append({
            "id": agent_id,
            "role": agent.role,
            "name": agent.name
        })
    return agents_list


@router.get("/problems/{problem_id}/analysis/init")
@router.post("/problems/{problem_id}/analysis/init")
def init_analysis(
    problem_id: int,
    workflow_q: Union[str, List[str]] = Query(None, alias="workflow"),
    workflow_b: AnalysisInitRequest = Body(None),
    db: Session = Depends(get_db)
):
    """Initialize a new analysis session for a problem"""
    coordinator = get_coordinator()

    try:
        # Determine workflow source
        workflow = "standard"
        if workflow_b and workflow_b.workflow:
            workflow = workflow_b.workflow
        elif workflow_q:
            workflow = workflow_q

        if isinstance(workflow, list):
            agent_ids = workflow
            valid_agents = list(coordinator.agents.keys())
            for agent_id in agent_ids:
                if agent_id not in valid_agents:
                    raise HTTPException(status_code=400, detail=f"Invalid agent ID: {agent_id}")
        else:
            agent_ids = coordinator.get_workflow(workflow)

        leader_agent_id = workflow_b.leader if workflow_b else None

        new_analysis = Analysis(
            problem_id=problem_id,
            workflow_used=agent_ids,
            leader_agent_id=leader_agent_id,
            individual_analyses=[],
            overall_confidence="PENDING"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

        return {
            "id": new_analysis.id,
            "analysis_id": new_analysis.id,
            "workflow": agent_ids,
            "leader": leader_agent_id,
            "current_agent_index": 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("init_analysis failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analysis/{analysis_id}")
def get_analysis_details(analysis_id: int, db: Session = Depends(get_db)):
    """Get full analysis details including problem/event context"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    result = {
        "id": analysis.id,
        "problem_id": analysis.problem_id,
        "event_id": getattr(analysis, 'event_id', None),
        "workflow": analysis.workflow_used,
        "individual_analyses": analysis.individual_analyses,
        "final_synthesis": analysis.final_synthesis,
    }

    # Try event-based context first
    ev_id = getattr(analysis, 'event_id', None)
    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            result["event"] = {
                "id": event.id,
                "phase": event.phase,
                "family": event.family,
                "event_type": event.event_type,
                "description": event.description
            }
            result["event_id"] = event.id

    # Fallback to legacy problem context
    if analysis.problem_id:
        problem = db.query(Problem).filter(Problem.id == analysis.problem_id).first()
        if problem:
            result["problem"] = {
                "id": problem.id,
                "description": problem.description,
                "additional_data": problem.additional_data,
                "well": {"name": problem.well.name} if problem.well else {}
            }
            if not result.get("event_id") and problem.additional_data:
                result["event_id"] = problem.additional_data.get("event_id")

    return result


@router.get("/analysis/{analysis_id}/agent/{agent_id}/query")
def get_query(analysis_id: int, agent_id: str, db: Session = Depends(get_db)):
    """Get the prompt for a specific agent in an analysis session"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    context = {"previous_analyses": analysis_record.individual_analyses or []}
    description = "No description available"

    ev_id = getattr(analysis_record, 'event_id', None)
    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            context["well_data"] = {
                "well_name": event.well.name if event.well else "Unknown",
                "description": event.description,
                "phase": event.phase,
                "family": event.family,
                "event_type": event.event_type
            }
            params = db.query(ParameterSet).filter(ParameterSet.event_id == ev_id).first()
            if params:
                context["well_data"]["depth_md"] = params.depth_md
                context["well_data"]["depth_tvd"] = params.depth_tvd
                context["well_data"]["mud_weight"] = params.mud_weight
            description = event.description or description

    if analysis_record.problem_id and "well_data" not in context:
        problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
        if problem:
            context["well_data"] = {
                "well_name": problem.well.name if problem.well else "Unknown",
                "depth_md": problem.depth_md,
                "description": problem.description
            }
            description = problem.description

    query_data = coordinator.get_agent_query(agent_id, description, context)
    return query_data


@router.post("/analysis/{analysis_id}/agent/{agent_id}/response")
def submit_response(analysis_id: int, agent_id: str, response: TextResponseBody, db: Session = Depends(get_db)):
    """Submit the response from Claude for an agent"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    individual_analyses = list(analysis_record.individual_analyses or [])
    agent_analysis = next((a for a in individual_analyses if a["agent"] == agent_id), None)

    description = "No description"
    context = {"previous_analyses": [a for a in individual_analyses if a["agent"] != agent_id]}

    ev_id = getattr(analysis_record, 'event_id', None)
    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            context["well_data"] = {"well_name": event.well.name if event.well else "Unknown"}
            description = event.description or description
    if analysis_record.problem_id and "well_data" not in context:
        problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
        if problem:
            context["well_data"] = {"well_name": problem.well.name}
            description = problem.description

    fresh_analysis = coordinator.get_agent_query(agent_id, description, context)
    updated_analysis = coordinator.process_agent_response(agent_id, fresh_analysis, response.text)

    if agent_analysis:
        index = individual_analyses.index(agent_analysis)
        individual_analyses[index] = updated_analysis
    else:
        individual_analyses.append(updated_analysis)

    analysis_record.individual_analyses = individual_analyses
    db.commit()

    return {"status": "success", "agent": agent_id, "confidence": updated_analysis["confidence"]}


@router.get("/analysis/{analysis_id}/synthesis/query")
def get_synthesis_query(analysis_id: int, db: Session = Depends(get_db)):
    """Get the final synthesis prompt"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    ev_id = getattr(analysis_record, 'event_id', None)
    op_problem = None

    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            params = db.query(ParameterSet).filter(ParameterSet.event_id == ev_id).first()
            op_problem = OperationalProblem(
                well_name=event.well.name if event.well else "Unknown",
                depth_md=params.depth_md if params else 0,
                depth_tvd=params.depth_tvd if params else 0,
                description=event.description or "",
                operation=event.phase or ""
            )

    if not op_problem and analysis_record.problem_id:
        problem_record = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
        if not problem_record:
            raise HTTPException(status_code=404, detail="Problem not found for this analysis")
        op_problem = OperationalProblem(
            well_name=problem_record.well.name,
            depth_md=problem_record.depth_md,
            depth_tvd=problem_record.depth_tvd,
            description=problem_record.description,
            operation=problem_record.operation
        )

    if not op_problem:
        raise HTTPException(status_code=404, detail="No event or problem found for this analysis")

    query = coordinator.get_synthesis_query(
        op_problem,
        analysis_record.individual_analyses,
        leader_id=analysis_record.leader_agent_id or "drilling_engineer"
    )
    return {"query": query}


@router.post("/analysis/{analysis_id}/synthesis/response")
def submit_synthesis(analysis_id: int, response: TextResponseBody, db: Session = Depends(get_db)):
    """Submit the final synthesis response from Claude"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    synthesis_text = response.text

    leader_id = analysis_record.leader_agent_id or "drilling_engineer"
    leader_agent = coordinator.agents.get(leader_id, coordinator.agents["drilling_engineer"])
    confidence = leader_agent._extract_confidence(synthesis_text)

    final_synthesis = {
        "agent": leader_id,
        "role": f"{leader_agent.role} (Synthesis Leader)",
        "analysis": synthesis_text,
        "confidence": confidence
    }

    analysis_record.final_synthesis = final_synthesis
    analysis_record.overall_confidence = confidence

    db.commit()
    return {"status": "success", "overall_confidence": confidence}


@router.post("/analysis/{analysis_id}/agent/{agent_id}/auto")
@limiter.limit(LLM_LIMIT)
async def run_auto_step(request: Request, analysis_id: int, agent_id: str, db: Session = Depends(get_db)):
    """Automatically run an analysis step using the local LLM"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    individual_analyses = list(analysis_record.individual_analyses or [])

    context = {"previous_analyses": individual_analyses}
    description = "No description"

    ev_id = getattr(analysis_record, 'event_id', None)
    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            context["well_data"] = {
                "well_name": event.well.name if event.well else "Unknown",
                "description": event.description
            }
            description = event.description or description

    if analysis_record.problem_id and "well_data" not in context:
        problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
        if problem:
            context["well_data"] = {"well_name": problem.well.name}
            description = problem.description

    # [REAL DATA INJECTION] — path-safe resolution
    match = re.search(r"\[REAL_DATA:(.*?)\]", description)
    if match:
        filename = match.group(1).strip()
        try:
            from utils.safe_path import resolve_safe_data_path
            from utils.data_loader import load_data_context

            # Resolve alias
            if filename == "BAKTE-9":
                filename = "BAKTE-9_ETAPA_18.5.pdf"

            file_path = resolve_safe_data_path(filename)
            context_text = load_data_context(file_path)
            context["extracted_report_text"] = context_text
        except ValueError as ve:
            logger.warning("Rejected unsafe data path: %s", ve)
        except Exception as e:
            logger.warning("Failed to load data context: %s", e)

    updated_analysis = await coordinator.run_automated_step(agent_id, description, context)

    existing = next((a for a in individual_analyses if a["agent"] == agent_id), None)
    if existing:
        index = individual_analyses.index(existing)
        individual_analyses[index] = updated_analysis
    else:
        individual_analyses.append(updated_analysis)

    analysis_record.individual_analyses = individual_analyses
    db.commit()

    return updated_analysis


@router.post("/analysis/{analysis_id}/synthesis/auto")
@limiter.limit(LLM_LIMIT)
async def run_auto_synthesis(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    """Automatically run the final synthesis using the local LLM"""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    ev_id = getattr(analysis_record, 'event_id', None)
    op_problem = None

    if ev_id:
        event = db.query(Event).filter(Event.id == ev_id).first()
        if event:
            params = db.query(ParameterSet).filter(ParameterSet.event_id == ev_id).first()
            op_problem = OperationalProblem(
                well_name=event.well.name if event.well else "Unknown",
                depth_md=params.depth_md if params else 0,
                depth_tvd=params.depth_tvd if params else 0,
                description=event.description or "",
                operation=event.phase or ""
            )

    if not op_problem and analysis_record.problem_id:
        problem_record = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
        if not problem_record:
            raise HTTPException(status_code=404, detail="Problem not found for this analysis")
        op_problem = OperationalProblem(
            well_name=problem_record.well.name,
            depth_md=problem_record.depth_md,
            depth_tvd=problem_record.depth_tvd,
            description=problem_record.description,
            operation=problem_record.operation
        )

    if not op_problem:
        raise HTTPException(status_code=404, detail="No event or problem found for this analysis")

    final_synthesis = await coordinator.run_automated_synthesis(
        op_problem,
        analysis_record.individual_analyses,
        leader_agent_id=analysis_record.leader_agent_id or "drilling_engineer"
    )

    analysis_record.final_synthesis = final_synthesis
    analysis_record.overall_confidence = final_synthesis["confidence"]
    db.commit()

    return final_synthesis


@router.post("/analysis/{analysis_id}/rca/generate")
@limiter.limit(LLM_LIMIT)
async def generate_rca_report(request: Request, analysis_id: int, payload: RCAGenerateRequest, db: Session = Depends(get_db)):
    """Generate an API RP 585 Report based on user's 5-Whys or Fishbone input."""
    coordinator = get_coordinator()
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")

    problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first() if analysis_record.problem_id else None
    individual_analyses = list(analysis_record.individual_analyses or [])

    well_name = "Unknown Well"
    if problem and hasattr(problem, 'well') and problem.well:
        well_name = problem.well.name
    context = {
        "well_data": {"well_name": well_name},
        "previous_analyses": individual_analyses
    }

    # [REAL DATA INJECTION] (RCA) — path-safe resolution
    problem_description = problem.description if problem else ""
    match = re.search(r"\[REAL_DATA:(.*?)\]", problem_description)
    if match:
        filename = match.group(1).strip()
        try:
            from utils.safe_path import resolve_safe_data_path
            from utils.data_loader import load_data_context

            # Resolve alias
            if filename == "BAKTE-9":
                filename = "BAKTE-9_ETAPA_18.5.pdf"

            file_path = resolve_safe_data_path(filename)
            context_text = load_data_context(file_path)
            context["extracted_report_text"] = context_text
        except ValueError as ve:
            logger.warning("Rejected unsafe data path: %s", ve)
        except Exception as e:
            logger.warning("Failed to load data context: %s", e)

    methodology = payload.methodology
    user_data = payload.data

    audit_result = await coordinator.run_automated_audit(methodology, user_data, context)

    existing = next((a for a in individual_analyses if a["agent"] == "rca_lead" and "AUDIT" in a.get("query", "")), None)
    if existing:
        index = individual_analyses.index(existing)
        individual_analyses[index] = audit_result
    else:
        individual_analyses.append(audit_result)

    analysis_record.individual_analyses = individual_analyses
    db.commit()

    return audit_result
