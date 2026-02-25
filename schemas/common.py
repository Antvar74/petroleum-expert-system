"""
Shared / cross-cutting Pydantic request models used by multiple route files.
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# AI Analysis — used by every ``/analyze`` endpoint in each module
# ---------------------------------------------------------------------------

class AIAnalysisRequest(BaseModel):
    """Body for per-module ``POST /wells/{well_id}/<module>/analyze`` routes."""

    result_data: Dict[str, Any] = Field(default_factory=dict, description="Calculation results to analyse")
    params: Dict[str, Any] = Field(default_factory=dict, description="Original input parameters for context")
    language: str = Field(default="en", description="Response language (ISO 639-1)")
    provider: str = Field(default="auto", description="LLM provider: anthropic | openai | auto")


class StandaloneAnalysisRequest(AIAnalysisRequest):
    """Body for ``POST /analyze/module`` — adds module name and optional well."""

    module: str = Field(..., min_length=1, description="Module key, e.g. 'torque-drag'")
    well_name: str = Field(default="General Analysis", description="Well name for context")


# ---------------------------------------------------------------------------
# Workflow / analysis-init helpers (used by analysis.py and events.py)
# ---------------------------------------------------------------------------

class AnalysisInitRequest(BaseModel):
    """Body for ``POST /problems/{id}/analysis/init`` and event analysis init."""

    workflow: str | None = Field(default=None, description="Workflow variant to run")
    leader: str | None = Field(default=None, description="Lead agent override")


class TextResponseBody(BaseModel):
    """Body for submitting free-text responses (agent / synthesis)."""

    text: str = Field(default="", description="Response text content")
