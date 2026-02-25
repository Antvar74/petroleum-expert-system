# Medium-Severity Audit Remediation Design

**Date:** 2026-02-25
**Scope:** 14 medium-severity findings from security audit
**Organization:** 4 thematic phases with commit per phase

---

## Phase A — Backend Safety & Quality (Findings 1, 8, 12, 13)

### Finding 1: Raw exception messages in HTTP 500 responses
- **Problem:** 11 `raise HTTPException(status_code=500, detail=str(e))` leak internal errors
- **Fix:** Replace with generic messages (`"Internal server error"`), log full exception with `logger.error()`
- **Files:** routes/analysis.py, routes/events.py, routes/files.py, routes/wells.py, routes/health.py

### Finding 8: print() as logging system
- **Problem:** 11 `print()` calls for error logging, no structured logging
- **Fix:** Create `utils/logger.py` with `logging.getLogger(__name__)` pattern. Replace all `print()` with `logger.error()` / `logger.warning()`
- **Files:** api_main.py, routes/analysis.py, routes/events.py, routes/wells.py

### Finding 12: python-jose unmaintained
- **Problem:** `python-jose[cryptography]` last meaningful update ~2021
- **Fix:** Replace with `PyJWT[crypto]` in requirements.txt. Update `middleware/auth.py` — API is nearly identical (`jwt.decode()`)
- **Files:** requirements.txt, middleware/auth.py, tests that import jose

### Finding 13: No type/size validation on upload endpoints
- **Problem:** 3 upload endpoints read files without size or type checks (DoS vector)
- **Fix:** Add pre-read validation: max 10MB, extension whitelist (.csv, .las, .dlis, .pdf, .txt, .md). Reject before `await file.read()`
- **Files:** routes/files.py, routes/events.py, routes/modules/shot_efficiency.py

---

## Phase B — Frontend Optimization (Findings 2, 3, 4, 5, 6)

### Finding 5: axios in devDependencies
- **Problem:** Runtime dependency listed in devDependencies
- **Fix:** Move `axios` from devDependencies to dependencies in package.json

### Finding 4: xlsx statically imported (7MB)
- **Problem:** `import * as XLSX from 'xlsx'` in 3 files loads 7MB at startup
- **Fix:** Dynamic import `const XLSX = (await import('xlsx')).default` at point of use
- **Files:** TorqueDragModule.tsx, HydraulicsModule.tsx, DailyReportsModule.tsx

### Finding 2: Duplicated AI provider logic in 14 components
- **Problem:** Each module copy-pastes ~25 lines for AI analysis (API call, error handling, state)
- **Fix:** Extract `useAIAnalysis(module, resultData, params)` custom hook. Replace in all 14 modules.
- **New file:** frontend/src/hooks/useAIAnalysis.ts

### Finding 3: No useCallback/useMemo in module components
- **Problem:** Expensive handlers recreated on every render in 14 large modules
- **Fix:** Wrap calculation handlers with `useCallback`, derived data with `useMemo`
- **Scope:** 14 module components — focus on handlers passed to child components

### Finding 6: DailyReportsModule.tsx (1247 lines)
- **Problem:** Single component handles form, KPIs, list, AI, and export
- **Fix:** Extract into sub-components: DDRForm, DDRKPIDashboard, DDRListView
- **Files:** frontend/src/components/DailyReportsModule.tsx → split into 3-4 files

---

## Phase C — Docker & Deployment (Findings 7, 9, 10)

### Finding 7: Missing HSTS and Permissions-Policy headers
- **Problem:** HSTS only in commented HTTPS block, no Permissions-Policy
- **Fix:** Add `Strict-Transport-Security` and `Permissions-Policy` headers to active server block
- **File:** nginx/nginx.conf

### Finding 9: Docker containers run as root
- **Problem:** No USER directive in Dockerfile or nginx/Dockerfile
- **Fix:** Add non-root user (appuser:1001) in both Dockerfiles, chown app directories
- **Files:** Dockerfile, nginx/Dockerfile

### Finding 10: No health checks in Docker
- **Problem:** docker-compose has no healthcheck directives
- **Fix:** Add healthcheck for app (curl /health) and nginx (curl localhost)
- **File:** docker-compose.yml

---

## Phase D — Database & i18n (Findings 11, 14)

### Finding 14: i18n key inconsistency
- **Problem:** `petrophysicsAdvanced` duplicated in both `modules` and `app` sections
- **Fix:** Remove duplicate keys, ensure single source of truth
- **Files:** frontend/src/locales/en.json, frontend/src/locales/es.json

### Finding 11: No Alembic/migrations
- **Problem:** Schema changes via raw `ALTER TABLE` in `init_db()`, no version tracking
- **Fix:** Initialize Alembic, generate initial migration from existing models, move ALTER TABLE to versioned migration
- **New files:** alembic.ini, alembic/env.py, alembic/versions/001_initial.py
- **Modified:** models/database.py (remove inline ALTER TABLE)
