"""
Completion Design Engine — constants, gun databases, and correction factor ranges.

References:
- API RP 19B: Evaluation of Well Perforators
- Karakas & Tariq (1991): SPE 18247
"""
from typing import Dict, Any, List

# -------------------------------------------------------------------
# Gun database — simple lookup by gun OD
# (Schlumberger PowerJet, Halliburton Piranha-class, Baker Atlas)
# -------------------------------------------------------------------
GUN_DATABASE: Dict[str, Dict[str, Any]] = {
    "2-1/8": {"od_in": 2.125, "max_casing_id": 4.090, "typical_spf": 4,  "phasing": [0, 60, 90]},
    "2-1/2": {"od_in": 2.500, "max_casing_id": 4.892, "typical_spf": 4,  "phasing": [0, 60, 90]},
    "3-3/8": {"od_in": 3.375, "max_casing_id": 6.276, "typical_spf": 6,  "phasing": [60, 90, 120]},
    "4-5/8": {"od_in": 4.625, "max_casing_id": 8.535, "typical_spf": 12, "phasing": [60, 90, 120]},
    "5":     {"od_in": 5.000, "max_casing_id": 8.921, "typical_spf": 12, "phasing": [60, 90, 120]},
    "7":     {"od_in": 7.000, "max_casing_id": 12.415, "typical_spf": 6, "phasing": [60, 120]},
}

# -------------------------------------------------------------------
# Expanded gun catalog — detailed entries with pressure/temp ratings
# -------------------------------------------------------------------
GUN_CATALOG: List[Dict[str, Any]] = [
    # Through-tubing wireline guns (small OD)
    {"name": "WL-2125-STD", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
     "ehd_in": 0.26, "penetration_berea_in": 8.5,  "spf": 4,  "phasing": 0,
     "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 4.090},
    {"name": "WL-2125-DP", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
     "ehd_in": 0.30, "penetration_berea_in": 10.0, "spf": 4,  "phasing": 60,
     "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 4.090},
    {"name": "WL-2500-STD", "od_in": 2.500, "gun_type": "wireline", "carrier_od_in": 2.500,
     "ehd_in": 0.29, "penetration_berea_in": 11.2, "spf": 4,  "phasing": 60,
     "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 4.892},
    {"name": "WL-2500-HP", "od_in": 2.500, "gun_type": "wireline", "carrier_od_in": 2.500,
     "ehd_in": 0.33, "penetration_berea_in": 12.8, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 4.892},
    {"name": "WL-2750-BH", "od_in": 2.750, "gun_type": "wireline", "carrier_od_in": 2.750,
     "ehd_in": 0.32, "penetration_berea_in": 13.5, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 5.524},
    # Mid-range casing guns (wireline & TCP)
    {"name": "WL-3375-STD", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
     "ehd_in": 0.36, "penetration_berea_in": 15.0, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 6.276},
    {"name": "WL-3375-DP", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
     "ehd_in": 0.42, "penetration_berea_in": 17.3, "spf": 6,  "phasing": 90,
     "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 6.276},
    {"name": "TCP-3375-UB", "od_in": 3.375, "gun_type": "tcp", "carrier_od_in": 3.375,
     "ehd_in": 0.38, "penetration_berea_in": 16.5, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 22000, "max_temp_f": 450, "max_casing_id": 6.276},
    # Large casing guns — high performance
    {"name": "WL-4500-STD", "od_in": 4.500, "gun_type": "wireline", "carrier_od_in": 4.500,
     "ehd_in": 0.42, "penetration_berea_in": 20.5, "spf": 12, "phasing": 60,
     "max_pressure_psi": 20000, "max_temp_f": 400, "max_casing_id": 8.535},
    {"name": "TCP-4500-DP", "od_in": 4.500, "gun_type": "tcp", "carrier_od_in": 4.500,
     "ehd_in": 0.50, "penetration_berea_in": 23.0, "spf": 12, "phasing": 60,
     "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.535},
    {"name": "WL-4625-HP", "od_in": 4.625, "gun_type": "wireline", "carrier_od_in": 4.625,
     "ehd_in": 0.45, "penetration_berea_in": 21.8, "spf": 12, "phasing": 90,
     "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 8.535},
    {"name": "TCP-4625-DP", "od_in": 4.625, "gun_type": "tcp", "carrier_od_in": 4.625,
     "ehd_in": 0.52, "penetration_berea_in": 24.5, "spf": 12, "phasing": 60,
     "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.535},
    {"name": "CT-4500-HP", "od_in": 4.500, "gun_type": "coiled_tubing", "carrier_od_in": 4.500,
     "ehd_in": 0.44, "penetration_berea_in": 21.0, "spf": 12, "phasing": 60,
     "max_pressure_psi": 15000, "max_temp_f": 400, "max_casing_id": 8.535},
    {"name": "WL-5000-STD", "od_in": 5.000, "gun_type": "wireline", "carrier_od_in": 5.000,
     "ehd_in": 0.48, "penetration_berea_in": 23.5, "spf": 12, "phasing": 90,
     "max_pressure_psi": 20000, "max_temp_f": 450, "max_casing_id": 8.921},
    {"name": "TCP-5000-DP", "od_in": 5.000, "gun_type": "tcp", "carrier_od_in": 5.000,
     "ehd_in": 0.55, "penetration_berea_in": 26.0, "spf": 12, "phasing": 60,
     "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 8.921},
    {"name": "WL-4750-EXT", "od_in": 4.750, "gun_type": "wireline", "carrier_od_in": 4.750,
     "ehd_in": 0.46, "penetration_berea_in": 22.0, "spf": 12, "phasing": 120,
     "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 8.921},
    # Large-bore guns for big casing
    {"name": "TCP-7000-STD", "od_in": 7.000, "gun_type": "tcp", "carrier_od_in": 7.000,
     "ehd_in": 0.70, "penetration_berea_in": 32.0, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 20000, "max_temp_f": 400, "max_casing_id": 12.415},
    {"name": "TCP-7000-DP", "od_in": 7.000, "gun_type": "tcp", "carrier_od_in": 7.000,
     "ehd_in": 0.85, "penetration_berea_in": 38.0, "spf": 6,  "phasing": 120,
     "max_pressure_psi": 25000, "max_temp_f": 500, "max_casing_id": 12.415},
    {"name": "WL-7000-HP", "od_in": 7.000, "gun_type": "wireline", "carrier_od_in": 7.000,
     "ehd_in": 0.72, "penetration_berea_in": 34.0, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 18000, "max_temp_f": 400, "max_casing_id": 12.415},
    # HPHT specialty guns
    {"name": "TCP-3375-HPHT", "od_in": 3.375, "gun_type": "tcp", "carrier_od_in": 3.375,
     "ehd_in": 0.34, "penetration_berea_in": 14.0, "spf": 6,  "phasing": 60,
     "max_pressure_psi": 30000, "max_temp_f": 550, "max_casing_id": 6.276},
    {"name": "TCP-4625-HPHT", "od_in": 4.625, "gun_type": "tcp", "carrier_od_in": 4.625,
     "ehd_in": 0.44, "penetration_berea_in": 20.0, "spf": 12, "phasing": 60,
     "max_pressure_psi": 30000, "max_temp_f": 550, "max_casing_id": 8.535},
    # Economy / shallow well guns
    {"name": "WL-2125-ECO", "od_in": 2.125, "gun_type": "wireline", "carrier_od_in": 2.125,
     "ehd_in": 0.22, "penetration_berea_in": 6.0,  "spf": 2,  "phasing": 0,
     "max_pressure_psi": 10000, "max_temp_f": 300, "max_casing_id": 4.090},
    {"name": "WL-3375-ECO", "od_in": 3.375, "gun_type": "wireline", "carrier_od_in": 3.375,
     "ehd_in": 0.30, "penetration_berea_in": 11.0, "spf": 4,  "phasing": 0,
     "max_pressure_psi": 10000, "max_temp_f": 300, "max_casing_id": 6.276},
]

# API RP 19B correction factor ranges
STRESS_CF_RANGE = (0.60, 1.00)   # Effective stress correction
TEMP_CF_RANGE   = (0.85, 1.10)   # Temperature correction
FLUID_CF_RANGE  = (0.70, 1.00)   # Completion fluid correction
