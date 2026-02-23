# Volve Field Dataset — V&V Reference Data

## About
The Volve field (North Sea, Norway) was operated by Equinor (Statoil) from 2008 to 2016.
Equinor released the complete field dataset in 2018 for research and education purposes.

## Download Instructions

1. Go to: https://data.equinor.com/dataset/Volve
2. Register (free) and download well log data for well **15/9-F-1**
3. Place LAS files in this directory: `data/volve/`
4. Run validation: `pytest tests/validation/test_validate_volve.py -v`

## Expected Files
- `15_9-F-1_logs.las` — Composite log (GR, RHOB, NPHI, RT, DT, CALI)

## Reference Values (Published by Equinor)
- Well: 15/9-F-1 (Hugin Formation, Upper Jurassic)
- Reservoir interval: ~3650–3700 m MD
- Average porosity: 20–25% (sandstone)
- Average Sw: 15–30% (hydrocarbon bearing)
- Formation water Rw: ~0.04 Ohm·m at formation temperature

## Notes
- Dataset is ~12 GB total; only LAS files are needed for petrophysics validation
- Tests auto-skip if data files are not present
