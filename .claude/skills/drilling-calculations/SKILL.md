---
name: drilling-calculations
description: Core drilling engineering calculations — torque & drag, hydraulics, well control, stuck pipe, and general oilfield formulas
---

# Drilling Engineering Calculations Reference

## Torque & Drag (Johancsik Soft-String, SPE 11380)

### Survey — Minimum Curvature
```
cos(dl) = cos(inc2-inc1) - sin(inc1)×sin(inc2)×(1-cos(azi2-azi1))
rf = (2/dl) × tan(dl/2)    [limit rf=1.0 for dl→0]
ΔTVD = (Δmd/2) × (cos(inc1) + cos(inc2)) × rf
DLS = degrees(dl) / Δmd × 100  [deg/100ft]
```

### Axial Force Model
- Direction factor: trip_out/back_ream = +1, trip_in/sliding = -1
- Normal force from curvature + gravity
- Drag = μ × N (friction × normal force)

## Hydraulics (API RP 13D)

### Bingham Plastic
```
Pipe:    ΔP = (PV×V×L)/(1500×d²) + (YP×L)/(225×d)         [laminar]
Annulus: ΔP = (PV×V×L)/(1000×(d2-d1)²) + (YP×L)/(200×(d2-d1))
```

### Bit Hydraulics
```
TFA = Σ(π/4 × nozzle_size²)
V_jet = Q / (3.117 × TFA)   [ft/s]
ΔP_bit = (MW × Q²) / (12032 × TFA²)  [psi]
HSI = (ΔP_bit × Q) / (1714 × A_bit)  [hp/in²]
```

### ECD
```
ECD = MW + (ΔP_annular / (0.052 × TVD))  [ppg]
```

### Surge/Swab
Pipe movement velocity → effective pressure change on formation.

## Well Control

### Kill Mud Weight
```
MW_kill = MW_original + SIDPP / (0.052 × TVD)  [ppg]
```

### Z-Factor (Dranchuk-Abou-Kassem)
Standing pseudo-critical properties:
```
T_pc = 168 + 325×SG - 12.5×SG²  [°R]
P_pc = 677 + 15×SG - 37.5×SG²   [psia]
```
Newton-Raphson with 11 DAK coefficients, tol=1e-6.

### Real Gas Law
```
V2 = V1 × (P1/P2) × (Z2/Z1) × (T2/T1)  [bbl]
```

### Barite Requirements
```
W_barite = 1490 × (MW_new - MW_old) / (35.0 - MW_new)  [lb/bbl]
```

## Stuck Pipe

### Free Point
```
L_free = (E × A × ΔL) / F_pull
```
Where: E=30e6 psi, A=π/4×(OD²-ID²), ΔL=measured stretch, F=pull force.

### Differential Sticking Force
```
F_ds = ΔP × A_contact × μ_cake
ΔP = (ECD - P_pore) × 0.052 × TVD
A_contact = π × pipe_od × contact_length × arc_fraction
```

## General Oilfield Constants

| Constant | Value | Use |
|----------|-------|-----|
| Hydrostatic | 0.052 psi/ft/ppg | Pressure from mud weight |
| Capacity | 1029.4 | bbl/ft from in² |
| Steel E | 30×10⁶ psi | Pipe stretch/buckling |
| Steel ρ | 490 lb/ft³ | String weight |
| Water ρ | 8.34 ppg | Freshwater reference |
| Barite SG | 4.20 | Weight material |
| g | 32.174 ft/s² | Gravity |

## Rheology Models

| Model | Parameters | When to use |
|-------|-----------|-------------|
| Bingham Plastic | PV, YP | Standard drilling fluids |
| Power Law | K, n | Non-Newtonian, polymer muds |
| Herschel-Bulkley | τ₀, K, n | Advanced (best fit), OBM |

FANN readings: 600, 300, 200, 100, 6, 3 RPM.
```
PV = θ600 - θ300  [cP]
YP = θ300 - PV    [lbf/100ft²]
n = 3.322 × log(θ600/θ300)
K = θ300 / (511^n)
```
