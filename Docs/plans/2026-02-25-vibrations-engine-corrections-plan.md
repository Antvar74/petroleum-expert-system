# Vibrations Engine Root-Cause Corrections — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 6 verified physics bugs in the vibrations engine across 4 incremental phases, starting with a modular restructure.

**Architecture:** Refactor monolithic `orchestrator/vibrations_engine.py` (1,456 lines) into a package of 9 focused modules following the `shot_efficiency_engine/` pattern. Then apply physics corrections to individual modules. Finally expose new parameters to schema/frontend.

**Tech Stack:** Python 3 (engine), Pydantic (schemas), React/TypeScript (frontend), pytest (tests)

**Design doc:** `Docs/plans/2026-02-25-vibrations-engine-corrections-design.md`

---

## Phase 0: Modular Restructure (Zero Functional Changes)

### Task 0.1: Create package directory and `__init__.py`

**Files:**
- Create: `orchestrator/vibrations_engine/__init__.py`

**Step 1: Create the package directory**

```bash
mkdir -p orchestrator/vibrations_engine
```

**Step 2: Write `__init__.py` (backward-compatible facade)**

Follow the exact pattern from `orchestrator/shot_efficiency_engine/__init__.py`.
Re-export all public methods as `staticmethod` on a `VibrationsEngine` class so that every existing import (`from orchestrator.vibrations_engine import VibrationsEngine`) continues working.

```python
"""Vibrations & Stability Engine -- backward-compatible facade.

Package split from monolithic vibrations_engine.py.
All existing imports continue to work unchanged.
"""
from .critical_speeds import (
    calculate_critical_rpm_axial,
    calculate_critical_rpm_lateral,
    calculate_critical_rpm_lateral_multi,
)
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
from .stability import (
    calculate_stability_index,
    generate_vibration_map,
    calculate_vibration_map_3d,
)
from .bit_excitation import calculate_bit_excitation, check_resonance
from .stabilizers import optimize_stabilizer_placement
from .fatigue import calculate_fatigue_damage
from .pipeline import calculate_full_vibration_analysis

# Steel constants (shared across submodules)
STEEL_E = 30e6          # Young's modulus (psi)
STEEL_DENSITY = 490.0   # lb/ft³
GRAVITY = 32.174        # ft/s²


class VibrationsEngine:
    """Backward-compatible facade -- delegates all methods to submodules."""

    STEEL_E = STEEL_E
    STEEL_DENSITY = STEEL_DENSITY
    GRAVITY = GRAVITY

    calculate_critical_rpm_axial = staticmethod(calculate_critical_rpm_axial)
    calculate_critical_rpm_lateral = staticmethod(calculate_critical_rpm_lateral)
    calculate_critical_rpm_lateral_multi = staticmethod(calculate_critical_rpm_lateral_multi)
    calculate_stick_slip_severity = staticmethod(calculate_stick_slip_severity)
    calculate_mse = staticmethod(calculate_mse)
    calculate_stability_index = staticmethod(calculate_stability_index)
    generate_vibration_map = staticmethod(generate_vibration_map)
    calculate_vibration_map_3d = staticmethod(calculate_vibration_map_3d)
    calculate_bit_excitation = staticmethod(calculate_bit_excitation)
    check_resonance = staticmethod(check_resonance)
    optimize_stabilizer_placement = staticmethod(optimize_stabilizer_placement)
    calculate_fatigue_damage = staticmethod(calculate_fatigue_damage)
    calculate_full_vibration_analysis = staticmethod(calculate_full_vibration_analysis)
```

**Step 3: Run tests to verify nothing is imported yet (expected: ImportError)**

```bash
pytest tests/unit/test_vibrations_engine.py -x -q 2>&1 | head -5
```

Expected: Tests still pass because the old monolithic file still exists and Python finds it first.

---

### Task 0.2: Extract `critical_speeds.py`

**Files:**
- Create: `orchestrator/vibrations_engine/critical_speeds.py`
- Source lines: `orchestrator/vibrations_engine.py:39-191` and `695-922`

**Step 1: Create `critical_speeds.py`**

Extract these 3 functions from the monolithic file:
- `calculate_critical_rpm_axial` (lines 39-116)
- `calculate_critical_rpm_lateral` (lines 119-191)
- `calculate_critical_rpm_lateral_multi` (lines 695-922, includes nested `_transfer_matrix_product` and `_boundary_det`)

Each function becomes a module-level function (remove `@staticmethod`). Add `import math` and `from typing import Dict, Any, List, Optional, Tuple` at the top. Import constants from the package:

```python
"""Critical speed calculations: axial, lateral, and multi-component BHA lateral."""
import math
from typing import Dict, Any, List, Optional, Tuple

# Steel constants
STEEL_E = 30e6
STEEL_DENSITY = 490.0
GRAVITY = 32.174
```

Copy each function body exactly as-is. Replace `VibrationsEngine.STEEL_E` references with module-level `STEEL_E`, etc.

---

### Task 0.3: Extract `stick_slip.py`

**Files:**
- Create: `orchestrator/vibrations_engine/stick_slip.py`
- Source lines: `orchestrator/vibrations_engine.py:194-296`

**Step 1: Create `stick_slip.py`**

Extract `calculate_stick_slip_severity` (lines 194-296). Module-level function, `import math`, typing imports.

---

### Task 0.4: Extract `mse.py`

**Files:**
- Create: `orchestrator/vibrations_engine/mse.py`
- Source lines: `orchestrator/vibrations_engine.py:299-376`

**Step 1: Create `mse.py`**

Extract `calculate_mse` (lines 299-376). Module-level function.

---

### Task 0.5: Extract `stability.py`

**Files:**
- Create: `orchestrator/vibrations_engine/stability.py`
- Source lines: `orchestrator/vibrations_engine.py:379-555` and `925-1054`

**Step 1: Create `stability.py`**

Extract 3 functions:
- `calculate_stability_index` (lines 379-464)
- `generate_vibration_map` (lines 467-555)
- `calculate_vibration_map_3d` (lines 925-1054)

The `generate_vibration_map` and `calculate_vibration_map_3d` call other engine functions internally. Replace `eng = VibrationsEngine` pattern with direct imports:

```python
from .critical_speeds import calculate_critical_rpm_axial, calculate_critical_rpm_lateral
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
```

Then replace `eng.calculate_*()` calls with direct function calls.

---

### Task 0.6: Extract `bit_excitation.py`

**Files:**
- Create: `orchestrator/vibrations_engine/bit_excitation.py`
- Source lines: `orchestrator/vibrations_engine.py:1057-1213`

**Step 1: Create `bit_excitation.py`**

Extract 2 functions:
- `calculate_bit_excitation` (lines 1057-1132)
- `check_resonance` (lines 1135-1213)

---

### Task 0.7: Extract `stabilizers.py`

**Files:**
- Create: `orchestrator/vibrations_engine/stabilizers.py`
- Source lines: `orchestrator/vibrations_engine.py:1216-1323`

**Step 1: Create `stabilizers.py`**

Extract `optimize_stabilizer_placement` (lines 1216-1323). This function calls `calculate_critical_rpm_lateral` — import from `.critical_speeds`.

---

### Task 0.8: Extract `fatigue.py`

**Files:**
- Create: `orchestrator/vibrations_engine/fatigue.py`
- Source lines: `orchestrator/vibrations_engine.py:1326-1456`

**Step 1: Create `fatigue.py`**

Extract `calculate_fatigue_damage` (lines 1326-1456).

---

### Task 0.9: Extract `pipeline.py`

**Files:**
- Create: `orchestrator/vibrations_engine/pipeline.py`
- Source lines: `orchestrator/vibrations_engine.py:558-688`

**Step 1: Create `pipeline.py`**

Extract `calculate_full_vibration_analysis` (lines 558-688). This is the orchestrator that calls all other functions. Import from sibling modules:

```python
from .critical_speeds import calculate_critical_rpm_axial, calculate_critical_rpm_lateral
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
from .stability import calculate_stability_index, generate_vibration_map
```

Replace all `eng = VibrationsEngine` / `eng.calculate_*()` patterns with direct function calls.

---

### Task 0.10: Run all tests and delete monolithic file

**Step 1: Run tests WITH old file still present (package takes precedence if directory exists)**

```bash
pytest tests/unit/test_vibrations_engine.py tests/unit/test_elite_fase8_vibrations.py -v
```

Expected: ALL PASS

**Step 2: Delete the monolithic file**

```bash
rm orchestrator/vibrations_engine.py
```

**Step 3: Run tests again to confirm package-based imports work**

```bash
pytest tests/unit/test_vibrations_engine.py tests/unit/test_elite_fase8_vibrations.py -v
```

Expected: ALL PASS — zero changes to any test file.

**Step 4: Verify imports from routes and agents still resolve**

```bash
python3 -c "from orchestrator.vibrations_engine import VibrationsEngine; print('OK:', list(dir(VibrationsEngine))[:5])"
```

**Step 5: Commit**

```bash
git add orchestrator/vibrations_engine/ && git rm orchestrator/vibrations_engine.py
git commit -m "refactor(vibrations): split monolithic engine into modular package

Follow shot_efficiency_engine pattern: 1,456-line monolith → 9 focused modules.
Zero functional changes. All existing imports and tests unchanged."
```

---

## Phase 1: Critical Fixes

### Task 1.1: Fix lateral critical RPM — stabilizer spacing fallback

**Files:**
- Modify: `orchestrator/vibrations_engine/critical_speeds.py` (`calculate_critical_rpm_lateral`)
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write failing test**

Add to `TestLateralVibrations` class in `tests/unit/test_vibrations_engine.py`:

```python
def test_estimated_span_caps_at_90ft(self, engine):
    """When no stabilizer_spacing given, L = min(bha_length, 90) — not full BHA length."""
    result = engine.calculate_critical_rpm_lateral(
        bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
        bha_weight_lbft=83.0, hole_diameter_in=8.5, mud_weight_ppg=10.0,
    )
    # With L=90 ft (capped), lateral RPM must be > 30 RPM
    assert result["critical_rpm"] > 30
    assert result["span_used_ft"] == 90.0
    assert result["span_source"] == "estimated"

def test_user_provided_stabilizer_spacing(self, engine):
    """When stabilizer_spacing_ft is given, use it directly."""
    result = engine.calculate_critical_rpm_lateral(
        bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
        bha_weight_lbft=83.0, hole_diameter_in=8.5, mud_weight_ppg=10.0,
        stabilizer_spacing_ft=60.0,
    )
    assert result["critical_rpm"] > 50
    assert result["span_used_ft"] == 60.0
    assert result["span_source"] == "user"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_vibrations_engine.py::TestLateralVibrations::test_estimated_span_caps_at_90ft -v
```

Expected: FAIL (no `span_used_ft` key, and RPM is still 3)

**Step 3: Implement fix in `critical_speeds.py`**

In `calculate_critical_rpm_lateral`, add parameter `stabilizer_spacing_ft: Optional[float] = None`.

After the existing validation block, add:

```python
# Determine span length for lateral calculation
if stabilizer_spacing_ft is not None and stabilizer_spacing_ft > 0:
    span_ft = stabilizer_spacing_ft
    span_source = "user"
else:
    span_ft = min(bha_length_ft, 90.0)
    span_source = "estimated"
```

Replace `l_in = bha_length_ft * 12.0` with `l_in = span_ft * 12.0`.

Add to the return dict:

```python
"span_used_ft": round(span_ft, 1),
"span_source": span_source,
```

**Step 4: Update existing test that checks physical range**

In `test_critical_rpm_physical_range`, change:
```python
# Before: assert 1 <= lateral_result["critical_rpm"] <= 500
assert 30 <= lateral_result["critical_rpm"] <= 500
```

**Step 5: Run all lateral tests**

```bash
pytest tests/unit/test_vibrations_engine.py::TestLateralVibrations -v
```

Expected: ALL PASS

**Step 6: Commit**

```bash
git add orchestrator/vibrations_engine/critical_speeds.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): lateral RPM uses stabilizer span instead of total BHA length

Root cause: L=300ft (total BHA) was used in Euler-Bernoulli beam model.
Fix: L = min(bha_length, 90ft) as fallback, or user-provided stabilizer_spacing_ft.
Lateral RPM changes from 3 → ~80 RPM. Stability map auto-corrects."
```

---

### Task 1.2: Propagate `stabilizer_spacing_ft` to map and pipeline

**Files:**
- Modify: `orchestrator/vibrations_engine/stability.py` (`generate_vibration_map`)
- Modify: `orchestrator/vibrations_engine/pipeline.py` (`calculate_full_vibration_analysis`)
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write failing test for map range**

Add to `TestVibrationMap`:

```python
def test_map_has_meaningful_range(self, engine, typical_bha):
    """Stability index must vary by > 20 points across the map (not the old 2.7 flat range)."""
    result = engine.generate_vibration_map(
        bit_diameter_in=8.5,
        bha_od_in=typical_bha["bha_od_in"],
        bha_id_in=typical_bha["bha_id_in"],
        bha_weight_lbft=typical_bha["bha_weight_lbft"],
        bha_length_ft=typical_bha["bha_length_ft"],
        hole_diameter_in=8.5,
        mud_weight_ppg=typical_bha["mud_weight_ppg"],
    )
    scores = [pt["stability_index"] for pt in result["map_data"]]
    score_range = max(scores) - min(scores)
    assert score_range > 20, f"Map range too flat: {score_range:.1f} (min={min(scores):.1f}, max={max(scores):.1f})"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_vibrations_engine.py::TestVibrationMap::test_map_has_meaningful_range -v
```

Expected: FAIL with "Map range too flat: 2.7"

**Step 3: Propagate parameter**

In `generate_vibration_map()` in `stability.py`:
- Add parameter: `stabilizer_spacing_ft: Optional[float] = None`
- Pass it to `calculate_critical_rpm_lateral(... , stabilizer_spacing_ft=stabilizer_spacing_ft)`

In `calculate_full_vibration_analysis()` in `pipeline.py`:
- Add parameter: `stabilizer_spacing_ft: Optional[float] = None`
- Pass it to both `calculate_critical_rpm_lateral()` and `generate_vibration_map()`

**Step 4: Run all tests**

```bash
pytest tests/unit/test_vibrations_engine.py -v
```

Expected: ALL PASS including new map range test

**Step 5: Commit**

```bash
git add orchestrator/vibrations_engine/stability.py orchestrator/vibrations_engine/pipeline.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): propagate stabilizer_spacing_ft to map and pipeline

Map stability range now >20 points (was 2.7). Lateral score varies
from 30-90 across RPM range instead of fixed 50."
```

---

### Task 1.3: Fix MSE tautological efficiency

**Files:**
- Modify: `orchestrator/vibrations_engine/mse.py`
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write failing tests**

Add to `TestMSE`:

```python
def test_efficiency_none_without_ucs(self, engine):
    """Without UCS, efficiency must be None (not the old hard-coded 35%)."""
    result = engine.calculate_mse(
        wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5,
    )
    assert result["efficiency_pct"] is None
    assert result["classification_basis"] == "absolute_mse"

def test_efficiency_calculated_with_ucs(self, engine):
    """With UCS provided, efficiency = UCS / MSE * 100."""
    result = engine.calculate_mse(
        wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5,
        ucs_psi=55000,
    )
    assert result["efficiency_pct"] is not None
    assert 30 <= result["efficiency_pct"] <= 40  # ~34.4% for these params
    assert result["classification_basis"] == "ucs_based"
```

**Step 2: Run to verify failure**

```bash
pytest tests/unit/test_vibrations_engine.py::TestMSE::test_efficiency_none_without_ucs -v
```

Expected: FAIL (efficiency_pct is 35.0, not None)

**Step 3: Implement fix in `mse.py`**

Add parameter `ucs_psi: Optional[float] = None` to `calculate_mse()`.

Replace the efficiency block:

```python
# Efficiency calculation
if ucs_psi is not None and ucs_psi > 0 and mse_total > 0:
    efficiency_pct = min(100.0, ucs_psi / mse_total * 100.0)
    classification_basis = "ucs_based"
    # UCS-based classification
    if efficiency_pct > 80:
        classification = "Efficient"
        color = "green"
    elif efficiency_pct > 40:
        classification = "Normal"
        color = "yellow"
    elif efficiency_pct > 20:
        classification = "Inefficient"
        color = "orange"
    else:
        classification = "Highly Inefficient"
        color = "red"
else:
    efficiency_pct = None
    classification_basis = "absolute_mse"
    # Absolute MSE classification (existing thresholds)
    if mse_total < 20000:
        classification = "Efficient"
        color = "green"
    elif mse_total < 50000:
        classification = "Normal"
        color = "yellow"
    elif mse_total < 100000:
        classification = "Inefficient"
        color = "orange"
    else:
        classification = "Highly Inefficient"
        color = "red"
```

Update return dict: remove `estimated_ccs_psi` and `is_founder_point` when no UCS. Add `"classification_basis": classification_basis`.

**Step 4: Update existing test**

In `test_efficiency_bounded`, change to handle `None`:

```python
def test_efficiency_bounded(self, mse_result):
    """Efficiency is None without UCS, or in [0, 100] with UCS."""
    assert mse_result["efficiency_pct"] is None  # no UCS in fixture
```

**Step 5: Run all MSE tests**

```bash
pytest tests/unit/test_vibrations_engine.py::TestMSE -v
```

Expected: ALL PASS

**Step 6: Propagate `ucs_psi` to pipeline**

In `pipeline.py` `calculate_full_vibration_analysis()`:
- Add parameter: `ucs_psi: Optional[float] = None`
- Pass to `calculate_mse(..., ucs_psi=ucs_psi)`

**Step 7: Commit**

```bash
git add orchestrator/vibrations_engine/mse.py orchestrator/vibrations_engine/pipeline.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): remove tautological MSE efficiency calculation

Old: efficiency = mse * 0.35 / mse = always 35% (circular).
New: efficiency = UCS / MSE when UCS provided, None otherwise.
Classification falls back to absolute MSE thresholds without UCS."
```

---

## Phase 2: Medium-Severity Fixes

### Task 2.1: Fix friction torque effective radius

**Files:**
- Modify: `orchestrator/vibrations_engine/stick_slip.py`
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write failing test**

Add to `TestStickSlip`:

```python
def test_friction_torque_uses_two_thirds_radius(self, engine, typical_bha):
    """Friction torque must use 2R/3 effective radius (centroid of uniform PDC face)."""
    result = engine.calculate_stick_slip_severity(
        surface_rpm=120, wob_klb=20.0, torque_ftlb=12000,
        bit_diameter_in=8.5, bha_length_ft=typical_bha["bha_length_ft"],
        bha_od_in=typical_bha["bha_od_in"], bha_id_in=typical_bha["bha_id_in"],
        mud_weight_ppg=typical_bha["mud_weight_ppg"], friction_factor=0.25,
    )
    # T = mu * WOB * 2R/3 = 0.25 * 20000 * 2*(8.5/24)/3 = 1181 ft-lb
    assert 1100 <= result["friction_torque_ftlb"] <= 1250
```

**Step 2: Run to verify failure**

```bash
pytest tests/unit/test_vibrations_engine.py::TestStickSlip::test_friction_torque_uses_two_thirds_radius -v
```

Expected: FAIL (friction_torque is 590, not ~1181)

**Step 3: Fix in `stick_slip.py`**

Change line:
```python
# Before:
t_friction = friction_factor * wob_lbs * r_bit_ft / 3.0
# After:
t_friction = friction_factor * wob_lbs * r_bit_ft * 2.0 / 3.0
```

**Step 4: Run all stick-slip tests**

```bash
pytest tests/unit/test_vibrations_engine.py::TestStickSlip -v
```

Expected: ALL PASS (severity comparisons still hold — both cases doubled proportionally)

**Step 5: Commit**

```bash
git add orchestrator/vibrations_engine/stick_slip.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): friction torque uses 2R/3 effective radius

R/3 assumed all contact at bit center. 2R/3 is the centroid of
uniformly distributed force across the PDC face (physically correct).
Friction torque: 590 → 1181 ft-lb. Severity doubles proportionally."
```

---

### Task 2.2: Add UCS-based contextual classification

**Files:**
- Modify: `orchestrator/vibrations_engine/mse.py` (already partially done in Task 1.3)
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write failing test**

Add to `TestMSE`:

```python
def test_ucs_based_classification_efficient(self, engine):
    """High UCS relative to MSE should classify as Efficient."""
    result = engine.calculate_mse(
        wob_klb=20, torque_ftlb=5000, rpm=60, rop_fph=100, bit_diameter_in=8.5,
        ucs_psi=50000,
    )
    # Low MSE + high UCS = high efficiency
    assert result["classification_basis"] == "ucs_based"
    assert result["efficiency_pct"] > 80
    assert result["classification"] == "Efficient"

def test_ucs_based_classification_inefficient(self, engine):
    """Low UCS relative to MSE should classify as Highly Inefficient."""
    result = engine.calculate_mse(
        wob_klb=20, torque_ftlb=12000, rpm=120, rop_fph=50, bit_diameter_in=8.5,
        ucs_psi=5000,
    )
    # High MSE + low UCS = low efficiency
    assert result["classification_basis"] == "ucs_based"
    assert result["efficiency_pct"] < 20
    assert result["classification"] == "Highly Inefficient"
```

**Step 2: Run to verify they pass (should already work from Task 1.3)**

```bash
pytest tests/unit/test_vibrations_engine.py::TestMSE -v
```

Expected: ALL PASS (the UCS-based classification logic was added in Task 1.3)

**Step 3: Commit (if new tests were added)**

```bash
git add tests/unit/test_vibrations_engine.py
git commit -m "test(vibrations): add UCS-based classification boundary tests"
```

---

## Phase 3: Schema, Frontend & Professionalization

### Task 3.1: Add new fields to Pydantic schema

**Files:**
- Modify: `schemas/vibrations.py`

**Step 1: Add fields to `VibrationsCalcRequest`**

```python
stabilizer_spacing_ft: Optional[float] = Field(default=None, description="Span between stabilizers (ft). If not provided, estimated as min(bha_length, 90).")
ucs_psi: Optional[float] = Field(default=None, description="Formation unconfined compressive strength (psi). Required for MSE efficiency calculation.")
n_blades: Optional[int] = Field(default=None, description="Number of PDC blades/cutters. Affects bit excitation frequency.")
```

**Step 2: Pass new fields through API route**

In `routes/modules/vibrations.py`, find the call to `calculate_full_vibration_analysis` and pass the new fields:

```python
stabilizer_spacing_ft=req.stabilizer_spacing_ft,
ucs_psi=req.ucs_psi,
```

**Step 3: Run API smoke test**

```bash
python3 -c "
from schemas.vibrations import VibrationsCalcRequest
r = VibrationsCalcRequest(stabilizer_spacing_ft=60, ucs_psi=25000, n_blades=6)
print('OK:', r.stabilizer_spacing_ft, r.ucs_psi, r.n_blades)
r2 = VibrationsCalcRequest()  # defaults still work
print('Defaults OK:', r2.stabilizer_spacing_ft, r2.ucs_psi)
"
```

**Step 4: Commit**

```bash
git add schemas/vibrations.py routes/modules/vibrations.py
git commit -m "feat(vibrations): add stabilizer_spacing, ucs_psi, n_blades to API schema"
```

---

### Task 3.2: Connect BHA multi-component route to pipeline

**Files:**
- Modify: `orchestrator/vibrations_engine/pipeline.py`
- Test: `tests/unit/test_vibrations_engine.py`

**Step 1: Write test**

Add to `TestFullVibrationAnalysis`:

```python
def test_multi_component_lateral_when_bha_components_provided(self, engine):
    """When bha_components with stabilizers are given, use multi-component lateral route."""
    bha_components = [
        {"type": "bit", "length_ft": 1, "od_in": 8.5, "id_in": 2.5, "weight_lbft": 50},
        {"type": "motor", "length_ft": 30, "od_in": 6.75, "id_in": 3.0, "weight_lbft": 83},
        {"type": "stabilizer", "length_ft": 3, "od_in": 8.25, "id_in": 2.5, "weight_lbft": 100},
        {"type": "collar", "length_ft": 60, "od_in": 6.75, "id_in": 2.813, "weight_lbft": 83},
        {"type": "stabilizer", "length_ft": 3, "od_in": 8.25, "id_in": 2.5, "weight_lbft": 100},
        {"type": "collar", "length_ft": 90, "od_in": 6.75, "id_in": 2.813, "weight_lbft": 83},
    ]
    result = engine.calculate_full_vibration_analysis(
        wob_klb=20, rpm=120, rop_fph=50, torque_ftlb=10000,
        bit_diameter_in=8.5, bha_components=bha_components,
    )
    lateral = result["lateral_vibrations"]
    # Should have span-level detail
    assert "critical_rpm_spans" in lateral or lateral["critical_rpm"] > 10
```

**Step 2: Implement in `pipeline.py`**

Add optional `bha_components: Optional[List[Dict]] = None` parameter.

Logic:
```python
if bha_components:
    lateral = calculate_critical_rpm_lateral_multi(
        bha_components=bha_components,
        mud_weight_ppg=mud_weight_ppg,
        hole_diameter_in=hole_diameter_in,
    )
else:
    lateral = calculate_critical_rpm_lateral(
        ..., stabilizer_spacing_ft=stabilizer_spacing_ft
    )
```

**Step 3: Run tests**

```bash
pytest tests/unit/test_vibrations_engine.py -v
```

Expected: ALL PASS

**Step 4: Commit**

```bash
git add orchestrator/vibrations_engine/pipeline.py tests/unit/test_vibrations_engine.py
git commit -m "feat(vibrations): connect BHA multi-component route to main pipeline

When bha_components with stabilizers provided, uses Transfer Matrix
method for precise per-span lateral RPM. Falls back to estimated span."
```

---

### Task 3.3: Update TypeScript types

**Files:**
- Modify: `frontend/src/types/modules/vibrations.ts`

**Step 1: Add new fields to types**

Add to the appropriate interfaces:

```typescript
// New request fields
stabilizer_spacing_ft?: number;
ucs_psi?: number;
n_blades?: number;

// New response fields in lateral result
span_used_ft?: number;
span_source?: 'user' | 'estimated';
critical_rpm_spans?: Array<{
  span: string;
  length_ft: number;
  critical_rpm: number;
}>;

// Updated MSE result
efficiency_pct: number | null;
classification_basis: 'ucs_based' | 'absolute_mse';
```

**Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add frontend/src/types/modules/vibrations.ts
git commit -m "feat(vibrations): update TypeScript types for new engine fields"
```

---

### Task 3.4: Add frontend input fields

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx`

**Step 1: Add input fields to the form**

Add 3 optional input fields to the parameters section:
- **Stabilizer Spacing (ft)** — numeric input, placeholder "Auto (max 90 ft)"
- **Formation UCS (psi)** — numeric input with lithology quick-select dropdown (Shale: 8000, Sandstone: 20000, Limestone: 35000, Dolomite: 50000)
- **PDC Blade Count** — numeric input, placeholder "Optional"

**Step 2: Pass values in API call**

Add the new fields to the request body sent to the vibrations API endpoint.

**Step 3: Update results display**

- Show efficiency percentage only when `efficiency_pct !== null`
- Show `span_used_ft` and `span_source` in lateral results card
- When `span_source === "estimated"`, show info icon with "Estimated — provide stabilizer spacing for precision"

**Step 4: Verify TypeScript compiles and UI renders**

```bash
cd frontend && npx tsc --noEmit
```

**Step 5: Commit**

```bash
git add frontend/src/components/VibrationsModule.tsx
git commit -m "feat(vibrations): add stabilizer spacing, UCS, blade count inputs to frontend

Shows efficiency only with real UCS. Indicates when span is estimated."
```

---

### Task 3.5: Final regression test suite

**Files:**
- Modify: `tests/unit/test_vibrations_engine.py`

**Step 1: Add comprehensive regression tests**

```python
class TestRegressionAuditFixes:
    """Regression tests ensuring audit-identified bugs stay fixed."""

    def test_lateral_rpm_never_below_30(self, engine):
        """Lateral RPM must never be below 30 for any reasonable BHA."""
        for length in [100, 200, 300, 500]:
            result = engine.calculate_critical_rpm_lateral(
                bha_length_ft=length, bha_od_in=6.75, bha_id_in=2.813,
                bha_weight_lbft=83.0, hole_diameter_in=8.5,
            )
            assert result["critical_rpm"] >= 30, f"L={length}: RPM={result['critical_rpm']}"

    def test_map_range_exceeds_20_points(self, engine):
        """Stability map must discriminate — range > 20 points."""
        result = engine.generate_vibration_map(
            bit_diameter_in=8.5, bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300, hole_diameter_in=8.5,
        )
        scores = [pt["stability_index"] for pt in result["map_data"]]
        assert max(scores) - min(scores) > 20

    def test_mse_efficiency_not_hardcoded(self, engine):
        """Efficiency must NOT be hard-coded 35%. Must vary with inputs or be None."""
        r1 = engine.calculate_mse(wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5, ucs_psi=5000)
        r2 = engine.calculate_mse(wob_klb=20, torque_ftlb=10000, rpm=120, rop_fph=50, bit_diameter_in=8.5, ucs_psi=50000)
        assert r1["efficiency_pct"] != r2["efficiency_pct"]

    def test_friction_torque_not_r_over_3(self, engine):
        """Friction torque must use 2R/3, not R/3."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=120, wob_klb=20, torque_ftlb=12000,
            bit_diameter_in=8.5, bha_length_ft=300,
            bha_od_in=6.75, bha_id_in=2.813, friction_factor=0.25,
        )
        # R/3 gives 590, 2R/3 gives ~1181
        assert result["friction_torque_ftlb"] > 900
```

**Step 2: Run full test suite**

```bash
pytest tests/unit/test_vibrations_engine.py tests/unit/test_elite_fase8_vibrations.py -v
```

Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/unit/test_vibrations_engine.py
git commit -m "test(vibrations): add regression tests for all 6 audit-identified bugs

Ensures lateral RPM >= 30, map range > 20, efficiency not hard-coded,
friction torque uses 2R/3. Guards against future regressions."
```

---

## Summary

| Phase | Tasks | Commits | Key Verification |
|---|---|---|---|
| **0** | 0.1-0.10 | 1 | `pytest` all green, old file deleted |
| **1** | 1.1-1.3 | 3 | Lateral RPM ~80, map range >20, efficiency nullable |
| **2** | 2.1-2.2 | 2 | Friction ~1181 ft-lb, severity ~0.045 |
| **3** | 3.1-3.5 | 5 | Schema + frontend + regression suite |
| **Total** | **17 tasks** | **11 commits** | |
