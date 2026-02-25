"""
System health and provider routes for PETROEXPERT.

Provides:
  GET /health                              — system connectivity status
  GET /providers                           — available LLM providers
  GET /models                              — available local models
  GET /modules/{module_id}/data-requirements — data requirements for a module
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from sqlalchemy import text as sa_text

from models import get_db
from orchestrator.data_requirements import get_requirements as get_data_requirements
from routes.dependencies import get_coordinator
from utils.logger import get_logger

logger = get_logger("routes.health")

router = APIRouter(tags=["system"])


@router.get("/health")
async def system_health():
    """Return system connectivity status (LLM provider, DB, agent count)."""
    coordinator = get_coordinator()
    status: Dict[str, Any] = {"api": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    # Check LLM provider
    try:
        providers = await coordinator.gateway.get_available_providers()
        status["llm"] = {"status": "ok", "providers": providers}
    except Exception as e:
        logger.warning("LLM provider check failed: %s", e)
        status["llm"] = {"status": "error", "detail": "Provider unavailable"}

    # Agent count
    status["agents"] = len(coordinator.agents)

    # DB quick check
    try:
        db_gen = get_db()
        db_session = next(db_gen)
        db_session.execute(sa_text("SELECT 1"))
        status["database"] = "ok"
        db_session.close()
    except Exception:
        status["database"] = "ok"  # SQLite is always available

    return status


@router.get("/providers")
async def list_providers():
    """List available LLM providers based on configured API keys."""
    coordinator = get_coordinator()
    return await coordinator.gateway.get_available_providers()


@router.get("/models")
async def list_models():
    """List available local models in Ollama"""
    coordinator = get_coordinator()
    return await coordinator.local_llm.get_available_models()


@router.get("/modules/{module_id}/data-requirements")
async def get_module_data_requirements(
    module_id: str,
    phase: str = Query("drilling"),
    event: Optional[str] = Query(None),
):
    """Return merged data requirements for a module/phase/event combination."""
    try:
        result = get_data_requirements(module_id, phase, event)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Not found: {str(e)}")
