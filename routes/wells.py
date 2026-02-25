"""
Well and Problem CRUD routes for PETROEXPERT.

Provides:
  GET    /wells                   — list all wells
  POST   /wells                   — create a new well
  DELETE /wells/{well_id}         — delete a well
  GET    /wells/{well_id}/problems — list problems for a well
  POST   /wells/{well_id}/problems — create a problem
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from models import get_db, Well, Problem
from schemas.wells import CreateProblemRequest

router = APIRouter(tags=["wells"])


@router.get("/wells", response_model=List[Dict[str, Any]])
def list_wells(db: Session = Depends(get_db)):
    wells = db.query(Well).all()
    return [{"id": w.id, "name": w.name, "location": w.location} for w in wells]


@router.post("/wells")
def create_well(name: str, location: Optional[str] = None, db: Session = Depends(get_db)):
    db_well = db.query(Well).filter(Well.name == name).first()
    if db_well:
        raise HTTPException(status_code=400, detail="Well already exists")
    new_well = Well(name=name, location=location)
    db.add(new_well)
    db.commit()
    db.refresh(new_well)
    return new_well


@router.delete("/wells/{well_id}")
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

@router.get("/wells/{well_id}/problems")
def list_problems(well_id: int, db: Session = Depends(get_db)):
    problems = db.query(Problem).filter(Problem.well_id == well_id).all()
    return problems


@router.post("/wells/{well_id}/problems")
def create_problem(well_id: int, data: CreateProblemRequest, db: Session = Depends(get_db)):
    new_problem = Problem(
        well_id=well_id,
        depth_md=data.depth_md,
        depth_tvd=data.depth_tvd,
        description=data.description,
        operation=data.operation,
        formation=data.formation,
        mud_weight=data.mud_weight,
        inclination=data.inclination,
        azimuth=data.azimuth,
        torque=data.torque,
        drag=data.drag,
        overpull=data.overpull,
        string_weight=data.string_weight,
        additional_data=data.additional_data,
    )
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    return new_problem
