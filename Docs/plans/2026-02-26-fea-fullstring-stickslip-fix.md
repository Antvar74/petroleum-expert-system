# FEA Full-String Assembly + Stick-Slip Data Flow Fix

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two critical bugs where the backend ignores BHA Editor data: FEA truncates the string to 335 ft (instead of 15,000 ft), and Stick-Slip reads stale results because the FEA endpoint never computes torsional vibrations.

**Architecture:** Remove the DP filter from the FEA solver, implement distributed axial force (compression at bit, tension at surface) so the full 15,000 ft matrix is well-conditioned, and connect the Stick-Slip computation to the FEA execution flow so both update simultaneously.

**Tech Stack:** Python (NumPy, SciPy), FastAPI, React/TypeScript

---

## Root Cause Analysis

### Bug 1: FEA Y-Axis stops at 335 ft (Mode Shapes show only BHA)

**Data flow:**
```
Frontend sends 15,005 ft (4 rows: collar+collar+hwdp+DP×489)
  → POST /vibrations/fea
    → run_fea_analysis()
      → _filter_bha_for_fea()  ← CULPRIT: removes DP with length_ft > 500
      → Only 335 ft of BHA enters assemble_global_matrices()
      → solve_eigenvalue() with 335 ft "floating" beam → 0.00 Hz
```

**Why eigenvalues = 0.00 Hz:**
The 335 ft BHA with `pinned-pinned` BCs has node 0 (bit) and node N (top of 335 ft) pinned. But the uniform WOB (25,000 lbs) applied to all elements creates a geometric stiffness that overwhelms the elastic stiffness of this short beam. The effective stiffness matrix becomes negative-definite → eigenvalues < 0 → clipped to 0.00 Hz.

**Previous fix attempt that failed:** Including full 15,000 ft with UNIFORM WOB gave condition number > 1e15 because every element (including 14,670 ft of DP) was under 25,000 lbs compression, which is physically impossible — only the BHA near the bit is under compression.

**Correct physics:** In a real drillstring:
- At the bit: P = WOB (25,000 lbs compression)
- Going upward: P decreases by the buoyant weight of each element
- At the **neutral point** (~1,500 ft from bit): P = 0
- Above the neutral point: P < 0 (tension — the DP hangs from the rig)
- At surface: P = -(total string weight - WOB) (tension)

Tension INCREASES effective stiffness → well-conditioned matrix → positive eigenvalues.

### Bug 2: Stick-Slip shows 0.09 despite 15,000 ft in BHA Editor

**The math code is correct.** The function `calculate_stick_slip_severity()` in `stick_slip.py` has the 3-priority model with `bha_components` support (Priority 1). The `VibrationsCalcRequest` schema has the `bha_components` field. The pipeline passes it.

**The disconnect is in the UI flow:**
```
User clicks "Calculate" (no BHA loaded) → result.stick_slip = 0.09
User loads BHA Editor (489 DP joints)
User clicks "Run FEA" → feaResult updated, but result.stick_slip UNCHANGED
User sees stick_slip = 0.09 from the old "Calculate" run
```

The FEA endpoint (`/vibrations/fea` → `run_fea_analysis()`) computes eigenvalue + forced response + Campbell. **It never computes stick-slip.** The stick-slip displayed in the UI comes from `result.stick_slip`, which is only updated when the main "Calculate" button is pressed.

**Proof:** If the user clicks "Calculate" AFTER loading the BHA Editor, the stick-slip function receives `bha_components` with the full 14,670 ft of DP and computes severity >> 1.0 (Critical). But the user only clicks "Run FEA", so the old result persists.

---

## Task 1: Remove DP Filter + Implement Distributed Axial Force

**Files:**
- Modify: `orchestrator/vibrations_engine/fea.py`
- Test: `tests/unit/test_fea_engine.py`

### Step 1: Remove `_filter_bha_for_fea()` and related code

In `fea.py`, delete:
- `_DP_FEA_MAX_LENGTH_FT` constant (line 123)
- `_BHA_TYPES` set (line 89)
- `_filter_bha_for_fea()` function (lines 126-147)

In `run_fea_analysis()`, replace:
```python
# OLD
fea_components = _filter_bha_for_fea(bha_components)
```
with:
```python
# NEW — use all components; auto-mesh handles long elements
fea_components = bha_components
```

In `generate_campbell_diagram()`, same change: use `bha_components` directly (it's already passed in).

### Step 2: Implement distributed axial force in `assemble_global_matrices()`

Replace the uniform `P_lbs = wob_klb * 1000.0` with per-element axial force:

```python
# Distributed axial force: compression at bit → tension at surface
P_lbs_wob = wob_klb * 1000.0
cumulative_weight_lbs = 0.0  # buoyant weight accumulated from bit upward

for i, comp in enumerate(elements):
    ...
    # Buoyant weight of this element
    element_weight = weight_ppf * bf * length_ft  # lbs

    # Axial force at MIDPOINT of this element
    # P > 0 = compression (reduces stiffness), P < 0 = tension (adds stiffness)
    P_element = P_lbs_wob - cumulative_weight_lbs - element_weight / 2.0

    # Accumulate weight for elements above
    cumulative_weight_lbs += element_weight

    # Element matrices with this element's axial force
    Ke, Kge, Me = beam_element_matrices(length_in, EI, rhoA, P_element)
    ...
```

**Key insight:** For the standard BHA (335 ft, total weight ~17,000 lbs, WOB=25,000 lbs):
- P at bottom: 25,000 lbs (compression)
- P at top: 25,000 - 17,000 = 8,000 lbs (still compression)
- All elements under compression → similar to uniform WOB → backward compatible

For the 15,000 ft string (total weight ~260,000 lbs, WOB=25,000 lbs):
- P at bottom: 25,000 lbs (compression)
- Neutral point: ~1,500 ft from bit
- P at 15,000 ft: 25,000 - 260,000 = -235,000 lbs (strong tension)
- Matrix well-conditioned → positive eigenvalues → real frequencies

### Step 3: Update summary (remove n_components_fea)

In `run_fea_analysis()`, since we no longer filter:
```python
summary = {
    ...
    "n_components": len(bha_components),  # back to single count
    # Remove "n_components_fea" key
}
```

### Step 4: Update existing tests

In `test_fea_engine.py`:
- Remove/update tests that reference `_filter_bha_for_fea` or `_BHA_TYPES`
- Update `test_fea_summary_reports_auto_mesh` to use `n_components` instead of `n_components_input`/`n_components_fea`
- Keep the `test_fea_nonzero_frequencies_with_long_dp` test — it should now pass with ALL modes > 0 Hz (change `any(f > 0)` to `all(f > 0)`)

### Step 5: Add new test for distributed axial force

```python
def test_distributed_axial_force_full_string():
    """15,000 ft string: all 5 modes should have positive frequencies."""
    bha = [
        {"type": "collar", "od": 8.0, "id_inner": 2.813, "length_ft": 30, "weight_ppf": 147},
        {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 120, "weight_ppf": 83},
        {"type": "hwdp", "od": 5.0, "id_inner": 3.0, "length_ft": 90, "weight_ppf": 49.3},
        {"type": "dp", "od": 5.0, "id_inner": 4.276, "length_ft": 14670, "weight_ppf": 19.5},
    ]
    result = run_fea_analysis(bha, wob_klb=25, rpm=60)
    freqs = result["eigenvalue"]["frequencies_hz"]
    assert all(f > 0 for f in freqs), f"Expected all positive frequencies, got {freqs}"
    # Mode shapes should span full 15,000 ft
    max_md = max(result["node_positions_ft"])
    assert max_md > 14000, f"Expected full string in model, got max MD = {max_md} ft"
```

### Step 6: Run tests

```bash
pytest tests/unit/test_fea_engine.py tests/unit/test_vibrations_engine.py -v
```

### Step 7: Commit

```bash
git add orchestrator/vibrations_engine/fea.py tests/unit/test_fea_engine.py
git commit -m "fix(fea): include full drillstring with distributed axial force"
```

---

## Task 2: Connect Stick-Slip to FEA Execution Flow

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx`
- Test: `tests/unit/test_vibrations_engine.py`

### Step 1: Write verification test for stick-slip with bha_components

Add to `tests/unit/test_vibrations_engine.py`:

```python
def test_stick_slip_severity_with_15000ft_bha_components():
    """When bha_components includes 15,000 ft of DP, severity must be >> 0.5."""
    from orchestrator.vibrations_engine import calculate_stick_slip_severity
    bha = [
        {"type": "collar", "od": 8.0, "id_inner": 2.813, "length_ft": 30, "weight_ppf": 147},
        {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 120, "weight_ppf": 83},
        {"type": "hwdp", "od": 5.0, "id_inner": 3.0, "length_ft": 90, "weight_ppf": 49.3},
        {"type": "dp", "od": 5.0, "id_inner": 4.276, "length_ft": 14670, "weight_ppf": 19.5},
    ]
    result = calculate_stick_slip_severity(
        surface_rpm=60, wob_klb=25, torque_ftlb=16000,
        bit_diameter_in=8.5, bha_length_ft=300,
        bha_od_in=6.75, bha_id_in=2.813,
        bha_components=bha,
    )
    assert result["severity_index"] > 1.0, (
        f"With 15,000 ft string, severity should be Critical, got {result['severity_index']}"
    )
    assert result["classification"] in ("Severe", "Critical")
```

Run: `pytest tests/unit/test_vibrations_engine.py::TestStickSlipWithBHAComponents -v`

This test proves the backend math IS correct. The issue is the frontend flow.

### Step 2: Fix frontend — auto-recalculate main results when FEA runs

In `VibrationsModule.tsx`, modify `calculateFEA` to also trigger the main `calculate()` after FEA completes. This ensures stick-slip is recomputed with the current BHA components.

```typescript
const calculateFEA = useCallback(async () => {
    if (bhaComponents.length < 2) {
      addToast('Add at least 2 BHA components for FEA analysis', 'error');
      return;
    }
    setFeaLoading(true);
    try {
      const res = await api.post('/vibrations/fea', {
        bha_components: bhaComponents,
        wob_klb: params.wob_klb || 20,
        rpm: params.rpm || 120,
        ...
      });
      setFeaResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('FEA Error: ' + ..., 'error');
    }
    setFeaLoading(false);
    // Also recalculate main vibrations (updates stick-slip with BHA data)
    calculate();
  }, [bhaComponents, params, addToast, calculate]);
```

### Step 3: Run TypeScript check

```bash
cd frontend && npx tsc --noEmit
```

### Step 4: Commit

```bash
git add frontend/src/components/VibrationsModule.tsx tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): connect stick-slip to FEA flow via auto-recalculate"
```

---

## Verification Checklist

- [ ] Standard BHA (335 ft, no DP): FEA frequencies unchanged from previous behavior
- [ ] 15,000 ft string: ALL 5 mode frequencies > 0 Hz
- [ ] 15,000 ft string: Mode shape Y-axis spans full 15,000 ft (not 335 ft)
- [ ] 15,000 ft string: Stick-slip severity >> 1.0 (Critical/Severe)
- [ ] Tests: `pytest tests/unit/test_fea_engine.py tests/unit/test_vibrations_engine.py` — all pass
- [ ] TypeScript: `npx tsc --noEmit` — clean
- [ ] Full test suite: `pytest -q` — no new failures
