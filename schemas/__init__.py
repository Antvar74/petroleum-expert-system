"""
Pydantic request schemas for PETROEXPERT API routes.

Every POST / PUT endpoint should accept a typed Pydantic model instead of
raw ``Dict[str, Any]``.  Shared models live in ``common.py``; domain-specific
models live in their own sub-modules (e.g. ``well_control.py``).
"""

from schemas.common import AIAnalysisRequest, StandaloneAnalysisRequest  # noqa: F401
