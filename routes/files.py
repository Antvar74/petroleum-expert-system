"""
File management and data ingestion routes for PETROEXPERT.

Provides:
  GET  /files           — list data files
  POST /ingest/csv      — ingest CSV data for a well
  POST /data/ingest/las — parse LAS content
  POST /data/ingest/dlis — parse DLIS file
"""
import os
import io
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Any

import pandas as pd

from models import get_db, Well
from orchestrator.data_ingest import DataIngestionService
from schemas.files import IngestLASRequest, IngestDLISRequest
from utils.upload_validation import validate_upload

router = APIRouter(tags=["files"])


@router.get("/files", response_model=List[str])
def list_data_files():
    """List all supported data files in the data directory"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []

    supported_exts = ['.pdf', '.csv', '.md', '.txt']
    files = [f for f in os.listdir(data_dir) if os.path.splitext(f)[1].lower() in supported_exts]
    return sorted(files)


@router.post("/ingest/csv")
async def ingest_csv(well_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    content = await validate_upload(file, allowed_extensions=[".csv"])
    try:
        df = pd.read_csv(io.BytesIO(content))
        return {
            "well_id": well_id,
            "rows_ingested": len(df),
            "columns": list(df.columns),
            "status": "Success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


@router.post("/data/ingest/las")
def ingest_las(data: IngestLASRequest):
    """Parse LAS content and return normalized data."""
    parsed = DataIngestionService.parse_las(data.content)
    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])
    normalized = DataIngestionService.normalize(parsed["data"])
    return {
        "data": normalized,
        "point_count": len(normalized),
        "curves": parsed.get("curves", []),
        "well_info": parsed.get("well_info", {})
    }


@router.post("/data/ingest/dlis")
def ingest_dlis(data: IngestDLISRequest):
    """Parse DLIS file and return normalized data."""
    file_path = data.file_path

    # Security: restrict to data/ directory only (prevent path traversal)
    data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "data"))
    resolved = os.path.realpath(file_path)
    if not resolved.startswith(data_dir + os.sep):
        raise HTTPException(status_code=403, detail="Access denied: path outside data directory")

    parsed = DataIngestionService.parse_dlis(resolved)
    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])
    normalized = DataIngestionService.normalize(parsed["data"])
    return {
        "data": normalized,
        "point_count": len(normalized),
        "curves": parsed.get("curves", [])
    }
