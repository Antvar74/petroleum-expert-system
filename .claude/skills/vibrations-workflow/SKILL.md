---
name: vibrations-workflow
description: Drilling vibrations analysis workflow — axial, lateral, torsional modes, MSE, stability index, and BHA optimization
---

# Vibrations Analysis Workflow

## Engine Location
`orchestrator/vibrations_engine/` with sub-modules:
- `pipeline.py` — Main orchestrator
- `critical_speeds.py` — Axial & lateral natural frequencies
- `stick_slip.py` — Torsional oscillation severity
- `mse.py` — Mechanical Specific Energy
- `stability.py` — Combined stability index
- `bit_excitation.py` — Bit-rock interaction frequency
- `fatigue.py` — Drillstring fatigue (Miner's rule)
- `stabilizers.py` — Stabilizer placement effects

## Vibration Modes

### Axial (Bit Bounce)
```
f_axial = (1/2π) × √(k/m_eff)
critical_rpm = 60 × f_axial
```
- Avoid operating at 1st, 2nd, 3rd harmonics
- Worse in hard formations, high WOB

### Lateral (Whirl)
- Forward whirl: tool joint contact with wellbore
- Backward whirl: BHA mass eccentricity
- Reference: Paslay & Dawson 1984
- Transfer Matrix Method for multi-component BHA
```
critical_rpm_lateral = 60 × f_lateral_hz
```

### Torsional (Stick-Slip)
```
severity_index = (τ_peak - τ_avg) / τ_avg
```
- None: < 0.2
- Mild: 0.2 - 0.5
- Severe: 0.5 - 1.0
- Critical: > 1.0

## MSE (Mechanical Specific Energy)
```
MSE = (WOB/A_bit) + (120π × RPM × T) / (A_bit × ROP)
```
- Efficiency: η = UCS / MSE × 100%
- Low MSE = efficient drilling
- High MSE = bit dulling, vibrations, or founder point

## Stability Index
Weighted composite (0-100):
- Axial: 20% weight
- Lateral: 30% weight
- Torsional: 35% weight
- MSE: 15% weight

Status classification:
- Stable: ≥ 80 (green)
- Marginal: 60-79 (yellow)
- Unstable: 40-59 (orange)
- Critical: < 40 (red)

## Bit Excitation Frequencies
- PDC: f_exc = (N_blades × RPM) / 60 Hz
- Tricone: f_exc = (3 × RPM) / 60 Hz
- Resonance risk: |f_exc - f_natural| < 0.2 × f_natural

## Fatigue (Miner's Rule)
```
D_cumulative = Σ(n_i / N_i)
```
- Failure when D ≥ 1.0
- S-N curves by pipe grade (E75, X95, G105, S135)

## Input Parameters
| Parameter | Unit | Typical Range |
|-----------|------|--------------|
| WOB | klb | 5-60 |
| RPM | rev/min | 40-200 |
| ROP | ft/h | 10-300 |
| Torque | ft-lbf | 2000-50000 |
| Bit diameter | in | 6.0-17.5 |
| BHA length | ft | 100-500 |
| Mud weight | ppg | 8.5-18.0 |
| UCS | psi | 1000-30000 |
| Stabilizer spacing | ft | 30-90 |
| Number of blades | - | 3-8 (PDC) |
