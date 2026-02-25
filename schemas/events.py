"""
Pydantic request schemas for event routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    """Body for ``POST /events``."""

    well_id: int = Field(..., description="Target well ID")
    phase: str | None = Field(default=None, description="Well phase (drilling, completion, etc.)")
    family: str | None = Field(default=None, description="Event family classification")
    event_type: str | None = Field(default=None, description="Specific event type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted event parameters")


class EventAnalysisInitRequest(BaseModel):
    """Body for ``POST /events/{event_id}/analysis/init``."""

    workflow: Union[str, List[str]] = Field(default="standard", description="Workflow name or list of agent IDs")
    leader: str | None = Field(default=None, description="Lead agent override")
