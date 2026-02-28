---
name: shot-efficiency-workflow
description: Shot efficiency (perforation) analysis workflow — log parsing, petrophysics, net pay identification, skin calculation, and interval ranking
---

# Shot Efficiency Analysis Workflow

## Engine Location
`orchestrator/shot_efficiency_engine/` with sub-modules:
- `pipeline.py` — Main orchestrator
- `log_parser.py` — Well log CSV validation
- `petrophysics.py` — Porosity, Sw, Vshale computation
- `permeability.py` — k estimation + HC type classification
- `net_pay.py` — Net pay interval identification
- `ranking.py` — Interval ranking by composite score
- `skin.py` — Karakas-Tariq perforation skin factor

## Pipeline Steps

### 1. Log Parsing
Input: CSV with columns [MD, GR, RHOB, NPHI, RT]
- Validate depth monotonicity
- Check value ranges (GR: 0-200, RHOB: 1.5-3.0, NPHI: -0.05-0.60, RT: 0.1-10000)
- Interpolate gaps if < 2 ft

### 2. Petrophysics
For each depth point:
1. Compute Vshale from GR (linear method)
2. Compute φ_density from RHOB
3. Auto-select Sw model based on avg Vshale
4. Compute Sw using selected model
5. Classify HC type from crossplot

### 3. Net Pay Identification
Apply cutoffs (configurable):
- φ ≥ φ_min (default 0.08)
- Sw ≤ Sw_max (default 0.60)
- Vsh ≤ Vsh_max (default 0.40)
Group contiguous qualifying points into intervals (min thickness 2 ft)

### 4. Permeability Estimation
For each net pay interval:
```
k_timur = (100 × φ_avg^4.4) / (Sw_irr²)
kh = k × h_net  [md·ft]
```

### 5. Skin Factor (Karakas-Tariq)
For each interval, given perforation parameters:
```
s_total = s_perforation + s_crushed_zone + s_wellbore
```
Parameters: SPF, phasing angle, perf length, perf diameter, crushed zone k ratio

### 6. Ranking
Composite score per interval:
```
Score = (φ - φ_min) + 10×(1 - Sw) + 10×(1 - Vsh) + 5×log10(kh)
```
Rank intervals: Best, 2nd, 3rd

## Output Structure
```json
{
  "summary": {
    "total_log_points": N,
    "net_pay_intervals_count": C,
    "total_net_pay_ft": H,
    "sw_model_used": "archie|simandoux|indonesia",
    "best_interval": { "top_md": X, "base_md": Y, "score": Z }
  },
  "processed_logs": [{ "md", "gr", "rhob", "nphi", "rt", "phi", "sw", "vsh" }],
  "intervals_with_skin": [{ "top_md", "base_md", "thickness", "avg_phi", "avg_sw", "avg_vsh", "kh", "skin_total", "score" }],
  "rankings": { "best": {...}, "second": {...}, "third": {...} }
}
```

## Frontend Charts
Located in `frontend/src/components/charts/se/`:
- LogTrackChart.tsx — Multi-log display (GR, RHOB, NPHI, Rt, net pay shading)
- NetPayIntervalChart.tsx — Net pay interval visualization
- IntervalRankingChart.tsx — Bar chart of interval scores
- SkinComponentsBar.tsx — Skin component breakdown
- CutoffSensitivityChart.tsx — Sensitivity analysis
