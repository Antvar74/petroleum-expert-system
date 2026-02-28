# Casing Design Engine — Refactoring & Improvements Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monolithic `casing_design_engine.py` (1442 lines) into a modular sub-module package following the established vibrations/shot_efficiency pattern, then fix critical audit findings and add missing capabilities.

**Architecture:** Split into 12 focused sub-modules with backward-compatible facade. The refactoring preserves all existing behavior (zero logic changes), then subsequent tasks layer in audit fixes. Same pattern as `orchestrator/vibrations_engine/` and `orchestrator/shot_efficiency_engine/`.

**Tech Stack:** Python 3.13, FastAPI, pytest. No new dependencies.

---

## Target Directory Structure

```
orchestrator/casing_design_engine/      # NEW package directory
├── __init__.py          # Facade: CasingDesignEngine class (backward compat)
├── constants.py         # Grade DB, casing catalog, default SF
├── loads.py             # Burst/collapse/tension load profiles
├── ratings.py           # Burst (Barlow) & collapse (API 5C3 4-zone) + temp derating
├── corrections.py       # Biaxial, triaxial VME, Lamé hoop stress
├── grade_selection.py   # Grade selection + catalog lookup
├── safety_factors.py    # SF calculation + SF-vs-depth profile (NEW)
├── scenarios.py         # Multi-scenario burst (5) & collapse (4)
├── running_loads.py     # Running loads with drag + thermal axial (NEW)
├── connections.py       # Connection verification (NEW — audit #6)
├── wear.py              # Wear/corrosion allowance
└── pipeline.py          # Full design orchestration + recommendations
```

## Consumers That MUST Keep Working

All of these import `from orchestrator.casing_design_engine import CasingDesignEngine`:

- `routes/modules/casing_design.py`
- `routes/cross_engine.py`
- `routes/calculations.py`
- `tests/unit/test_casing_design_engine.py` (47 tests)
- `tests/unit/test_elite_fase6_casing.py`
- `tests/unit/test_elite_fase9.py`
- `tests/validation/test_validate_casing_design.py` (9 tests)

---

## Phase 1: Refactoring (Tasks 1–5)

Zero logic changes. Move code, verify tests pass.

---

### Task 1: Create package directory + constants.py

**Files:**
- Create: `orchestrator/casing_design_engine/__init__.py` (empty placeholder)
- Create: `orchestrator/casing_design_engine/constants.py`
- Keep: `orchestrator/casing_design_engine.py` (original file stays until Task 5)

**Step 1: Create the package directory**

```bash
mkdir -p orchestrator/casing_design_engine
```

**Step 2: Create constants.py**

Extract from `casing_design_engine.py:30-47` (CASING_GRADES, DEFAULT_SF) and `casing_design_engine.py:912-963` (CASING_CATALOG).

```python
"""
Casing Design Constants — Grade database, catalog, and default safety factors.

References:
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
"""
from typing import Dict, Any, List

# ── Grade Database (API 5CT) ──
CASING_GRADES: Dict[str, Dict[str, Any]] = {
    "J55":  {"yield_psi": 55000,  "tensile_psi": 75000,  "color": "#4CAF50"},
    "K55":  {"yield_psi": 55000,  "tensile_psi": 95000,  "color": "#66BB6A"},
    "L80":  {"yield_psi": 80000,  "tensile_psi": 95000,  "color": "#2196F3"},
    "N80":  {"yield_psi": 80000,  "tensile_psi": 100000, "color": "#42A5F5"},
    "C90":  {"yield_psi": 90000,  "tensile_psi": 100000, "color": "#FF9800"},
    "T95":  {"yield_psi": 95000,  "tensile_psi": 105000, "color": "#FFA726"},
    "C110": {"yield_psi": 110000, "tensile_psi": 120000, "color": "#F44336"},
    "P110": {"yield_psi": 110000, "tensile_psi": 125000, "color": "#EF5350"},
    "Q125": {"yield_psi": 125000, "tensile_psi": 135000, "color": "#9C27B0"},
}

DEFAULT_SF = {
    "burst": 1.10,
    "collapse": 1.00,
    "tension": 1.60,
}

# ── Expanded Casing Catalog (API 5CT) ──
# Key = nominal OD as string "X.XXX", value = list of available weights/grades
CASING_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    # ... (exact copy of lines 913-963 from original file)
    "4.500": [
        {"weight": 9.50, "id": 4.090, "wall": 0.205, "grade": "J55", "burst": 4380, "collapse": 2760},
        {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "J55", "burst": 6230, "collapse": 5430},
        {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "N80", "burst": 9060, "collapse": 8600},
        {"weight": 13.50, "id": 3.810, "wall": 0.345, "grade": "N80", "burst": 10790, "collapse": 11080},
        {"weight": 15.10, "id": 3.680, "wall": 0.410, "grade": "P110", "burst": 17530, "collapse": 17350},
    ],
    "5.500": [
        {"weight": 14.00, "id": 5.012, "wall": 0.244, "grade": "J55", "burst": 4270, "collapse": 2870},
        {"weight": 15.50, "id": 4.950, "wall": 0.275, "grade": "J55", "burst": 4810, "collapse": 3660},
        {"weight": 17.00, "id": 4.892, "wall": 0.304, "grade": "N80", "burst": 7740, "collapse": 6070},
        {"weight": 20.00, "id": 4.778, "wall": 0.361, "grade": "N80", "burst": 9190, "collapse": 8440},
        {"weight": 23.00, "id": 4.670, "wall": 0.415, "grade": "P110", "burst": 14510, "collapse": 13680},
    ],
    "7.000": [
        {"weight": 17.00, "id": 6.538, "wall": 0.231, "grade": "J55", "burst": 3180, "collapse": 1420},
        {"weight": 23.00, "id": 6.366, "wall": 0.317, "grade": "J55", "burst": 4360, "collapse": 3270},
        {"weight": 26.00, "id": 6.276, "wall": 0.362, "grade": "N80", "burst": 7250, "collapse": 5410},
        {"weight": 29.00, "id": 6.184, "wall": 0.408, "grade": "N80", "burst": 8160, "collapse": 6980},
        {"weight": 32.00, "id": 6.094, "wall": 0.453, "grade": "L80", "burst": 9070, "collapse": 8240},
        {"weight": 35.00, "id": 6.004, "wall": 0.498, "grade": "C90", "burst": 11210, "collapse": 10520},
        {"weight": 38.00, "id": 5.920, "wall": 0.540, "grade": "P110", "burst": 14850, "collapse": 13290},
    ],
    "9.625": [
        {"weight": 36.00, "id": 8.921, "wall": 0.352, "grade": "J55", "burst": 3520, "collapse": 2020},
        {"weight": 40.00, "id": 8.835, "wall": 0.395, "grade": "J55", "burst": 3950, "collapse": 2570},
        {"weight": 43.50, "id": 8.755, "wall": 0.435, "grade": "N80", "burst": 6330, "collapse": 4130},
        {"weight": 47.00, "id": 8.681, "wall": 0.472, "grade": "N80", "burst": 6870, "collapse": 4760},
        {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "C90", "burst": 8930, "collapse": 7040},
        {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "P110", "burst": 10910, "collapse": 9120},
    ],
    "10.750": [
        {"weight": 32.75, "id": 10.192, "wall": 0.279, "grade": "J55", "burst": 2500, "collapse": 920},
        {"weight": 40.50, "id": 10.050, "wall": 0.350, "grade": "J55", "burst": 3140, "collapse": 1580},
        {"weight": 45.50, "id": 9.950, "wall": 0.400, "grade": "N80", "burst": 5210, "collapse": 2710},
        {"weight": 51.00, "id": 9.850, "wall": 0.450, "grade": "N80", "burst": 5860, "collapse": 3480},
        {"weight": 55.50, "id": 9.760, "wall": 0.495, "grade": "P110", "burst": 8890, "collapse": 5210},
    ],
    "13.375": [
        {"weight": 48.00, "id": 12.715, "wall": 0.330, "grade": "J55", "burst": 2380, "collapse": 870},
        {"weight": 54.50, "id": 12.615, "wall": 0.380, "grade": "J55", "burst": 2740, "collapse": 1180},
        {"weight": 61.00, "id": 12.515, "wall": 0.430, "grade": "N80", "burst": 4510, "collapse": 1900},
        {"weight": 68.00, "id": 12.415, "wall": 0.480, "grade": "N80", "burst": 5030, "collapse": 2420},
        {"weight": 72.00, "id": 12.347, "wall": 0.514, "grade": "P110", "burst": 7430, "collapse": 3340},
    ],
    "20.000": [
        {"weight": 94.00, "id": 19.124, "wall": 0.438, "grade": "J55", "burst": 2110, "collapse": 520},
        {"weight": 106.50, "id": 18.936, "wall": 0.532, "grade": "K55", "burst": 2560, "collapse": 870},
        {"weight": 133.00, "id": 18.730, "wall": 0.635, "grade": "K55", "burst": 3060, "collapse": 1370},
    ],
}
```

**Step 3: Create empty `__init__.py` placeholder**

```python
# Placeholder — will be replaced in Task 4 with full facade
```

**Step 4: Commit**

```bash
git add orchestrator/casing_design_engine/
git commit -m "refactor(casing): create package directory with constants.py"
```

---

### Task 2: Extract loads.py, ratings.py, corrections.py

**Files:**
- Create: `orchestrator/casing_design_engine/loads.py`
- Create: `orchestrator/casing_design_engine/ratings.py`
- Create: `orchestrator/casing_design_engine/corrections.py`

**Step 1: Create loads.py**

Extract from original file:
- `calculate_burst_load()` (lines 52–120)
- `calculate_collapse_load()` (lines 125–186)
- `calculate_tension_load()` (lines 191–245)

```python
"""
Casing load profiles — burst, collapse, and tension vs. depth.

References:
- API TR 5C3 (ISO 10400): Load scenarios for casing design
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 7
"""
import math
from typing import Dict, Any


def calculate_burst_load(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    gas_gradient_psi_ft: float = 0.1,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    # ... exact copy of original method body (lines 62-120)


def calculate_collapse_load(
    tvd_ft: float,
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
    cement_top_tvd_ft: float = 0.0,
    cement_density_ppg: float = 16.0,
    evacuation_level_ft: float = 0.0,
    num_points: int = 20,
) -> Dict[str, Any]:
    # ... exact copy of original method body (lines 134-186)


def calculate_tension_load(
    casing_weight_ppf: float,
    casing_length_ft: float,
    mud_weight_ppg: float,
    casing_od_in: float,
    casing_id_in: float,
    buoyancy_applied: bool = True,
    shock_load: bool = True,
    bending_load_dls: float = 0.0,
    overpull_lbs: float = 50000.0,
) -> Dict[str, Any]:
    # ... exact copy of original method body (lines 203-245)
```

**CRITICAL:** Copy function bodies verbatim. Remove `@staticmethod` decorator (these are now module-level functions). No logic changes.

**Step 2: Create ratings.py**

Extract from original:
- `calculate_burst_rating()` (lines 250–276)
- `calculate_collapse_rating()` (lines 281–367)
- `derate_for_temperature()` (lines 854–907)

```python
"""
Casing resistance ratings — burst (Barlow), collapse (API 5C3 4-zone), temperature derating.

References:
- API TR 5C3 (ISO 10400): Equations for Casing, Tubing, and Line Pipe
- API 5CT: Specification for Casing and Tubing
- Barlow's formula: P_burst = 0.875 * 2 * Yp * t / OD
"""
import math
from typing import Dict, Any


def calculate_burst_rating(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    # ... exact copy (lines 257-276)


def calculate_collapse_rating(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    # ... exact copy (lines 288-367)


def derate_for_temperature(
    grade: str,
    yield_strength_psi: float,
    temperature_f: float,
    ambient_temperature_f: float = 70.0,
) -> Dict[str, Any]:
    # ... exact copy (lines 861-907)
```

**Step 3: Create corrections.py**

Extract from original:
- `calculate_biaxial_correction()` (lines 372–416)
- `calculate_triaxial_vme()` (lines 421–473)

```python
"""
Casing stress corrections — biaxial (API 5C3 ellipse) and triaxial (Von Mises).

References:
- API TR 5C3: Biaxial correction for collapse under axial tension
- Von Mises yield criterion: Combined stress check
"""
import math
from typing import Dict, Any


def calculate_biaxial_correction(
    collapse_rating_psi: float,
    axial_stress_psi: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    # ... exact copy (lines 378-416)


def calculate_triaxial_vme(
    axial_stress_psi: float,
    hoop_stress_psi: float,
    radial_stress_psi: float = 0.0,
    shear_stress_psi: float = 0.0,
    yield_strength_psi: float = 80000.0,
    safety_factor: float = 1.25,
) -> Dict[str, Any]:
    # ... exact copy (lines 429-473)
```

**Step 4: Commit**

```bash
git add orchestrator/casing_design_engine/loads.py orchestrator/casing_design_engine/ratings.py orchestrator/casing_design_engine/corrections.py
git commit -m "refactor(casing): extract loads, ratings, corrections sub-modules"
```

---

### Task 3: Extract grade_selection.py, safety_factors.py, scenarios.py, wear.py, running_loads.py

**Files:**
- Create: `orchestrator/casing_design_engine/grade_selection.py`
- Create: `orchestrator/casing_design_engine/safety_factors.py`
- Create: `orchestrator/casing_design_engine/scenarios.py`
- Create: `orchestrator/casing_design_engine/running_loads.py`
- Create: `orchestrator/casing_design_engine/wear.py`

**Step 1: Create grade_selection.py**

Extract `select_casing_grade()` (lines 478-565) and `lookup_casing_catalog()` (lines 965-999). These import from `constants.py` and `ratings.py`.

```python
"""
Casing grade selection and catalog lookup.

References:
- API 5CT: Casing grade specifications
"""
import math
from typing import Dict, Any, Optional

from .constants import CASING_GRADES, CASING_CATALOG
from .ratings import calculate_collapse_rating


def select_casing_grade(
    required_burst_psi: float,
    required_collapse_psi: float,
    required_tension_lbs: float,
    casing_od_in: float,
    wall_thickness_in: float,
    sf_burst: float = 1.10,
    sf_collapse: float = 1.00,
    sf_tension: float = 1.60,
) -> Dict[str, Any]:
    # ... exact copy (lines 488-565)
    # Change CasingDesignEngine.CASING_GRADES → CASING_GRADES
    # Change CasingDesignEngine.calculate_collapse_rating() → calculate_collapse_rating()


def lookup_casing_catalog(
    casing_od_in: float,
    min_weight_ppf: float = 0.0,
    grade_filter: Optional[str] = None,
) -> Dict[str, Any]:
    # ... exact copy (lines 971-999)
    # Change CasingDesignEngine.CASING_CATALOG → CASING_CATALOG
```

**Step 2: Create safety_factors.py**

Extract `calculate_safety_factors()` (lines 570-628).

```python
"""
Casing safety factor evaluation.

References:
- NORSOK D-010: Design factor requirements
"""
from typing import Dict, Any


def calculate_safety_factors(
    burst_load_psi: float,
    burst_rating_psi: float,
    collapse_load_psi: float,
    collapse_rating_psi: float,
    tension_load_lbs: float,
    tension_rating_lbs: float,
    sf_burst_min: float = 1.10,
    sf_collapse_min: float = 1.00,
    sf_tension_min: float = 1.60,
) -> Dict[str, Any]:
    # ... exact copy (lines 582-628)
```

**Step 3: Create scenarios.py**

Extract `calculate_burst_scenarios()` (lines 633-743) and `calculate_collapse_scenarios()` (lines 748-849).

```python
"""
Multi-scenario burst and collapse analysis.

References:
- API TR 5C3 / ISO 10400: Design load cases
"""
from typing import Dict, Any


def calculate_burst_scenarios(...) -> Dict[str, Any]:
    # ... exact copy (lines 646-743)


def calculate_collapse_scenarios(...) -> Dict[str, Any]:
    # ... exact copy (lines 759-849)
```

**Step 4: Create running_loads.py**

Extract `calculate_running_loads()` (lines 1117-1185).

```python
"""
Running loads — hookload during casing run.

References:
- Lubinski: Bending load on casing (API)
"""
import math
from typing import Dict, Any, List, Optional


def calculate_running_loads(
    casing_weight_ppf: float,
    casing_length_ft: float,
    casing_od_in: float,
    casing_id_in: float,
    mud_weight_ppg: float,
    survey: Optional[List[Dict[str, float]]] = None,
    friction_factor: float = 0.30,
) -> Dict[str, Any]:
    # ... exact copy (lines 1127-1185)
```

**Step 5: Create wear.py**

Extract `apply_wear_allowance()` (lines 1190-1235). It imports from ratings.

```python
"""
Wear and corrosion allowance — derate wall thickness over design life.
"""
from typing import Dict, Any

from .ratings import calculate_burst_rating, calculate_collapse_rating


def apply_wear_allowance(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
    wear_pct: float = 0.0,
    corrosion_rate_in_yr: float = 0.0,
    design_life_years: float = 20.0,
) -> Dict[str, Any]:
    # ... exact copy (lines 1199-1235)
    # Change CasingDesignEngine.calculate_burst_rating → calculate_burst_rating
    # Change CasingDesignEngine.calculate_collapse_rating → calculate_collapse_rating
```

**Step 6: Commit**

```bash
git add orchestrator/casing_design_engine/grade_selection.py orchestrator/casing_design_engine/safety_factors.py orchestrator/casing_design_engine/scenarios.py orchestrator/casing_design_engine/running_loads.py orchestrator/casing_design_engine/wear.py
git commit -m "refactor(casing): extract grade_selection, safety_factors, scenarios, running_loads, wear"
```

---

### Task 4: Create pipeline.py and facade __init__.py

**Files:**
- Create: `orchestrator/casing_design_engine/pipeline.py`
- Modify: `orchestrator/casing_design_engine/__init__.py`

**Step 1: Create pipeline.py**

Extract `calculate_full_casing_design()` (lines 1240-1394) and `generate_recommendations()` (lines 1399-1442). This orchestrates calls to all sub-modules.

```python
"""
Full casing design pipeline — orchestrates all sub-module calculations.

References:
- API TR 5C3 (ISO 10400): Complete casing design workflow
- NORSOK D-010: Well integrity requirements
"""
import math
from typing import Dict, Any, List

from .constants import CASING_GRADES
from .loads import calculate_burst_load, calculate_collapse_load, calculate_tension_load
from .ratings import calculate_burst_rating, calculate_collapse_rating
from .corrections import calculate_biaxial_correction, calculate_triaxial_vme
from .grade_selection import select_casing_grade
from .safety_factors import calculate_safety_factors


def calculate_full_casing_design(
    casing_od_in: float = 9.625,
    casing_id_in: float = 8.681,
    wall_thickness_in: float = 0.472,
    casing_weight_ppf: float = 47.0,
    casing_length_ft: float = 10000.0,
    tvd_ft: float = 9500.0,
    mud_weight_ppg: float = 10.5,
    pore_pressure_ppg: float = 9.0,
    fracture_gradient_ppg: float = 16.5,
    gas_gradient_psi_ft: float = 0.1,
    cement_top_tvd_ft: float = 5000.0,
    cement_density_ppg: float = 16.0,
    bending_dls: float = 3.0,
    overpull_lbs: float = 50000.0,
    sf_burst: float = 1.10,
    sf_collapse: float = 1.00,
    sf_tension: float = 1.60,
) -> Dict[str, Any]:
    # ... exact logic copy (lines 1265-1394)
    # Replace CasingDesignEngine.method() → module-level function calls
    # Replace CasingDesignEngine.CASING_GRADES → CASING_GRADES


def generate_recommendations(result: Dict[str, Any]) -> List[str]:
    # ... exact copy (lines 1400-1442)
```

**CRITICAL refactoring notes for pipeline.py:**
- `CasingDesignEngine.calculate_burst_load(...)` → `calculate_burst_load(...)`
- `CasingDesignEngine.calculate_collapse_rating(...)` → `calculate_collapse_rating(...)`
- `CasingDesignEngine.CASING_GRADES` → `CASING_GRADES`
- Same for all other internal calls

**Step 2: Write facade __init__.py**

```python
"""Casing Design Engine -- backward-compatible facade.

Package split from monolithic casing_design_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.casing_design_engine import CasingDesignEngine
"""
from .constants import CASING_GRADES, CASING_CATALOG, DEFAULT_SF
from .loads import calculate_burst_load, calculate_collapse_load, calculate_tension_load
from .ratings import calculate_burst_rating, calculate_collapse_rating, derate_for_temperature
from .corrections import calculate_biaxial_correction, calculate_triaxial_vme
from .grade_selection import select_casing_grade, lookup_casing_catalog
from .safety_factors import calculate_safety_factors
from .scenarios import calculate_burst_scenarios, calculate_collapse_scenarios
from .running_loads import calculate_running_loads
from .wear import apply_wear_allowance
from .pipeline import calculate_full_casing_design, generate_recommendations


class CasingDesignEngine:
    """Backward-compatible facade -- delegates all methods to submodules."""

    # Constants (re-exported as class attributes)
    CASING_GRADES = CASING_GRADES
    CASING_CATALOG = CASING_CATALOG
    DEFAULT_SF = DEFAULT_SF

    # loads
    calculate_burst_load = staticmethod(calculate_burst_load)
    calculate_collapse_load = staticmethod(calculate_collapse_load)
    calculate_tension_load = staticmethod(calculate_tension_load)

    # ratings
    calculate_burst_rating = staticmethod(calculate_burst_rating)
    calculate_collapse_rating = staticmethod(calculate_collapse_rating)
    derate_for_temperature = staticmethod(derate_for_temperature)

    # corrections
    calculate_biaxial_correction = staticmethod(calculate_biaxial_correction)
    calculate_triaxial_vme = staticmethod(calculate_triaxial_vme)

    # grade selection
    select_casing_grade = staticmethod(select_casing_grade)
    lookup_casing_catalog = staticmethod(lookup_casing_catalog)

    # safety factors
    calculate_safety_factors = staticmethod(calculate_safety_factors)

    # scenarios
    calculate_burst_scenarios = staticmethod(calculate_burst_scenarios)
    calculate_collapse_scenarios = staticmethod(calculate_collapse_scenarios)

    # running loads
    calculate_running_loads = staticmethod(calculate_running_loads)

    # wear
    apply_wear_allowance = staticmethod(apply_wear_allowance)

    # pipeline
    calculate_full_casing_design = staticmethod(calculate_full_casing_design)
    generate_recommendations = staticmethod(generate_recommendations)

    # combination string (stays in pipeline or grade_selection)
    design_combination_string = staticmethod(
        __import__('orchestrator.casing_design_engine.grade_selection', fromlist=['design_combination_string']).design_combination_string
    )
```

**NOTE:** `design_combination_string()` (lines 1004-1112) should be extracted to `grade_selection.py` as well. Include it in Step 1 of this task alongside `select_casing_grade` and `lookup_casing_catalog`.

For the `__init__.py` facade, use a simpler approach:

```python
from .grade_selection import select_casing_grade, lookup_casing_catalog, design_combination_string
# ...
class CasingDesignEngine:
    # ...
    design_combination_string = staticmethod(design_combination_string)
```

**Step 3: Commit**

```bash
git add orchestrator/casing_design_engine/pipeline.py orchestrator/casing_design_engine/__init__.py
git commit -m "refactor(casing): create pipeline.py and facade __init__.py"
```

---

### Task 5: Remove old monolithic file + verify all tests pass

**Files:**
- Delete: `orchestrator/casing_design_engine.py` (the old monolithic file)

**Step 1: Run all existing casing tests BEFORE deletion (baseline)**

```bash
cd /Users/antvar/Downloads/petroleum-expert-system && python -m pytest tests/unit/test_casing_design_engine.py tests/validation/test_validate_casing_design.py tests/unit/test_elite_fase6_casing.py -v
```

Expected: ALL PASS (this confirms the old file works).

**Step 2: Verify the new package imports work**

```bash
python -c "from orchestrator.casing_design_engine import CasingDesignEngine; print(sorted([m for m in dir(CasingDesignEngine) if not m.startswith('_')]))"
```

Expected: List of all method names matching the old class.

**Step 3: Delete the old monolithic file**

```bash
rm orchestrator/casing_design_engine.py
```

**Step 4: Run ALL casing tests**

```bash
python -m pytest tests/unit/test_casing_design_engine.py tests/validation/test_validate_casing_design.py tests/unit/test_elite_fase6_casing.py -v
```

Expected: ALL PASS — identical results to Step 1.

**Step 5: Run the cross-engine and calculations routes import check**

```bash
python -c "from routes.modules.casing_design import router; print('casing route OK')"
python -c "from routes.cross_engine import router; print('cross_engine OK')"
python -c "from routes.calculations import router; print('calculations OK')"
```

Expected: All print OK with no import errors.

**Step 6: Run full test suite**

```bash
python -m pytest tests/ -x --tb=short -q
```

Expected: ALL PASS.

**Step 7: Commit**

```bash
git rm orchestrator/casing_design_engine.py
git add -A
git commit -m "refactor(casing): remove monolithic file, package migration complete"
```

---

## Phase 2: Critical Fixes (Tasks 6–7)

---

### Task 6: Fix collapse boundary calculations (Audit #1 — CRITICAL)

**Problem:** The transition-elastic boundary `dt_te` in `calculate_collapse_rating()` has a buggy formula that produces absurd values (e.g., 53,000+ for N80). The `sorted()` workaround masks the error. Additionally, the benchmark validates against the engine's own value (7461 psi for 9-5/8 N80) instead of the published API value (~4760 psi).

**Files:**
- Modify: `orchestrator/casing_design_engine/ratings.py`
- Modify: `tests/validation/benchmark_data.py`
- Modify: `tests/validation/test_validate_casing_design.py`
- Test: `tests/unit/test_casing_design_engine.py`

**Step 1: Add benchmark test with real API TR 5C3 published values**

Add to `tests/validation/test_validate_casing_design.py`:

```python
class TestCollapseZoneClassification:
    """Validate collapse zone boundaries against API TR 5C3 published tables."""

    def test_9625_n80_collapse_zone_is_plastic(self):
        """9-5/8 47# N80 (D/t=20.39) should be in Plastic zone per API TR 5C3."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert result["collapse_zone"] == "Plastic", (
            f"Expected Plastic for D/t={result['dt_ratio']}, got {result['collapse_zone']}"
        )

    def test_9625_n80_collapse_matches_api(self):
        """API TR 5C3 published collapse for 9-5/8 47# N80 = 4760 psi (±10%)."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000)
        assert 4280 <= result["collapse_rating_psi"] <= 5240, (
            f"Collapse {result['collapse_rating_psi']} outside API range 4760 ±10%"
        )

    def test_7_29_p110_collapse_matches_api(self):
        """API TR 5C3 published collapse for 7 29# P110 = 10680 psi (±10%)."""
        result = CasingDesignEngine.calculate_collapse_rating(7.0, 0.408, 110000)
        assert 9610 <= result["collapse_rating_psi"] <= 11750, (
            f"Collapse {result['collapse_rating_psi']} outside API range 10680 ±10%"
        )

    def test_thin_wall_elastic_zone(self):
        """Very thin wall (D/t > 40) should be Elastic or Transition zone."""
        result = CasingDesignEngine.calculate_collapse_rating(9.625, 0.200, 55000)
        assert result["collapse_zone"] in ("Transition", "Elastic"), (
            f"D/t={result['dt_ratio']} should be Transition/Elastic, got {result['collapse_zone']}"
        )

    def test_thick_wall_yield_zone(self):
        """Very thick wall (D/t < 12) should be Yield zone."""
        result = CasingDesignEngine.calculate_collapse_rating(7.0, 0.700, 80000)
        assert result["collapse_zone"] == "Yield", (
            f"D/t={result['dt_ratio']} should be Yield, got {result['collapse_zone']}"
        )
```

**Step 2: Run tests to verify they FAIL (current boundaries are wrong)**

```bash
python -m pytest tests/validation/test_validate_casing_design.py::TestCollapseZoneClassification -v
```

Expected: `test_9625_n80_collapse_matches_api` FAILS (current value ~7461 vs expected ~4760).

**Step 3: Fix `calculate_collapse_rating()` in ratings.py**

Replace the boundary computation. The key fix is the transition-elastic boundary formula. The correct API TR 5C3 approach:

```python
def calculate_collapse_rating(
    casing_od_in: float,
    wall_thickness_in: float,
    yield_strength_psi: float,
) -> Dict[str, Any]:
    """
    Calculate collapse rating per API TR 5C3 (ISO 10400).

    Four collapse regimes based on D/t ratio with corrected boundary formulas.
    """
    if casing_od_in <= 0 or wall_thickness_in <= 0:
        return {"error": "Invalid dimensions"}

    dt = casing_od_in / wall_thickness_in
    yp = yield_strength_psi

    # API 5C3 empirical coefficients (functions of yield strength)
    A = 2.8762 + 0.10679e-4 * yp + 0.21301e-10 * yp ** 2 - 0.53132e-16 * yp ** 3
    B = 0.026233 + 0.50609e-6 * yp
    C = -465.93 + 0.030867 * yp - 0.10483e-7 * yp ** 2 + 0.36989e-13 * yp ** 3

    # Transition coefficients F, G (API TR 5C3)
    ratio_3ba = 3.0 * B / A
    denom = 2.0 + B / A
    F = 46.95e6 * (ratio_3ba / denom) ** 3
    G = F * B / A

    # ── Boundary D/t ratios (API TR 5C3) ──

    # Yield-Plastic boundary: equate yield and plastic formulas
    try:
        disc = (A - 2) ** 2 + 8 * (B + C / yp)
        if disc < 0:
            dt_yp = 15.0
        else:
            dt_yp = (math.sqrt(disc) + (A - 2)) / (2 * (B + C / yp))
    except (ValueError, ZeroDivisionError):
        dt_yp = 15.0

    # Plastic-Transition boundary: equate plastic and transition formulas
    try:
        dt_pt = yp * (A - F) / (C + yp * (B - G))
    except ZeroDivisionError:
        dt_pt = 25.0

    # Transition-Elastic boundary: solve numerically
    # At boundary: Yp*(F/x - G) = 46.95e6 / (x*(x-1)^2)
    # Use bisection between dt_pt and a reasonable upper limit
    dt_te = _find_transition_elastic_boundary(yp, F, G, dt_pt)

    # Validate boundary ordering
    if not (dt_yp <= dt_pt <= dt_te):
        # Fallback: use boundaries but ensure order
        dt_yp, dt_pt, dt_te = sorted([dt_yp, dt_pt, dt_te])

    # Determine zone and calculate rating
    if dt <= dt_yp:
        zone = "Yield"
        p_collapse = 2.0 * yp * ((dt - 1) / dt ** 2)
    elif dt <= dt_pt:
        zone = "Plastic"
        p_collapse = yp * (A / dt - B) - C
    elif dt <= dt_te:
        zone = "Transition"
        p_collapse = yp * (F / dt - G)
    else:
        zone = "Elastic"
        p_collapse = 46.95e6 / (dt * (dt - 1) ** 2)

    p_collapse = max(p_collapse, 0.0)

    return {
        "collapse_rating_psi": round(p_collapse, 0),
        "collapse_zone": zone,
        "dt_ratio": round(dt, 2),
        "yield_strength_psi": yield_strength_psi,
        "boundaries": {
            "yield_plastic": round(dt_yp, 2),
            "plastic_transition": round(dt_pt, 2),
            "transition_elastic": round(dt_te, 2),
        },
    }


def _find_transition_elastic_boundary(
    yp: float, F: float, G: float, dt_pt: float,
    tol: float = 0.01, max_iter: int = 50,
) -> float:
    """
    Find D/t where transition and elastic collapse formulas intersect.

    Uses bisection method:
      f(x) = Yp*(F/x - G) - 46.95e6 / (x*(x-1)^2) = 0
    """
    def residual(x: float) -> float:
        if x <= 1:
            return 1e12
        return yp * (F / x - G) - 46.95e6 / (x * (x - 1) ** 2)

    # Search range: start from dt_pt, go up to reasonable limit
    lo = max(dt_pt, 5.0)
    hi = 80.0

    # Ensure bracket: residual should change sign
    f_lo = residual(lo)
    f_hi = residual(hi)

    if f_lo * f_hi > 0:
        # No sign change — return geometric estimate
        return max(lo * 1.5, 30.0)

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = residual(mid)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return mid
        if f_mid * f_lo < 0:
            hi = mid
        else:
            lo = mid
            f_lo = f_mid

    return (lo + hi) / 2.0
```

**Step 4: Run tests to verify they PASS**

```bash
python -m pytest tests/validation/test_validate_casing_design.py tests/unit/test_casing_design_engine.py -v
```

Expected: ALL PASS — including new zone classification tests and existing tests.

**Step 5: Update benchmark data for correct collapse values**

In `tests/validation/benchmark_data.py`, update:

```python
API_5C3_CASING_9_625_N80 = {
    # ...
    "expected": {
        "burst_psi": {"value": 6870, "tolerance_pct": 5},
        "collapse_psi": {"value": 4760, "tolerance_pct": 10},  # was 7461 (yield-zone only)
    },
}
```

**Step 6: Run all validation tests**

```bash
python -m pytest tests/validation/test_validate_casing_design.py -v
```

Expected: ALL PASS.

**Step 7: Commit**

```bash
git add orchestrator/casing_design_engine/ratings.py tests/validation/benchmark_data.py tests/validation/test_validate_casing_design.py
git commit -m "fix(casing): correct API 5C3 collapse boundaries with numerical solver"
```

---

### Task 7: Fix hoop stress with Lamé equations (Audit #2 — HIGH)

**Problem:** The triaxial VME check in `pipeline.py` uses a rough hoop stress approximation (`max_collapse * (D/t) / 2`). The correct approach is Lamé's thick-walled cylinder equations using actual internal and external pressures.

**Files:**
- Modify: `orchestrator/casing_design_engine/corrections.py`
- Modify: `orchestrator/casing_design_engine/pipeline.py`
- Modify: `tests/unit/test_casing_design_engine.py`

**Step 1: Add failing test for Lamé hoop stress**

Add to `tests/unit/test_casing_design_engine.py`:

```python
class TestLameHoopStress:
    """Validate Lamé thick-wall hoop stress calculation."""

    def test_external_pressure_only(self, engine):
        """External pressure only → hoop stress negative (compressive) at inner wall."""
        result = engine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=0, p_external_psi=5000,
        )
        assert result["hoop_inner_psi"] < 0  # compressive

    def test_internal_pressure_only(self, engine):
        """Internal pressure only → hoop stress positive (tensile) at inner wall."""
        result = engine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=5000, p_external_psi=0,
        )
        assert result["hoop_inner_psi"] > 0  # tensile

    def test_known_value(self, engine):
        """Verify against manual Lamé calculation for 9-5/8 casing."""
        # ro=4.8125, ri=4.3405
        # P_ext=5000, P_int=0
        # sigma_h(ri) = (Po*ro² - Pi*ri²)/(ro²-ri²) - ri²*ro²*(Po-Pi)/(ri²*(ro²-ri²))
        #             = (5000*4.8125² - 0) / (4.8125²-4.3405²) - 4.3405²*4.8125²*5000 / (4.3405²*(4.8125²-4.3405²))
        result = engine.calculate_hoop_stress_lame(
            od_in=9.625, id_in=8.681,
            p_internal_psi=0, p_external_psi=5000,
        )
        # Expected: approximately -10,820 psi (compressive) at inner wall
        assert -12000 < result["hoop_inner_psi"] < -9000
```

**Step 2: Run tests to verify they FAIL**

```bash
python -m pytest tests/unit/test_casing_design_engine.py::TestLameHoopStress -v
```

Expected: FAIL — `calculate_hoop_stress_lame` does not exist yet.

**Step 3: Add `calculate_hoop_stress_lame()` to corrections.py**

```python
def calculate_hoop_stress_lame(
    od_in: float,
    id_in: float,
    p_internal_psi: float,
    p_external_psi: float,
) -> Dict[str, Any]:
    """
    Lamé thick-walled cylinder hoop stress at inner and outer wall.

    sigma_h(r) = (Pi*ri² - Po*ro²)/(ro²-ri²) + ri²*ro²*(Pi-Po)/(r²*(ro²-ri²))

    At inner wall (r=ri): maximum magnitude for collapse
    At outer wall (r=ro): maximum magnitude for burst

    References:
    - Timoshenko: Theory of Elasticity, thick cylinder analysis
    - API TR 5C3 Annex B: Stress analysis of casing
    """
    ro = od_in / 2.0
    ri = id_in / 2.0

    if ro <= ri or ri <= 0:
        return {"error": "Invalid dimensions: OD must be > ID > 0"}

    ro2 = ro ** 2
    ri2 = ri ** 2
    diff = ro2 - ri2

    # Hoop stress at inner wall (r = ri)
    hoop_inner = (p_internal_psi * ri2 - p_external_psi * ro2) / diff + \
                 ri2 * ro2 * (p_internal_psi - p_external_psi) / (ri2 * diff)

    # Hoop stress at outer wall (r = ro)
    hoop_outer = (p_internal_psi * ri2 - p_external_psi * ro2) / diff + \
                 ri2 * ro2 * (p_internal_psi - p_external_psi) / (ro2 * diff)

    # Radial stress at inner wall = -P_internal, at outer wall = -P_external
    radial_inner = -p_internal_psi
    radial_outer = -p_external_psi

    return {
        "hoop_inner_psi": round(hoop_inner, 0),
        "hoop_outer_psi": round(hoop_outer, 0),
        "radial_inner_psi": round(radial_inner, 0),
        "radial_outer_psi": round(radial_outer, 0),
    }
```

**Step 4: Update __init__.py facade to expose `calculate_hoop_stress_lame`**

In `__init__.py`:

```python
from .corrections import calculate_biaxial_correction, calculate_triaxial_vme, calculate_hoop_stress_lame

class CasingDesignEngine:
    # ...
    calculate_hoop_stress_lame = staticmethod(calculate_hoop_stress_lame)
```

**Step 5: Update pipeline.py to use Lamé hoop stress**

In `calculate_full_casing_design()`, replace the old approximation (line ~1331):

FROM:
```python
hoop_stress = max_collapse * (casing_od_in / wall_thickness_in) / 2 if wall_thickness_in > 0 else 0
```

TO:
```python
from .corrections import calculate_hoop_stress_lame

# Use Lamé equations for accurate hoop stress at maximum collapse depth
lame = calculate_hoop_stress_lame(
    od_in=casing_od_in, id_in=casing_id_in,
    p_internal_psi=0.0,  # worst case: evacuated casing
    p_external_psi=max_collapse,
)
hoop_stress = lame.get("hoop_inner_psi", 0)
```

**Step 6: Run all tests**

```bash
python -m pytest tests/unit/test_casing_design_engine.py tests/validation/test_validate_casing_design.py -v
```

Expected: ALL PASS.

**Step 7: Commit**

```bash
git add orchestrator/casing_design_engine/corrections.py orchestrator/casing_design_engine/pipeline.py orchestrator/casing_design_engine/__init__.py tests/unit/test_casing_design_engine.py
git commit -m "fix(casing): use Lamé thick-wall hoop stress for triaxial VME check"
```

---

## Phase 3: HIGH Priority Improvements (Tasks 8–10)

---

### Task 8: Add thermal axial load + integrate drag into main flow (Audit #5, #7)

**Problem:** `calculate_full_casing_design()` uses `calculate_tension_load()` which lacks drag from deviated wells (audit #5) and thermal expansion (audit #7). The separate `calculate_running_loads()` handles drag but isn't integrated.

**Files:**
- Modify: `orchestrator/casing_design_engine/running_loads.py`
- Modify: `orchestrator/casing_design_engine/pipeline.py`
- Test: `tests/unit/test_casing_design_engine.py`

**Step 1: Add `calculate_thermal_axial_load()` to running_loads.py**

```python
# Steel properties
STEEL_E_PSI = 30e6           # Young's modulus (psi)
STEEL_ALPHA_F = 6.9e-6       # Thermal expansion coefficient (/°F)


def calculate_thermal_axial_load(
    casing_od_in: float,
    casing_id_in: float,
    surface_temp_f: float = 80.0,
    bottomhole_temp_f: float = 250.0,
    cement_temp_f: float = 150.0,
    locked_in: bool = True,
) -> Dict[str, Any]:
    """
    Calculate thermal axial load from temperature change after cement sets.

    When casing is cemented and later heated (production) or cooled (injection),
    the restrained thermal expansion/contraction creates axial stress:

        F_thermal = E * A * alpha * delta_T

    References:
    - API TR 5C3 Annex G: Temperature effects on casing
    - Bourgoyne et al.: Applied Drilling Engineering, Ch. 7
    """
    if not locked_in:
        return {
            "thermal_load_lbs": 0,
            "thermal_stress_psi": 0,
            "delta_t_f": 0,
            "note": "Casing free to expand — no thermal load",
        }

    area = math.pi / 4.0 * (casing_od_in ** 2 - casing_id_in ** 2)

    # Average temperature change from cement-set temperature
    delta_t = bottomhole_temp_f - cement_temp_f

    f_thermal = STEEL_E_PSI * area * STEEL_ALPHA_F * delta_t
    stress = f_thermal / area if area > 0 else 0

    return {
        "thermal_load_lbs": round(abs(f_thermal), 0),
        "thermal_stress_psi": round(abs(stress), 0),
        "delta_t_f": round(delta_t, 1),
        "load_type": "compressive" if delta_t > 0 else "tensile",
        "note": "Heating → compressive, Cooling → tensile",
    }
```

**Step 2: Add tests**

```python
class TestThermalAxialLoad:
    def test_heating_produces_compressive(self, engine):
        result = engine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681,
            surface_temp_f=80, bottomhole_temp_f=300, cement_temp_f=150,
        )
        assert result["load_type"] == "compressive"
        assert result["thermal_load_lbs"] > 0

    def test_no_delta_t_no_load(self, engine):
        result = engine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681,
            surface_temp_f=80, bottomhole_temp_f=150, cement_temp_f=150,
        )
        assert result["thermal_load_lbs"] == 0

    def test_free_casing_no_load(self, engine):
        result = engine.calculate_thermal_axial_load(
            casing_od_in=9.625, casing_id_in=8.681, locked_in=False,
        )
        assert result["thermal_load_lbs"] == 0
```

**Step 3: Update facade to expose new function**

Add to `__init__.py`:

```python
from .running_loads import calculate_running_loads, calculate_thermal_axial_load

class CasingDesignEngine:
    # ...
    calculate_thermal_axial_load = staticmethod(calculate_thermal_axial_load)
```

**Step 4: Run tests**

```bash
python -m pytest tests/unit/test_casing_design_engine.py -v
```

Expected: ALL PASS.

**Step 5: Commit**

```bash
git add orchestrator/casing_design_engine/running_loads.py orchestrator/casing_design_engine/__init__.py tests/unit/test_casing_design_engine.py
git commit -m "feat(casing): add thermal axial load calculation (audit #7)"
```

---

### Task 9: Add connection verification (Audit #6 — HIGH)

**Problem:** No connection type or torque verification exists. In real wells, the connection is often the weak link.

**Files:**
- Create: `orchestrator/casing_design_engine/connections.py`
- Modify: `orchestrator/casing_design_engine/__init__.py`
- Test: `tests/unit/test_casing_design_engine.py`

**Step 1: Create connections.py**

```python
"""
Casing connection verification — API 5B thread performance.

References:
- API 5B: Threading, gauging, and thread inspection of casing, tubing, and line pipe
- API 5C3: Performance properties of casing, tubing, and drill pipe
"""
from typing import Dict, Any, Optional

# Connection performance catalog (API 5B/5C3)
# Values: tension efficiency (% of pipe body), internal pressure efficiency, external pressure efficiency
CONNECTION_CATALOG: Dict[str, Dict[str, Any]] = {
    "STC": {
        "name": "Short Thread & Coupling",
        "tension_efficiency": 0.60,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 10000,
        "notes": "Standard API, not gas-tight",
    },
    "LTC": {
        "name": "Long Thread & Coupling",
        "tension_efficiency": 0.70,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 10000,
        "notes": "Standard API, not gas-tight",
    },
    "BTC": {
        "name": "Buttress Thread & Coupling",
        "tension_efficiency": 0.80,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 15000,
        "notes": "Higher tension than STC/LTC, not gas-tight",
    },
    "PREMIUM": {
        "name": "Premium Connection (Generic)",
        "tension_efficiency": 0.95,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 20000,
        "notes": "Metal-to-metal seal, gas-tight",
    },
}


def verify_connection(
    connection_type: str,
    pipe_body_yield_lbs: float,
    burst_rating_psi: float,
    collapse_rating_psi: float,
    applied_tension_lbs: float,
    applied_burst_psi: float,
    applied_collapse_psi: float,
    sf_tension: float = 1.60,
    sf_burst: float = 1.10,
) -> Dict[str, Any]:
    """
    Verify connection performance against applied loads.

    Connection tension rating = tension_efficiency * pipe_body_yield
    Connection burst/collapse = burst/collapse_efficiency * pipe_rating

    Returns PASS/FAIL for each criterion.
    """
    conn = CONNECTION_CATALOG.get(connection_type.upper())
    if conn is None:
        available = list(CONNECTION_CATALOG.keys())
        return {"error": f"Unknown connection type '{connection_type}'. Available: {available}"}

    # Connection ratings
    conn_tension = conn["tension_efficiency"] * pipe_body_yield_lbs
    conn_burst = conn["burst_efficiency"] * burst_rating_psi
    conn_collapse = conn["collapse_efficiency"] * collapse_rating_psi

    # Safety factors
    sf_t = conn_tension / applied_tension_lbs if applied_tension_lbs > 0 else 999
    sf_b = conn_burst / applied_burst_psi if applied_burst_psi > 0 else 999
    sf_c = conn_collapse / applied_collapse_psi if applied_collapse_psi > 0 else 999

    passes_tension = sf_t >= sf_tension
    passes_burst = sf_b >= sf_burst
    passes_all = passes_tension and passes_burst

    # Check if connection is the weak link
    is_weak_link = conn_tension < pipe_body_yield_lbs * 0.95

    return {
        "connection_type": connection_type.upper(),
        "connection_name": conn["name"],
        "tension_rating_lbs": round(conn_tension, 0),
        "tension_sf": round(sf_t, 2),
        "passes_tension": passes_tension,
        "burst_rating_psi": round(conn_burst, 0),
        "burst_sf": round(sf_b, 2),
        "passes_burst": passes_burst,
        "passes_all": passes_all,
        "is_weak_link": is_weak_link,
        "efficiency": conn["tension_efficiency"],
        "gas_tight": "gas-tight" in conn.get("notes", ""),
        "notes": conn["notes"],
        "alerts": [
            f"Connection is weak link — tension efficiency {conn['tension_efficiency']*100:.0f}%"
        ] if is_weak_link else [],
    }
```

**Step 2: Add tests**

```python
class TestConnectionVerification:
    def test_stc_lower_tension_than_body(self, engine):
        result = engine.verify_connection(
            connection_type="STC",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert result["tension_rating_lbs"] == 600000  # 60% of 1M
        assert result["is_weak_link"] is True

    def test_premium_passes_all(self, engine):
        result = engine.verify_connection(
            connection_type="PREMIUM",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert result["passes_all"] is True
        assert result["gas_tight"] is True

    def test_unknown_connection_error(self, engine):
        result = engine.verify_connection(
            connection_type="XYZ",
            pipe_body_yield_lbs=1000000,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            applied_tension_lbs=400000,
            applied_burst_psi=4000, applied_collapse_psi=3000,
        )
        assert "error" in result
```

**Step 3: Update facade**

```python
from .connections import verify_connection, CONNECTION_CATALOG

class CasingDesignEngine:
    CONNECTION_CATALOG = CONNECTION_CATALOG
    verify_connection = staticmethod(verify_connection)
```

**Step 4: Run tests, commit**

```bash
python -m pytest tests/unit/test_casing_design_engine.py -v
git add orchestrator/casing_design_engine/connections.py orchestrator/casing_design_engine/__init__.py tests/unit/test_casing_design_engine.py
git commit -m "feat(casing): add connection verification with API 5B catalog (audit #6)"
```

---

### Task 10: Add safety factor vs depth profile (Audit #10 — MEDIUM)

**Problem:** Safety factors are only computed at the worst-case point. A depth-wise profile (like Landmark WellPlan) is needed for combination string design and professional visualization.

**Files:**
- Modify: `orchestrator/casing_design_engine/safety_factors.py`
- Modify: `orchestrator/casing_design_engine/__init__.py`
- Test: `tests/unit/test_casing_design_engine.py`

**Step 1: Add `calculate_sf_vs_depth()` to safety_factors.py**

```python
def calculate_sf_vs_depth(
    burst_profile: list,
    collapse_profile: list,
    burst_rating_psi: float,
    collapse_rating_psi: float,
    tension_at_surface_lbs: float,
    tension_rating_lbs: float,
    casing_weight_ppf: float,
    mud_weight_ppg: float,
    casing_length_ft: float,
) -> Dict[str, Any]:
    """
    Calculate burst, collapse, and tension safety factors at each depth point.

    Produces a depth-wise SF profile for visualization (similar to Landmark WellPlan).

    burst_profile/collapse_profile: list of {"tvd_ft": float, "burst_load_psi": float, ...}
    """
    bf = 1.0 - mud_weight_ppg / 65.4

    sf_profile = []
    for i, bp in enumerate(burst_profile):
        depth = bp.get("tvd_ft", 0)
        burst_load = abs(bp.get("burst_load_psi", 0))
        collapse_load = 0
        if i < len(collapse_profile):
            collapse_load = abs(collapse_profile[i].get("collapse_load_psi", 0))

        # Tension decreases with depth (less string below)
        remaining = max(casing_length_ft - depth, 0)
        tension_at_depth = casing_weight_ppf * remaining * bf
        # At surface, add full string weight
        if depth == 0:
            tension_at_depth = tension_at_surface_lbs

        sf_b = burst_rating_psi / burst_load if burst_load > 0 else 99.0
        sf_c = collapse_rating_psi / collapse_load if collapse_load > 0 else 99.0
        sf_t = tension_rating_lbs / tension_at_depth if tension_at_depth > 0 else 99.0

        sf_profile.append({
            "tvd_ft": round(depth, 0),
            "sf_burst": round(min(sf_b, 99.0), 2),
            "sf_collapse": round(min(sf_c, 99.0), 2),
            "sf_tension": round(min(sf_t, 99.0), 2),
            "governing_sf": round(min(sf_b, sf_c, sf_t, 99.0), 2),
        })

    # Find minimum SF and its depth
    min_point = min(sf_profile, key=lambda p: p["governing_sf"])

    return {
        "profile": sf_profile,
        "min_sf": min_point["governing_sf"],
        "min_sf_depth_ft": min_point["tvd_ft"],
        "num_points": len(sf_profile),
    }
```

**Step 2: Add tests**

```python
class TestSFvsDepth:
    def test_profile_length_matches_input(self, engine):
        burst = [{"tvd_ft": i * 500, "burst_load_psi": 3000 - i * 100} for i in range(20)]
        collapse = [{"tvd_ft": i * 500, "collapse_load_psi": i * 200} for i in range(20)]
        result = engine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        assert len(result["profile"]) == 20

    def test_sf_values_positive(self, engine):
        burst = [{"tvd_ft": 0, "burst_load_psi": 3000}]
        collapse = [{"tvd_ft": 0, "collapse_load_psi": 2000}]
        result = engine.calculate_sf_vs_depth(
            burst_profile=burst, collapse_profile=collapse,
            burst_rating_psi=6870, collapse_rating_psi=4760,
            tension_at_surface_lbs=500000, tension_rating_lbs=1200000,
            casing_weight_ppf=47.0, mud_weight_ppg=10.5, casing_length_ft=10000,
        )
        assert result["profile"][0]["sf_burst"] > 0
        assert result["min_sf"] > 0
```

**Step 3: Update facade, run tests, commit**

```bash
python -m pytest tests/unit/test_casing_design_engine.py -v
git add orchestrator/casing_design_engine/safety_factors.py orchestrator/casing_design_engine/__init__.py tests/unit/test_casing_design_engine.py
git commit -m "feat(casing): add safety factor vs depth profile (audit #10)"
```

---

## Verification Checklist

After all 10 tasks:

1. **Directory structure matches target:**
   ```bash
   ls orchestrator/casing_design_engine/
   # Should show: __init__.py constants.py loads.py ratings.py corrections.py
   #              grade_selection.py safety_factors.py scenarios.py
   #              running_loads.py connections.py wear.py pipeline.py
   ```

2. **Old monolithic file is gone:**
   ```bash
   test ! -f orchestrator/casing_design_engine.py && echo "GONE"
   ```

3. **All imports still work:**
   ```bash
   python -c "from orchestrator.casing_design_engine import CasingDesignEngine; r = CasingDesignEngine.calculate_full_casing_design(); print(r['summary']['overall_status'])"
   ```

4. **All tests pass:**
   ```bash
   python -m pytest tests/unit/test_casing_design_engine.py tests/validation/test_validate_casing_design.py tests/unit/test_elite_fase6_casing.py -v
   ```

5. **Collapse values match API TR 5C3:**
   ```bash
   python -c "from orchestrator.casing_design_engine import CasingDesignEngine; r = CasingDesignEngine.calculate_collapse_rating(9.625, 0.472, 80000); print(f'Zone: {r[\"collapse_zone\"]}, Rating: {r[\"collapse_rating_psi\"]} psi')"
   # Expected: Zone: Plastic, Rating: ~4760 psi
   ```

6. **New capabilities available:**
   ```bash
   python -c "from orchestrator.casing_design_engine import CasingDesignEngine; print(hasattr(CasingDesignEngine, 'calculate_hoop_stress_lame'), hasattr(CasingDesignEngine, 'calculate_thermal_axial_load'), hasattr(CasingDesignEngine, 'verify_connection'), hasattr(CasingDesignEngine, 'calculate_sf_vs_depth'))"
   # Expected: True True True True
   ```
