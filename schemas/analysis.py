"""
Pydantic request schemas for Analysis workflow routes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RCAGenerateRequest(BaseModel):
    """Body for ``POST /analysis/{id}/rca/generate``."""

    methodology: str = Field(..., description="RCA methodology: five_whys | fishbone")
    data: Dict[str, Any] = Field(..., description="User-provided RCA data")
