"""
Petroleum Expert System API — Application Entry Point.

This module only handles app configuration and router mounting.
All route handlers live in the `routes/` package.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.logger import get_logger

from models import init_db
from middleware.auth import verify_auth, AUTH_MODE
from middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# ── Import all routers ────────────────────────────────────────────────────────
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.wells import router as wells_router
from routes.analysis import router as analysis_router
from routes.events import router as events_router
from routes.files import router as files_router
from routes.programs import router as programs_router
from routes.cross_engine import router as cross_engine_router
from routes.calculations import router as calculations_router
from routes.modules.torque_drag import router as torque_drag_router
from routes.modules.hydraulics import router as hydraulics_router
from routes.modules.stuck_pipe import router as stuck_pipe_router
from routes.modules.well_control import router as well_control_router
from routes.modules.wellbore_cleanup import router as wellbore_cleanup_router
from routes.modules.packer_forces import router as packer_forces_router
from routes.modules.workover import router as workover_router
from routes.modules.sand_control import router as sand_control_router
from routes.modules.completion import router as completion_router
from routes.modules.shot_efficiency import router as shot_efficiency_router
from routes.modules.vibrations import router as vibrations_router
from routes.modules.cementing import router as cementing_router
from routes.modules.casing_design import router as casing_design_router
from routes.modules.daily_reports import router as daily_reports_router
from routes.modules.petrophysics import router as petrophysics_router


# ── Application Setup ─────────────────────────────────────────────────────────

_logger = get_logger("api")


@asynccontextmanager
async def lifespan(app):
    init_db()
    _logger.info("Auth mode: %s", AUTH_MODE.upper())
    if AUTH_MODE == "dev":
        _logger.warning("⚠️  Running WITHOUT authentication — set JWT_SECRET for production")
    yield


app = FastAPI(
    title="Petroleum Expert System API",
    root_path="/api" if os.environ.get("VERCEL") else "",
    dependencies=[Depends(verify_auth)],
    lifespan=lifespan,
)

# ── Rate Limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# ── Global Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    _logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── CORS ──────────────────────────────────────────────────────────────────────
# Wildcard + allow_credentials is FORBIDDEN by the CORS spec and is a security
# risk (any site can make credentialed requests).  We handle three cases:
#   1. CORS_ORIGINS not set       → dev mode, localhost only
#   2. CORS_ORIGINS=*             → public API, credentials OFF
#   3. CORS_ORIGINS=http://a,b,c  → production, explicit list

_cors_env = os.environ.get("CORS_ORIGINS", "").strip()

if _cors_env == "*":
    # Explicit public API — credentials MUST be false per CORS spec
    _cors_origins = ["*"]
    _cors_credentials = False
    _logger.warning("CORS: wildcard origin — credentials DISABLED per CORS spec")
elif _cors_env:
    # Production: explicit origin list with credentials
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
    _cors_credentials = True
    _logger.info("CORS: %d explicit origin(s) configured", len(_cors_origins))
else:
    # Dev mode: common local dev servers only
    _cors_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]
    _cors_credentials = True
    _logger.warning("CORS_ORIGINS not set — allowing localhost only (dev mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mount Routers ─────────────────────────────────────────────────────────────
# Auth routes are PUBLIC (no global auth dependency)
app.include_router(auth_router)

# System
app.include_router(health_router)
app.include_router(wells_router)
app.include_router(files_router)

# Core workflow
app.include_router(analysis_router)
app.include_router(events_router)
app.include_router(programs_router)

# Engineering modules
app.include_router(torque_drag_router)
app.include_router(hydraulics_router)
app.include_router(stuck_pipe_router)
app.include_router(well_control_router)
app.include_router(wellbore_cleanup_router)
app.include_router(packer_forces_router)
app.include_router(workover_router)
app.include_router(sand_control_router)
app.include_router(completion_router)
app.include_router(shot_efficiency_router)
app.include_router(vibrations_router)
app.include_router(cementing_router)
app.include_router(casing_design_router)
app.include_router(daily_reports_router)
app.include_router(petrophysics_router)

# Cross-engine correlations & standalone calculators
app.include_router(cross_engine_router)
app.include_router(calculations_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
