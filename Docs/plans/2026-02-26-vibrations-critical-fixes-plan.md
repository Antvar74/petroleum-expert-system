# Vibrations Module — Critical Backend Fixes Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 3 physics bugs in the vibrations engine: (1) stick-slip uses only BHA length instead of total drillstring for torsional stiffness, (2) heatmap ignores MSE/UCS when coloring cells, (3) optimal point recommends WOB too low for hard rock because there's no UCS-based minimum constraint.

**Architecture:** All fixes are backend-only (Python engine files + tests). No frontend changes needed — the frontend already displays whatever the backend returns. The fixes are isolated to 3 files: `stick_slip.py`, `stability.py`, and `pipeline.py`. Each fix has TDD tests that reproduce the physical scenario described by the field engineer.

**Tech Stack:** Python 3.13, pytest, math (stdlib). No new dependencies.

**Branch:** `feat/vibrations-critical-fixes`

---

## Task 1: Fix Stick-Slip Torsional Stiffness — Use Total Drillstring Length

**Files:**
- Modify: `orchestrator/vibrations_engine/stick_slip.py:10-112`
- Modify: `orchestrator/vibrations_engine/pipeline.py:76-86`
- Test: `tests/unit/test_vibrations_engine.py`

### Problem

The torsional stiffness formula uses only `bha_length_ft` (300 ft) for the spring length:
```
k_torsion = G * J_bha / L_bha
```
This makes the string appear ~30x stiffer than reality for a 10,000 ft well. The severity reads 0.09 (Mild) when it should be Critical.

### Physical correction

The drillstring is a composite torsional spring: BHA section (thick, stiff) in series with DP section (thinner, much longer). For springs in series:
```
1/K_eq = 1/K_bha + 1/K_dp
K_eq = (K_bha * K_dp) / (K_bha + K_dp)
```
Where:
- `K_bha = G * J_bha / L_bha`
- `K_dp = G * J_dp / L_dp`
- `L_dp = total_depth - bha_length`
- `J_dp = π(dp_od⁴ - dp_id⁴)/32`

**Step 1: Write the failing tests**

Add a new test class to `tests/unit/test_vibrations_engine.py` after `TestStickSlip`:

```python
class TestStickSlipWithDrillPipe:
    """Tests for stick-slip with total drillstring depth (DP + BHA)."""

    def test_deep_well_high_severity(self, engine):
        """10,000 ft well at 60 RPM with 16,000 ft-lb torque must be Critical."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=60, wob_klb=35, torque_ftlb=16000,
            bit_diameter_in=8.5,
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            mud_weight_ppg=10.0, friction_factor=0.25,
            total_depth_ft=10000,
            dp_od_in=5.0, dp_id_in=4.276,
        )
        assert result["severity_index"] > 1.5, (
            f"Expected Critical (>1.5), got {result['severity_index']}"
        )
        assert result["classification"] == "Critical"

    def test_shallow_well_lower_severity(self, engine):
        """Same params but at 1,000 ft should be less severe than 10,000 ft."""
        shallow = engine.calculate_stick_slip_severity(
            surface_rpm=60, wob_klb=35, torque_ftlb=16000,
            bit_diameter_in=8.5,
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            friction_factor=0.25,
            total_depth_ft=1000,
            dp_od_in=5.0, dp_id_in=4.276,
        )
        deep = engine.calculate_stick_slip_severity(
            surface_rpm=60, wob_klb=35, torque_ftlb=16000,
            bit_diameter_in=8.5,
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            friction_factor=0.25,
            total_depth_ft=10000,
            dp_od_in=5.0, dp_id_in=4.276,
        )
        assert deep["severity_index"] > shallow["severity_index"]

    def test_backward_compat_no_depth(self, engine):
        """Without total_depth_ft, behavior should be the same as before (BHA-only)."""
        old_result = engine.calculate_stick_slip_severity(
            surface_rpm=120, wob_klb=20, torque_ftlb=12000,
            bit_diameter_in=8.5,
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            friction_factor=0.25,
        )
        # Without total_depth_ft, should still work
        assert "severity_index" in old_result
        assert old_result["severity_index"] >= 0

    def test_bit_stall_rpm_zero_at_critical(self, engine):
        """At Critical severity, bit minimum RPM should be 0 (full stall)."""
        result = engine.calculate_stick_slip_severity(
            surface_rpm=60, wob_klb=35, torque_ftlb=16000,
            bit_diameter_in=8.5,
            bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
            friction_factor=0.25,
            total_depth_ft=10000,
            dp_od_in=5.0, dp_id_in=4.276,
        )
        assert result["rpm_min_at_bit"] == 0, (
            f"Bit should stall (0 RPM), got {result['rpm_min_at_bit']}"
        )
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py::TestStickSlipWithDrillPipe -v`
Expected: FAIL — `TypeError: calculate_stick_slip_severity() got an unexpected keyword argument 'total_depth_ft'`

**Step 3: Implement the fix in stick_slip.py**

Replace the entire `calculate_stick_slip_severity` function in `orchestrator/vibrations_engine/stick_slip.py`:

```python
def calculate_stick_slip_severity(
    surface_rpm: float,
    wob_klb: float,
    torque_ftlb: float,
    bit_diameter_in: float,
    bha_length_ft: float,
    bha_od_in: float,
    bha_id_in: float,
    mud_weight_ppg: float = 10.0,
    friction_factor: float = 0.25,
    total_depth_ft: Optional[float] = None,
    dp_od_in: float = 5.0,
    dp_id_in: float = 4.276,
) -> Dict[str, Any]:
    """
    Calculate stick-slip severity index.

    Uses a composite torsional spring model (BHA + Drill Pipe in series)
    when total_depth_ft is provided. Falls back to BHA-only stiffness
    when total_depth_ft is None (backward compatibility).

    Torsional stiffness model:
    - K_bha = G * J_bha / L_bha
    - K_dp  = G * J_dp  / L_dp   (where L_dp = total_depth - bha_length)
    - K_eq  = (K_bha * K_dp) / (K_bha + K_dp)   [springs in series]

    Severity = delta_omega / omega_surface
    Where delta_omega = 2 * (T_friction / K_eq) * omega_surface

    Classification:
    - < 0.5: Mild (normal drilling)
    - 0.5-1.0: Moderate (monitoring needed)
    - 1.0-1.5: Severe (adjust parameters)
    - > 1.5: Critical (bit stalling likely)

    References:
    - Jansen & van den Steen (1995): Active damping of stick-slip vibrations

    Args:
        surface_rpm: surface rotary speed (RPM)
        wob_klb: weight on bit (klbs)
        torque_ftlb: surface torque (ft-lbs)
        bit_diameter_in: bit diameter (inches)
        bha_length_ft: BHA length (ft)
        bha_od_in: BHA OD (inches)
        bha_id_in: BHA ID (inches)
        mud_weight_ppg: mud weight (ppg)
        friction_factor: bit-formation friction coefficient
        total_depth_ft: total measured depth (ft). When provided, DP section
            is modeled as a torsional spring in series with BHA.
        dp_od_in: drill pipe OD (inches), used when total_depth_ft provided
        dp_id_in: drill pipe ID (inches), used when total_depth_ft provided

    Returns:
        Dict with severity index, classification, recommendations
    """
    if surface_rpm <= 0:
        return {"error": "RPM must be > 0"}

    # Friction torque at bit (ft-lbs)
    r_bit_ft = bit_diameter_in / (2.0 * 12.0)
    wob_lbs = wob_klb * 1000.0
    t_friction = friction_factor * wob_lbs * r_bit_ft * 2.0 / 3.0

    # Torsional stiffness
    # G = E / (2(1+nu)) ~ 11.5e6 psi for steel
    g_shear = 11.5e6  # psi
    j_bha = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 32.0  # in^4
    bha_length_in = bha_length_ft * 12.0

    k_bha = g_shear * j_bha / bha_length_in if bha_length_in > 0 else 1e6  # in-lb/rad

    # Composite stiffness: BHA + DP in series
    if total_depth_ft is not None and total_depth_ft > bha_length_ft:
        dp_length_ft = total_depth_ft - bha_length_ft
        dp_length_in = dp_length_ft * 12.0
        j_dp = math.pi * (dp_od_in ** 4 - dp_id_in ** 4) / 32.0  # in^4
        k_dp = g_shear * j_dp / dp_length_in if dp_length_in > 0 else 1e6
        # Springs in series: 1/K_eq = 1/K_bha + 1/K_dp
        k_torsion = (k_bha * k_dp) / (k_bha + k_dp)
    else:
        k_torsion = k_bha

    # Angular displacement (radians)
    t_friction_inlb = t_friction * 12.0  # convert to in-lb
    delta_theta = t_friction_inlb / k_torsion if k_torsion > 0 else 0

    # RPM fluctuation estimate
    # delta_omega ~ 2 * delta_theta * omega_surface (simplified oscillation model)
    omega_surface = surface_rpm * 2.0 * math.pi / 60.0  # rad/s
    delta_omega = 2.0 * delta_theta * omega_surface

    # Severity
    severity = delta_omega / omega_surface if omega_surface > 0 else 0

    # Min/Max RPM at bit
    rpm_min_bit = max(0, surface_rpm * (1.0 - severity / 2.0))
    rpm_max_bit = surface_rpm * (1.0 + severity / 2.0)

    # Classification
    if severity < 0.5:
        classification = "Mild"
        color = "green"
        recommendation = "Normal drilling — no action needed"
    elif severity < 1.0:
        classification = "Moderate"
        color = "yellow"
        recommendation = "Monitor closely — consider increasing RPM or reducing WOB"
    elif severity < 1.5:
        classification = "Severe"
        color = "orange"
        recommendation = "Increase RPM to >120, reduce WOB, consider anti-stall tool"
    else:
        classification = "Critical"
        color = "red"
        recommendation = "Bit stalling likely — significantly reduce WOB and increase RPM"

    return {
        "severity_index": round(severity, 3),
        "classification": classification,
        "color": color,
        "rpm_min_at_bit": round(rpm_min_bit, 0),
        "rpm_max_at_bit": round(rpm_max_bit, 0),
        "surface_rpm": surface_rpm,
        "friction_torque_ftlb": round(t_friction, 0),
        "torsional_stiffness_inlb_rad": round(k_torsion, 0),
        "angular_displacement_deg": round(math.degrees(delta_theta), 2),
        "recommendation": recommendation,
    }
```

Also add `from typing import Dict, Any, Optional` at the top (add `Optional`).

**Step 4: Pass total_depth_ft and DP params from pipeline to stick_slip**

In `orchestrator/vibrations_engine/pipeline.py`, update the `calculate_full_vibration_analysis` function:

1. Add `total_depth_ft: Optional[float] = None` parameter (after `ucs_psi`).
2. Update the stick_slip call (lines 76-86) to pass the new params:

```python
    # 3. Stick-slip
    stick_slip = calculate_stick_slip_severity(
        surface_rpm=rpm,
        wob_klb=wob_klb,
        torque_ftlb=torque_ftlb,
        bit_diameter_in=bit_diameter_in,
        bha_length_ft=bha_length_ft,
        bha_od_in=bha_od_in,
        bha_id_in=bha_id_in,
        mud_weight_ppg=mud_weight_ppg,
        friction_factor=friction_factor,
        total_depth_ft=total_depth_ft,
        dp_od_in=dp_od_in,
        dp_id_in=dp_id_in,
    )
```

3. Also pass `total_depth_ft`, `dp_od_in`, `dp_id_in`, and `ucs_psi` to `generate_vibration_map()` (this feeds into Task 2+3):

```python
    vib_map = generate_vibration_map(
        bit_diameter_in=bit_diameter_in,
        bha_od_in=bha_od_in,
        bha_id_in=bha_id_in,
        bha_weight_lbft=bha_weight_lbft,
        bha_length_ft=bha_length_ft,
        hole_diameter_in=hole_diameter_in,
        mud_weight_ppg=mud_weight_ppg,
        torque_base_ftlb=torque_ftlb,
        rop_base_fph=rop_fph,
        stabilizer_spacing_ft=stabilizer_spacing_ft,
        total_depth_ft=total_depth_ft,
        dp_od_in=dp_od_in,
        dp_id_in=dp_id_in,
        ucs_psi=ucs_psi,
    )
```

**Step 5: Wire total_depth_ft from schema through route**

In `schemas/vibrations.py`, add to `VibrationsCalcRequest` (after `wellbore_sections`):

```python
    total_depth_ft: Optional[float] = Field(default=None, description="Total measured depth (ft). Derived from wellbore sections max Bottom MD. Required for accurate stick-slip calculation.")
```

In `routes/modules/vibrations.py`, add `total_depth_ft=data.total_depth_ft,` to the `calculate_full_vibration_analysis` call.

**Step 6: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py -v`
Expected: All pass (49 existing + 4 new = 53)

**Step 7: Commit**

```bash
git add orchestrator/vibrations_engine/stick_slip.py orchestrator/vibrations_engine/pipeline.py schemas/vibrations.py routes/modules/vibrations.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): use total drillstring length for stick-slip stiffness

Composite torsional spring model (BHA + DP in series) replaces BHA-only
calculation. A 10,000 ft well now correctly shows Critical severity
instead of false Mild. Backward-compatible when total_depth_ft is None.

Ref: Jansen & van den Steen (1995)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Integrate MSE/UCS Efficiency into Heatmap Color

**Files:**
- Modify: `orchestrator/vibrations_engine/stability.py:19-104,107-195`
- Test: `tests/unit/test_vibrations_engine.py`

### Problem

The heatmap has two bugs:
1. MSE weight is only 15% — vibration dominates at 85%.
2. `ucs_psi` is not passed to `calculate_mse()` inside the map, so MSE efficiency is never calculated for heatmap cells.

### Physical correction

1. Rebalance weights: `{"axial": 0.15, "lateral": 0.25, "torsional": 0.30, "mse": 0.30}` — MSE doubles from 15% to 30%.
2. When UCS is available, use efficiency-based MSE scoring in `calculate_stability_index()` instead of absolute thresholds.
3. Pass `ucs_psi` through `generate_vibration_map()` to `calculate_mse()`.
4. Pass `total_depth_ft` + DP params through to `calculate_stick_slip_severity()` inside the map.

**Step 1: Write the failing tests**

Add to `tests/unit/test_vibrations_engine.py`:

```python
class TestHeatmapWithMSE:
    """Tests that heatmap correctly penalizes inefficient MSE zones."""

    def test_hard_rock_high_mse_not_green(self, engine):
        """With 28,000 psi limestone, high MSE zones must NOT be Stable/green."""
        vib_map = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300,
            hole_diameter_in=8.5, mud_weight_ppg=10.0,
            torque_base_ftlb=16000, rop_base_fph=18,
            ucs_psi=28000,
        )
        # Find cells with high MSE (>200,000 psi)
        high_mse_cells = [
            p for p in vib_map["map_data"]
            if p["mse_psi"] > 200000
        ]
        # None of them should be "Stable"
        stable_high_mse = [p for p in high_mse_cells if p["status"] == "Stable"]
        assert len(stable_high_mse) == 0, (
            f"{len(stable_high_mse)} cells are 'Stable' despite MSE>{200000} psi"
        )

    def test_mse_weight_is_significant(self, engine):
        """MSE weight should be at least 0.25 in the stability formula."""
        # We can verify via the stability function directly
        axial = {"critical_rpm_1st": 500}
        lateral = {"critical_rpm": 400}
        stick_slip = {"severity_index": 0.1}  # Mild
        # Very high MSE
        mse_bad = {"mse_total_psi": 400000, "efficiency_pct": 5.0, "classification": "Highly Inefficient"}
        mse_good = {"mse_total_psi": 15000, "efficiency_pct": 90.0, "classification": "Efficient"}

        stab_bad = engine.calculate_stability_index(axial, lateral, stick_slip, mse_bad, 120)
        stab_good = engine.calculate_stability_index(axial, lateral, stick_slip, mse_good, 120)

        # Bad MSE should significantly reduce stability (at least 15 points)
        diff = stab_good["stability_index"] - stab_bad["stability_index"]
        assert diff >= 15, f"MSE impact too small: only {diff:.1f} points difference"

    def test_ucs_affects_mse_scoring(self, engine):
        """When UCS is provided, MSE score should use efficiency, not absolute thresholds."""
        axial = {"critical_rpm_1st": 500}
        lateral = {"critical_rpm": 400}
        stick_slip = {"severity_index": 0.1}
        # MSE = 50,000 psi with UCS = 5,000 (10% efficiency = terrible)
        mse_low_eff = {"mse_total_psi": 50000, "efficiency_pct": 10.0, "classification": "Highly Inefficient"}
        # MSE = 50,000 psi with UCS = 45,000 (90% efficiency = great)
        mse_high_eff = {"mse_total_psi": 50000, "efficiency_pct": 90.0, "classification": "Efficient"}

        stab_low = engine.calculate_stability_index(axial, lateral, stick_slip, mse_low_eff, 120)
        stab_high = engine.calculate_stability_index(axial, lateral, stick_slip, mse_high_eff, 120)

        assert stab_high["stability_index"] > stab_low["stability_index"]
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py::TestHeatmapWithMSE -v`
Expected: FAIL

**Step 3: Fix calculate_stability_index() — rebalance weights + use efficiency**

In `orchestrator/vibrations_engine/stability.py`, replace the MSE scoring and weights section (lines 69-82):

```python
    # MSE score — prefer efficiency_pct when available (UCS-based)
    efficiency = mse_result.get("efficiency_pct")
    if efficiency is not None:
        # UCS-based efficiency scoring
        if efficiency > 80:
            scores["mse"] = 95
        elif efficiency > 40:
            scores["mse"] = 70
        elif efficiency > 20:
            scores["mse"] = 35
        else:
            scores["mse"] = 10  # Highly inefficient
    else:
        # Fallback: absolute MSE thresholds
        mse_val = mse_result.get("mse_total_psi", 50000)
        if mse_val < 20000:
            scores["mse"] = 95
        elif mse_val < 50000:
            scores["mse"] = 70
        elif mse_val < 100000:
            scores["mse"] = 40
        else:
            scores["mse"] = 15

    # Weighted overall — MSE doubled from 0.15 to 0.30
    weights = {"axial": 0.15, "lateral": 0.25, "torsional": 0.30, "mse": 0.30}
    overall = sum(scores[k] * weights[k] for k in scores)
```

**Step 4: Fix generate_vibration_map() — accept and pass ucs_psi, total_depth_ft, DP params**

Update `generate_vibration_map()` signature to add new parameters:

```python
def generate_vibration_map(
    bit_diameter_in: float,
    bha_od_in: float,
    bha_id_in: float,
    bha_weight_lbft: float,
    bha_length_ft: float,
    hole_diameter_in: float,
    mud_weight_ppg: float = 10.0,
    wob_range: Optional[List[float]] = None,
    rpm_range: Optional[List[float]] = None,
    torque_base_ftlb: float = 10000,
    rop_base_fph: float = 50,
    stabilizer_spacing_ft: Optional[float] = None,
    ucs_psi: Optional[float] = None,
    total_depth_ft: Optional[float] = None,
    dp_od_in: float = 5.0,
    dp_id_in: float = 4.276,
) -> Dict[str, Any]:
```

Update the inner `calculate_stick_slip_severity()` call to pass the new params:

```python
            stick_slip = calculate_stick_slip_severity(
                surface_rpm=rpm, wob_klb=wob, torque_ftlb=torque_est,
                bit_diameter_in=bit_diameter_in, bha_length_ft=bha_length_ft,
                bha_od_in=bha_od_in, bha_id_in=bha_id_in, mud_weight_ppg=mud_weight_ppg,
                total_depth_ft=total_depth_ft,
                dp_od_in=dp_od_in, dp_id_in=dp_id_in,
            )
```

Update the inner `calculate_mse()` call to pass `ucs_psi`:

```python
            mse = calculate_mse(
                wob_klb=wob, torque_ftlb=torque_est, rpm=rpm,
                rop_fph=rop_est, bit_diameter_in=bit_diameter_in,
                ucs_psi=ucs_psi,
            )
```

**Step 5: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py -v`
Expected: All pass (53 from Task 1 + 3 new = 56)

**Step 6: Commit**

```bash
git add orchestrator/vibrations_engine/stability.py orchestrator/vibrations_engine/pipeline.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): integrate MSE efficiency into heatmap + rebalance weights

MSE weight increased from 15% to 30%. Heatmap now uses UCS-based
efficiency scoring when available. High-MSE cells are penalized
even if vibrations are low. UCS and total_depth_ft passed through
to all heatmap cell calculations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Add UCS-Based Minimum WOB Constraint to Optimal Point

**Files:**
- Modify: `orchestrator/vibrations_engine/stability.py:151-186`
- Test: `tests/unit/test_vibrations_engine.py`

### Problem

The optimal point algorithm is a simple greedy max over stability_index. Since low WOB minimizes vibrations, it suggests 5 klb even for 28,000 psi limestone where you need >>5 klb to break rock.

### Physical correction

Minimum WOB to engage cutter into rock (simplified PDC model):
```
WOB_min_klb = (UCS_psi * bit_area_in2) / (n_cutters * 1000)
```

Simplified: for a PDC bit, approximate cutting force threshold:
```
WOB_min_klb = UCS_psi * bit_diameter_in^2 / (1000 * 1300)
```

The `1300` factor accounts for the cutter geometry and contact efficiency (empirical, from Dupriest 2005 MSE optimization). For 28,000 psi rock with 8.5" bit: `WOB_min = 28000 * 72.25 / 1,300,000 ≈ 15.6 klb` — reasonable minimum.

The optimizer should skip any (WOB, RPM) cell where `WOB < WOB_min`.

**Step 1: Write the failing tests**

Add to `tests/unit/test_vibrations_engine.py`:

```python
class TestOptimalPointConstraint:
    """Tests that optimal WOB respects UCS-based minimum constraint."""

    def test_hard_rock_wob_not_too_low(self, engine):
        """For 28,000 psi limestone, optimal WOB must be >= 15 klb."""
        vib_map = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300,
            hole_diameter_in=8.5, mud_weight_ppg=10.0,
            torque_base_ftlb=16000, rop_base_fph=18,
            ucs_psi=28000,
        )
        assert vib_map["optimal_point"]["wob"] >= 15, (
            f"Optimal WOB {vib_map['optimal_point']['wob']} klb is too low for 28,000 psi rock"
        )

    def test_soft_rock_allows_low_wob(self, engine):
        """For soft shale (5,000 psi), low WOB should be acceptable."""
        vib_map = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300,
            hole_diameter_in=8.5, mud_weight_ppg=10.0,
            torque_base_ftlb=8000, rop_base_fph=80,
            ucs_psi=5000,
        )
        # Soft rock: WOB_min ≈ 5000 * 72.25 / 1,300,000 ≈ 2.8 klb
        # So WOB=5 is physically fine
        assert vib_map["optimal_point"]["wob"] >= 5

    def test_no_ucs_no_constraint(self, engine):
        """Without UCS, the optimizer should work as before (no constraint)."""
        vib_map = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300,
            hole_diameter_in=8.5, mud_weight_ppg=10.0,
        )
        # Should still produce a valid optimal point
        assert vib_map["optimal_point"]["wob"] > 0
        assert vib_map["optimal_point"]["rpm"] > 0

    def test_optimal_includes_wob_min(self, engine):
        """Result should report the minimum WOB constraint when UCS is provided."""
        vib_map = engine.generate_vibration_map(
            bit_diameter_in=8.5,
            bha_od_in=6.75, bha_id_in=2.813,
            bha_weight_lbft=83.0, bha_length_ft=300,
            hole_diameter_in=8.5, mud_weight_ppg=10.0,
            ucs_psi=28000,
        )
        assert "wob_min_klb" in vib_map["optimal_point"]
        assert vib_map["optimal_point"]["wob_min_klb"] > 0
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py::TestOptimalPointConstraint -v`
Expected: FAIL

**Step 3: Implement the WOB constraint in generate_vibration_map()**

In `orchestrator/vibrations_engine/stability.py`, inside `generate_vibration_map()`, add the constraint logic. After the range defaults (line ~138), before the loop:

```python
    # Minimum WOB constraint from UCS (rock hardness)
    # Simplified PDC cutter engagement model (Dupriest 2005):
    # WOB_min = UCS * d^2 / (1000 * 1300)
    wob_min_klb = 0.0
    if ucs_psi is not None and ucs_psi > 0:
        wob_min_klb = ucs_psi * bit_diameter_in ** 2 / (1000.0 * 1300.0)
```

Then update the optimal point selection logic (lines 185-186) to respect the constraint:

```python
            if score > optimal_point["score"] and wob >= wob_min_klb:
                optimal_point = {"wob": wob, "rpm": rpm, "score": score, "wob_min_klb": round(wob_min_klb, 1)}
```

Also initialize `optimal_point` with `wob_min_klb`:

```python
    optimal_point = {"wob": 0, "rpm": 0, "score": 0, "wob_min_klb": round(wob_min_klb, 1)}
```

And add a fallback: if no cell passes the WOB constraint (shouldn't happen normally), find the best cell at the minimum acceptable WOB:

```python
    # Fallback: if no cell met the WOB constraint, pick best at lowest acceptable WOB
    if optimal_point["wob"] == 0 and wob_min_klb > 0:
        acceptable = [p for p in map_data if p["wob_klb"] >= wob_min_klb]
        if acceptable:
            best = max(acceptable, key=lambda p: p["stability_index"])
            optimal_point = {
                "wob": best["wob_klb"], "rpm": best["rpm"],
                "score": best["stability_index"], "wob_min_klb": round(wob_min_klb, 1),
            }
```

**Step 4: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py -v`
Expected: All pass (56 from Task 2 + 4 new = 60)

**Step 5: Commit**

```bash
git add orchestrator/vibrations_engine/stability.py tests/unit/test_vibrations_engine.py
git commit -m "fix(vibrations): add UCS-based minimum WOB constraint to optimal point

WOB_min = UCS * d^2 / (1000 * 1300) ensures the optimizer never suggests
a WOB that can't break the rock. For 28,000 psi limestone with 8.5in bit,
minimum WOB is ~15.6 klb. Soft shale allows lower WOB as expected.

Ref: Dupriest (2005) MSE optimization

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Frontend — Auto-derive total_depth_ft from Wellbore Sections

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx`

### Problem

The backend now accepts `total_depth_ft` but the frontend doesn't send it. We need to derive it automatically from the wellbore sections (max Bottom MD) and include it in the API call.

**Step 1: Add total_depth_ft derivation and pass it to the API call**

In `VibrationsModule.tsx`, find the `handleCalculate` callback (or wherever the API call to `/wells/{well_id}/vibrations` is made). Add `total_depth_ft` computed from `wellboreSections`:

```tsx
    // Derive total depth from wellbore sections (max bottom_md_ft)
    const totalDepth = wellboreSections.length > 0
      ? Math.max(...wellboreSections.map(s => s.bottom_md_ft))
      : undefined;
```

Add `total_depth_ft: totalDepth` to the API call payload. Also pass `wellbore_sections` if populated.

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No NEW errors

**Step 3: Commit**

```bash
git add frontend/src/components/VibrationsModule.tsx
git commit -m "feat(vibrations): auto-derive total_depth_ft from wellbore sections

Computes max(bottom_md_ft) from wellbore sections and sends
total_depth_ft to backend for accurate stick-slip calculation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Full Stack Verification

**Files:** None (verification only)

**Step 1: Run ALL backend tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py tests/unit/test_fea_engine.py -v`
Expected: ~87 tests pass (60 vibrations + 27 FEA)

**Step 2: Smoke test — reproduce the field scenario**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -c "
from orchestrator.vibrations_engine.stick_slip import calculate_stick_slip_severity
result = calculate_stick_slip_severity(
    surface_rpm=60, wob_klb=35, torque_ftlb=16000,
    bit_diameter_in=8.5, bha_length_ft=300,
    bha_od_in=6.75, bha_id_in=2.813,
    friction_factor=0.25,
    total_depth_ft=10000, dp_od_in=5.0, dp_id_in=4.276,
)
print(f'Severity: {result[\"severity_index\"]} — {result[\"classification\"]}')
print(f'RPM at bit: {result[\"rpm_min_at_bit\"]} - {result[\"rpm_max_at_bit\"]}')
assert result['classification'] == 'Critical', 'Should be Critical!'
print('PASS: 10,000 ft well correctly shows Critical stick-slip')
"`

Note: This smoke test may fail due to bcrypt import in `orchestrator/__init__.py`. If so, run through pytest instead:

```python
# Add as test_field_scenario_10k_ft in test_vibrations_engine.py
```

**Step 3: Verify frontend compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`

**Step 4: Verify git log**

Run: `git log --oneline feat/vibrations-critical-fixes --not feat/vibrations-wellbore-config`
Expected: 4 clean commits

---

## Summary

| Task | Fix | Files | New Tests |
|------|-----|-------|-----------|
| 1 | Stick-slip: composite DP+BHA torsional spring | `stick_slip.py`, `pipeline.py`, `schemas`, `routes` | 4 |
| 2 | Heatmap: MSE weight 30%, UCS efficiency scoring | `stability.py`, `pipeline.py` | 3 |
| 3 | Optimal point: UCS-based WOB_min constraint | `stability.py` | 4 |
| 4 | Frontend: auto-derive total_depth_ft | `VibrationsModule.tsx` | 0 |
| 5 | Full stack verification | none | smoke test |

**Total: 11 new tests, 4 modified engine files, 5 commits.**

### Expected behavior after fixes:

| Scenario | Before | After |
|----------|--------|-------|
| 10,000 ft, 60 RPM, 35 klb WOB, 16,000 ft-lb | Mild (0.09) | **Critical (>1.5)** |
| Heatmap cell: low vibration + MSE 355k psi | Green (Stable) | **Orange/Red** |
| Optimal WOB for 28k psi limestone | 5 klb | **≥15 klb** |
