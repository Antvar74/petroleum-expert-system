# Data Readiness Panel — Design Document

> **Goal:** Each module shows a "Data Readiness" panel that recommends what data the user needs for optimal analysis, depending on the operational phase and event.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Backend                             │
│                                                         │
│  orchestrator/data_requirements.py                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ DATA_REQUIREMENTS = {                             │  │
│  │   "module-id": {                                  │  │
│  │     phases: {                                     │  │
│  │       "drilling": {                               │  │
│  │         base: { required: [...], optional: [...] }│  │
│  │         events: {                                 │  │
│  │           "kick": { additional_required: [...] }  │  │
│  │         }                                         │  │
│  │       }                                           │  │
│  │     }                                             │  │
│  │   }                                               │  │
│  │ }                                                 │  │
│  └───────────────────────────────────────────────────┘  │
│                         │                               │
│    GET /modules/{id}/data-requirements?phase=X&event=Y  │
│                         │                               │
│  api_main.py ──→ returns merged (base + event) list     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Frontend                            │
│                                                         │
│  DataReadinessPanel.tsx                                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Props: moduleId, phase, event, currentData        │  │
│  │                                                   │  │
│  │ 1. Fetch /modules/{id}/data-requirements          │  │
│  │ 2. Cross-check requirements vs currentData        │  │
│  │ 3. Render:                                        │  │
│  │    ✅ param (value)  — data present               │  │
│  │    ❌ param — missing, upload or enter manually   │  │
│  │    ⚠️ param — using default (0.65)                │  │
│  │ 4. Compute readiness percentage                   │  │
│  │ 5. Show recommended files to upload               │  │
│  │ 6. Enable/disable analysis button                 │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Embedded in each module, before the analysis trigger   │
└─────────────────────────────────────────────────────────┘
```

## Backend: Data Requirements Registry

### File: `orchestrator/data_requirements.py`

Single dictionary mapping every module → phases → events → required/optional data.

### Structure per module

```python
DATA_REQUIREMENTS: Dict[str, ModuleRequirements] = {
    "module-id": {
        "name": "Module Display Name",
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {
                            "key": "parameter_key",       # matches engine param name
                            "label": "Human-Readable Name",
                            "source": "LAS/CSV/manual",   # how to provide it
                            "unit": "ppg",                 # expected unit
                        },
                    ],
                    "optional": [
                        {
                            "key": "parameter_key",
                            "label": "Human-Readable Name",
                            "default": "value used if not provided",
                            "impact": "What happens if missing",
                        },
                    ],
                    "recommended_files": [
                        "Survey LAS/CSV",
                        "Drilling parameters LAS",
                    ],
                },
                "events": {
                    "kick": {
                        "additional_required": [...],
                        "additional_optional": [...],
                    },
                },
            },
            "completion": { ... },
            "workover": { ... },
        },
        "min_readiness_pct": 60,  # minimum % to enable analysis
    },
}
```

### Merge logic

```python
def get_requirements(module_id, phase, event=None):
    """Returns merged requirements: base[phase] + events[event]."""
    module = DATA_REQUIREMENTS[module_id]
    phase_data = module["phases"][phase]
    base = phase_data["base"]

    result = {
        "module": module["name"],
        "phase": phase,
        "event": event,
        "required": list(base["required"]),
        "optional": list(base["optional"]),
        "recommended_files": list(base.get("recommended_files", [])),
        "min_readiness_pct": module.get("min_readiness_pct", 60),
    }

    if event and "events" in phase_data and event in phase_data["events"]:
        evt = phase_data["events"][event]
        result["required"].extend(evt.get("additional_required", []))
        result["optional"].extend(evt.get("additional_optional", []))

    return result
```

### API endpoint

```
GET /modules/{module_id}/data-requirements?phase=drilling&event=kick
```

Returns the merged requirements JSON.

### Modules covered (14)

| Module | Phases | Events |
|--------|--------|--------|
| torque-drag | drilling, completion, workover | stuck_pipe, high_torque |
| hydraulics | drilling, completion, workover | lost_circulation, barite_sag |
| stuck-pipe | drilling | differential, mechanical, packoff, keyseating |
| well-control | drilling | kick, underground_blowout, lost_circulation |
| wellbore-cleanup | drilling | poor_hole_cleaning, tight_hole |
| packer-forces | completion | leak, movement |
| workover-hydraulics | workover | bullheading, circulation |
| sand-control | completion | screen_failure, sand_production |
| completion-design | completion | skin_damage, flow_efficiency |
| shot-efficiency | completion | perforation |
| vibrations | drilling | lateral, torsional, axial |
| cementing | drilling, completion | channeling, contamination |
| casing-design | drilling | burst, collapse, tension |
| petrophysics | drilling, completion | — (no events) |

## Frontend: DataReadinessPanel Component

### File: `frontend/src/components/DataReadinessPanel.tsx`

### Props

```typescript
interface DataReadinessPanelProps {
  moduleId: string;           // e.g., "torque-drag"
  phase: string;              // e.g., "drilling"
  event?: string;             // e.g., "kick" (optional)
  currentData: Record<string, any>;  // values the user already has
  onPhaseChange?: (phase: string) => void;
  onEventChange?: (event: string) => void;
}
```

### Visual Layout

```
┌──────────────────────────────────────────────────────┐
│ 📋 Data Readiness                                    │
│ Phase: [Drilling ▼]  Event: [Kick ▼]       ██░░ 75% │
│ ──────────────────────────────────────────────────── │
│                                                      │
│ Required                                             │
│ ✅ Mud Weight .......................... 10.5 ppg     │
│ ✅ Casing Shoe TVD .................... 8,500 ft     │
│ ✅ SIDPP ............................... 200 psi      │
│ ❌ SICP .............. Upload or enter manually      │
│                                                      │
│ Optional (improves accuracy)                         │
│ ⚠️ Gas Gravity ....................... Using 0.65    │
│ ⚠️ Pit Gain .......................... Using 20 bbl  │
│                                                      │
│ 📁 Recommended uploads: Survey LAS, Drilling LAS    │
└──────────────────────────────────────────────────────┘
```

### States

- **✅ Present**: `currentData[key]` exists and is not null/empty
- **❌ Missing required**: Key not in currentData — shown in red with action hint
- **⚠️ Using default**: Optional key not provided — shown in amber with default value

### Readiness calculation

```
readiness = (present_required / total_required) * 100
```

Only required fields count toward readiness. Optional fields show status but don't block analysis.

### Integration

Each module adds `<DataReadinessPanel>` in its parameters/analysis tab:

```tsx
<DataReadinessPanel
  moduleId="well-control"
  phase={selectedPhase}
  event={selectedEvent}
  currentData={currentParams}
/>
```

### Localization

All labels come from locale files:
- `dataReadiness.title`: "Data Readiness" / "Preparación de Datos"
- `dataReadiness.required`: "Required" / "Requerido"
- `dataReadiness.optional`: "Optional (improves accuracy)" / "Opcional (mejora precisión)"
- `dataReadiness.missingAction`: "Upload or enter manually" / "Sube o ingresa manualmente"
- `dataReadiness.usingDefault`: "Using {{value}}" / "Usando {{value}}"
- `dataReadiness.recommendedUploads`: "Recommended uploads" / "Archivos recomendados"
- `dataReadiness.readiness`: "Data Readiness" / "Preparación de Datos"
- Phase labels: `dataReadiness.phases.drilling`, `.completion`, `.workover`

## Testing

- Unit tests for `get_requirements()` merge logic (~8 tests)
- Unit tests for readiness calculation
- Verify all 14 modules have valid entries
- Verify all phase/event combos return non-empty required lists

## Success Criteria

1. Every module shows data readiness before analysis
2. Requirements change based on phase + event selection
3. User sees exactly what to upload for optimal analysis
4. Analysis button disabled when readiness < threshold
5. Bilingual (EN/ES) labels throughout
