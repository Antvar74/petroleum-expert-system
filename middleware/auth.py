"""
API Key authentication middleware for PETROEXPERT.

Behavior:
- If API_KEY env var is NOT set → auth is disabled (dev mode), all requests pass.
- If API_KEY IS set → requests must include X-API-Key header with matching value.
"""
import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_setting() -> str | None:
    """Read API_KEY from environment. None means auth is disabled."""
    return os.environ.get("API_KEY")


async def verify_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str | None:
    """
    FastAPI dependency that validates the X-API-Key header.

    - If API_KEY is not configured in env → all requests pass (dev mode).
    - If API_KEY IS configured → requests must include matching X-API-Key header.
    """
    expected = get_api_key_setting()
    if expected is None:
        # Auth disabled — dev mode
        return None
    if api_key is None or api_key != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
