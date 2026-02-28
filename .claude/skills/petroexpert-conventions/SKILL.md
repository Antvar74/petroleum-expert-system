---
name: petroexpert-conventions
description: PETROEXPERT project conventions, patterns, and architecture standards for all engineering modules
---

# PETROEXPERT Project Conventions

## Module Pattern

Every engineering module follows this exact structure:

### Backend (add a new module)
1. **Engine:** `orchestrator/<module>_engine.py` — Class with `calculate_*` methods, SPE/API reference in docstring
2. **Schema:** `schemas/<module>.py` — Pydantic v2 `<Module>CalcRequest` and `<Module>Result`
3. **Route:** `routes/modules/<module>.py` — FastAPI router with `/wells/{well_id}/<module>` and `/<module>/<action>`
4. **Test:** `tests/unit/test_<module>_engine.py` and `tests/integration/test_<module>_api.py`

### Frontend (add a new module)
1. **Component:** `frontend/src/components/<Module>Module.tsx` — Input form + results tabs + AI panel
2. **Types:** `frontend/src/types/modules/<module>.ts` — Request/response TypeScript interfaces
3. **Charts:** `frontend/src/components/charts/<prefix>/` — Domain-specific Recharts components
4. **Translations:** Add keys to `frontend/src/locales/en.json` and `es.json`
5. **Sidebar:** Register in `frontend/src/components/Sidebar.tsx` navigation
6. **App.tsx:** Add view case in main switch

## Chart Prefix Map
- td = torque-drag, hyd = hydraulics, sp = stuck-pipe, wc = well-control
- se = shot-efficiency, vb = vibrations, csg = casing, cem = cementing
- cd = completion, sc = sand-control, pf = packer-forces, cu = cleanup
- wh = workover, petro = petrophysics, ddr = daily-reports

## Engineering Constants (field units)
- Hydrostatic gradient: 0.052 psi/ft/ppg
- Pipe capacity factor: 1029.4 (bbl/ft from in²)
- Steel Young's modulus: 30×10⁶ psi
- Steel density: 490 lb/ft³
- Gravity: 32.174 ft/s²

## API Response Pattern
All calculation endpoints return:
```json
{
  "summary": { ... },
  "details": [ ... ],
  "warnings": [ ... ],
  "metadata": { "engine_version": "...", "reference": "..." }
}
```

## AI Analysis Pattern
Every module supports: `POST /wells/{well_id}/<module>/analyze`
- Input: `{ result_data, params, language, provider }`
- Provider options: "gemini" (current), "ollama" (local), "auto"
- Future: "claude" (premium)
