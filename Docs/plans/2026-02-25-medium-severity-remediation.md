# Medium-Severity Audit Remediation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve all 14 medium-severity findings from the security audit, organized in 4 thematic phases with a commit per phase.

**Architecture:** Each phase is independent. Phase A hardens backend error handling and dependencies. Phase B optimizes the frontend bundle and code quality. Phase C secures the Docker deployment. Phase D adds database migrations and fixes i18n.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic, React 19 / Vite / TypeScript, Docker / nginx, Alembic / SQLAlchemy

---

## Phase A — Backend Safety & Quality

### Task A1: Create structured logger utility

**Files:**
- Create: `utils/logger.py`
- Test: `tests/unit/test_logger.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_logger.py
import logging
from utils.logger import get_logger

def test_get_logger_returns_named_logger():
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "petroexpert.test_module"

def test_get_logger_has_handler():
    logger = get_logger("handler_test")
    # Root petroexpert logger should have at least one handler
    root = logging.getLogger("petroexpert")
    assert len(root.handlers) >= 1
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_logger.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.logger'"

**Step 3: Write minimal implementation**

```python
# utils/logger.py
"""Structured logging for PETROEXPERT."""
import logging
import sys

_initialized = False

def _init_logging():
    global _initialized
    if _initialized:
        return
    root = logging.getLogger("petroexpert")
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(handler)
    _initialized = True

def get_logger(module: str) -> logging.Logger:
    _init_logging()
    return logging.getLogger(f"petroexpert.{module}")
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_logger.py -v`
Expected: PASS

---

### Task A2: Replace print() with logger + sanitize exception messages

**Files:**
- Modify: `api_main.py:80-88`
- Modify: `routes/analysis.py:97-101,354,356,462,464`
- Modify: `routes/events.py:66-68,136-140,209-211,273-275`
- Modify: `routes/wells.py:50-53`
- Modify: `routes/health.py:33`

**Step 1: Write failing test**

```python
# tests/unit/test_error_sanitization.py
"""Verify that 500 responses never leak internal exception details."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from api_main import app
    return TestClient(app, raise_server_exceptions=False)

def test_500_hides_exception_details(client):
    """POST to events/extract with no files should not leak traceback."""
    resp = client.post("/events/extract")
    if resp.status_code == 500:
        body = resp.json()
        # Must NOT contain Python traceback markers
        detail = body.get("detail", "")
        assert "Traceback" not in detail
        assert "File \"" not in detail
        # Should be a generic message
        assert detail in ("Internal server error", "Internal Server Error")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_error_sanitization.py -v`
Expected: FAIL because current code returns `detail=str(e)` with raw exception text

**Step 3: Apply all replacements**

In every file, replace the pattern:
```python
print(f"...")
raise HTTPException(status_code=500, detail=str(e))
```
with:
```python
logger.exception("Descriptive context message")
raise HTTPException(status_code=500, detail="Internal server error")
```

Specific changes:

**api_main.py** — import logger, replace print in global handler:
```python
from utils.logger import get_logger
_logger = get_logger("api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    _logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**routes/analysis.py** — add logger, fix 3 exception blocks:
```python
from utils.logger import get_logger
logger = get_logger("routes.analysis")
```
- Line 99-101: `print(error_msg)` → `logger.exception("init_analysis failed")`, `detail=f"Server Error: {str(e)}"` → `detail="Internal server error"`
- Line 354: `print(f"Rejected unsafe data path: {ve}")` → `logger.warning("Rejected unsafe data path: %s", ve)`
- Line 356: `print(f"Failed to load data context: {e}")` → `logger.warning("Failed to load data context: %s", e)`
- Line 462: same as 354
- Line 464: same as 356

**routes/events.py** — add logger, fix 4 exception blocks:
```python
from utils.logger import get_logger
logger = get_logger("routes.events")
```
- Line 67: `print(...)` → `logger.exception("Event parameter extraction failed")`
- Line 68: `detail=str(e)` → `detail="Internal server error"`
- Line 139: `print(...)` → `logger.exception("Event creation failed")`
- Line 140: `detail=str(e)` → `detail="Internal server error"`
- Line 210: `print(...)` → `logger.exception("Event calculation failed")`
- Line 211: `detail=str(e)` → `detail="Internal server error"`
- Line 274: `print(...)` → `logger.exception("RCA generation failed")`
- Line 275: `detail=str(e)` → `detail="Internal server error"`

**routes/wells.py** — add logger, fix 1 block:
```python
from utils.logger import get_logger
logger = get_logger("routes.wells")
```
- Line 52: `print(...)` → `logger.exception("Failed to delete well %d", well_id)`
- Line 53: `detail=f"Database error: {str(e)}"` → `detail="Internal server error"`

**routes/health.py** — fix 1 leak (line 33, LLM status):
```python
from utils.logger import get_logger
logger = get_logger("routes.health")
```
- Line 33: `status["llm"] = {"status": "error", "detail": str(e)}` → `logger.warning("LLM provider check failed: %s", e)` + `status["llm"] = {"status": "error", "detail": "Provider unavailable"}`

**Step 4: Run tests**

Run: `python3 -m pytest tests/unit/test_error_sanitization.py tests/unit/test_logger.py -v`
Expected: PASS

---

### Task A3: Replace python-jose with PyJWT

**Files:**
- Modify: `requirements.txt:9`
- Modify: `middleware/auth.py:26-27,88,92`
- Test: `tests/unit/test_auth_middleware.py`

**Step 1: Write failing test**

```python
# Add to tests/unit/test_auth_middleware.py (or verify existing tests pass after swap)
def test_jwt_roundtrip():
    from middleware.auth import create_access_token, decode_access_token
    token = create_access_token({"sub": "42"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload
```

**Step 2: Install PyJWT, uninstall python-jose**

Run: `pip install PyJWT[crypto] && pip uninstall python-jose -y`

**Step 3: Update requirements.txt**

Replace line 9:
```
python-jose[cryptography]>=3.3.0
```
with:
```
PyJWT[crypto]>=2.8.0
```

**Step 4: Update middleware/auth.py imports**

Replace:
```python
from jose import JWTError, jwt
```
with:
```python
import jwt
from jwt.exceptions import PyJWTError as JWTError
```

Update `decode_access_token` (PyJWT returns `algorithms` not `algorithm`):
```python
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```
(This line is already correct — no change needed.)

Update `create_access_token`:
```python
return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
```
(Also already correct for PyJWT — `jwt.encode` in PyJWT returns a string directly since v2.0.)

**Step 5: Run full auth tests**

Run: `python3 -m pytest tests/unit/test_auth_middleware.py -v`
Expected: PASS

---

### Task A4: Add file upload validation (type + size)

**Files:**
- Create: `utils/upload_validation.py`
- Modify: `routes/files.py:37-53`
- Modify: `routes/events.py:36-68`
- Modify: `routes/modules/shot_efficiency.py:55-94`
- Test: `tests/unit/test_upload_validation.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_upload_validation.py
import pytest
from fastapi import UploadFile, HTTPException
from io import BytesIO
from utils.upload_validation import validate_upload

@pytest.mark.asyncio
async def test_rejects_oversized_file():
    content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
    file = UploadFile(filename="big.csv", file=BytesIO(content))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file, allowed_extensions=[".csv"])
    assert exc_info.value.status_code == 413

@pytest.mark.asyncio
async def test_rejects_wrong_extension():
    file = UploadFile(filename="hack.exe", file=BytesIO(b"data"))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file, allowed_extensions=[".csv", ".pdf"])
    assert exc_info.value.status_code == 415

@pytest.mark.asyncio
async def test_accepts_valid_file():
    file = UploadFile(filename="data.csv", file=BytesIO(b"a,b\n1,2"))
    content = await validate_upload(file, allowed_extensions=[".csv"])
    assert content == b"a,b\n1,2"
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_upload_validation.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Implement validation utility**

```python
# utils/upload_validation.py
"""File upload validation: size and extension checks."""
import os
from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

async def validate_upload(
    file: UploadFile,
    allowed_extensions: list[str],
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> bytes:
    """Read and validate an uploaded file. Returns content bytes."""
    # Extension check
    safe_name = os.path.basename(file.filename or "")
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Size check — read in chunks to avoid buffering unlimited data
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)  # 64KB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_bytes // (1024*1024)}MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)
```

**Step 4: Wire into route files**

**routes/files.py** — `ingest_csv` endpoint:
```python
from utils.upload_validation import validate_upload

@router.post("/ingest/csv")
async def ingest_csv(well_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    content = await validate_upload(file, allowed_extensions=[".csv"])
    try:
        df = pd.read_csv(io.BytesIO(content))
        ...
```

**routes/events.py** — `extract_event_parameters`:
```python
from utils.upload_validation import validate_upload

# Inside the for loop, replace `tmp.write(await file.read())` with:
    content = await validate_upload(file, allowed_extensions=[".pdf", ".csv", ".txt", ".md"])
    tmp.write(content)
```

**routes/modules/shot_efficiency.py** — `upload_log_csv`:
```python
from utils.upload_validation import validate_upload

# Replace `contents = await file.read()` with:
    contents = await validate_upload(file, allowed_extensions=[".csv"])
```

**Step 5: Run all tests**

Run: `python3 -m pytest tests/unit/test_upload_validation.py tests/unit/test_path_traversal.py -v`
Expected: PASS

**Step 6: Commit Phase A**

```bash
git add utils/logger.py utils/upload_validation.py requirements.txt middleware/auth.py \
  api_main.py routes/analysis.py routes/events.py routes/wells.py routes/health.py \
  routes/files.py routes/modules/shot_efficiency.py \
  tests/unit/test_logger.py tests/unit/test_error_sanitization.py tests/unit/test_upload_validation.py
git commit -m "fix: backend safety — structured logging, sanitized errors, PyJWT, upload validation

- Replace python-jose with PyJWT (actively maintained)
- Replace 11 print() calls with structured logging (utils/logger.py)
- Sanitize all HTTP 500 responses to hide internal exceptions
- Add file upload validation: 10MB limit + extension whitelist
- Resolves audit findings #1, #8, #12, #13 (medium severity)"
```

---

## Phase B — Frontend Optimization

### Task B1: Move axios to dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Move axios**

In `frontend/package.json`, remove `"axios": "^1.13.5"` from `devDependencies` and add it to `dependencies`:

```json
"dependencies": {
    "axios": "^1.13.5",
    "html2pdf.js": "^0.14.0",
    ...
}
```

**Step 2: Verify build still works**

Run: `cd frontend && npm run build`
Expected: Build succeeds

---

### Task B2: Lazy-load xlsx library

**Files:**
- Modify: `frontend/src/components/HydraulicsModule.tsx:17`
- Modify: `frontend/src/components/TorqueDragModule.tsx` (same pattern)
- Modify: `frontend/src/components/DailyReportsModule.tsx:26`

**Step 1: Replace static import in all 3 files**

Remove the top-level import:
```typescript
import * as XLSX from 'xlsx';
```

At each usage site (the export/download functions), add dynamic import:
```typescript
const XLSX = await import('xlsx');
```

The functions that use XLSX are already `async` (or can be made async since they're event handlers). Example pattern:

```typescript
// Before:
const handleExport = () => {
  const ws = XLSX.utils.json_to_sheet(data);
  ...
};

// After:
const handleExport = async () => {
  const XLSX = await import('xlsx');
  const ws = XLSX.utils.json_to_sheet(data);
  ...
};
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, xlsx no longer in initial bundle chunk

---

### Task B3: Extract useAIAnalysis custom hook

**Files:**
- Create: `frontend/src/hooks/useAIAnalysis.ts`
- Modify: All 14 module components (replace duplicated ~25 lines with hook call)

**Step 1: Create the shared hook**

```typescript
// frontend/src/hooks/useAIAnalysis.ts
import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { useLanguage } from './useLanguage';
import type { Provider, ProviderOption } from '../types/ai';
import type { AIAnalysisResponse, APIError } from '../types/api';

interface UseAIAnalysisOptions {
  module: string;
  wellId?: number;
  wellName?: string;
}

export function useAIAnalysis({ module, wellId, wellName }: UseAIAnalysisOptions) {
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { language } = useLanguage();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' },
  ]);

  useEffect(() => {
    api.get('/providers')
      .then(res => setAvailableProviders(res.data))
      .catch(() => {});
  }, []);

  const runAnalysis = useCallback(async (resultData: Record<string, unknown>, params: Record<string, unknown>) => {
    setIsAnalyzing(true);
    try {
      const url = wellId
        ? `/wells/${wellId}/${module}/analyze`
        : '/analyze/module';
      const res = await api.post(url, {
        ...(wellId ? {} : { module, well_name: wellName || 'General Analysis' }),
        result_data: resultData,
        params,
        language,
        provider,
      });
      setAiAnalysis(res.data);
    } catch (e: unknown) {
      const err = e as APIError;
      const errMsg = err.response?.data?.detail || err.message || 'Connection error';
      setAiAnalysis({ analysis: `Error: ${errMsg}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  }, [wellId, wellName, module, language, provider]);

  return { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis };
}
```

**Step 2: Replace in each module component**

In each of the 14 components, replace:
1. Remove the ~6 `useState` declarations (aiAnalysis, isAnalyzing, provider, availableProviders)
2. Remove the `useEffect` that fetches providers
3. Remove the `runAIAnalysis` function
4. Add the hook:

```typescript
const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
  module: 'hydraulics',
  wellId,
  wellName,
});
```

Then replace `runAIAnalysis()` calls with `runAnalysis(resultData, params)` passing the appropriate data.

**Components to update (14):**
- HydraulicsModule.tsx
- TorqueDragModule.tsx
- StuckPipeAnalyzer.tsx
- WellControlModule.tsx
- WellboreCleanupModule.tsx
- PackerForcesModule.tsx
- WorkoverHydraulicsModule.tsx
- SandControlModule.tsx
- CompletionDesignModule.tsx
- ShotEfficiencyModule.tsx
- VibrationsModule.tsx
- CementingModule.tsx
- CasingDesignModule.tsx
- DailyReportsModule.tsx

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors

---

### Task B4: Add useCallback to module handlers

**Files:**
- Modify: All 14 module components

**Step 1: Wrap expensive handlers with useCallback**

In each module, wrap calculation handlers (the functions passed to onClick or that trigger API calls) with `useCallback`:

```typescript
// Before:
const handleCalculate = async () => { ... };

// After:
const handleCalculate = useCallback(async () => { ... }, [dependency1, dependency2]);
```

Focus on:
- `handleCalculate` / `runCalculation` functions
- File upload handlers
- Tab change handlers that compute derived data

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

---

### Task B5: Split DailyReportsModule.tsx

**Files:**
- Create: `frontend/src/components/ddr/DDRForm.tsx`
- Create: `frontend/src/components/ddr/DDRKPIDashboard.tsx`
- Create: `frontend/src/components/ddr/DDRListView.tsx`
- Modify: `frontend/src/components/DailyReportsModule.tsx`

**Step 1: Extract sub-components**

Extract three logical sections from DailyReportsModule:

1. **DDRForm.tsx** — The form with all 10+ sections (header, operations, drilling, mud, BHA, gas, NPT, HSSE, costs, completion, termination). Accepts props for form state and setters.

2. **DDRKPIDashboard.tsx** — The KPI cards + charts section (TimeDepthChart, CostTrackingChart, NPTBreakdownChart, ROPProgressChart, DailyOperationsTimeline). Accepts reports array as props.

3. **DDRListView.tsx** — The reports table/list with filter, edit, delete actions. Accepts reports array and CRUD callbacks.

4. **DailyReportsModule.tsx** — Becomes the orchestrator (~200-300 lines) holding state and composing the 3 sub-components + AI analysis.

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, DailyReportsModule.tsx < 400 lines

**Step 3: Commit Phase B**

```bash
git add frontend/
git commit -m "perf: frontend optimization — lazy xlsx, useAIAnalysis hook, DDR split

- Move axios from devDependencies to dependencies
- Lazy-load xlsx (7MB) in 3 components — only loads on export
- Extract useAIAnalysis hook from 14 duplicated implementations
- Add useCallback to calculation handlers in all modules
- Split DailyReportsModule (1247 lines) into 4 focused components
- Resolves audit findings #2, #3, #4, #5, #6 (medium severity)"
```

---

## Phase C — Docker & Deployment

### Task C1: Add HSTS and Permissions-Policy to nginx

**Files:**
- Modify: `nginx/nginx.conf:34-39`

**Step 1: Add missing headers**

After the existing security headers block (line 39), add:

```nginx
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
```

Also uncomment HSTS in the HTTPS block (line 99) and add Permissions-Policy there too.

**Step 2: Verify nginx config**

Run: `docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t`
Expected: "syntax is ok"

---

### Task C2: Run Docker containers as non-root

**Files:**
- Modify: `Dockerfile`
- Modify: `nginx/Dockerfile`

**Step 1: Add non-root user to Dockerfile**

After the `COPY` commands and before `EXPOSE`, add:

```dockerfile
# Copy schemas
COPY schemas/ ./schemas/

# Create non-root user and set ownership
RUN addgroup --gid 1001 appgroup && \
    adduser --uid 1001 --ingroup appgroup --disabled-password --no-create-home appuser && \
    chown -R appuser:appgroup /app

USER appuser
```

**Step 2: Add non-root user to nginx/Dockerfile**

nginx:alpine already supports running as non-root. After the COPY commands:

```dockerfile
# nginx:alpine ships with nginx user (uid 101)
# Ensure the html directory is accessible
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

USER nginx
```

**Step 3: Verify Docker build**

Run: `docker compose build`
Expected: Build succeeds

---

### Task C3: Add Docker health checks

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add healthcheck to app service**

```yaml
  app:
    build: .
    expose:
      - "8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=sqlite:////app/data/petroleum_expert.db
    volumes:
      - app-data:/app/data
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped
```

**Step 2: Add healthcheck to nginx service + depends_on condition**

```yaml
  nginx:
    build:
      context: .
      dockerfile: nginx/Dockerfile
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - certbot-www:/var/www/certbot
    depends_on:
      app:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:80/ || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped
```

**Step 3: Commit Phase C**

```bash
git add nginx/nginx.conf Dockerfile nginx/Dockerfile docker-compose.yml
git commit -m "sec: Docker hardening — non-root containers, healthchecks, HSTS

- Add HSTS and Permissions-Policy headers to nginx
- Run backend container as non-root user (appuser:1001)
- Run nginx container as non-root user (nginx:101)
- Add healthchecks for app (/health endpoint) and nginx
- Use depends_on condition: service_healthy for startup ordering
- Resolves audit findings #7, #9, #10 (medium severity)"
```

---

## Phase D — Database & i18n

### Task D1: Fix i18n key inconsistency

**Files:**
- Modify: `frontend/src/locales/en.json:90`
- Modify: `frontend/src/locales/es.json:89`

**Step 1: Fix en.json — remove duplicate key from app section**

Line 90 in en.json has `"petrophysicsAdvanced": "Advanced Petrophysics"` in the `app` section. This is already present in the `modules` section (line 45). Remove line 90.

**Step 2: Fix es.json — add missing key in app section**

In es.json, the `app` section (ending at line 89) is missing the `petrophysicsAdvanced` key that en.json has. Since we're removing it from en.json's `app` section, we just need to verify es.json doesn't need it either.

Check which code references `app.petrophysicsAdvanced` vs `modules.petrophysicsAdvanced` and ensure consistent usage.

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

---

### Task D2: Initialize Alembic for database migrations

**Files:**
- Modify: `requirements.txt` (add `alembic>=1.13.0`)
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/001_initial_schema.py`
- Modify: `models/database.py:99-107` (remove inline ALTER TABLE)

**Step 1: Install alembic**

Add to requirements.txt:
```
alembic>=1.13.0
```

Run: `pip install alembic`

**Step 2: Initialize alembic**

Run: `alembic init alembic`

**Step 3: Configure alembic/env.py**

Update `alembic/env.py` to use the project's database URL and Base metadata:

```python
from models.database import Base, DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata
```

Also import all model files to ensure metadata is populated:
```python
from models.database import Well, Problem, Analysis, Program
from models.models_v2 import Event, ParameterSet, RCAReport
from models.user import User
```

**Step 4: Generate initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`

This creates the baseline migration from the current models.

**Step 5: Remove inline ALTER TABLE from init_db**

In `models/database.py`, simplify `init_db()`:

```python
def init_db():
    Base.metadata.create_all(bind=engine)
    # NOTE: Schema migrations are now managed by Alembic.
    # Run: alembic upgrade head
```

**Step 6: Verify migration works**

Run: `alembic upgrade head`
Expected: "Running upgrade -> 001_initial_schema"

**Step 7: Commit Phase D**

```bash
git add alembic/ alembic.ini requirements.txt models/database.py \
  frontend/src/locales/en.json frontend/src/locales/es.json
git commit -m "chore: add Alembic migrations + fix i18n key duplication

- Initialize Alembic with initial schema migration
- Remove inline ALTER TABLE from init_db()
- Fix duplicate petrophysicsAdvanced key in locale files
- Resolves audit findings #11, #14 (medium severity)"
```

---

## Final Verification

Run full test suite after all phases:

```bash
python3 -m pytest tests/ -q --tb=short
cd frontend && npm run build
```

Expected: All existing tests pass, frontend builds cleanly.

### Summary

| Phase | Findings | Commit |
|-------|----------|--------|
| A | #1 (exceptions), #8 (logging), #12 (python-jose), #13 (uploads) | `fix: backend safety` |
| B | #2 (AI hook), #3 (memoization), #4 (xlsx), #5 (axios), #6 (DDR split) | `perf: frontend optimization` |
| C | #7 (HSTS), #9 (non-root), #10 (healthchecks) | `sec: Docker hardening` |
| D | #11 (Alembic), #14 (i18n) | `chore: Alembic + i18n` |
