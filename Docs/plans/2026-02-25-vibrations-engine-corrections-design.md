# Design: Vibrations Engine Root-Cause Corrections

**Date:** 2026-02-25
**Module:** Vibrations & Stability (`orchestrator/vibrations_engine.py`)
**Trigger:** Technical audit + independent code verification against source

---

## Problem Statement

The vibrations engine has 6 verified bugs, 3 critical and 3 medium. All critical bugs share a single root cause: `calculate_critical_rpm_lateral()` uses `bha_length_ft` (total BHA length, 300 ft) as the beam span `L`, when it should use the distance between stabilizers (~30-90 ft). This produces a lateral critical RPM of 3 RPM (physically impossible), which cascades into a flat stability map (range 69-72 instead of ~35-90) and a misleading "optimal point".

Additionally, the MSE efficiency calculation is tautological (`efficiency = mse * 0.35 / mse = 35%` always), and the stick-slip friction torque uses an incorrect effective radius (R/3 instead of 2R/3).

## Approach: 4 Incremental Phases

### Phase 0 — Modular Restructure (Zero Functional Changes)

**Pattern:** Same as `shot_efficiency_engine/` (1,370 lines → 8 files of 47-425 lines)

Convert monolithic `orchestrator/vibrations_engine.py` (1,456 lines) into a package:

```
orchestrator/vibrations_engine/          # Package (replaces single file)
    __init__.py          (~50 lines)   # Re-exports VibrationsEngine public API
    critical_speeds.py   (~350 lines)  # calculate_critical_rpm_axial, _lateral, _lateral_multi
    stick_slip.py        (~100 lines)  # calculate_stick_slip_severity
    mse.py               (~80 lines)   # calculate_mse
    stability.py         (~350 lines)  # calculate_stability_index, generate_vibration_map, _map_3d
    bit_excitation.py    (~160 lines)  # calculate_bit_excitation, check_resonance
    stabilizers.py       (~110 lines)  # optimize_stabilizer_placement
    fatigue.py           (~130 lines)  # calculate_fatigue_damage
    pipeline.py          (~130 lines)  # calculate_full_vibration_analysis (orchestrator)
```

**Rules:**
- Pure file reorganization — no logic changes, no bug fixes
- `__init__.py` re-exports `VibrationsEngine` class so all imports remain unchanged
- All existing tests must pass without modification
- Steel constants (`STEEL_E`, `STEEL_DENSITY`, `GRAVITY`) move to a module-level `constants` or stay in `__init__.py`
- Delete original `orchestrator/vibrations_engine.py` after confirming tests pass

**Verification:** `pytest tests/unit/test_vibrations_engine.py` — all green, zero changes to tests or routes.

---

### Phase 1 — Critical Fixes (Engine Only)

**Files:** `orchestrator/vibrations_engine/critical_speeds.py`, `orchestrator/vibrations_engine/mse.py`, `orchestrator/vibrations_engine/stability.py`, `orchestrator/vibrations_engine/pipeline.py`

#### 1.1 Lateral Critical RPM — Stabilizer Spacing Fallback

**Function:** `calculate_critical_rpm_lateral()`

- Add optional parameter: `stabilizer_spacing_ft: Optional[float] = None`
- Logic: `L = stabilizer_spacing_ft if provided else min(bha_length_ft, 90.0)`
- 90 ft cap = maximum typical stabilizer span in industry practice
- Add to result: `"span_used_ft"`, `"span_source": "user" | "estimated"`
- Propagate parameter to `generate_vibration_map()` and `calculate_full_vibration_analysis()`

**Expected result:** Lateral RPM changes from 3 → ~80 RPM (with L=90 ft estimated)

#### 1.2 RPM x WOB Map — Auto-corrected

No code changes needed. Fixing lateral RPM causes the lateral stability score to vary from 30-90 across the map (instead of fixed 50), producing a map with range ~35-90 (instead of 69-72).

#### 1.3 MSE Efficiency — Remove Tautological Calculation

**Function:** `calculate_mse()`

Current (broken):
```python
estimated_ccs = mse_total * 0.35  # circular
efficiency_pct = estimated_ccs / mse_total * 100  # always 35%
```

Fix:
- Add optional parameter: `ucs_psi: Optional[float] = None`
- If `ucs_psi` provided: `efficiency_pct = min(100, ucs_psi / mse_total * 100)`
- If not provided: `efficiency_pct = None` (not computed)
- Remove `estimated_ccs` field from response when UCS not available
- Keep absolute MSE classification thresholds as fallback
- Add `"classification_basis": "ucs_based" | "absolute_mse"` to result

### Phase 2 — Medium-Severity Fixes (Engine Only)

**Files:** `orchestrator/vibrations_engine/stick_slip.py`, `orchestrator/vibrations_engine/mse.py`

#### 2.1 Friction Torque — R/3 → 2R/3

**Function:** `calculate_stick_slip_severity()`

Change:
```python
# Before: t_friction = friction_factor * wob_lbs * r_bit_ft / 3.0
t_friction = friction_factor * wob_lbs * r_bit_ft * 2.0 / 3.0
```

Physical basis: 2R/3 is the centroid of uniformly distributed force across a circular PDC bit face. R/3 (current) assumes all contact at the center; R (audit's suggestion) assumes all contact at gauge. Neither is correct.

**Effect:** Friction torque doubles (590 → 1,181 ft-lb for WOB=20 klb). Stick-slip severity approximately doubles, making the model more sensitive and realistic. RPM range at bit widens from 119-121 to ~117-123.

#### 2.2 Stick-Slip RPM Range — Auto-corrected

No formula change needed. The correction in 2.1 propagates through:
- `severity = delta_omega / omega_surface` increases ~2x
- `rpm_min_bit` and `rpm_max_bit` use severity directly
- Range widens naturally

#### 2.3 MSE Classification — Contextual When UCS Available

Add efficiency-based classification when `ucs_psi` is provided (field from 1.3):

| Efficiency (UCS/MSE) | Classification |
|---|---|
| > 80% | Efficient |
| 40-80% | Normal |
| 20-40% | Inefficient |
| < 20% | Highly Inefficient |

When UCS not available, keep absolute MSE thresholds with `"classification_basis": "absolute_mse"`.

### Phase 3 — Schema, Frontend & Professionalization

**Files:** `schemas/vibrations.py`, `frontend/src/components/VibrationsModule.tsx`, `frontend/src/types/modules/vibrations.ts`, `tests/unit/test_vibrations_engine.py`

#### 3.1 New Schema Fields

```python
# schemas/vibrations.py — VibrationsCalcRequest
stabilizer_spacing_ft: Optional[float] = Field(default=None, description="Span between stabilizers (ft)")
ucs_psi: Optional[float] = Field(default=None, description="Formation UCS (psi)")
n_blades: Optional[int] = Field(default=None, description="Number of PDC blades/cutters")
```

#### 3.2 Lateral RPM — BHA Multi-Component Route (Approach B)

Connect existing `calculate_critical_rpm_lateral_multi()` to main flow:
- If request includes `bha_components` with stabilizers → use multi route, extract real spans
- If not → keep Phase 1 fallback (`min(bha_length_ft, 90)`)

Result changes from single `critical_rpm` to:
```json
{
  "critical_rpm_spans": [
    {"span": "Bit to Stab1", "length_ft": 45, "critical_rpm": 156},
    {"span": "Stab1 to Stab2", "length_ft": 60, "critical_rpm": 80}
  ],
  "critical_rpm": 80
}
```

#### 3.3 Frontend — New Input Fields

Add to `VibrationsModule.tsx` input form:
- **Stabilizer Spacing (ft)** — numeric, optional, with tooltip
- **Formation UCS (psi)** — numeric or lithology selector (Shale/Sandstone/Limestone/Dolomite with preset values)
- **PDC Blade Count** — numeric, optional

Update result display to show efficiency only when UCS is provided.

#### 3.4 TypeScript Types

Update `frontend/src/types/modules/vibrations.ts` for new response fields: `span_used_ft`, `span_source`, `efficiency_pct: number | null`, `classification_basis`, `critical_rpm_spans`.

#### 3.5 Test Updates

- Change `test_critical_rpm_physical_range` accepted range from `1-500` to `30-500`
- Add tests: span estimated vs provided, efficiency with/without UCS, friction torque 2R/3, contextual classification
- Add regression test: map stability index range must be > 20 points (not 2.7)

---

## Verification Criteria

### Phase 0 — After Implementation
- `pytest tests/unit/test_vibrations_engine.py` — all tests pass, zero modifications to tests
- `pytest tests/unit/test_elite_fase8_vibrations.py` — all tests pass (if applicable)
- `from orchestrator.vibrations_engine import VibrationsEngine` still works
- All API routes unchanged and functional
- Original monolithic file deleted

### Phase 1 — After Implementation
- `calculate_critical_rpm_lateral(bha_length_ft=300)` → RPM ~80 (not 3)
- Stability map range > 20 points across 72 cells
- `calculate_mse(..., ucs_psi=None)` → `efficiency_pct: None`
- `calculate_mse(..., ucs_psi=55000)` → `efficiency_pct: ~34.4%`
- All existing tests pass (with updated expected values)

### Phase 2 — After Implementation
- Friction torque for WOB=20 klb, bit=8.5" → ~1,181 ft-lb (not 590)
- Stick-slip severity ~0.045 (not 0.022) for default params
- RPM range at bit: ~117-123 (not 119-121)

### Phase 3 — After Implementation
- API accepts `stabilizer_spacing_ft`, `ucs_psi`, `n_blades`
- Frontend renders new fields
- Multi-component BHA route produces per-span critical RPMs
- TypeScript compiles without errors

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Phase 0 restructure breaks imports | `__init__.py` re-exports everything; no import changes needed |
| Existing tests fail with new lateral RPM values | Update expected values in test fixtures |
| Frontend breaks if `efficiency_pct` becomes null | Use conditional rendering (already handles optional fields) |
| Phase 2 torque change makes all stick-slip "Moderate" | Verify classification thresholds still appropriate with 2x torque |
| Phase 3 multi-component route has edge cases | Keep fallback; multi route only activates with stabilizer data |

---

*References: Paslay & Dawson (1984), Teale (1965) SPE-1260, Brett (1992) SPE-21943, Mitchell (2003) Transfer Matrix*
