from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import uvicorn
import os
import json
import io
import io
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import init_db, get_db, Well, Problem, Analysis, Program, OperationalProblem
from orchestrator.api_coordinator import APICoordinator
from utils.optimization_engine import OptimizationEngine

app = FastAPI(
    title="Petroleum Expert System API",
    root_path="/api" if os.environ.get("VERCEL") else ""
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Initialize Coordinator
coordinator = APICoordinator()

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

@app.get("/problems/{problem_id}/analysis/init")
@app.post("/problems/{problem_id}/analysis/init")
def init_analysis(problem_id: int, workflow: str = "standard", db: Session = Depends(get_db)):
    """Initialize a new analysis session for a problem"""
    agent_ids = coordinator.get_workflow(workflow)
    
    # Store initial analysis record
    new_analysis = Analysis(
        problem_id=problem_id,
        workflow_used=agent_ids,
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
        "current_agent_index": 0
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
    
    query = coordinator.get_synthesis_query(op_problem, analysis_record.individual_analyses)
    return {"query": query}

@app.post("/analysis/{analysis_id}/synthesis/response")
def submit_synthesis(analysis_id: int, response: Dict[str, str], db: Session = Depends(get_db)):
    """Submit the final synthesis response from Claude"""
    analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    synthesis_text = response.get("text", "")
    confidence = coordinator.agents["drilling_engineer"]._extract_confidence(synthesis_text)
    
    final_synthesis = {
        "agent": "drilling_engineer",
        "role": "Drilling Engineer / Company Man (Synthesis)",
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
    # Check for [REAL_DATA:filename.pdf] tag
    import re
    match = re.search(r"\[REAL_DATA:(.*?)\]", problem.description)
    if match:
        filename = match.group(1).strip()
        print(f"🚀 DETECTED REAL DATA FLAG: Injecting {filename} PDF Context")
        try:
            from utils.pdf_loader import load_pdf_text
            # Look in data folder
            pdf_path = f"data/{filename}"
            # Fallback for simple BAKTE-9 legacy tag
            if filename == "BAKTE-9": pdf_path = "data/BAKTE-9_ETAPA_18.5.pdf"
            
            pdf_text = load_pdf_text(pdf_path, max_pages=30) # Increased page limit
            context["extracted_report_text"] = pdf_text
        except Exception as e:
            print(f"❌ Failed to load PDF context: {e}")

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
    
    final_synthesis = await coordinator.run_automated_synthesis(op_problem, analysis_record.individual_analyses)
    
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

# --- Optimization Engine (v3.0 Phase 3) ---

@app.post("/optimize/hydraulics")
def optimize_hydraulics(flow_rate: float, mw: float, depth: float, pipe_id: float):
    return OptimizationEngine.calculate_hydraulics(flow_rate, mw, depth, pipe_id)

@app.post("/optimize/torque-drag")
def optimize_torque_drag(depth: float, inclination: float, mw: float, pipe_weight: float, friction: float = 0.25):
    return OptimizationEngine.calculate_torque_drag(depth, inclination, mw, pipe_weight, friction)

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
    match = re.search(r"\[REAL_DATA:(.*?)\]", problem.description)
    if match:
        filename = match.group(1).strip()
        print(f"🚀 DETECTED REAL DATA FLAG (RCA): Injecting {filename}")
        try:
            from utils.pdf_loader import load_pdf_text
            pdf_path = f"data/{filename}"
            if filename == "BAKTE-9": pdf_path = "data/BAKTE-9_ETAPA_18.5.pdf"
            
            pdf_text = load_pdf_text(pdf_path, max_pages=30)
            context["extracted_report_text"] = pdf_text
        except Exception as e:
            print(f"❌ Failed to load PDF context: {e}")
    
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



# --- Data Management ---

@app.get("/files", response_model=List[str])
def list_data_files():
    """List all PDF files in the data directory"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []
    
    files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
