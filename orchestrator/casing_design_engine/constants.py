"""
Casing Design Constants

Casing grade properties (API 5CT), default safety factors (NORSOK D-010),
and expanded casing catalog with burst/collapse ratings.

References:
- API 5CT: Specification for Casing and Tubing
- NORSOK D-010: Well Integrity in Drilling and Well Operations
"""

from typing import Dict, List, Any


# ------------------------------------------------------------------
# Casing Grade Database (API 5CT)
# ------------------------------------------------------------------
CASING_GRADES: Dict[str, Dict[str, Any]] = {
    "J55":  {"yield_psi": 55000,  "tensile_psi": 75000,  "color": "#4CAF50"},
    "K55":  {"yield_psi": 55000,  "tensile_psi": 95000,  "color": "#66BB6A"},
    "L80":  {"yield_psi": 80000,  "tensile_psi": 95000,  "color": "#2196F3"},
    "N80":  {"yield_psi": 80000,  "tensile_psi": 100000, "color": "#42A5F5"},
    "C90":  {"yield_psi": 90000,  "tensile_psi": 100000, "color": "#FF9800"},
    "T95":  {"yield_psi": 95000,  "tensile_psi": 105000, "color": "#FFA726"},
    "C110": {"yield_psi": 110000, "tensile_psi": 120000, "color": "#F44336"},
    "P110": {"yield_psi": 110000, "tensile_psi": 125000, "color": "#EF5350"},
    "Q125": {"yield_psi": 125000, "tensile_psi": 135000, "color": "#9C27B0"},
}

# ------------------------------------------------------------------
# Standard Design Safety Factors (NORSOK D-010 / operator standards)
# ------------------------------------------------------------------
DEFAULT_SF: Dict[str, float] = {
    "burst": 1.10,
    "collapse": 1.00,   # API minimum; many operators use 1.0-1.125
    "tension": 1.60,     # body yield; connections may require 1.8
}

# ------------------------------------------------------------------
# Expanded Casing Catalog (API 5CT)
#
# Keys are nominal OD in inches (formatted to 3 decimals).
# Each entry: weight (ppf), ID (in), wall thickness (in), grade,
#             burst rating (psi), collapse rating (psi).
# ------------------------------------------------------------------
CASING_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "4.500": [
        {"weight": 9.50, "id": 4.090, "wall": 0.205, "grade": "J55", "burst": 4380, "collapse": 2760},
        {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "J55", "burst": 6230, "collapse": 5430},
        {"weight": 11.60, "id": 3.920, "wall": 0.290, "grade": "N80", "burst": 9060, "collapse": 8600},
        {"weight": 13.50, "id": 3.810, "wall": 0.345, "grade": "N80", "burst": 10790, "collapse": 11080},
        {"weight": 15.10, "id": 3.680, "wall": 0.410, "grade": "P110", "burst": 17530, "collapse": 17350},
    ],
    "5.500": [
        {"weight": 14.00, "id": 5.012, "wall": 0.244, "grade": "J55", "burst": 4270, "collapse": 2870},
        {"weight": 15.50, "id": 4.950, "wall": 0.275, "grade": "J55", "burst": 4810, "collapse": 3660},
        {"weight": 17.00, "id": 4.892, "wall": 0.304, "grade": "N80", "burst": 7740, "collapse": 6070},
        {"weight": 20.00, "id": 4.778, "wall": 0.361, "grade": "N80", "burst": 9190, "collapse": 8440},
        {"weight": 23.00, "id": 4.670, "wall": 0.415, "grade": "P110", "burst": 14510, "collapse": 13680},
    ],
    "7.000": [
        {"weight": 17.00, "id": 6.538, "wall": 0.231, "grade": "J55", "burst": 3180, "collapse": 1420},
        {"weight": 23.00, "id": 6.366, "wall": 0.317, "grade": "J55", "burst": 4360, "collapse": 3270},
        {"weight": 26.00, "id": 6.276, "wall": 0.362, "grade": "N80", "burst": 7250, "collapse": 5410},
        {"weight": 29.00, "id": 6.184, "wall": 0.408, "grade": "N80", "burst": 8160, "collapse": 6980},
        {"weight": 32.00, "id": 6.094, "wall": 0.453, "grade": "L80", "burst": 9070, "collapse": 8240},
        {"weight": 35.00, "id": 6.004, "wall": 0.498, "grade": "C90", "burst": 11210, "collapse": 10520},
        {"weight": 38.00, "id": 5.920, "wall": 0.540, "grade": "P110", "burst": 14850, "collapse": 13290},
    ],
    "9.625": [
        {"weight": 36.00, "id": 8.921, "wall": 0.352, "grade": "J55", "burst": 3520, "collapse": 2020},
        {"weight": 40.00, "id": 8.835, "wall": 0.395, "grade": "J55", "burst": 3950, "collapse": 2570},
        {"weight": 43.50, "id": 8.755, "wall": 0.435, "grade": "N80", "burst": 6330, "collapse": 4130},
        {"weight": 47.00, "id": 8.681, "wall": 0.472, "grade": "N80", "burst": 6870, "collapse": 4760},
        {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "C90", "burst": 8930, "collapse": 7040},
        {"weight": 53.50, "id": 8.535, "wall": 0.545, "grade": "P110", "burst": 10910, "collapse": 9120},
    ],
    "10.750": [
        {"weight": 32.75, "id": 10.192, "wall": 0.279, "grade": "J55", "burst": 2500, "collapse": 920},
        {"weight": 40.50, "id": 10.050, "wall": 0.350, "grade": "J55", "burst": 3140, "collapse": 1580},
        {"weight": 45.50, "id": 9.950, "wall": 0.400, "grade": "N80", "burst": 5210, "collapse": 2710},
        {"weight": 51.00, "id": 9.850, "wall": 0.450, "grade": "N80", "burst": 5860, "collapse": 3480},
        {"weight": 55.50, "id": 9.760, "wall": 0.495, "grade": "P110", "burst": 8890, "collapse": 5210},
    ],
    "13.375": [
        {"weight": 48.00, "id": 12.715, "wall": 0.330, "grade": "J55", "burst": 2380, "collapse": 870},
        {"weight": 54.50, "id": 12.615, "wall": 0.380, "grade": "J55", "burst": 2740, "collapse": 1180},
        {"weight": 61.00, "id": 12.515, "wall": 0.430, "grade": "N80", "burst": 4510, "collapse": 1900},
        {"weight": 68.00, "id": 12.415, "wall": 0.480, "grade": "N80", "burst": 5030, "collapse": 2420},
        {"weight": 72.00, "id": 12.347, "wall": 0.514, "grade": "P110", "burst": 7430, "collapse": 3340},
    ],
    "20.000": [
        {"weight": 94.00, "id": 19.124, "wall": 0.438, "grade": "J55", "burst": 2110, "collapse": 520},
        {"weight": 106.50, "id": 18.936, "wall": 0.532, "grade": "K55", "burst": 2560, "collapse": 870},
        {"weight": 133.00, "id": 18.730, "wall": 0.635, "grade": "K55", "burst": 3060, "collapse": 1370},
    ],
}
