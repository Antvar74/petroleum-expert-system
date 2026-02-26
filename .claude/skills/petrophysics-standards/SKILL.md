---
name: petrophysics-standards
description: Petroleum petrophysics calculation standards — Archie, Simandoux, Indonesia Sw models, net pay cutoffs, and log interpretation
---

# Petrophysics Engineering Standards

## Water Saturation Models

### Archie (1942) — Clean Sands
```
Sw = [(a × Rw) / (φ^m × Rt)]^(1/n)
```
- a = tortuosity factor (typically 0.62-1.0)
- m = cementation exponent (1.8-2.2)
- n = saturation exponent (typically 2.0)
- Rw = formation water resistivity (ohm·m)
- Use when: Vshale < 0.10

### Simandoux (1963) — Shaly Sands
```
1/Rt = (φ^m × Sw^n) / (a × Rw) + (Vsh × Sw) / Rsh
```
- Iterative solution required
- Use when: 0.10 ≤ Vshale ≤ 0.40

### Indonesia (Poupon-Leveaux 1971) — Highly Shaly
```
1/√Rt = (Vsh^(1-Vsh/2)) / √Rsh + (φ^(m/2) × Sw^(n/2)) / √(a × Rw)
```
- Use when: Vshale > 0.40 or Indonesian-type formations

### Auto-Selection Logic
```python
if vshale_avg < 0.10: model = "archie"
elif vshale_avg < 0.40: model = "simandoux"
else: model = "indonesia"
```

## Porosity Calculations

### Density Porosity
```
φ_density = (ρ_matrix - ρ_bulk) / (ρ_matrix - ρ_fluid)
```
- Sandstone: ρ_matrix = 2.65 g/cc
- Limestone: ρ_matrix = 2.71 g/cc
- Dolomite: ρ_matrix = 2.87 g/cc
- ρ_fluid = 1.0 g/cc (water) or 1.1 (salt mud)

### Neutron-Density Crossplot
- Gas effect: φ_neutron < φ_density (crossover)
- Shale effect: φ_neutron > φ_density
- Clean water sand: φ_neutron ≈ φ_density

## Vshale (Gamma Ray)
```
Vsh_linear = (GR - GR_clean) / (GR_shale - GR_clean)
```
Clamp to [0, 1].

## Net Pay Cutoffs (typical)
| Parameter | Cutoff | Notes |
|-----------|--------|-------|
| Porosity (φ) | ≥ 0.08 (8%) | Reservoir quality minimum |
| Water Saturation (Sw) | ≤ 0.60 (60%) | Hydrocarbon bearing |
| Vshale | ≤ 0.40 (40%) | Non-shale |
| Minimum bed thickness | ≥ 2 ft | Resolvable on logs |

## Permeability (Timur 1968)
```
k = (100 × φ^4.4) / (Sw_irr²)  [md]
```
Valid for: 0.05 < φ < 0.35, sandstones.

## Skin Factor (Karakas-Tariq 1991)
```
s_total = s_perforation + s_vertical_crushed + s_wellbore
```
- Optimum phasing: 90° or 120°
- SPF effect: higher density = lower skin
- Perforation length: deeper = lower skin (if clean)

## Hydrocarbon Type Classification
| Condition | Interpretation |
|-----------|---------------|
| φ_D ≈ φ_N, GR low | Clean water sand |
| φ_D > φ_N (crossover), GR low | Gas sand |
| φ_D < φ_N, GR high | Shale |
| Sw < 0.40, good φ | Oil/gas pay zone |
