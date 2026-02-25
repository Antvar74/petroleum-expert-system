"""Shared dependencies for all API routers."""
from functools import lru_cache
from orchestrator.api_coordinator import APICoordinator


@lru_cache(maxsize=1)
def get_coordinator() -> APICoordinator:
    """Return a singleton APICoordinator instance."""
    return APICoordinator()
