"""
Rate limiting configuration for PETROEXPERT.

Uses slowapi with tiered limits:
  - AUTH_LIMIT:  strict for login/register (prevent brute-force)
  - LLM_LIMIT:   moderate for AI-calling endpoints (prevent cost abuse)
  - CALC_LIMIT:  relaxed for calculation endpoints (normal usage)

Usage in routes:
    from middleware.rate_limit import limiter, AUTH_LIMIT
    @router.post("/auth/login")
    @limiter.limit(AUTH_LIMIT)
    def login(request: Request, ...):
"""
import os

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse


def _key_func(request: Request) -> str:
    """Extract client IP from X-Real-IP (nginx proxy) or fall back to remote address."""
    return request.headers.get("X-Real-IP", get_remote_address(request))


limiter = Limiter(
    key_func=_key_func,
    default_limits=[],  # No default — explicit per-route only
    storage_uri=os.environ.get("RATE_LIMIT_STORAGE", "memory://"),
)

# ── Rate Limit Tiers ─────────────────────────────────────────────────────────
AUTH_LIMIT = os.environ.get("RATE_LIMIT_AUTH", "5/minute")
LLM_LIMIT = os.environ.get("RATE_LIMIT_LLM", "10/minute")
CALC_LIMIT = os.environ.get("RATE_LIMIT_CALC", "60/minute")


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 with retry information."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
        headers={"Retry-After": "60"},
    )
