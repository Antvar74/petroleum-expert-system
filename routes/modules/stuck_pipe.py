from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import StuckPipeAnalysis, Event, ParameterSet
from orchestrator.stuck_pipe_engine import StuckPipeEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.stuck_pipe import (
    DiagnosisAnswerRequest, FreePointRequest, RiskAssessmentRequest,
    FullStuckPipeRequest, DifferentialStickingRequest, PackoffRiskRequest,
)

router = APIRouter(tags=["Stuck Pipe"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/stuck-pipe/diagnose/start")
def start_stuck_pipe_diagnosis():
    """Start the stuck pipe decision tree -- returns first question."""
    return StuckPipeEngine.get_next_question()


@router.post("/stuck-pipe/diagnose/answer")
def answer_stuck_pipe_question(data: DiagnosisAnswerRequest):
    """Answer a question in the decision tree -- returns next question or result."""
    return StuckPipeEngine.get_next_question(
        current_node=data.node_id,
        answer=data.answer
    )


@router.post("/stuck-pipe/free-point")
def calculate_free_point(data: FreePointRequest):
    """Calculate free point depth from pipe stretch data."""
    return StuckPipeEngine.calculate_free_point(
        pipe_od=data.pipe_od,
        pipe_id=data.pipe_id,
        pipe_grade=data.pipe_grade,
        stretch_inches=data.stretch_inches,
        pull_force_lbs=data.pull_force_lbs
    )


@router.post("/stuck-pipe/risk-assessment")
def assess_stuck_pipe_risk(data: RiskAssessmentRequest):
    """Assess stuck pipe risk matrix."""
    return StuckPipeEngine.assess_risk_matrix(
        mechanism=data.mechanism,
        params=data.params
    )


@router.post("/events/{event_id}/stuck-pipe")
def full_stuck_pipe_analysis(event_id: int, data: FullStuckPipeRequest, db: Session = Depends(get_db)):
    """Full stuck pipe analysis linked to an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Classify mechanism from answers
    answers = data.answers
    classification = StuckPipeEngine.classify_mechanism(answers)

    # Risk assessment
    risk = StuckPipeEngine.assess_risk_matrix(
        mechanism=classification["mechanism"],
        params=data.params
    )

    # Recommended actions
    actions = StuckPipeEngine.get_recommended_actions(classification["mechanism"])

    # Free point if stretch data provided
    free_point = None
    if data.stretch_inches and data.pull_force_lbs:
        free_point = StuckPipeEngine.calculate_free_point(
            pipe_od=data.pipe_od,
            pipe_id=data.pipe_id,
            pipe_grade=data.pipe_grade,
            stretch_inches=data.stretch_inches,
            pull_force_lbs=data.pull_force_lbs
        )

    # Save
    analysis = StuckPipeAnalysis(
        event_id=event_id,
        well_id=event.well_id,
        mechanism=classification["mechanism"],
        decision_tree_path=classification.get("decision_path"),
        free_point_depth=free_point["free_point_depth_ft"] if free_point else None,
        pipe_stretch_inches=data.stretch_inches,
        pull_force_lbs=data.pull_force_lbs,
        risk_matrix=risk,
        recommended_actions=actions
    )
    db.add(analysis)
    db.commit()

    return {
        "classification": classification,
        "risk": risk,
        "actions": actions,
        "free_point": free_point
    }


@router.post("/stuck-pipe/differential-sticking")
def calculate_differential_sticking(data: DifferentialStickingRequest):
    """Calculate differential sticking force from ECD and formation pressure."""
    return StuckPipeEngine.calculate_differential_sticking_force(
        ecd_ppg=data.ecd_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg,
        contact_length_ft=data.contact_length_ft,
        pipe_od_in=data.pipe_od_in,
        filter_cake_thickness_in=data.filter_cake_thickness_in,
        friction_coefficient_cake=data.friction_coefficient_cake,
        tvd_ft=data.tvd_ft
    )


@router.post("/stuck-pipe/packoff-risk")
def assess_packoff_risk(data: PackoffRiskRequest):
    """Assess pack-off risk from hole cleaning indicators."""
    return StuckPipeEngine.assess_packoff_risk(
        hci=data.hci,
        cuttings_concentration_pct=data.cuttings_concentration_pct,
        inclination=data.inclination,
        annular_velocity_ftmin=data.annular_velocity_ftmin
    )


@router.post("/wells/{well_id}/stuck-pipe/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_stuck_pipe(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Stuck Pipe results via drilling_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_stuck_pipe(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
