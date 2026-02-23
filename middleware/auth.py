"""
Authentication middleware for PETROEXPERT.

Supports two modes (tried in order):
  1. JWT Bearer token  — Authorization: Bearer <token>
  2. Static API Key     — X-API-Key: <key>
  3. Dev mode           — if neither JWT_SECRET nor API_KEY are set, auth is disabled.

Public routes (e.g. /auth/register, /auth/login) bypass the global dependency
by being placed on a separate APIRouter that is included *without* the dependency.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.database import get_db

# Paths that are public (no authentication required)
PUBLIC_PATHS = ("/auth/register", "/auth/login", "/health", "/docs", "/openapi.json", "/redoc")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("JWT_SECRET", "petroexpert-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "72"))

# Security schemes
_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Legacy API-key helper
# ---------------------------------------------------------------------------
def _get_api_key_setting() -> Optional[str]:
    return os.environ.get("API_KEY")


# ---------------------------------------------------------------------------
# Main dependency — used globally on the FastAPI app
# ---------------------------------------------------------------------------
async def verify_auth(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
    api_key: Optional[str] = Security(_api_key_header),
    db: Session = Depends(get_db),
):
    """
    Authenticate the request.  Tries JWT first, then API key, then dev mode.
    Returns a User ORM object when JWT is used, None otherwise.
    """
    # Allow public endpoints through without authentication
    path = request.scope.get("path", "")
    if any(path.rstrip("/").startswith(p) for p in PUBLIC_PATHS):
        return None

    from models.user import User  # avoid circular import

    # 1. JWT Bearer token
    if bearer and bearer.credentials:
        try:
            payload = decode_access_token(bearer.credentials)
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account is disabled")
            return user
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 2. Legacy API key
    expected_key = _get_api_key_setting()
    if expected_key:
        if api_key and api_key == expected_key:
            return None  # Authenticated via API key, no user object
        # API key is configured but not provided / wrong → reject
        if not bearer:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide a Bearer token or X-API-Key.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Dev mode — no JWT_SECRET override AND no API_KEY → open access
    if JWT_SECRET == "petroexpert-dev-secret-change-in-prod" and not expected_key:
        return None

    # Nothing matched — reject
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Strict dependency — requires a real User (JWT only)
# ---------------------------------------------------------------------------
async def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Dependency that requires a valid JWT and returns the User."""
    from models.user import User

    if not bearer or not bearer.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(bearer.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
