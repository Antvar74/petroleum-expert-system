"""
Authentication middleware for PETROEXPERT.

Supports two modes (tried in order):
  1. JWT Bearer token  — Authorization: Bearer <token>
  2. Static API Key     — X-API-Key: <key>
  3. Dev mode           — if JWT_SECRET is NOT set, auth is disabled for convenience.
                          A random ephemeral secret is generated (tokens die on restart).

Public routes (e.g. /auth/register, /auth/login) bypass the global dependency
by being placed on a separate APIRouter that is included *without* the dependency.

Security notes:
  - NEVER commit a real JWT_SECRET to source control.
  - In production, set JWT_SECRET to a strong random value:  openssl rand -hex 32
  - If ENVIRONMENT=production or VERCEL is set, JWT_SECRET is REQUIRED (app fails fast).
"""
import logging
import os
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.database import get_db

_logger = logging.getLogger("petroexpert.auth")

# Paths that are public (no authentication required)
PUBLIC_PATHS = ("/auth/register", "/auth/login", "/health", "/docs", "/openapi.json", "/redoc")

# ---------------------------------------------------------------------------
# Configuration — JWT_SECRET is NEVER hardcoded
# ---------------------------------------------------------------------------
_JWT_SECRET_ENV: Optional[str] = os.environ.get("JWT_SECRET")
_IS_PRODUCTION = bool(os.environ.get("VERCEL") or os.environ.get("ENVIRONMENT", "").lower() == "production")

# Fail fast in production if JWT_SECRET is missing
if _IS_PRODUCTION and not _JWT_SECRET_ENV:
    raise RuntimeError(
        "FATAL: JWT_SECRET environment variable is REQUIRED in production. "
        "Generate one with:  openssl rand -hex 32"
    )

if _JWT_SECRET_ENV:
    # Production / explicit configuration
    JWT_SECRET: str = _JWT_SECRET_ENV
    AUTH_MODE: str = "production"
    if len(_JWT_SECRET_ENV) < 32:
        _logger.warning(
            "JWT_SECRET is shorter than 32 characters — this is weak. "
            "Generate a stronger one with:  openssl rand -hex 32"
        )
    _logger.info("Auth mode: PRODUCTION (JWT_SECRET configured)")
else:
    # Dev mode — generate random ephemeral secret (tokens die on restart)
    JWT_SECRET = _secrets.token_hex(32)
    AUTH_MODE = "dev"
    _logger.warning(
        "\n"
        "╔══════════════════════════════════════════════════════════════╗\n"
        "║  ⚠️  JWT_SECRET NOT SET — RUNNING IN DEVELOPMENT MODE       ║\n"
        "║  Auth is DISABLED for unauthenticated requests.             ║\n"
        "║  Tokens issued this session won't survive restarts.         ║\n"
        "║  For production set:  export JWT_SECRET=$(openssl rand -hex 32)  ║\n"
        "╚══════════════════════════════════════════════════════════════╝"
    )

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
            try:
                uid = int(user_id)
            except (TypeError, ValueError):
                raise HTTPException(status_code=401, detail="Invalid token payload")
            user = db.query(User).filter(User.id == uid).first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account is disabled")
            return user
        except HTTPException:
            raise
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

    # 3. Dev mode — JWT_SECRET was NOT configured → open access for development
    if AUTH_MODE == "dev" and not expected_key:
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
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == uid).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        return user
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
