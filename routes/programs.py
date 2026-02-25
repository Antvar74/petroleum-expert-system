"""
Program routes for PETROEXPERT.

Provides:
  GET  /wells/{well_id}/programs      — list programs for a well
  POST /wells/{well_id}/programs      — create a new program
  GET  /programs/{program_id}         — get program details
  POST /programs/{program_id}/generate — generate program content via LLM
"""
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from sqlalchemy.orm import Session

from models import get_db, Well, Program
from routes.dependencies import get_coordinator
from middleware.rate_limit import limiter, LLM_LIMIT

router = APIRouter(tags=["programs"])


@router.get("/wells/{well_id}/programs")
def get_programs(well_id: int, db: Session = Depends(get_db)):
    return db.query(Program).filter(Program.well_id == well_id).all()


@router.post("/wells/{well_id}/programs")
async def create_program(well_id: int, type: str, db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    new_program = Program(well_id=well_id, type=type, status="draft")
    db.add(new_program)
    db.commit()
    db.refresh(new_program)
    return new_program


@router.get("/programs/{program_id}")
def get_program(program_id: int, db: Session = Depends(get_db)):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.post("/programs/{program_id}/generate")
@limiter.limit(LLM_LIMIT)
async def generate_program_content(request: Request, program_id: int, db: Session = Depends(get_db)):
    """Generate the technical content for a program using LLM"""
    coordinator = get_coordinator()
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    content_text = await coordinator.run_automated_program(
        program_type=program.type,
        well_name=program.well.name
    )

    program.content = {"markdown": content_text}
    program.status = "generated"
    db.commit()
    return program
