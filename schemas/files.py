"""
Pydantic request schemas for file ingestion routes.
"""

from pydantic import BaseModel, Field


class IngestLASRequest(BaseModel):
    """Body for ``POST /data/ingest/las``."""

    content: str = Field(..., min_length=1, description="Raw LAS file content")


class IngestDLISRequest(BaseModel):
    """Body for ``POST /data/ingest/dlis``."""

    file_path: str = Field(..., min_length=1, description="Path to the DLIS file inside the data directory")
