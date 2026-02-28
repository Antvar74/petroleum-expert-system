# Vibrations Module — Wellbore Configuration & Mud Rheology Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the Vibrations module input panel: add mud rheology (PV, YP, flow rate) to Operating Parameters, replace "Configuración BHA" with "Configuración del Agujero" (wellbore sections: casing, liner, open hole), and add CSV/Excel import to the BHA Editor. Each module is autonomous — must allow full data acquisition independently for standalone licensing.

**Architecture:** Frontend-first approach. Add new fields to `params` state + new `wellboreSections` state. Backend schemas get new optional fields (backward-compatible). Engine functions accept but don't yet consume the new fields (pass-through wiring). FEA damping formula upgraded to use PV when available. BHA Editor gets file upload capability.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Pydantic v2, FastAPI, Papa Parse (CSV), SheetJS/xlsx (Excel)

**Branch:** `feat/vibrations-wellbore-config`

---

## Task 1: Add Mud Rheology Fields to Backend Schema

**Files:**
- Modify: `schemas/vibrations.py:12-33`

**Step 1: Add mud rheology fields to VibrationsCalcRequest**

In `schemas/vibrations.py`, add 3 new optional fields after `mud_weight_ppg` (line 27):

```python
class VibrationsCalcRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/vibrations``."""

    wob_klb: float = Field(default=25, description="Weight on bit (klbs)")
    rpm: float = Field(default=120, description="RPM")
    rop_fph: float = Field(default=60, description="Rate of penetration (ft/hr)")
    torque_ftlb: float = Field(default=15000, description="Torque (ft-lb)")
    bit_diameter_in: float = Field(default=8.5, description="Bit diameter (in)")
    dp_od_in: float = Field(default=5.0, description="Drill pipe OD (in)")
    dp_id_in: float = Field(default=4.276, description="Drill pipe ID (in)")
    dp_weight_lbft: float = Field(default=19.5, description="DP weight (lb/ft)")
    bha_length_ft: float = Field(default=300, description="BHA length (ft)")
    bha_od_in: float = Field(default=6.75, description="BHA OD (in)")
    bha_id_in: float = Field(default=2.813, description="BHA ID (in)")
    bha_weight_lbft: float = Field(default=83.0, description="BHA weight (lb/ft)")
    mud_weight_ppg: float = Field(default=10.0, description="Mud weight (ppg)")
    pv_cp: Optional[float] = Field(default=None, description="Plastic viscosity (cP)")
    yp_lbf_100ft2: Optional[float] = Field(default=None, description="Yield point (lbf/100ft²)")
    flow_rate_gpm: Optional[float] = Field(default=None, description="Circulation rate (gpm)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    inclination_deg: float = Field(default=30, description="Inclination (deg)")
    friction_factor: float = Field(default=0.25, description="Friction factor")
    stabilizer_spacing_ft: Optional[float] = Field(default=None, description="Span between stabilizers (ft). If not provided, estimated as min(bha_length, 90).")
    ucs_psi: Optional[float] = Field(default=None, description="Formation unconfined compressive strength (psi). Required for MSE efficiency calculation.")
    n_blades: Optional[int] = Field(default=None, description="Number of PDC blades/cutters. Affects bit excitation frequency.")
```

Also add `pv_cp` and `yp_lbf_100ft2` to `FEARequest` (after `mud_weight_ppg`, line 78):

```python
class FEARequest(BaseModel):
    """Body for ``POST /vibrations/fea``."""

    bha_components: List[Dict[str, Any]] = Field(..., description="BHA component list")
    wob_klb: float = Field(default=20, description="Weight on bit (klbs)")
    rpm: float = Field(default=120, description="Operating RPM")
    mud_weight_ppg: float = Field(default=10, description="Mud weight (ppg)")
    pv_cp: Optional[float] = Field(default=None, description="Plastic viscosity (cP)")
    yp_lbf_100ft2: Optional[float] = Field(default=None, description="Yield point (lbf/100ft²)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    boundary_conditions: str = Field(default="pinned-pinned", description="BC: pinned-pinned, fixed-pinned, fixed-free")
    n_modes: int = Field(default=5, description="Number of modes to compute")
    include_forced_response: bool = Field(default=True, description="Include forced response analysis")
    include_campbell: bool = Field(default=True, description="Include Campbell diagram")
    n_blades: Optional[int] = Field(default=None, description="PDC blade count for blade-pass excitation")
```

**Step 2: Run existing tests to verify backward compatibility**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py tests/unit/test_fea_engine.py -q`
Expected: 73 passed (no breakage — all new fields are Optional with defaults)

**Step 3: Commit**

```bash
git add schemas/vibrations.py
git commit -m "feat(vibrations): add mud rheology fields (PV, YP, flow rate) to schemas

Optional fields pv_cp, yp_lbf_100ft2, flow_rate_gpm added to
VibrationsCalcRequest and FEARequest. Backward-compatible.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Add Wellbore Section Schema

**Files:**
- Modify: `schemas/vibrations.py` (append after CampbellRequest)

**Step 1: Add WellboreSection model**

Append to `schemas/vibrations.py` after the `CampbellRequest` class:

```python


class WellboreSection(BaseModel):
    """A single wellbore section (casing, liner, or open hole)."""

    section_type: str = Field(..., description="Type: surface_casing, intermediate_casing, production_casing, liner, open_hole")
    top_md_ft: float = Field(..., description="Top measured depth (ft)")
    bottom_md_ft: float = Field(..., description="Bottom measured depth (ft)")
    id_in: float = Field(..., description="Inner diameter (in)")
    shoe_depth_ft: Optional[float] = Field(default=None, description="Shoe depth (ft), typically = bottom_md_ft")
```

Then add `wellbore_sections` to `VibrationsCalcRequest` (after `n_blades`):

```python
    wellbore_sections: Optional[List[Dict[str, Any]]] = Field(default=None, description="Wellbore sections: casing, liner, open hole. Each dict has section_type, top_md_ft, bottom_md_ft, id_in.")
```

**Step 2: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py tests/unit/test_fea_engine.py -q`
Expected: 73 passed

**Step 3: Commit**

```bash
git add schemas/vibrations.py
git commit -m "feat(vibrations): add WellboreSection schema and wellbore_sections field

Supports surface_casing, intermediate_casing, production_casing, liner,
and open_hole section types with MD ranges and inner diameters.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Upgrade FEA Damping to Use PV/YP

**Files:**
- Modify: `orchestrator/vibrations_engine/fea.py:280-315`
- Test: `tests/unit/test_fea_engine.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_fea_engine.py` a new test class after `TestRunFEAAnalysis`:

```python
class TestDampingWithRheology:
    """Test that PV/YP improve the damping model."""

    def test_pv_increases_damping_alpha(self):
        """Higher PV should produce higher alpha (more viscous damping)."""
        from orchestrator.vibrations_engine.fea import _compute_damping_alpha
        alpha_no_pv = _compute_damping_alpha(mud_weight_ppg=10.0, pv_cp=None, yp_lbf_100ft2=None)
        alpha_with_pv = _compute_damping_alpha(mud_weight_ppg=10.0, pv_cp=25.0, yp_lbf_100ft2=15.0)
        assert alpha_with_pv > alpha_no_pv

    def test_heavier_mud_increases_damping(self):
        """Heavier mud should produce higher alpha regardless of PV availability."""
        from orchestrator.vibrations_engine.fea import _compute_damping_alpha
        alpha_light = _compute_damping_alpha(mud_weight_ppg=8.0)
        alpha_heavy = _compute_damping_alpha(mud_weight_ppg=14.0)
        assert alpha_heavy > alpha_light

    def test_damping_without_pv_matches_legacy(self):
        """When PV is None, should match the legacy formula: 0.01 + MW * 0.002."""
        from orchestrator.vibrations_engine.fea import _compute_damping_alpha
        alpha = _compute_damping_alpha(mud_weight_ppg=10.0, pv_cp=None, yp_lbf_100ft2=None)
        expected = 0.01 + 10.0 * 0.002
        assert abs(alpha - expected) < 1e-10
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_fea_engine.py::TestDampingWithRheology -v`
Expected: FAIL with "cannot import name '_compute_damping_alpha'"

**Step 3: Extract damping into a testable function and upgrade**

In `orchestrator/vibrations_engine/fea.py`, add a new function before `solve_forced_response()`:

```python
def _compute_damping_alpha(
    mud_weight_ppg: float = 10.0,
    pv_cp: Optional[float] = None,
    yp_lbf_100ft2: Optional[float] = None,
) -> float:
    """Compute mass-proportional Rayleigh damping coefficient.

    When PV and YP are available, uses a rheology-based model:
        alpha = 0.005 + MW * 0.001 + PV * 0.0008 + YP * 0.0003

    When only MW is available, uses the legacy empirical formula:
        alpha = 0.01 + MW * 0.002

    The rheology-based model accounts for:
    - Mud weight: buoyant mass effect on damping
    - Plastic viscosity: viscous shear dissipation around BHA
    - Yield point: gel structure dissipation at low shear rates

    Returns:
        alpha: Mass-proportional damping coefficient (dimensionless).
    """
    if pv_cp is not None and yp_lbf_100ft2 is not None:
        return 0.005 + mud_weight_ppg * 0.001 + pv_cp * 0.0008 + yp_lbf_100ft2 * 0.0003
    return 0.01 + mud_weight_ppg * 0.002
```

Then modify `solve_forced_response()` to use it. Replace lines 311-313:

```python
    if alpha is None:
        # Light damping: ~2-5% critical for drilling systems
        alpha = 0.01 + mud_weight_ppg * 0.002
```

With:

```python
    if alpha is None:
        alpha = _compute_damping_alpha(mud_weight_ppg, pv_cp, yp_lbf_100ft2)
```

And add `pv_cp` and `yp_lbf_100ft2` parameters to `solve_forced_response()` signature:

```python
def solve_forced_response(
    K: NDArray,
    Kg: NDArray,
    M: NDArray,
    bc: str = "pinned-pinned",
    excitation_freq_hz: float = 2.0,
    excitation_node: int = 0,
    force_lbs: float = 100.0,
    mud_weight_ppg: float = 10.0,
    pv_cp: Optional[float] = None,
    yp_lbf_100ft2: Optional[float] = None,
    alpha: Optional[float] = None,
    beta: float = 0.01,
) -> Dict[str, Any]:
```

Also update `run_fea_analysis()` to accept and pass through `pv_cp` and `yp_lbf_100ft2`.

**Step 4: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_fea_engine.py -v`
Expected: All tests PASS (27 total: 24 existing + 3 new)

**Step 5: Commit**

```bash
git add orchestrator/vibrations_engine/fea.py tests/unit/test_fea_engine.py
git commit -m "feat(vibrations): upgrade FEA damping to use PV/YP when available

Extract _compute_damping_alpha() with rheology-based model:
alpha = 0.005 + MW*0.001 + PV*0.0008 + YP*0.0003
Falls back to legacy formula when PV/YP are None.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Wire New Schema Fields Through Routes

**Files:**
- Modify: `routes/modules/vibrations.py:145-159`

**Step 1: Pass pv_cp and yp_lbf_100ft2 through the FEA route**

In `routes/modules/vibrations.py`, update the `calculate_fea` endpoint to pass the new fields:

```python
@router.post("/vibrations/fea")
def calculate_fea(data: FEARequest):
    """Finite Element Analysis of BHA lateral vibrations."""
    return VibrationsEngine.run_fea_analysis(
        bha_components=data.bha_components,
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        bc=data.boundary_conditions,
        n_modes=data.n_modes,
        include_forced_response=data.include_forced_response,
        include_campbell=data.include_campbell,
        n_blades=data.n_blades,
        pv_cp=data.pv_cp,
        yp_lbf_100ft2=data.yp_lbf_100ft2,
    )
```

**Step 2: Run tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_vibrations_engine.py tests/unit/test_fea_engine.py -q`
Expected: All pass

**Step 3: Commit**

```bash
git add routes/modules/vibrations.py
git commit -m "feat(vibrations): wire PV/YP through FEA route to engine

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Install Papa Parse + SheetJS for CSV/Excel Import

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install dependencies**

```bash
cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm install papaparse xlsx && npm install -D @types/papaparse
```

**Step 2: Verify build**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add papaparse and xlsx for CSV/Excel import support

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Add CSV/Excel Import to BHA Editor

**Files:**
- Modify: `frontend/src/components/charts/vb/BHAEditor.tsx`

**Step 1: Add file upload capability**

In `BHAEditor.tsx`, add imports at top:

```tsx
import { useRef } from 'react';
import { Plus, Trash2, ChevronUp, ChevronDown, Upload } from 'lucide-react';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
```

Add the file import handler function inside the `BHAEditor` component (after `moveComponent`):

```tsx
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();

    const parseRows = (rows: Record<string, string>[]) => {
      const mapped: BHAComponent[] = rows
        .filter(r => r.type || r.Type || r.component)
        .map(r => ({
          type: (r.type || r.Type || r.component || 'collar').toLowerCase(),
          od: parseFloat(r.od || r.OD || r.od_in || '6.75') || 6.75,
          id_inner: parseFloat(r.id_inner || r.ID || r.id_in || r.id || '2.813') || 2.813,
          length_ft: parseFloat(r.length_ft || r.length || r.Length || '30') || 30,
          weight_ppf: parseFloat(r.weight_ppf || r.weight || r.Weight || r.weight_lbft || '83') || 83,
        }));
      if (mapped.length > 0) onChange(mapped);
    };

    if (ext === 'csv') {
      Papa.parse<Record<string, string>>(file, {
        header: true,
        skipEmptyLines: true,
        complete: (result) => parseRows(result.data),
      });
    } else if (ext === 'xlsx' || ext === 'xls') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const wb = XLSX.read(e.target?.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<Record<string, string>>(ws);
        parseRows(rows);
      };
      reader.readAsArrayBuffer(file);
    }
    // Reset input so same file can be re-imported
    if (fileInputRef.current) fileInputRef.current.value = '';
  };
```

Add the upload button in the footer, next to "Add Component":

```tsx
      {/* Footer */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button onClick={addComponent} type="button"
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors">
            <Plus size={14} /> Add Component
          </button>
          <button onClick={() => fileInputRef.current?.click()} type="button"
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors">
            <Upload size={14} /> Import CSV/Excel
          </button>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileImport} className="hidden" />
        </div>
        <span className="text-xs text-gray-500">
          {components.length} components &middot; Total: {totalLength.toFixed(0)} ft
        </span>
      </div>
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/charts/vb/BHAEditor.tsx
git commit -m "feat(vibrations): add CSV/Excel import to BHA Editor

Supports .csv (Papa Parse) and .xlsx/.xls (SheetJS) with flexible
column mapping (type/Type/component, od/OD/od_in, etc.).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Add Mud Rheology Fields to Frontend Operating Parameters

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx:29-49,66,167-178`
- Modify: `frontend/src/locales/es.json` and `frontend/src/locales/en.json`

**Step 1: Add i18n keys**

In `frontend/src/locales/es.json`, inside the `"vibrations"` object (after `"frictionCoeff"` key), add:

```json
    "pvCp": "PV (cP)",
    "ypLbf": "YP (lbf/100ft²)",
    "flowRate": "Gasto (gpm)",
```

In `frontend/src/locales/en.json`, same location:

```json
    "pvCp": "PV (cP)",
    "ypLbf": "YP (lbf/100ft²)",
    "flowRate": "Flow Rate (gpm)",
```

**Step 2: Add to params state and optional fields**

In `VibrationsModule.tsx`, add new keys to the `params` initial state (after `mud_weight_ppg: 10.0,` on line 42):

```tsx
    pv_cp: undefined,
    yp_lbf_100ft2: undefined,
    flow_rate_gpm: undefined,
```

Add them to the `optionalFields` Set (line 66):

```tsx
  const optionalFields = new Set(['stabilizer_spacing_ft', 'ucs_psi', 'n_blades', 'pv_cp', 'yp_lbf_100ft2', 'flow_rate_gpm']);
```

**Step 3: Add the 3 new fields to the Operating Parameters grid**

In the Operating Parameters field array (lines 167-178), add the 3 new fields after `mud_weight_ppg`:

```tsx
                    { key: 'mud_weight_ppg', label: t('vibrations.mudWeight'), step: '0.5' },
                    { key: 'pv_cp', label: t('vibrations.pvCp'), step: '1', placeholder: 'Opcional' },
                    { key: 'yp_lbf_100ft2', label: t('vibrations.ypLbf'), step: '1', placeholder: 'Opcional' },
                    { key: 'flow_rate_gpm', label: t('vibrations.flowRate'), step: '50', placeholder: 'Opcional' },
```

**Step 4: Also pass PV/YP in the FEA call**

In the `calculateFEA` callback (line 106), add after `mud_weight_ppg`:

```tsx
        pv_cp: params.pv_cp || undefined,
        yp_lbf_100ft2: params.yp_lbf_100ft2 || undefined,
```

**Step 5: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/components/VibrationsModule.tsx frontend/src/locales/es.json frontend/src/locales/en.json
git commit -m "feat(vibrations): add PV, YP, flow rate inputs to Operating Parameters

Three new optional fields in the input panel with i18n labels (ES/EN).
PV/YP passed to FEA endpoint for improved damping calculation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Create Wellbore Section Editor Component

**Files:**
- Create: `frontend/src/components/charts/vb/WellboreSectionEditor.tsx`

**Step 1: Create the wellbore section editor**

Create `frontend/src/components/charts/vb/WellboreSectionEditor.tsx`:

```tsx
/**
 * WellboreSectionEditor.tsx — Wellbore section editor for casing/liner/open hole.
 * Allows defining the wellbore geometry from surface to TD.
 */
import React from 'react';
import { Plus, Trash2 } from 'lucide-react';

export interface WellboreSection {
  section_type: string;
  top_md_ft: number;
  bottom_md_ft: number;
  id_in: number;
}

interface WellboreSectionEditorProps {
  sections: WellboreSection[];
  onChange: (sections: WellboreSection[]) => void;
}

const SECTION_TYPES = [
  'surface_casing',
  'intermediate_casing',
  'production_casing',
  'liner',
  'open_hole',
];

const SECTION_LABELS: Record<string, string> = {
  surface_casing: 'Csg Superficial',
  intermediate_casing: 'Csg Intermedio',
  production_casing: 'Csg Producción',
  liner: 'Liner',
  open_hole: 'Open Hole',
};

const DEFAULT_BY_SECTION: Record<string, Partial<WellboreSection>> = {
  surface_casing:       { id_in: 18.0, top_md_ft: 0, bottom_md_ft: 500 },
  intermediate_casing:  { id_in: 12.347, top_md_ft: 0, bottom_md_ft: 5000 },
  production_casing:    { id_in: 8.681, top_md_ft: 0, bottom_md_ft: 10000 },
  liner:                { id_in: 6.094, top_md_ft: 8000, bottom_md_ft: 12000 },
  open_hole:            { id_in: 8.5, top_md_ft: 10000, bottom_md_ft: 12500 },
};

const TYPE_COLORS: Record<string, string> = {
  surface_casing: 'bg-blue-500/20 text-blue-300',
  intermediate_casing: 'bg-cyan-500/20 text-cyan-300',
  production_casing: 'bg-green-500/20 text-green-300',
  liner: 'bg-amber-500/20 text-amber-300',
  open_hole: 'bg-rose-500/20 text-rose-300',
};

const PRESETS: Record<string, WellboreSection[]> = {
  'Vertical Simple': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 500, id_in: 18.0 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 8000, id_in: 8.681 },
    { section_type: 'open_hole', top_md_ft: 8000, bottom_md_ft: 10000, id_in: 8.5 },
  ],
  'Direccional con Liner': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 1000, id_in: 18.0 },
    { section_type: 'intermediate_casing', top_md_ft: 0, bottom_md_ft: 6000, id_in: 12.347 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 10000, id_in: 8.681 },
    { section_type: 'liner', top_md_ft: 9500, bottom_md_ft: 13000, id_in: 6.094 },
    { section_type: 'open_hole', top_md_ft: 13000, bottom_md_ft: 15000, id_in: 6.125 },
  ],
  'Pozo Profundo': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 2000, id_in: 18.0 },
    { section_type: 'intermediate_casing', top_md_ft: 0, bottom_md_ft: 8000, id_in: 12.347 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 14000, id_in: 8.681 },
    { section_type: 'open_hole', top_md_ft: 14000, bottom_md_ft: 18000, id_in: 8.5 },
  ],
};

const WellboreSectionEditor: React.FC<WellboreSectionEditorProps> = ({ sections, onChange }) => {

  const addSection = () => {
    const defaults = DEFAULT_BY_SECTION['open_hole'];
    onChange([...sections, { section_type: 'open_hole', ...defaults } as WellboreSection]);
  };

  const removeSection = (index: number) => {
    onChange(sections.filter((_, i) => i !== index));
  };

  const updateSection = (index: number, field: keyof WellboreSection, value: string | number) => {
    const updated = [...sections];
    if (field === 'section_type') {
      const newType = value as string;
      const defaults = DEFAULT_BY_SECTION[newType] || {};
      updated[index] = { ...updated[index], ...defaults, section_type: newType };
    } else {
      updated[index] = { ...updated[index], [field]: typeof value === 'string' ? parseFloat(value) || 0 : value };
    }
    onChange(updated);
  };

  const lastShoe = sections
    .filter(s => s.section_type !== 'open_hole')
    .reduce((max, s) => Math.max(max, s.bottom_md_ft), 0);
  const td = sections.reduce((max, s) => Math.max(max, s.bottom_md_ft), 0);
  const openHoleLength = td - lastShoe;

  return (
    <div className="space-y-3">
      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        {Object.keys(PRESETS).map(name => (
          <button key={name} type="button"
            onClick={() => onChange([...PRESETS[name]])}
            className="px-3 py-1 text-xs rounded-md border bg-white/5 border-white/10 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors"
          >
            {name}
          </button>
        ))}
      </div>

      {/* Section Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-white/10">
              <th className="text-left py-2 px-1">Tipo</th>
              <th className="text-right py-2 px-1">Top MD (ft)</th>
              <th className="text-right py-2 px-1">Bottom MD (ft)</th>
              <th className="text-right py-2 px-1">ID (in)</th>
              <th className="py-2 px-1 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {sections.map((sec, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="py-1 px-1">
                  <select value={sec.section_type}
                    onChange={e => updateSection(i, 'section_type', e.target.value)}
                    className={`bg-transparent border border-white/10 rounded px-2 py-1 text-xs ${TYPE_COLORS[sec.section_type] || 'text-gray-300'}`}>
                    {SECTION_TYPES.map(t => <option key={t} value={t}>{SECTION_LABELS[t]}</option>)}
                  </select>
                </td>
                {(['top_md_ft', 'bottom_md_ft', 'id_in'] as const).map(field => (
                  <td key={field} className="py-1 px-1">
                    <input type="number"
                      value={sec[field]}
                      step={field === 'id_in' ? '0.125' : '100'}
                      onChange={e => updateSection(i, field, e.target.value)}
                      className="w-full text-right bg-white/5 border border-white/10 rounded px-2 py-1 text-xs focus:border-rose-500 focus:outline-none"
                    />
                  </td>
                ))}
                <td className="py-1 px-1">
                  <button onClick={() => removeSection(i)}
                    className="p-1 text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center">
        <button onClick={addSection} type="button"
          className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors">
          <Plus size={14} /> Add Section
        </button>
        <div className="text-xs text-gray-500 space-x-3">
          {lastShoe > 0 && <span>Shoe: {lastShoe.toLocaleString()} ft</span>}
          {openHoleLength > 0 && <span>OH: {openHoleLength.toLocaleString()} ft</span>}
          {td > 0 && <span>TD: {td.toLocaleString()} ft</span>}
        </div>
      </div>
    </div>
  );
};

export default WellboreSectionEditor;
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/charts/vb/WellboreSectionEditor.tsx
git commit -m "feat(vibrations): add Wellbore Section Editor component

Supports surface/intermediate/production casing, liner, and open hole.
Presets: Vertical Simple, Direccional con Liner, Pozo Profundo.
Displays shoe depth, open hole length, and TD in footer.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Restructure VibrationsModule Input Panel

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx:220-243`
- Modify: `frontend/src/locales/es.json`, `frontend/src/locales/en.json`

**Step 1: Add i18n keys for the new section**

In `frontend/src/locales/es.json`, change `"bha": "Configuración BHA"` to:

```json
    "sections": {
      "operating": "Parámetros Operativos",
      "wellbore": "Configuración del Agujero"
    },
```

In `frontend/src/locales/en.json`, same:

```json
    "sections": {
      "operating": "Operating Parameters",
      "wellbore": "Wellbore Configuration"
    },
```

**Step 2: Add wellbore state and import**

In `VibrationsModule.tsx`, add import:

```tsx
import WellboreSectionEditor, { type WellboreSection } from './charts/vb/WellboreSectionEditor';
import { Layers } from 'lucide-react';
```

Add state after `showBhaEditor` (line 55):

```tsx
  const [wellboreSections, setWellboreSections] = useState<WellboreSection[]>([]);
```

**Step 3: Replace "BHA Configuration" section with "Wellbore Configuration"**

Replace the entire `{/* BHA Configuration */}` block (lines 220-243, the `<div>` with `h3 = t('vibrations.sections.bha')`) with:

```tsx
              {/* Wellbore Configuration */}
              <div>
                <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                  <Layers size={18} />
                  {t('vibrations.sections.wellbore')}
                </h3>
                <div className="glass-panel p-4 rounded-xl border border-white/5">
                  <WellboreSectionEditor sections={wellboreSections} onChange={setWellboreSections} />
                </div>
              </div>
```

**Step 4: Keep BHA simplified params as hidden fallback**

The original BHA params (`bha_length_ft`, `bha_od_in`, etc.) remain in the `params` state — they're still used when the user runs the standard vibrations analysis without the FEA BHA editor. They just no longer have their own UI section (the BHA Editor replaced them for detailed input, the simple params serve as defaults).

However, the DP params (`dp_od_in`, `dp_id_in`, `dp_weight_lbft`) should be moved into the Operating Parameters grid since they're needed for the standard analysis. Add them after `friction_factor`:

```tsx
                    { key: 'dp_od_in', label: t('vibrations.dpOD'), step: '0.125' },
                    { key: 'dp_id_in', label: t('vibrations.dpID'), step: '0.125' },
                    { key: 'dp_weight_lbft', label: t('vibrations.dpWeight'), step: '1' },
```

**Step 5: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/components/VibrationsModule.tsx frontend/src/locales/es.json frontend/src/locales/en.json
git commit -m "feat(vibrations): replace BHA Configuration with Wellbore Configuration

Rename section to 'Configuración del Agujero' with WellboreSectionEditor
supporting casing/liner/open hole sections. DP params moved to Operating.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Full Stack Verification

**Files:** None (verification only)

**Step 1: Run ALL backend tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && /Library/Frameworks/Python.framework/Versions/3.13/bin/pytest tests/unit/test_fea_engine.py tests/unit/test_vibrations_engine.py -v`
Expected: All tests PASS (76 total: 49 vibrations + 27 FEA)

**Step 2: Verify frontend builds**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Verify git log**

Run: `git log --oneline feat/vibrations-wellbore-config --not feat/fea-vibrations`
Expected: 9 clean commits

---

## Summary

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| 1 | Add PV/YP/flow_rate to schemas | `schemas/vibrations.py` | 0 (backward-compat) |
| 2 | Add WellboreSection schema | `schemas/vibrations.py` | 0 (backward-compat) |
| 3 | Upgrade FEA damping with PV/YP | `fea.py` + test | 3 |
| 4 | Wire new fields through routes | `routes/modules/vibrations.py` | 0 |
| 5 | Install Papa Parse + SheetJS | `package.json` | 0 |
| 6 | CSV/Excel import for BHA Editor | `BHAEditor.tsx` | 0 (UI) |
| 7 | Mud rheology in Operating Params | `VibrationsModule.tsx` + locales | 0 (UI) |
| 8 | Wellbore Section Editor component | `WellboreSectionEditor.tsx` | 0 (UI) |
| 9 | Restructure input panel | `VibrationsModule.tsx` + locales | 0 (UI) |
| 10 | Full stack verification | none | smoke test |

**Total: 3 new tests, 1 new frontend component, 1 modified component, 2 modified backend files, 10 commits.**

**New UI Layout after completion:**

```
1. Parámetros Operativos
   - WOB, RPM, ROP, Torque, Bit diameter
   - Mud weight, PV, YP, Flow rate        ← NEW
   - Hole diameter, Inclination, Friction
   - DP OD, DP ID, DP weight              ← MOVED from BHA Config
   - Stabilizer spacing, Blades PDC
   - UCS (with lithology presets)

2. Configuración del Agujero              ← RENAMED from "Configuración BHA"
   - Presets: Vertical Simple, Direccional con Liner, Pozo Profundo
   - Table: section_type | Top MD | Bottom MD | ID
   - Footer: Shoe depth, OH length, TD

3. BHA Detallado (FEA)                    ← EXISTING (enhanced)
   - Presets: Standard Rotary, Motor BHA, RSS BHA
   - Table: type | OD | ID | Length | Weight
   - Import CSV/Excel button              ← NEW
   - Run FEA Analysis button

4. [Analizar Vibraciones button]
```
