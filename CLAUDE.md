# PETROEXPERT v5.0 — Claude Code Instructions

## Project Identity

PETROEXPERT is an advanced petroleum engineering expert system designed to be a serious, low-cost competitor to industry-leading software (Landmark/Halliburton DecisionSpace, SLB Techlog/DrillBench, Weatherford WellFlo). Currently in **field data testing, evaluation, and calibration phase**.

- **Language:** Bilingual (ES/EN). Code, comments, and git messages in **English**. UI supports both via i18next.
- **Domain:** Petroleum engineering — drilling, completions, production, well control, petrophysics.
- **Users:** Petroleum engineers, drilling supervisors, field operations teams.

---

## Architecture Overview

```
petroleum-expert-system/
├── api_main.py                 # FastAPI entry (root_path=/api)
├── frontend/                   # React 19 + TypeScript 5.9 + Vite 7
├── orchestrator/               # 14 calculation engines + sub-engines
│   ├── vibrations_engine/      # 8 sub-modules (critical_speeds, stick_slip, mse, etc.)
│   └── shot_efficiency_engine/ # 7 sub-modules (petrophysics, net_pay, ranking, etc.)
├── routes/                     # FastAPI routes (27 files, ~55+ endpoints)
│   └── modules/                # Per-module route files
├── schemas/                    # Pydantic v2 request/response models (22 files)
├── models/                     # SQLAlchemy 2.0 ORM + Alembic migrations
├── agents/                     # 16 specialized AI agents (multi-agent system)
├── config/                     # agents_config.yaml
├── middleware/                 # JWT auth + rate limiting
├── utils/                      # LLM gateway, PDF, logging
├── knowledge_base/             # Domain expertise (drilling, fluids, geology, well_design)
├── tests/                      # 71 test files (unit, integration, validation)
└── Docs/                       # Technical documentation and plans
```

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript 5.9, Vite 7, Tailwind CSS 3.4 |
| Charts | Recharts 3.7, Framer Motion 12.34 |
| Backend | FastAPI, Python 3.13, Gunicorn + Uvicorn |
| ORM | SQLAlchemy 2.0, Alembic migrations |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (PyJWT) + bcrypt |
| LLM | Gemini (current primary), future: Claude (premium) + Gemini (basic) |
| PDF | html2pdf.js (frontend), pypdf (backend) |
| Deploy | Docker Compose (Nginx + App), Vercel (optional) |

### LLM Strategy

- **Current:** Google Gemini API as primary LLM provider (`GEMINI_API_KEY`).
- **Future plan:** Anthropic Claude (paid, premium responses) + Gemini (basic/fallback).
- **Local fallback:** Ollama for offline/development use.
- **Gateway:** `utils/llm_gateway.py` handles provider routing and failover.

---

## 14 Engineering Modules

| Module | Engine File | Reference |
|--------|------------|-----------|
| Torque & Drag | `torque_drag_engine.py` | SPE 11380 (Johancsik 1984) |
| Hydraulics | `hydraulics_engine.py` | API RP 13D, Dodge-Metzner |
| Stuck Pipe | `stuck_pipe_engine.py` | IADC decision trees |
| Well Control | `well_control_engine.py` | IWCF/IADC, DAK Z-factor |
| Shot Efficiency | `shot_efficiency_engine/` | Archie 1942, Karakas-Tariq |
| Vibrations | `vibrations_engine/` | Paslay & Dawson 1984, Transfer Matrix |
| Casing Design | `casing_design_engine.py` | API 5CT |
| Cementing | `cementing_engine.py` | API RP 10B |
| Completion Design | `completion_design_engine.py` | IPR/Vogel |
| Sand Control | `sand_control_engine.py` | Saucier criteria |
| Packer Forces | `packer_forces_engine.py` | Lubinski method |
| Wellbore Cleanup | `wellbore_cleanup_engine.py` | HCI/transport ratio |
| Workover Hydraulics | `workover_hydraulics_engine.py` | CT pressure loss |
| Petrophysics | `petrophysics_engine.py` | Timur/Gassmann |

---

## Code Conventions

### Backend (Python)

- **Framework:** FastAPI with async endpoints where beneficial.
- **Models:** Pydantic v2 for schemas (strict validation). SQLAlchemy 2.0 for ORM.
- **Route structure:** `routes/modules/<module>.py` — one file per engineering module.
- **Schema structure:** `schemas/<module>.py` — mirrors route files.
- **Engine structure:** `orchestrator/<module>_engine.py` or `orchestrator/<module>_engine/` for complex modules.
- **Naming:** snake_case for Python. Module names match across routes, schemas, orchestrator, and frontend types.
- **Units:** Field units (psi, ppg, ft, in, lbf, ft-lbf, bbl, gpm). Always document unit in variable names or comments when ambiguous.
- **Engineering calculations:** Must include SPE/API/IADC reference in docstring. Intermediate results should be traceable.
- **Error handling:** FastAPI HTTPException with descriptive messages. Validate at API boundary, trust internal code.
- **Tests:** pytest + pytest-asyncio. Located in `tests/unit/`, `tests/integration/`, `tests/validation/`.

### Frontend (TypeScript/React)

- **Components:** One module component per engineering module in `frontend/src/components/`.
- **Charts:** Domain-specific charts in `frontend/src/components/charts/<prefix>/` (td=torque-drag, hyd=hydraulics, vb=vibrations, se=shot-efficiency, etc.).
- **Types:** Module types in `frontend/src/types/modules/<module>.ts`.
- **State:** React Context API (AuthContext, ToastContext). No Redux. Module state is local.
- **API client:** Axios in `frontend/src/lib/api.ts` with JWT interceptor.
- **Styling:** Tailwind CSS with custom glassmorphism dark theme. Classes: `glass-panel`, `glass-card`, `btn-primary`, `btn-secondary`, `input-field`.
- **i18n:** All user-facing strings via `t('key')` from react-i18next. Keys in `frontend/src/locales/en.json` and `es.json`.
- **Icons:** lucide-react.
- **Animations:** Framer Motion for transitions and AnimatePresence.

### Naming Conventions

- Routes: `/wells/{well_id}/<module>` for well-specific, `/<module>/<action>` for standalone.
- Schemas: `<Module>CalcRequest`, `<Module>Result`.
- Engines: `<Module>Engine` class with `calculate_*` methods.
- Frontend: `<Module>Module.tsx` component, `<ChartName>.tsx` chart.
- Tests: `test_<module>_<aspect>.py`.

---

## Engineering Standards

### Calculation Quality Requirements

- All physics engines must produce results validated against published SPE/API benchmarks.
- Numerical methods must converge (DAK Z-factor: tol=1e-6, max 15 iterations).
- Unit conversions must use exact API/oilfield constants (e.g., 0.052 psi/ft/ppg, 1029.4 bbl/ft capacity factor).
- Edge cases: Handle vertical wells (inc=0), horizontal (inc=90), and S-type trajectories.
- Rheology: Support Bingham Plastic, Power Law, and Herschel-Bulkley models.
- Petrophysics: Support Archie (clean sand), Simandoux (shaly), and Indonesia (shaly) Sw models.

### Competing Software Benchmarks

Our calculations must match or exceed accuracy of:
- **Landmark WellPlan/COMPASS** (Torque & Drag, survey calculations)
- **SLB DrillBench** (Well control, kick simulation)
- **Techlog** (Petrophysics, log interpretation)
- **Weatherford WellFlo** (Completion design, IPR)
- **PIPESIM** (Hydraulics, multiphase flow)

---

## Multi-Agent AI System

- 16 agents defined in `agents/` (base_agent.py + 15 specialists).
- Agent config in `config/agents_config.yaml`.
- Workflows: standard, quick_differential, quick_mechanical, lost_circulation, wellbore_stability.
- LLM Gateway (`utils/llm_gateway.py`): Gemini (current) → Ollama fallback. Future: Claude → Gemini → Ollama.
- AI analysis available on every engineering module via `/wells/{well_id}/<module>/analyze`.

---

## Development Workflow

### Running Locally

```bash
# Backend
python3 api_main.py                    # Port 8000

# Frontend
cd frontend && npm run dev             # Port 5173

# Docker
docker compose up --build              # Nginx:80 → App:8000
```

### Testing

```bash
pytest tests/unit/                     # Unit tests
pytest tests/integration/              # Integration tests
pytest tests/validation/               # Validation tests
pytest -x --tb=short                   # Quick run, stop on first failure
```

### Database

```bash
alembic upgrade head                   # Apply migrations
alembic revision --autogenerate -m ""  # Create migration
```

### Key Environment Variables

- `GEMINI_API_KEY` — Google Gemini API (current primary LLM)
- `DATABASE_URL` — DB connection (default: SQLite)
- `JWT_SECRET` — Auth token signing
- `ENVIRONMENT` — "production" enables JWT enforcement
- `CORS_ORIGINS` — Allowed frontend origins
- Future: `ANTHROPIC_API_KEY` — Claude API (premium LLM, not yet active)

---

## Current Phase: Field Testing & Calibration

### Focus Areas

1. **Validation against field data** — Engines must match real well measurements.
2. **Engine accuracy tuning** — Calibrate constants, friction factors, correlations.
3. **UI/UX polish** — Professional look competing with $50k+/seat software.
4. **PDF report quality** — IADC-standard DDR reports, executive summaries.
5. **Performance** — Sub-second calculation response times.
6. **Security hardening** — OWASP compliance, rate limiting, input validation.

### Known Architecture Decisions

- No React Router: View switching via string state in App.tsx (acceptable for current scale).
- SQLite for development simplicity; PostgreSQL-ready for production.
- html2pdf.js for client-side PDF (no server-side PDF dependency).
- Framer Motion kept in devDependencies but used in production bundle.

---

## File Quick Reference

| What | Where |
|------|-------|
| API entry | `api_main.py` |
| Route handlers | `routes/` and `routes/modules/` |
| Pydantic schemas | `schemas/` |
| Calculation engines | `orchestrator/` |
| Vibrations sub-engines | `orchestrator/vibrations_engine/` |
| Shot efficiency sub-engines | `orchestrator/shot_efficiency_engine/` |
| AI agents | `agents/` |
| Agent config | `config/agents_config.yaml` |
| LLM gateway | `utils/llm_gateway.py` |
| Frontend app | `frontend/src/App.tsx` |
| Frontend components | `frontend/src/components/` |
| Frontend charts | `frontend/src/components/charts/` |
| TypeScript types | `frontend/src/types/` |
| API client | `frontend/src/lib/api.ts` |
| Auth context | `frontend/src/context/AuthContext.tsx` |
| Global styles | `frontend/src/index.css` |
| Translations | `frontend/src/locales/` |
| Tests | `tests/` |
| Docker config | `Dockerfile`, `docker-compose.yml` |
| Nginx config | `nginx/nginx.conf` |
| DB migrations | `alembic/` |
| Knowledge base | `knowledge_base/` |
| Documentation | `Docs/` |
