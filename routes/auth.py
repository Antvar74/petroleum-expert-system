"""
Authentication routes for PETROEXPERT.

Provides:
  POST /auth/register  — create a new account
  POST /auth/login     — obtain JWT access token
  GET  /auth/me        — get current user profile
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from models.database import get_db
from models.user import User
from middleware.auth import create_access_token, get_current_user
from middleware.rate_limit import limiter, AUTH_LIMIT

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Registration Gate ────────────────────────────────────────────────────────
_ALLOW_REGISTRATION = os.environ.get("ALLOW_REGISTRATION", "true").lower() in ("true", "1", "yes")
_INVITE_CODE: str | None = os.environ.get("INVITE_CODE")  # None = no code required


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    invite_code: str | None = None


class LoginRequest(BaseModel):
    login: str = Field(..., description="Username or email")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    is_active: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_LIMIT)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account and return a JWT token."""
    # Registration gate
    if not _ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    if _INVITE_CODE and body.invite_code != _INVITE_CODE:
        raise HTTPException(status_code=403, detail="Invalid or missing invite code")

    # Check duplicates
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        hashed_password=User.hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": _user_dict(user)}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_LIMIT)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username/email + password and return a JWT token."""
    user = (
        db.query(User)
        .filter((User.username == body.login) | (User.email == body.login))
        .first()
    )
    if not user or not user.verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": _user_dict(user)}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )
