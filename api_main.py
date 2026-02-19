from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import uvicorn
import os
import json
import io
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import init_db, get_db, Well, Problem, Analysis, Program, OperationalProblem
from orchestrator.api_coordinator import APICoordinator
from utils.optimization_engine import OptimizationEngine
from middleware.auth import verify_api_key


# Lifespan — replaces deprecated @app.on_event("startup")
@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(
    title="Petroleum Expert System API",
    root_path="/api" if os.environ.get("VERCEL") else "",
    dependencies=[Depends(verify_api_key)],
    lifespan=lifespan,
)

# Global Exception Handler
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_msg = f"GLOBAL HANDLER: {str(exc)}\n{traceback.format_exc()}"
    print(error_msg)
    with open("server_error_global.log", "a") as f:
        f.write(error_msg + "\n" + "-"*80 + "\n")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

# Enable CORS for React frontend (configurable via CORS_ORIGINS env var)
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Coordinator
coordinator = APICoordinator()

# --- Providers ---

@app.get("/providers")
async def list_providers():
    """List available LLM providers based on configured API keys."""
    return await coordinator.gateway.get_available_providers()


# --- Wells ---

@app.get("/wells", response_model=List[Dict[str, Any]])
def list_wells(db: Session = Depends(get_db)):
    wells = db.query(Well).all()
    return [{"id": w.id, "name": w.name, "location": w.location} for w in wells]

@app.post("/wells")
def create_well(name: str, location: Optional[str] = None, db: Session = Depends(get_db)):
    db_well = db.query(Well).filter(Well.name == name).first()
    if db_well:
        raise HTTPException(status_code=400, detail="Well already exists")
    new_well = Well(name=name, location=location)
    db.add(new_well)
    db.commit()
    db.refresh(new_well)
    return new_well

@app.delete("/wells/{well_id}")
def delete_well(well_id: int, db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    
    try:
        db.delete(well)
        db.commit()
        return {"message": "Well deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"ERROR deleting well: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# --- Problems ---

@app.get("/wells/{well_id}/problems")
def list_problems(well_id: int, db: Session = Depends(get_db)):
    problems = db.query(Problem).filter(Problem.well_id == well_id).all()
    return problems

@app.post("/wells/{well_id}/problems")
def create_problem(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    print(f"DEBUG: Creating problem for well {well_id}")
    print(f"DEBUG: Received data: {json.dumps(data, indent=2)}")
    
    # Map common variations
    depth_md = data.get("depth_md")
    depth_tvd = data.get("depth_tvd")
    description = data.get("description")
    operation = data.get("operation") or data.get("operation_type")
    
    if depth_md is None or depth_tvd is None or description is None or operation is None:
        missing = [k for k, v in {"depth_md": depth_md, "depth_tvd": depth_tvd, "description": description, "operation": operation}.items() if v is None]
        print(f"ERROR: Missing required fields: {missing}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

    new_problem = Problem(
        well_id=well_id,
        depth_md=float(depth_md),
        depth_tvd=float(depth_tvd),
        description=description,
        operation=operation,
        formation=data.get("formation"),
        mud_weight=data.get("mud_weight_ppg") or data.get("mud_weight"),
        inclination=data.get("inclination_deg") or data.get("inclination"),
        azimuth=data.get("azimuth_deg") or data.get("azimuth"),
        torque=data.get("torque_klbft") or data.get("torque"),
        drag=data.get("drag_lbs") or data.get("drag"),
        overpull=data.get("overpull_lbs") or data.get("overpull"),
        string_weight=data.get("string_weight_lbs") or data.get("string_weight"),
        additional_data=data.get("additional_data") or {}
    )
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    print(f"DEBUG: Problem created successfully with ID: {new_problem.id}")
    return new_problem

# --- Analysis Workflow ---

@app.get("/agents", response_model=List[Dict[str, str]])
def list_agents():
    """List all available specialist agents"""
    agents_list = []
    for agent_id, agent in coordinator.agents.items():
        agents_list.append({
            "id": agent_id,
            "role": agent.role,
            "name": agent.name
        })
    return agents_list

@app.get("/problems/{problem_id}/analysis/init")
@app.post("/problems/{problem_id}/analysis/init")
def init_analysis(
    problem_id: int, 
    workflow_q: Union[str, List[str]] = Query(None, alias="workflow"),
    workflow_b: Dict[str, Any] = Body(None),
    db: Session = Depends(get_db)
):
    """Initialize a new analysis session for a problem"""
    print(f"DEBUG: init_analysis called for problem {problem_id}")
    print(f"DEBUG: workflow_q={workflow_q}, workflow_b={workflow_b}")
    
    try:
        # Determine workflow source
        workflow = "standard"
        if workflow_b and "workflow" in workflow_b:
            workflow = workflow_b["workflow"]
        elif workflow_q:
            workflow = workflow_q
            
        if isinstance(workflow, list):
            # Custom workflow from frontend
            agent_ids = workflow
            # Validate agents
            valid_agents = list(coordinator.agents.keys())
            for agent_id in agent_ids:
                if agent_id not in valid_agents:
                    raise HTTPException(status_code=400, detail=f"Invalid agent ID: {agent_id}")
        else:
            # Standard named workflow
            agent_ids = coordinator.get_workflow(workflow)
        
        # Capture leader if provided in body
        leader_agent_id = workflow_b.get("leader") if workflow_b else None
        
        # Store initial analysis record
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
    except Exception as e:
        import traceback
        error_msg = f"ERROR in init_analysis: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        with open("server_error.log", "a") as f:
            f.write(error_msg + "\n" + "-"*80 + "\n")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.get("/analysis/{analysis_id}")
def get_analysis_details(analysis_id: int, db: Session = Depends(get_db)):
    """Get full analysis details including problem context"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis session not found")
        
    return {
        "id": analysis.id,
        "problem_id": analysis.problem_id,
        "workflow": analysis.workflow_used,
        "individual_analyses": analysis.individual_analyses,
        "final_synthesis": analysis.final_synthesis,
        "problem": {
            "id": analysis.problem.id,
            "description": analysis.problem.description,
            "additional_data": analysis.problem.additional_data,
            "well": {
                "name": analysis.problem.well.name
            }
        }
    }

@app.get("/analysis/{analysis_id}/agent/{agent_id}/query")
def get_query(analysis_id: int, agent_id: str, db: Session = Depends(get_db)):
    """Get the prompt for a specific agent in an analysis session"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")
        
    problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    
    # Reconstruct context from previous analyses in this session
    context = {
        "well_data": {
            "well_name": problem.well.name,
            "depth_md": problem.depth_md,
            "description": problem.description
        },
        "previous_analyses": analysis_record.individual_analyses or []
    }
    
    query_data = coordinator.get_agent_query(agent_id, problem.description, context)
    return query_data

@app.post("/analysis/{analysis_id}/agent/{agent_id}/response")
def submit_response(analysis_id: int, agent_id: str, response: Dict[str, str], db: Session = Depends(get_db)):
    """Submit the response from Claude for an agent"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")
        
    # Get current analysis state
    individual_analyses = list(analysis_record.individual_analyses or [])
    
    # Find or create placeholder for this agent
    agent_analysis = next((a for a in individual_analyses if a["agent"] == agent_id), None)
    
    # We need the original query to update the response
    problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    context = {
        "well_data": {"well_name": problem.well.name},
        "previous_analyses": [a for a in individual_analyses if a["agent"] != agent_id]
    }
    
    fresh_analysis = coordinator.get_agent_query(agent_id, problem.description, context)
    updated_analysis = coordinator.process_agent_response(agent_id, fresh_analysis, response.get("text", ""))
    
    # Update list
    if agent_analysis:
        index = individual_analyses.index(agent_analysis)
        individual_analyses[index] = updated_analysis
    else:
        individual_analyses.append(updated_analysis)
        
    analysis_record.individual_analyses = individual_analyses
    db.commit()
    
    return {"status": "success", "agent": agent_id, "confidence": updated_analysis["confidence"]}

@app.get("/analysis/{analysis_id}/synthesis/query")
def get_synthesis_query(analysis_id: int, db: Session = Depends(get_db)):
    """Get the final synthesis prompt"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    problem_record = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    
    # Wrap problem record in OperationalProblem dataclass to use coordinator's method
    op_problem = OperationalProblem(
        well_name=problem_record.well.name,
        depth_md=problem_record.depth_md,
        depth_tvd=problem_record.depth_tvd,
        description=problem_record.description,
        operation=problem_record.operation
    )
    
    query = coordinator.get_synthesis_query(
        op_problem, 
        analysis_record.individual_analyses,
        leader_id=analysis_record.leader_agent_id or "drilling_engineer"
    )
    return {"query": query}

@app.post("/analysis/{analysis_id}/synthesis/response")
def submit_synthesis(analysis_id: int, response: Dict[str, str], db: Session = Depends(get_db)):
    """Submit the final synthesis response from Claude"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    synthesis_text = response.get("text", "")
    
    # Use leader to analyze confidence
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
    # Calculate overall confidence
    # (Simplified logic for now)
    analysis_record.overall_confidence = confidence
    
    db.commit()
    return {"status": "success", "overall_confidence": confidence}

# --- Automated Analysis (v3.0) ---

@app.get("/models")
async def list_models():
    """List available local models in Ollama"""
    return await coordinator.local_llm.get_available_models()

@app.post("/analysis/{analysis_id}/agent/{agent_id}/auto")
async def run_auto_step(analysis_id: int, agent_id: str, db: Session = Depends(get_db)):
    """Automatically run an analysis step using the local LLM"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")
        
    problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    individual_analyses = list(analysis_record.individual_analyses or [])
    
    # Context for the agent
    context = {
        "well_data": {"well_name": problem.well.name},
        "previous_analyses": individual_analyses
    }
    
    # [REAL DATA INJECTION]
    # Check for [REAL_DATA:filename.ext] tag
    import re
    match = re.search(r"\[REAL_DATA:(.*?)\]", problem.description)
    if match:
        filename = match.group(1).strip()
        print(f"🚀 DETECTED REAL DATA FLAG: Injecting {filename} Data Context")
        try:
            from utils.data_loader import load_data_context
            
            # Look in data folder
            file_path = f"data/{filename}"
            
            # Fallback for simple BAKTE-9 legacy tag
            if filename == "BAKTE-9": file_path = "data/BAKTE-9_ETAPA_18.5.pdf"
            
            # Load context using unified loader
            context_text = load_data_context(file_path)
            context["extracted_report_text"] = context_text
            
        except Exception as e:
            print(f"❌ Failed to load data context: {e}")

    # Run automated analysis
    updated_analysis = await coordinator.run_automated_step(agent_id, problem.description, context)
    
    # Save to db
    existing = next((a for a in individual_analyses if a["agent"] == agent_id), None)
    if existing:
        index = individual_analyses.index(existing)
        individual_analyses[index] = updated_analysis
    else:
        individual_analyses.append(updated_analysis)
        
    analysis_record.individual_analyses = individual_analyses
    db.commit()
    
    return updated_analysis

@app.post("/analysis/{analysis_id}/synthesis/auto")
async def run_auto_synthesis(analysis_id: int, db: Session = Depends(get_db)):
    """Automatically run the final synthesis using the local LLM"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    problem_record = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    
    op_problem = OperationalProblem(
        well_name=problem_record.well.name,
        depth_md=problem_record.depth_md,
        depth_tvd=problem_record.depth_tvd,
        description=problem_record.description,
        operation=problem_record.operation
    )
    
    final_synthesis = await coordinator.run_automated_synthesis(
        op_problem, 
        analysis_record.individual_analyses,
        leader_agent_id=analysis_record.leader_agent_id or "drilling_engineer"
    )
    
    analysis_record.final_synthesis = final_synthesis
    analysis_record.overall_confidence = final_synthesis["confidence"]
    db.commit()
    
    return final_synthesis

# --- Programs (v3.0 Phase 2) ---

@app.get("/wells/{well_id}/programs")
def get_programs(well_id: int, db: Session = Depends(get_db)):
    return db.query(Program).filter(Program.well_id == well_id).all()

@app.post("/wells/{well_id}/programs")
async def create_program(well_id: int, type: str, db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    
    new_program = Program(well_id=well_id, type=type, status="draft")
    db.add(new_program)
    db.commit()
    db.refresh(new_program)
    return new_program

@app.get("/programs/{program_id}")
def get_program(program_id: int, db: Session = Depends(get_db)):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program

@app.post("/programs/{program_id}/generate")
async def generate_program_content(program_id: int, db: Session = Depends(get_db)):
    """Generate the technical content for a program using LLM"""
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Generate content
    content_text = await coordinator.run_automated_program(
        program_type=program.type,
        well_name=program.well.name
    )
    
    program.content = {"markdown": content_text}
    program.status = "generated"
    db.commit()
    return program



# --- RCA Hybrid Generation (v3.0 Phase 7) ---

@app.post("/analysis/{analysis_id}/rca/generate")
async def generate_rca_report(analysis_id: int, payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Generate an API RP 585 Report based on user's 5-Whys or Fishbone input.
    """
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis session not found")
        
    problem = db.query(Problem).filter(Problem.id == analysis_record.problem_id).first()
    individual_analyses = list(analysis_record.individual_analyses or [])
    
    # Context
    context = {
        "well_data": {"well_name": problem.well.name},
        "previous_analyses": individual_analyses
    }
    
    # [REAL DATA INJECTION] (RCA)
    import re
    # Match [REAL_DATA:filename.ext]
    match = re.search(r"\[REAL_DATA:(.*?)\]", problem.description)
    if match:
        filename = match.group(1).strip()
        print(f"🚀 DETECTED REAL DATA FLAG (RCA): Injecting {filename}")
        try:
            from utils.data_loader import load_data_context
            
            # Look in data folder
            file_path = f"data/{filename}"
            
            # Fallback for legacy
            if filename == "BAKTE-9": file_path = "data/BAKTE-9_ETAPA_18.5.pdf"
            
            # Load context using unified loader
            context_text = load_data_context(file_path)
            context["extracted_report_text"] = context_text
            
        except Exception as e:
            print(f"❌ Failed to load data context: {e}")
    
    methodology = payload.get("methodology") # "5whys" or "fishbone"
    user_data = payload.get("data")
    
    if not methodology or not user_data:
        raise HTTPException(status_code=400, detail="Missing methodology or data")
        
    # Run Audit
    audit_result = await coordinator.run_automated_audit(methodology, user_data, context)
    
    # Save to db (append to analyses)
    # Check if we already have an RCA Lead audit, if so replace it
    existing = next((a for a in individual_analyses if a["agent"] == "rca_lead" and "AUDIT" in a.get("query", "")), None)
    
    if existing:
        index = individual_analyses.index(existing)
        individual_analyses[index] = audit_result
    else:
        individual_analyses.append(audit_result)
        
    analysis_record.individual_analyses = individual_analyses
    db.commit()
    
    return audit_result


# --- Structured Event Analysis (v4.0) ---

from agents.data_extractor import DataExtractionAgent
data_extractor = DataExtractionAgent()

@app.post("/events/extract")
async def extract_event_parameters(files: List[UploadFile] = File(...)):
    """
    Extracts structured parameters from uploaded files (PDF/CSV/TXT/MD).
    Accepts multiple files and combines their content.
    Returns JSON for the frontend wizard to pre-fill.
    """
    try:
        combined_text = ""
        
        for file in files:
            # Save temp file
            temp_filename = f"temp_{file.filename}"
            with open(temp_filename, "wb") as buffer:
                buffer.write(await file.read())
                
            # 1. Load Text using unified loader
            from utils.data_loader import load_data_context
            text_content = load_data_context(temp_filename)
            
            # Append with separator
            combined_text += f"\n\n--- BEGIN FILE: {file.filename} ---\n{text_content}\n--- END FILE: {file.filename} ---\n"
            
            # Cleanup
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            
        # 2. Extract Parameters using LLM (Combined context)
        # Note: DataExtractionAgent truncates to 15k chars to fit context window
        extracted_data = await data_extractor.extract_parameters(combined_text)
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ Extraction Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events")
def create_event(event_data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Creates a new Structured Event with Parameters.
    """
    try:
        from models.models_v2 import Event, ParameterSet
        import re

        def safe_float(val, default=0.0):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                # Extract first number found
                match = re.search(r"[-+]?\d*\.?\d+", val)
                if match:
                    return float(match.group())
            return default
        
        # 1. Create Event
        new_event = Event(
            well_id=event_data.get("well_id"),
            phase=event_data.get("phase"),
            family=event_data.get("family"),
            description=event_data.get("parameters", {}).get("operation_summary", "No description"),
            status="analyzing"
        )
        db.add(new_event)
        db.flush() # Generate ID
        
        # 2. Create Parameter Set
        params = event_data.get("parameters", {})
        # Filter out keys that don't match the model (like 'operation_summary' which handled above)
        valid_keys = [c.name for c in ParameterSet.__table__.columns if c.name not in ['id', 'event_id']]
        
        # Sanitize parameters for ParameterSet (it also has Float columns)
        filtered_params = {}
        for k, v in params.items():
            if k in valid_keys:
                # Check if column is float
                col = ParameterSet.__table__.columns[k]
                if str(col.type) == 'FLOAT' or str(col.type) == 'INTEGER':
                    filtered_params[k] = safe_float(v, default=None)
                else:
                    filtered_params[k] = v
        
        new_params = ParameterSet(
            event_id=new_event.id,
            **filtered_params
        )
        db.add(new_params)
        
        # 3. Create a Legacy Problem record for backward compatibility/dashboard
        # This bridges the gap so the rest of the system (Analyses) still works
        legacy_problem = Problem(
            well_id=event_data.get("well_id"),
            depth_md=safe_float(params.get("depth_md"), 0),
            depth_tvd=safe_float(params.get("depth_tvd"), 0),
            description=f"[{event_data.get('family').upper()}] {params.get('operation_summary', '')}",
            operation=event_data.get("phase"),
            formation="Unknown", # Could be extracted
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
        import traceback
        print(f"❌ Create Event Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

from orchestrator.calculation_engine import CalculationEngine
calc_engine = CalculationEngine()

@app.post("/events/{event_id}/calculate")
def calculate_event_physics(event_id: int, db: Session = Depends(get_db)):
    """
    Run Physics Engine (Module 3) on the event parameters.
    Returns ECD, CCI, and Risk Assessment.
    """
    try:
        from models.models_v2 import Event, ParameterSet
        
        # 1. Get Event Parameters
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
            
        params = db.query(ParameterSet).filter(ParameterSet.event_id == event_id).first()
        if not params:
            raise HTTPException(status_code=404, detail="Parameters not found for this event")
            
        # Convert SQLAlchemy model to dict
        param_dict = {c.name: getattr(params, c.name) for c in params.__table__.columns}
        
        # 2. Run Calculations
        results = calc_engine.calculate_all(param_dict)
        
        return {
            "event_id": event_id,
            "physics_results": results
        }
        
    except Exception as e:
        print(f"❌ Calculation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- RCA Generation (Module 4) ---

from agents.rca_lead import RCALeadAgent
rca_agent = RCALeadAgent()

@app.post("/events/{event_id}/rca")
async def generate_structured_rca(event_id: int, db: Session = Depends(get_db)):
    """
    Triggers Structured RCA using Event Data + Physics Results.
    """
    try:
        from models.models_v2 import Event, ParameterSet, RCAReport
        
        # 1. Fetch Event & Parameters
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
            
        params = db.query(ParameterSet).filter(ParameterSet.event_id == event_id).first()
        if not params:
            raise HTTPException(status_code=400, detail="Parameters not found. Run extraction first.")
            
        # 2. Run/Fetch Physics Calculations
        # (Re-running to ensure fresh data)
        param_dict = {c.name: getattr(params, c.name) for c in params.__table__.columns}
        physics_results = calc_engine.calculate_all(param_dict)
        
        # 3. Call RCA Agent
        event_details = {
            "phase": event.phase,
            "family": event.family,
            "event_type": event.event_type,
            "description": event.description
        }
        
        print(f"🤖 Starting RCA for Event component {event_id}...")
        rca_output = await rca_agent.perform_structured_rca(
            event_details=event_details,
            parameters=param_dict,
            physics_results=physics_results
        )
        
        # 4. Save Report
        new_report = RCAReport(
            event_id=event_id,
            root_cause_category=rca_output.get("root_cause_category"),
            root_cause_description=rca_output.get("root_cause_description"),
            five_whys=rca_output.get("five_whys"),
            fishbone_factors=rca_output.get("fishbone_factors"),
            corrective_actions=rca_output.get("corrective_actions"),
            confidence_score=rca_output.get("confidence_score")
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return rca_output
        
    except Exception as e:
        print(f"❌ RCA Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# --- Data Management ---

@app.get("/files", response_model=List[str])
def list_data_files():
    """List all supported data files in the data directory"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []
    
    supported_exts = ['.pdf', '.csv', '.md', '.txt']
    files = [f for f in os.listdir(data_dir) if os.path.splitext(f)[1].lower() in supported_exts]
    return sorted(files)

# --- Data Ingestion (v3.0 Phase 3) ---

@app.post("/ingest/csv")
async def ingest_csv(well_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    
    content = await file.read()
    # Simple parsing logic for the example
    try:
        df = pd.read_csv(io.BytesIO(content))
        # Here we would save to a 'historical_data' table
        # For now, we return summary
        return {
            "well_id": well_id,
            "rows_ingested": len(df),
            "columns": list(df.columns),
            "status": "Success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

# ============================================================
# MODULE ENGINES: Torque & Drag, Hydraulics, Stuck Pipe, Well Control
# ============================================================

from orchestrator.module_analysis_engine import ModuleAnalysisEngine
module_analyzer = ModuleAnalysisEngine()

from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.stuck_pipe_engine import StuckPipeEngine
from orchestrator.well_control_engine import WellControlEngine
from models.models_v2 import (
    SurveyStation, DrillstringSection, TorqueDragResult,
    HydraulicSection, BitNozzle, HydraulicResult,
    StuckPipeAnalysis, KillSheet
)

# --- Torque & Drag ---

@app.post("/wells/{well_id}/survey")
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


@app.get("/wells/{well_id}/survey")
def get_survey(well_id: int, db: Session = Depends(get_db)):
    """Get survey stations for a well."""
    stations = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    return [
        {"id": s.id, "md": s.md, "inclination": s.inclination, "azimuth": s.azimuth,
         "tvd": s.tvd, "north": s.north, "east": s.east, "dls": s.dls}
        for s in stations
    ]


@app.post("/wells/{well_id}/drillstring")
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


@app.get("/wells/{well_id}/drillstring")
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


@app.post("/wells/{well_id}/torque-drag")
def calculate_torque_drag(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
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
        friction_cased=data.get("friction_cased", 0.25),
        friction_open=data.get("friction_open", 0.35),
        operation=data.get("operation", "trip_out"),
        mud_weight=data.get("mud_weight", 10.0),
        wob=data.get("wob", 0.0),
        rpm=data.get("rpm", 0.0),
        casing_shoe_md=data.get("casing_shoe_md", 0.0)
    )

    # Save result
    td_result = TorqueDragResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        operation=data.get("operation", "trip_out"),
        friction_cased=data.get("friction_cased", 0.25),
        friction_open=data.get("friction_open", 0.35),
        wob=data.get("wob"),
        rpm=data.get("rpm"),
        result_data=result.get("station_results"),
        summary=result.get("summary")
    )
    db.add(td_result)
    db.commit()

    return result


@app.post("/torque-drag/back-calculate")
def back_calculate_friction(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Back-calculate friction factor from measured hookload."""
    well_id = data.get("well_id")
    if not well_id:
        raise HTTPException(status_code=400, detail="well_id required")

    survey_rows = db.query(SurveyStation).filter(SurveyStation.well_id == well_id).order_by(SurveyStation.md).all()
    survey = [{"md": s.md, "inclination": s.inclination, "azimuth": s.azimuth, "tvd": s.tvd} for s in survey_rows]

    ds_rows = db.query(DrillstringSection).filter(DrillstringSection.well_id == well_id).order_by(DrillstringSection.order_from_bit).all()
    drillstring = [{"od": s.od, "id_inner": s.id_inner, "weight": s.weight,
                    "length": s.length, "order_from_bit": s.order_from_bit} for s in ds_rows]

    result = TorqueDragEngine.back_calculate_friction(
        survey=survey,
        drillstring=drillstring,
        measured_hookload=data.get("measured_hookload", 0),
        operation=data.get("operation", "trip_out"),
        mud_weight=data.get("mud_weight", 10.0),
        wob=data.get("wob", 0.0),
        casing_shoe_md=data.get("casing_shoe_md", 0.0)
    )

    return result


@app.post("/wells/{well_id}/torque-drag/compare")
def compare_torque_drag(well_id: int, data: Dict[str, Any] = Body(default={}), db: Session = Depends(get_db)):
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

    operations = data.get("operations", ["trip_out", "trip_in", "rotating", "sliding", "lowering"])
    friction_cased = data.get("friction_cased", 0.25)
    friction_open = data.get("friction_open", 0.35)
    mud_weight = data.get("mud_weight", 10.0)
    wob = data.get("wob", 0.0)
    rpm = data.get("rpm", 0.0)
    casing_shoe_md = data.get("casing_shoe_md", 0.0)

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

    # Build combined data array — one row per MD with all operations
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


# --- Hydraulics / ECD ---

@app.post("/wells/{well_id}/hydraulic-sections")
def upload_hydraulic_sections(well_id: int, sections: List[Dict[str, Any]] = Body(...), db: Session = Depends(get_db)):
    """Define hydraulic circuit sections."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    db.query(HydraulicSection).filter(HydraulicSection.well_id == well_id).delete()

    for sec in sections:
        db.add(HydraulicSection(
            well_id=well_id,
            section_type=sec["section_type"],
            length=sec["length"],
            od=sec["od"],
            id_inner=sec["id_inner"]
        ))

    db.commit()
    return {"well_id": well_id, "sections_count": len(sections)}


@app.post("/wells/{well_id}/bit-nozzles")
def upload_bit_nozzles(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Define bit nozzle configuration."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    db.query(BitNozzle).filter(BitNozzle.well_id == well_id).delete()

    nozzle_sizes = data.get("nozzle_sizes", [])
    import math
    tfa = sum(math.pi / 4.0 * (n / 32.0) ** 2 for n in nozzle_sizes)

    nozzle = BitNozzle(
        well_id=well_id,
        nozzle_count=len(nozzle_sizes),
        nozzle_sizes=nozzle_sizes,
        tfa=round(tfa, 4),
        bit_diameter=data.get("bit_diameter")
    )
    db.add(nozzle)
    db.commit()

    return {"well_id": well_id, "nozzle_count": len(nozzle_sizes), "tfa": round(tfa, 4)}


@app.post("/wells/{well_id}/hydraulics/calculate")
def calculate_hydraulics(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Full hydraulic circuit calculation."""
    # Get sections
    sec_rows = db.query(HydraulicSection).filter(HydraulicSection.well_id == well_id).all()
    if not sec_rows:
        raise HTTPException(status_code=400, detail="No hydraulic sections defined")

    sections = [{"section_type": s.section_type, "length": s.length, "od": s.od, "id_inner": s.id_inner}
                for s in sec_rows]

    # Get nozzles
    nozzle = db.query(BitNozzle).filter(BitNozzle.well_id == well_id).first()
    nozzle_sizes = nozzle.nozzle_sizes if nozzle else data.get("nozzle_sizes", [12, 12, 12])

    result = HydraulicsEngine.calculate_full_circuit(
        sections=sections,
        nozzle_sizes=nozzle_sizes,
        flow_rate=data.get("flow_rate", 400),
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        tvd=data.get("tvd", 10000),
        rheology_model=data.get("rheology_model", "bingham_plastic"),
        n=data.get("n", 0.5),
        k=data.get("k", 300),
        surface_equipment_loss=data.get("surface_equipment_loss", 80.0)
    )

    # Save result
    hyd_result = HydraulicResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        flow_rate=data.get("flow_rate", 400),
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        rheology_model=data.get("rheology_model", "bingham_plastic"),
        result_data=result.get("section_results"),
        bit_hydraulics=result.get("bit_hydraulics"),
        summary=result.get("summary")
    )
    db.add(hyd_result)
    db.commit()

    return result


@app.post("/wells/{well_id}/hydraulics/surge-swab")
def calculate_surge_swab(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Calculate surge and swab pressures."""
    result = HydraulicsEngine.calculate_surge_swab(
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        tvd=data.get("tvd", 10000),
        pipe_od=data.get("pipe_od", 5.0),
        pipe_id=data.get("pipe_id", 4.276),
        hole_id=data.get("hole_id", 8.5),
        pipe_velocity_fpm=data.get("pipe_velocity_fpm", 90),
        pipe_open=data.get("pipe_open", True)
    )

    return result


# --- Stuck Pipe ---

@app.post("/stuck-pipe/diagnose/start")
def start_stuck_pipe_diagnosis():
    """Start the stuck pipe decision tree — returns first question."""
    return StuckPipeEngine.get_next_question()


@app.post("/stuck-pipe/diagnose/answer")
def answer_stuck_pipe_question(data: Dict[str, Any] = Body(...)):
    """Answer a question in the decision tree — returns next question or result."""
    return StuckPipeEngine.get_next_question(
        current_node=data.get("node_id", "start"),
        answer=data.get("answer", "yes")
    )


@app.post("/stuck-pipe/free-point")
def calculate_free_point(data: Dict[str, Any] = Body(...)):
    """Calculate free point depth from pipe stretch data."""
    return StuckPipeEngine.calculate_free_point(
        pipe_od=data.get("pipe_od", 5.0),
        pipe_id=data.get("pipe_id", 4.276),
        pipe_grade=data.get("pipe_grade", "S135"),
        stretch_inches=data.get("stretch_inches", 0),
        pull_force_lbs=data.get("pull_force_lbs", 0)
    )


@app.post("/stuck-pipe/risk-assessment")
def assess_stuck_pipe_risk(data: Dict[str, Any] = Body(...)):
    """Assess stuck pipe risk matrix."""
    return StuckPipeEngine.assess_risk_matrix(
        mechanism=data.get("mechanism", ""),
        params=data.get("params", {})
    )


@app.post("/events/{event_id}/stuck-pipe")
def full_stuck_pipe_analysis(event_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Full stuck pipe analysis linked to an event."""
    from models.models_v2 import Event

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Classify mechanism from answers
    answers = data.get("answers", [])
    classification = StuckPipeEngine.classify_mechanism(answers)

    # Risk assessment
    risk = StuckPipeEngine.assess_risk_matrix(
        mechanism=classification["mechanism"],
        params=data.get("params", {})
    )

    # Recommended actions
    actions = StuckPipeEngine.get_recommended_actions(classification["mechanism"])

    # Free point if stretch data provided
    free_point = None
    if data.get("stretch_inches") and data.get("pull_force_lbs"):
        free_point = StuckPipeEngine.calculate_free_point(
            pipe_od=data.get("pipe_od", 5.0),
            pipe_id=data.get("pipe_id", 4.276),
            pipe_grade=data.get("pipe_grade", "S135"),
            stretch_inches=data["stretch_inches"],
            pull_force_lbs=data["pull_force_lbs"]
        )

    # Save
    analysis = StuckPipeAnalysis(
        event_id=event_id,
        well_id=event.well_id,
        mechanism=classification["mechanism"],
        decision_tree_path=classification.get("decision_path"),
        free_point_depth=free_point["free_point_depth_ft"] if free_point else None,
        pipe_stretch_inches=data.get("stretch_inches"),
        pull_force_lbs=data.get("pull_force_lbs"),
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


# --- Well Control / Kill Sheet ---

@app.post("/wells/{well_id}/kill-sheet/pre-record")
def pre_record_kill_sheet(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Pre-record static kill sheet data."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WellControlEngine.pre_record_kill_sheet(
        well_name=well.name,
        depth_md=data.get("depth_md", 0),
        depth_tvd=data.get("depth_tvd", 0),
        original_mud_weight=data.get("original_mud_weight", 10.0),
        casing_shoe_tvd=data.get("casing_shoe_tvd", 0),
        casing_id=data.get("casing_id", 8.681),
        dp_od=data.get("dp_od", 5.0),
        dp_id=data.get("dp_id", 4.276),
        dp_length=data.get("dp_length", 0),
        dc_od=data.get("dc_od", 6.5),
        dc_id=data.get("dc_id", 2.813),
        dc_length=data.get("dc_length", 0),
        scr_pressure=data.get("scr_pressure", 0),
        scr_rate=data.get("scr_rate", 0),
        lot_emw=data.get("lot_emw", 14.0),
        pump_output=data.get("pump_output", 0.1),
        hole_size=data.get("hole_size", 8.5)
    )

    # Save to DB
    ks = KillSheet(
        well_id=well_id,
        well_name=well.name,
        depth_md=data.get("depth_md", 0),
        depth_tvd=data.get("depth_tvd", 0),
        original_mud_weight=data.get("original_mud_weight", 10.0),
        casing_shoe_tvd=data.get("casing_shoe_tvd", 0),
        casing_id=data.get("casing_id", 8.681),
        dp_capacity=result["capacities_bbl_ft"]["dp_capacity"],
        annular_capacity=result["capacities_bbl_ft"]["annular_oh_dp"],
        scr_pressure=data.get("scr_pressure"),
        scr_rate=data.get("scr_rate"),
        strokes_surface_to_bit=result["strokes"]["strokes_surface_to_bit"],
        strokes_bit_to_surface=result["strokes"]["strokes_bit_to_surface"],
        total_strokes=result["strokes"]["total_strokes"],
        lot_emw=data.get("lot_emw", 14.0),
        calculations=result,
        status="pre-recorded"
    )
    db.add(ks)
    db.commit()

    return result


@app.get("/wells/{well_id}/kill-sheet")
def get_kill_sheet(well_id: int, db: Session = Depends(get_db)):
    """Get the latest kill sheet for a well."""
    ks = db.query(KillSheet).filter(KillSheet.well_id == well_id).order_by(KillSheet.id.desc()).first()
    if not ks:
        raise HTTPException(status_code=404, detail="No kill sheet found for this well")

    return {
        "id": ks.id, "well_id": ks.well_id, "well_name": ks.well_name,
        "depth_md": ks.depth_md, "depth_tvd": ks.depth_tvd,
        "original_mud_weight": ks.original_mud_weight,
        "casing_shoe_tvd": ks.casing_shoe_tvd,
        "dp_capacity": ks.dp_capacity, "annular_capacity": ks.annular_capacity,
        "scr_pressure": ks.scr_pressure, "scr_rate": ks.scr_rate,
        "strokes_surface_to_bit": ks.strokes_surface_to_bit,
        "lot_emw": ks.lot_emw,
        "sidpp": ks.sidpp, "sicp": ks.sicp, "pit_gain": ks.pit_gain,
        "calculations": ks.calculations,
        "pressure_schedule": ks.pressure_schedule,
        "kill_method": ks.kill_method,
        "status": ks.status
    }


@app.post("/wells/{well_id}/kill-sheet/calculate")
def calculate_kill_sheet(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Calculate kill sheet with kick data."""
    # Get pre-recorded data
    ks = db.query(KillSheet).filter(KillSheet.well_id == well_id).order_by(KillSheet.id.desc()).first()
    if not ks:
        raise HTTPException(status_code=400, detail="No pre-recorded kill sheet. Pre-record first.")

    result = WellControlEngine.calculate_kill_sheet(
        depth_md=ks.depth_md,
        depth_tvd=ks.depth_tvd,
        original_mud_weight=ks.original_mud_weight,
        casing_shoe_tvd=ks.casing_shoe_tvd,
        sidpp=data.get("sidpp", 0),
        sicp=data.get("sicp", 0),
        pit_gain=data.get("pit_gain", 0),
        scr_pressure=ks.scr_pressure or 0,
        scr_rate=ks.scr_rate or 0,
        dp_capacity=ks.dp_capacity or 0,
        annular_capacity=ks.annular_capacity or 0,
        strokes_surface_to_bit=ks.strokes_surface_to_bit or 0,
        lot_emw=ks.lot_emw or 14.0,
        casing_id=ks.casing_id or 0
    )

    # Update kill sheet with kick data
    ks.sidpp = data.get("sidpp")
    ks.sicp = data.get("sicp")
    ks.pit_gain = data.get("pit_gain")
    ks.calculations = result
    ks.pressure_schedule = result.get("pressure_schedule")
    ks.kill_method = data.get("kill_method", "wait_weight")
    ks.status = "active"
    db.commit()

    # Add kill method details
    if data.get("kill_method") == "drillers":
        method_detail = WellControlEngine.calculate_drillers_method(result, ks.scr_pressure or 0)
    else:
        method_detail = WellControlEngine.calculate_wait_and_weight(result)

    return {**result, "method_detail": method_detail}


@app.post("/kill-sheet/volumetric")
def calculate_volumetric(data: Dict[str, Any] = Body(...)):
    """Volumetric method calculation (no circulation)."""
    return WellControlEngine.calculate_volumetric(
        mud_weight=data.get("mud_weight", 10.0),
        sicp=data.get("sicp", 0),
        tvd=data.get("tvd", 10000),
        annular_capacity=data.get("annular_capacity", 0.05),
        lot_emw=data.get("lot_emw", 14.0),
        casing_shoe_tvd=data.get("casing_shoe_tvd", 5000),
        safety_margin_psi=data.get("safety_margin_psi", 50),
        pressure_increment_psi=data.get("pressure_increment_psi", 100)
    )


@app.post("/kill-sheet/bullhead")
def calculate_bullhead(data: Dict[str, Any] = Body(...)):
    """Bullhead calculation."""
    return WellControlEngine.calculate_bullhead(
        mud_weight=data.get("mud_weight", 10.0),
        kill_mud_weight=data.get("kill_mud_weight", 11.0),
        depth_tvd=data.get("depth_tvd", 10000),
        casing_shoe_tvd=data.get("casing_shoe_tvd", 5000),
        lot_emw=data.get("lot_emw", 14.0),
        dp_capacity=data.get("dp_capacity", 0.018),
        depth_md=data.get("depth_md", 10000),
        formation_pressure=data.get("formation_pressure", 5720)
    )


# ============================================================
# ELITE PHASE 1-4: ADVANCED CALCULATION ENDPOINTS
# ============================================================

@app.post("/well-control/kick-tolerance")
def calculate_kick_tolerance(data: Dict[str, Any] = Body(...)):
    """Calculate kick tolerance (max influx volume before shoe fracture)."""
    return WellControlEngine.calculate_kick_tolerance(
        mud_weight=data.get("mud_weight", 10.0),
        shoe_tvd=data.get("shoe_tvd", 5000),
        lot_emw=data.get("lot_emw", 14.0),
        well_depth_tvd=data.get("well_depth_tvd", 10000),
        gas_gravity=data.get("gas_gravity", 0.65),
        bht=data.get("bht", 150.0),
        annular_capacity=data.get("annular_capacity", 0.05),
        influx_type=data.get("influx_type", "gas")
    )


@app.post("/well-control/barite-requirements")
def calculate_barite_requirements(data: Dict[str, Any] = Body(...)):
    """Calculate barite weighting material requirements."""
    return WellControlEngine.calculate_barite_requirements(
        current_mud_weight=data.get("current_mud_weight", 10.0),
        target_mud_weight=data.get("target_mud_weight", 12.0),
        system_volume_bbl=data.get("system_volume_bbl", 500),
        barite_sg=data.get("barite_sg", 4.20),
        sack_weight_lbs=data.get("sack_weight_lbs", 100.0)
    )


@app.post("/well-control/z-factor")
def calculate_z_factor(data: Dict[str, Any] = Body(...)):
    """Calculate real gas Z-factor (Dranchuk-Abou-Kassem)."""
    return WellControlEngine.calculate_z_factor(
        pressure=data.get("pressure", 5000),
        temperature=data.get("temperature", 200),
        gas_gravity=data.get("gas_gravity", 0.65)
    )


@app.post("/hydraulics/bha-breakdown")
def calculate_bha_breakdown(data: Dict[str, Any] = Body(...)):
    """Calculate pressure loss breakdown for individual BHA tools."""
    return HydraulicsEngine.calculate_bha_pressure_breakdown(
        bha_tools=data.get("bha_tools", []),
        flow_rate=data.get("flow_rate", 400),
        mud_weight=data.get("mud_weight", 12.0),
        pv=data.get("pv", 20),
        yp=data.get("yp", 12),
        rheology_model=data.get("rheology_model", "bingham_plastic"),
        n=data.get("n", 0.5),
        k=data.get("k", 300.0),
        tau_0=data.get("tau_0", 0.0),
        k_hb=data.get("k_hb", 0.0),
        n_hb=data.get("n_hb", 0.5)
    )


@app.post("/hydraulics/pressure-waterfall")
def generate_pressure_waterfall(data: Dict[str, Any] = Body(...)):
    """Generate pressure waterfall from circuit results."""
    circuit_result = data.get("circuit_result", {})
    bha_breakdown = data.get("bha_breakdown", None)
    return HydraulicsEngine.generate_pressure_waterfall(circuit_result, bha_breakdown)


@app.post("/hydraulics/fit-herschel-bulkley")
def fit_herschel_bulkley(data: Dict[str, Any] = Body(...)):
    """Fit Herschel-Bulkley model from FANN viscometer readings."""
    return HydraulicsEngine.fit_herschel_bulkley(
        fann_readings=data.get("fann_readings", {})
    )


@app.post("/stuck-pipe/differential-sticking")
def calculate_differential_sticking(data: Dict[str, Any] = Body(...)):
    """Calculate differential sticking force from ECD and formation pressure."""
    return StuckPipeEngine.calculate_differential_sticking_force(
        ecd_ppg=data.get("ecd_ppg", 12.5),
        pore_pressure_ppg=data.get("pore_pressure_ppg", 10.0),
        contact_length_ft=data.get("contact_length_ft", 30),
        pipe_od_in=data.get("pipe_od_in", 5.0),
        filter_cake_thickness_in=data.get("filter_cake_thickness_in", 0.25),
        friction_coefficient_cake=data.get("friction_coefficient_cake", 0.10),
        tvd_ft=data.get("tvd_ft", 10000)
    )


@app.post("/stuck-pipe/packoff-risk")
def assess_packoff_risk(data: Dict[str, Any] = Body(...)):
    """Assess pack-off risk from hole cleaning indicators."""
    return StuckPipeEngine.assess_packoff_risk(
        hci=data.get("hci", 0.8),
        cuttings_concentration_pct=data.get("cuttings_concentration_pct", 3.0),
        inclination=data.get("inclination", 0.0),
        annular_velocity_ftmin=data.get("annular_velocity_ftmin", 150.0)
    )


@app.post("/workover/ct-elongation")
def calculate_ct_elongation(data: Dict[str, Any] = Body(...)):
    """Calculate coiled tubing elongation (weight, temp, ballooning, Bourdon)."""
    from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine
    return WorkoverHydraulicsEngine.calculate_ct_elongation(
        ct_od=data.get("ct_od", 2.0),
        ct_id=data.get("ct_id", 1.688),
        ct_length=data.get("ct_length", 15000),
        weight_per_ft=data.get("weight_per_ft", 3.24),
        mud_weight=data.get("mud_weight", 8.6),
        delta_p_internal=data.get("delta_p_internal", 3000),
        delta_t=data.get("delta_t", 100),
        wellhead_pressure=data.get("wellhead_pressure", 500)
    )


@app.post("/workover/ct-fatigue")
def calculate_ct_fatigue(data: Dict[str, Any] = Body(...)):
    """Calculate coiled tubing fatigue life (API RP 5C7, Miner's rule)."""
    from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine
    return WorkoverHydraulicsEngine.calculate_ct_fatigue(
        ct_od=data.get("ct_od", 2.0),
        wall_thickness=data.get("wall_thickness", 0.156),
        reel_diameter=data.get("reel_diameter", 72),
        internal_pressure=data.get("internal_pressure", 5000),
        yield_strength_psi=data.get("yield_strength_psi", 80000),
        trips_history=data.get("trips_history", None)
    )


# ============================================================
# MODULE AI ANALYSIS ENDPOINTS
# ============================================================

@app.post("/wells/{well_id}/torque-drag/analyze")
async def analyze_torque_drag(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Torque & Drag results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_torque_drag(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


@app.post("/wells/{well_id}/hydraulics/analyze")
async def analyze_hydraulics(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Hydraulics/ECD results via mud_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_hydraulics(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


@app.post("/wells/{well_id}/stuck-pipe/analyze")
async def analyze_stuck_pipe(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Stuck Pipe results via drilling_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_stuck_pipe(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


@app.post("/wells/{well_id}/well-control/analyze")
async def analyze_well_control(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Well Control results via drilling_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_well_control(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 5: Wellbore Cleanup (Hole Cleaning) Endpoints
# ============================================================

from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine
from models.models_v2 import WellboreCleanupResult

@app.post("/wells/{well_id}/wellbore-cleanup")
def calculate_wellbore_cleanup(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run wellbore cleanup / hole cleaning calculation."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WellboreCleanupEngine.calculate_full_cleanup(
        flow_rate=data.get("flow_rate", 500),
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        hole_id=data.get("hole_id", 8.5),
        pipe_od=data.get("pipe_od", 5.0),
        inclination=data.get("inclination", 0),
        rop=data.get("rop", 60),
        cutting_size=data.get("cutting_size", 0.25),
        cutting_density=data.get("cutting_density", 21.0),
        rpm=data.get("rpm", 0),
        annular_length=data.get("annular_length", 1000)
    )

    # Save result
    cu_result = WellboreCleanupResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        flow_rate=data.get("flow_rate", 500),
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        hole_id=data.get("hole_id", 8.5),
        pipe_od=data.get("pipe_od", 5.0),
        inclination=data.get("inclination", 0),
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(cu_result)
    db.commit()
    db.refresh(cu_result)

    return {"id": cu_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/wellbore-cleanup")
def get_wellbore_cleanup(well_id: int, db: Session = Depends(get_db)):
    """Get latest wellbore cleanup result for a well."""
    result = db.query(WellboreCleanupResult).filter(
        WellboreCleanupResult.well_id == well_id
    ).order_by(WellboreCleanupResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No cleanup results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


# ============================================================
# MODULE 6: Packer Forces Endpoints
# ============================================================

from orchestrator.packer_forces_engine import PackerForcesEngine
from models.models_v2 import PackerForcesResult

@app.post("/wells/{well_id}/packer-forces")
def calculate_packer_forces(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run packer forces calculation."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = PackerForcesEngine.calculate_total_packer_force(
        tubing_od=data.get("tubing_od", 2.875),
        tubing_id=data.get("tubing_id", 2.441),
        tubing_weight=data.get("tubing_weight", 6.5),
        tubing_length=data.get("tubing_length", 10000),
        seal_bore_id=data.get("seal_bore_id", 3.25),
        initial_tubing_pressure=data.get("initial_tubing_pressure", 0),
        final_tubing_pressure=data.get("final_tubing_pressure", 3000),
        initial_annulus_pressure=data.get("initial_annulus_pressure", 0),
        final_annulus_pressure=data.get("final_annulus_pressure", 0),
        initial_temperature=data.get("initial_temperature", 80),
        final_temperature=data.get("final_temperature", 250),
        packer_depth_tvd=data.get("packer_depth_tvd", 10000),
        mud_weight_tubing=data.get("mud_weight_tubing", 8.34),
        mud_weight_annulus=data.get("mud_weight_annulus", 8.34),
        poisson_ratio=data.get("poisson_ratio", 0.30),
        thermal_expansion=data.get("thermal_expansion", 6.9e-6)
    )

    # Save result
    pf_result = PackerForcesResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        tubing_od=data.get("tubing_od", 2.875),
        tubing_id=data.get("tubing_id", 2.441),
        tubing_weight=data.get("tubing_weight", 6.5),
        packer_depth_tvd=data.get("packer_depth_tvd", 10000),
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(pf_result)
    db.commit()
    db.refresh(pf_result)

    return {"id": pf_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/packer-forces")
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


# ============================================================
# MODULE 5 & 6 AI ANALYSIS ENDPOINTS
# ============================================================

@app.post("/wells/{well_id}/wellbore-cleanup/analyze")
async def analyze_wellbore_cleanup(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Wellbore Cleanup results via mud_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_wellbore_cleanup(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


@app.post("/wells/{well_id}/packer-forces/analyze")
async def analyze_packer_forces(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Packer Forces results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_packer_forces(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 7: WORKOVER HYDRAULICS ENDPOINTS
# ============================================================

from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine
from models.models_v2 import WorkoverHydraulicsResult


@app.post("/wells/{well_id}/workover-hydraulics")
def calculate_workover_hydraulics(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run workover/CT hydraulics calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WorkoverHydraulicsEngine.calculate_full_workover(
        flow_rate=data.get("flow_rate", 80),
        mud_weight=data.get("mud_weight", 8.6),
        pv=data.get("pv", 12),
        yp=data.get("yp", 8),
        ct_od=data.get("ct_od", 2.0),
        wall_thickness=data.get("wall_thickness", 0.156),
        ct_length=data.get("ct_length", 10000),
        hole_id=data.get("hole_id", 4.892),
        tvd=data.get("tvd", 10000),
        inclination=data.get("inclination", 0),
        friction_factor=data.get("friction_factor", 0.25),
        wellhead_pressure=data.get("wellhead_pressure", 0),
        reservoir_pressure=data.get("reservoir_pressure", 5200),
        yield_strength_psi=data.get("yield_strength_psi", 80000)
    )

    wh_result = WorkoverHydraulicsResult(
        well_id=well_id,
        ct_od=data.get("ct_od", 2.0),
        wall_thickness=data.get("wall_thickness", 0.156),
        ct_length=data.get("ct_length", 10000),
        flow_rate=data.get("flow_rate", 80),
        mud_weight=data.get("mud_weight", 8.6),
        hole_id=data.get("hole_id", 4.892),
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(wh_result)
    db.commit()
    db.refresh(wh_result)

    return {"id": wh_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/workover-hydraulics")
def get_workover_hydraulics(well_id: int, db: Session = Depends(get_db)):
    """Get latest workover hydraulics result for a well."""
    result = db.query(WorkoverHydraulicsResult).filter(
        WorkoverHydraulicsResult.well_id == well_id
    ).order_by(WorkoverHydraulicsResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No workover hydraulics results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


# ============================================================
# MODULE 8: SAND CONTROL ENDPOINTS
# ============================================================

from orchestrator.sand_control_engine import SandControlEngine
from models.models_v2 import SandControlResult


@app.post("/wells/{well_id}/sand-control")
def calculate_sand_control(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run sand control analysis calculations."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = SandControlEngine.calculate_full_sand_control(
        sieve_sizes_mm=data.get("sieve_sizes_mm", [2.0, 0.85, 0.425, 0.25, 0.15, 0.075]),
        cumulative_passing_pct=data.get("cumulative_passing_pct", [100, 95, 70, 40, 15, 2]),
        hole_id=data.get("hole_id", 8.5),
        screen_od=data.get("screen_od", 5.5),
        interval_length=data.get("interval_length", 50),
        ucs_psi=data.get("ucs_psi", 500),
        friction_angle_deg=data.get("friction_angle_deg", 30),
        reservoir_pressure_psi=data.get("reservoir_pressure_psi", 4500),
        overburden_stress_psi=data.get("overburden_stress_psi", 10000),
        formation_permeability_md=data.get("formation_permeability_md", 500),
        wellbore_radius_ft=data.get("wellbore_radius_ft", 0.354),
        wellbore_type=data.get("wellbore_type", "cased"),
        gravel_permeability_md=data.get("gravel_permeability_md", 80000),
        pack_factor=data.get("pack_factor", 1.4),
        washout_factor=data.get("washout_factor", 1.1)
    )

    sc_result = SandControlResult(
        well_id=well_id,
        d50_mm=result.get("psd", {}).get("d50_mm", 0),
        uniformity_coefficient=result.get("psd", {}).get("uniformity_coefficient", 0),
        ucs_psi=data.get("ucs_psi", 500),
        interval_length=data.get("interval_length", 50),
        result_data=result,
        summary=result.get("summary", {})
    )
    db.add(sc_result)
    db.commit()
    db.refresh(sc_result)

    return {"id": sc_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/sand-control")
def get_sand_control(well_id: int, db: Session = Depends(get_db)):
    """Get latest sand control result for a well."""
    result = db.query(SandControlResult).filter(
        SandControlResult.well_id == well_id
    ).order_by(SandControlResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No sand control results found")
    return {
        "id": result.id, "well_id": well_id,
        "result_data": result.result_data,
        "summary": result.summary,
        "created_at": str(result.created_at)
    }


# ============================================================
# MODULE 7 & 8 AI ANALYSIS ENDPOINTS
# ============================================================

@app.post("/wells/{well_id}/workover-hydraulics/analyze")
async def analyze_workover_hydraulics(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Workover Hydraulics results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_workover_hydraulics(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


@app.post("/wells/{well_id}/sand-control/analyze")
async def analyze_sand_control(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Sand Control results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_sand_control(
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 9: COMPLETION DESIGN ENDPOINTS
# ============================================================

from orchestrator.completion_design_engine import CompletionDesignEngine
from models.models_v2 import CompletionDesignResult


@app.post("/wells/{well_id}/completion-design")
def calculate_completion_design(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run completion design calculations (perforating, fracture, productivity)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CompletionDesignEngine.calculate_full_completion_design(
        casing_id_in=data.get("casing_id_in", 6.276),
        formation_permeability_md=data.get("formation_permeability_md", 100),
        formation_thickness_ft=data.get("formation_thickness_ft", 30),
        reservoir_pressure_psi=data.get("reservoir_pressure_psi", 5000),
        wellbore_pressure_psi=data.get("wellbore_pressure_psi", 4200),
        depth_tvd_ft=data.get("depth_tvd_ft", 10000),
        overburden_stress_psi=data.get("overburden_stress_psi", 10000),
        pore_pressure_psi=data.get("pore_pressure_psi", 4500),
        sigma_min_psi=data.get("sigma_min_psi", 6000),
        sigma_max_psi=data.get("sigma_max_psi", 8000),
        tensile_strength_psi=data.get("tensile_strength_psi", 500),
        poisson_ratio=data.get("poisson_ratio", 0.25),
        penetration_berea_in=data.get("penetration_berea_in", 12.0),
        effective_stress_psi=data.get("effective_stress_psi", 3000),
        temperature_f=data.get("temperature_f", 200),
        completion_fluid=data.get("completion_fluid", "brine"),
        wellbore_radius_ft=data.get("wellbore_radius_ft", 0.354),
        kv_kh_ratio=data.get("kv_kh_ratio", 0.5),
        tubing_od_in=data.get("tubing_od_in", 0.0),
        damage_radius_ft=data.get("damage_radius_ft", 0.5),
        damage_permeability_md=data.get("damage_permeability_md", 50.0),
        formation_type=data.get("formation_type", "sandstone"),
    )

    cd_result = CompletionDesignResult(
        well_id=well_id,
        casing_id_in=data.get("casing_id_in", 6.276),
        formation_permeability_md=data.get("formation_permeability_md", 100),
        depth_tvd_ft=data.get("depth_tvd_ft", 10000),
        penetration_berea_in=data.get("penetration_berea_in", 12.0),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(cd_result)
    db.commit()
    db.refresh(cd_result)

    return {"id": cd_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/completion-design")
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


@app.post("/wells/{well_id}/completion-design/analyze")
async def analyze_completion_design(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Completion Design results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_module(
        module="completion_design",
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 10: SHOT EFFICIENCY ENDPOINTS
# ============================================================

from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine
from models.models_v2 import ShotEfficiencyResult


@app.post("/wells/{well_id}/shot-efficiency")
def calculate_shot_efficiency(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run shot efficiency analysis (petrophysics + interval ranking)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = ShotEfficiencyEngine.calculate_full_shot_efficiency(
        log_entries=data.get("log_entries", []),
        archie_params=data.get("archie_params", {"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05}),
        matrix_params=data.get("matrix_params", {"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120}),
        cutoffs=data.get("cutoffs", {"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40, "min_thickness_ft": 2.0}),
        perf_params=data.get("perf_params", {"spf": 6, "phasing_deg": 60, "perf_length_in": 10, "tunnel_radius_in": 0.2}),
        reservoir_params=data.get("reservoir_params", {"k_h": 100, "kv_kh": 0.5, "wellbore_radius_ft": 0.354}),
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


@app.post("/wells/{well_id}/shot-efficiency/upload-csv")
async def upload_log_csv(well_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload CSV with log data (columns: MD, GR, RHOB, NPHI, Rt, Caliper)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    contents = await file.read()
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


@app.get("/wells/{well_id}/shot-efficiency")
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


@app.post("/wells/{well_id}/shot-efficiency/analyze")
async def analyze_shot_efficiency(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Shot Efficiency results via geologist agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_module(
        module="shot_efficiency",
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 11: VIBRATIONS / STABILITY ENDPOINTS
# ============================================================

from orchestrator.vibrations_engine import VibrationsEngine
from models.models_v2 import VibrationsResult


@app.post("/wells/{well_id}/vibrations")
def calculate_vibrations(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run vibrations/stability analysis."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = VibrationsEngine.calculate_full_vibration_analysis(
        wob_klb=data.get("wob_klb", 25),
        rpm=data.get("rpm", 120),
        rop_fph=data.get("rop_fph", 60),
        torque_ftlb=data.get("torque_ftlb", 15000),
        bit_diameter_in=data.get("bit_diameter_in", 8.5),
        dp_od_in=data.get("dp_od_in", 5.0),
        dp_id_in=data.get("dp_id_in", 4.276),
        dp_weight_lbft=data.get("dp_weight_lbft", 19.5),
        bha_length_ft=data.get("bha_length_ft", 300),
        bha_od_in=data.get("bha_od_in", 6.75),
        bha_id_in=data.get("bha_id_in", 2.813),
        bha_weight_lbft=data.get("bha_weight_lbft", 83.0),
        mud_weight_ppg=data.get("mud_weight_ppg", 10.0),
        hole_diameter_in=data.get("hole_diameter_in", 8.5),
        inclination_deg=data.get("inclination_deg", 30),
    )

    vib_result = VibrationsResult(
        well_id=well_id,
        wob_klb=data.get("wob_klb", 25),
        rpm=data.get("rpm", 120),
        bit_diameter_in=data.get("bit_diameter_in", 8.5),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(vib_result)
    db.commit()
    db.refresh(vib_result)

    return {"id": vib_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/vibrations")
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


@app.post("/wells/{well_id}/vibrations/analyze")
async def analyze_vibrations(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Vibrations results via optimization_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_module(
        module="vibrations",
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 12: Cementing Simulation Endpoints
# ============================================================

@app.post("/wells/{well_id}/cementing")
def calculate_cementing(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run cementing simulation calculations."""
    from orchestrator.cementing_engine import CementingEngine
    from models.models_v2 import CementingResult

    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CementingEngine.calculate_full_cementing(
        casing_od_in=data.get("casing_od_in", 9.625),
        casing_id_in=data.get("casing_id_in", 8.681),
        hole_id_in=data.get("hole_id_in", 12.25),
        casing_shoe_md_ft=data.get("casing_shoe_md_ft", 10000.0),
        casing_shoe_tvd_ft=data.get("casing_shoe_tvd_ft", 9500.0),
        toc_md_ft=data.get("toc_md_ft", 5000.0),
        toc_tvd_ft=data.get("toc_tvd_ft", 4750.0),
        float_collar_md_ft=data.get("float_collar_md_ft", 9900.0),
        mud_weight_ppg=data.get("mud_weight_ppg", 10.5),
        spacer_density_ppg=data.get("spacer_density_ppg", 11.5),
        lead_cement_density_ppg=data.get("lead_cement_density_ppg", 13.5),
        tail_cement_density_ppg=data.get("tail_cement_density_ppg", 16.0),
        tail_length_ft=data.get("tail_length_ft", 500.0),
        spacer_volume_bbl=data.get("spacer_volume_bbl", 25.0),
        excess_pct=data.get("excess_pct", 50.0),
        rat_hole_ft=data.get("rat_hole_ft", 50.0),
        pump_rate_bbl_min=data.get("pump_rate_bbl_min", 5.0),
        pv_mud=data.get("pv_mud", 15.0),
        yp_mud=data.get("yp_mud", 10.0),
        fracture_gradient_ppg=data.get("fracture_gradient_ppg", 16.5),
        pore_pressure_ppg=data.get("pore_pressure_ppg", 9.0),
    )

    cem_result = CementingResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        casing_od_in=data.get("casing_od_in", 9.625),
        hole_id_in=data.get("hole_id_in", 12.25),
        casing_shoe_md_ft=data.get("casing_shoe_md_ft", 10000.0),
        cement_density_ppg=data.get("tail_cement_density_ppg", 16.0),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(cem_result)
    db.commit()
    db.refresh(cem_result)

    return {"id": cem_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/cementing")
def get_cementing(well_id: int, db: Session = Depends(get_db)):
    """Get latest cementing result for a well."""
    from models.models_v2 import CementingResult

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


@app.post("/wells/{well_id}/cementing/analyze")
async def analyze_cementing(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Cementing results via cementing_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_module(
        module="cementing",
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


# ============================================================
# MODULE 13: Casing Design Endpoints
# ============================================================

@app.post("/wells/{well_id}/casing-design")
def calculate_casing_design(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Run casing design calculations."""
    from orchestrator.casing_design_engine import CasingDesignEngine
    from models.models_v2 import CasingDesignResult

    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = CasingDesignEngine.calculate_full_casing_design(
        casing_od_in=data.get("casing_od_in", 9.625),
        casing_id_in=data.get("casing_id_in", 8.681),
        wall_thickness_in=data.get("wall_thickness_in", 0.472),
        casing_weight_ppf=data.get("casing_weight_ppf", 47.0),
        casing_length_ft=data.get("casing_length_ft", 10000.0),
        tvd_ft=data.get("tvd_ft", 9500.0),
        mud_weight_ppg=data.get("mud_weight_ppg", 10.5),
        pore_pressure_ppg=data.get("pore_pressure_ppg", 9.0),
        fracture_gradient_ppg=data.get("fracture_gradient_ppg", 16.5),
        gas_gradient_psi_ft=data.get("gas_gradient_psi_ft", 0.1),
        cement_top_tvd_ft=data.get("cement_top_tvd_ft", 5000.0),
        cement_density_ppg=data.get("cement_density_ppg", 16.0),
        bending_dls=data.get("bending_dls", 3.0),
        overpull_lbs=data.get("overpull_lbs", 50000.0),
        sf_burst=data.get("sf_burst", 1.10),
        sf_collapse=data.get("sf_collapse", 1.00),
        sf_tension=data.get("sf_tension", 1.60),
    )

    csg_result = CasingDesignResult(
        well_id=well_id,
        event_id=data.get("event_id"),
        casing_od_in=data.get("casing_od_in", 9.625),
        casing_weight_ppf=data.get("casing_weight_ppf", 47.0),
        tvd_ft=data.get("tvd_ft", 9500.0),
        selected_grade=result.get("summary", {}).get("selected_grade", ""),
        result_data=result,
        summary=result.get("summary", {}),
    )
    db.add(csg_result)
    db.commit()
    db.refresh(csg_result)

    return {"id": csg_result.id, "well_id": well_id, **result}


@app.get("/wells/{well_id}/casing-design")
def get_casing_design(well_id: int, db: Session = Depends(get_db)):
    """Get latest casing design result for a well."""
    from models.models_v2 import CasingDesignResult

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


@app.post("/wells/{well_id}/casing-design/analyze")
async def analyze_casing_design(well_id: int, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """AI executive analysis of Casing Design results via well_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.get("language", "en")
    provider = data.get("provider", "auto")
    return await module_analyzer.analyze_module(
        module="casing_design",
        result_data=data.get("result_data", {}),
        well_name=well.name,
        params=data.get("params", {}),
        language=language,
        provider=provider
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
