# Finite Element Analysis (FEA) — Vibrations Module Design

**Date**: 2026-02-25
**Status**: Approved
**Module**: Vibrations (`orchestrator/vibrations_engine/`)

## 1. Objective

Implement a Finite Element Analysis (FEA) solver for BHA lateral vibrations to bring
PetroExpert to Tier-1 level (Halliburton DrillSim, NOV ReedHycalog, Landmark WellPlan).

Currently the module uses Transfer Matrix Method (TMM) which finds natural frequencies
but does NOT provide:
- **Mode shapes** (deflection profile along BHA)
- **Geometric stiffness** (WOB pre-stress effects)
- **Damping** (drilling fluid viscous damping)
- **Forced response** (vibration amplitudes from bit excitation)
- **Campbell diagram** (frequency vs RPM with excitation crossings)

FEA solves all of these with assembled [K], [Kg], [M] matrices and standard eigenvalue
solvers.

## 2. Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| FEA Level | Beam Completo | Full [K], [Kg], [M], mode shapes, pre-stress, forced response |
| Architecture | Pure Python/NumPy + scipy.linalg.eigh | Zero new heavy deps, <10ms for 40x40 |
| Data Source | Dedicated BHA editor in Vibrations | Module-specific, no T&D coupling |
| Visualizations | Mode Shape Plot + Campbell Diagram | Both needed for engineering value |
| Integration | Opt-in, backward compatible | TMM remains for simple inputs |

## 3. FEA Solver Architecture

### File: `orchestrator/vibrations_engine/fea.py` (~450 lines)

```
fea.py
├── _beam_element_matrices(L, EI, rhoA, P=0)       → K_e, Kg_e, M_e (4x4)
├── _assemble_global(elements, bc, stabilizers)      → K, Kg, M globals (nxn)
├── solve_eigenvalue(K, Kg, M, P, n_modes=5)         → freqs_hz[], mode_shapes[][]
├── solve_forced_response(K, Kg, M, C, F, omegas)    → amplitudes[][]
├── run_fea_analysis(bha_components, params)          → Dict complete
└── generate_campbell_diagram(bha_components, params, rpm_range) → Dict Campbell data
```

### 3.1 Element Formulation (Euler-Bernoulli Beam, 4 DOF)

Two DOF per node: lateral deflection `y` and rotation `theta`.
Element matrices (4x4) for segment of length L, bending stiffness EI, mass/length rhoA,
axial load P:

**Stiffness [Ke]** — standard Euler-Bernoulli:
```
(EI/L^3) * [  12    6L   -12    6L  ]
            [  6L   4L^2  -6L   2L^2 ]
            [ -12   -6L    12   -6L  ]
            [  6L   2L^2  -6L   4L^2 ]
```

**Geometric stiffness [Kge]** — pre-stress from WOB:
```
(P/30L) * [  36    3L   -36    3L  ]
          [  3L   4L^2  -3L   -L^2 ]
          [ -36   -3L    36   -3L  ]
          [  3L   -L^2  -3L   4L^2 ]
```

**Consistent mass [Me]**:
```
(rhoA*L/420) * [ 156    22L    54   -13L  ]
               [  22L   4L^2   13L  -3L^2 ]
               [  54    13L   156   -22L  ]
               [ -13L  -3L^2  -22L   4L^2 ]
```

### 3.2 Global Assembly

- BHA: ~10 components segmented into ~20 nodes → 40x40 matrices
- Standard FEM assembly: overlap shared DOFs at node interfaces
- Boundary conditions by elimination:
  - pinned-pinned: y=0 at bit (node 0) and top (node N)
  - fixed-pinned: y=0, theta=0 at bit; y=0 at top
  - fixed-free: y=0, theta=0 at bit; free at top
- Stabilizers: large spring constant (1e8 lb/in) at stabilizer nodes → y≈0

### 3.3 Eigenvalue Solver

Generalized symmetric eigenvalue problem:

```
([K] - P*[Kg]) {phi} = omega^2 [M] {phi}
```

- Solver: `scipy.linalg.eigh(K_eff, M)` → returns eigenvalues + eigenvectors
- K_eff = K - P*Kg (P = WOB converted to consistent units)
- Returns first n_modes (default 5):
  - Natural frequencies in Hz and critical RPM
  - Mode shape vectors (deflection at each node)
- Performance: <10ms for 40x40 with NumPy/SciPy

### 3.4 Forced Response

```
([K] + i*omega*[C] - omega^2*[M]) {U} = {F}
```

- **Rayleigh damping**: [C] = alpha*[M] + beta*[K]
  - alpha estimated from mud weight (higher MW = more damping)
  - beta from material damping (~0.01)
- **Excitation force** {F}:
  - Mass imbalance at bit node: F = m*e*omega^2
  - Bit excitation: from n_blades * RPM frequency
- **Output**: complex amplitude at each node → magnitude = vibration level
- Solved via `numpy.linalg.solve` for each frequency

### 3.5 Campbell Diagram Generation

- Sweep RPM from rpm_min to rpm_max (step rpm_step)
- At each RPM: solve eigenvalue with corresponding WOB → natural frequencies
- Excitation lines: f = n * RPM/60 for n = 1, 2, 3
- Crossings detected where |f_natural - n*RPM/60| < threshold
- Returns structured data for frontend plotting

## 4. Frontend: BHA Editor Component

### File: `frontend/src/components/charts/vb/BHAEditor.tsx` (~200 lines)

Interactive table for multi-component BHA definition:

| Column | Type | Default | Units |
|--------|------|---------|-------|
| type | dropdown | collar | collar/dp/hwdp/stabilizer/motor/MWD |
| od | number | 6.75 | in |
| id_inner | number | 2.813 | in |
| length_ft | number | 30 | ft |
| weight_ppf | number | 83 | lb/ft |

**Features:**
- Add/remove component rows
- Drag-and-drop reorder (bit → surface)
- Presets: "Standard Rotary BHA", "Motor BHA", "RSS BHA"
- Auto-suggest weight_ppf from type + OD
- Visual BHA stack graphic (right side)
- Collapsible in Input tab under "BHA Detallado (FEA)"

## 5. Frontend: Visualization Charts

### 5A: Mode Shape Plot

**File:** `frontend/src/components/charts/vb/ModeShapePlot.tsx` (~180 lines)

- Recharts LineChart, `layout="vertical"`
- Y-axis: Depth MD (ft), reversed (bit at bottom)
- X-axis: Normalized deflection (-1 to +1)
- Up to 3 modes overlaid (Mode 1 blue, Mode 2 green, Mode 3 orange)
- BHA component markers (colored bands by type)
- Node points (zero-crossings) marked
- Toggle to show/hide individual modes

### 5B: Campbell Diagram

**File:** `frontend/src/components/charts/vb/CampbellDiagram.tsx` (~220 lines)

- Recharts ScatterChart/LineChart
- X-axis: RPM (20-300)
- Y-axis: Frequency (Hz)
- Solid lines: natural frequency curves (Mode 1..5)
- Dashed red: 1xRPM excitation line
- Dashed lighter: 2xRPM, 3xRPM harmonics
- Warning markers at crossings (resonances)
- Operating band: semi-transparent rectangle at current RPM
- Danger zones: red semi-transparent regions near crossings

## 6. API: Schemas and Routes

### New Schemas in `schemas/vibrations.py`:

```python
class FEARequest(BaseModel):
    bha_components: List[Dict[str, Any]]
    wob_klb: float = 20
    rpm: float = 120
    mud_weight_ppg: float = 10
    hole_diameter_in: float = 8.5
    boundary_conditions: str = "pinned-pinned"
    n_modes: int = 5
    include_forced_response: bool = True
    n_blades: Optional[int] = None

class CampbellRequest(BaseModel):
    bha_components: List[Dict[str, Any]]
    wob_klb: float = 20
    mud_weight_ppg: float = 10
    hole_diameter_in: float = 8.5
    boundary_conditions: str = "pinned-pinned"
    rpm_min: float = 20
    rpm_max: float = 300
    rpm_step: float = 5
    n_modes: int = 5
    n_blades: Optional[int] = None
```

### New Routes in `routes/modules/vibrations.py`:

```
POST /vibrations/fea          → run_fea_analysis()
POST /vibrations/campbell      → generate_campbell_diagram()
```

## 7. Integration with Existing Pipeline

When `bha_components` provided AND FEA enabled:

1. FEA **replaces** TMM for lateral vibrations (more accurate)
2. Mode shapes → `fatigue.py` can use real bending stress (not just DLS-based)
3. Forced response → better input for `stability.py` (actual vibration amplitudes)
4. Resonance check uses FEA frequencies directly

**Backward compatible**: Without bha_components, pipeline continues using existing TMM.

### Facade update (`__init__.py`):
```python
from .fea import run_fea_analysis, generate_campbell_diagram

# In VibrationsEngine class:
run_fea_analysis = staticmethod(run_fea_analysis)
generate_campbell_diagram = staticmethod(generate_campbell_diagram)
```

## 8. Dependencies

- **numpy**: Already in project requirements
- **scipy**: NEW — needed for `scipy.linalg.eigh` (generalized eigenvalue solver)
- No other new dependencies

## 9. File Summary

| Action | File | Est. Lines |
|--------|------|-----------|
| NEW | `orchestrator/vibrations_engine/fea.py` | ~450 |
| NEW | `frontend/src/components/charts/vb/BHAEditor.tsx` | ~200 |
| NEW | `frontend/src/components/charts/vb/ModeShapePlot.tsx` | ~180 |
| NEW | `frontend/src/components/charts/vb/CampbellDiagram.tsx` | ~220 |
| MODIFY | `orchestrator/vibrations_engine/__init__.py` | +6 |
| MODIFY | `orchestrator/vibrations_engine/pipeline.py` | +30 |
| MODIFY | `schemas/vibrations.py` | +25 |
| MODIFY | `routes/modules/vibrations.py` | +20 |
| MODIFY | `frontend/src/components/VibrationsModule.tsx` | +80 |
| NEW | `tests/unit/test_fea_engine.py` | ~120 |

**Total**: ~1,330 new lines, ~160 modified lines.

## 10. Verification

```bash
# Unit tests
python3 -m pytest tests/unit/test_fea_engine.py -v

# Existing tests still pass
python3 -m pytest tests/unit/test_vibrations_engine.py -v

# Frontend build
cd frontend && npx tsc --noEmit && npm run build

# Manual checks:
# 1. BHA editor: add/remove/reorder components
# 2. FEA results: mode shapes display correctly (vertical depth plot)
# 3. Campbell diagram: excitation crossings visible
# 4. Forced response amplitudes shown
# 5. Backward compat: simple inputs still use TMM
```
