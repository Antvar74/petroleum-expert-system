"""
Petrophysics Engine — Constants and reference data.

Common LAS mnemonic mappings and lithology matrix parameters.
"""

# Common LAS mnemonic mapping to standard names
MNEMONIC_MAP = {
    "DEPT": "md", "DEPTH": "md", "MD": "md", "TDEP": "md",
    "GR": "gr", "SGR": "gr", "CGR": "gr", "ECGR": "gr",
    "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob", "DENSITY": "rhob",
    "NPHI": "nphi", "TNPH": "nphi", "PHIN": "nphi", "NEU": "nphi", "CNPHI": "nphi",
    "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt", "RILM": "rt",
    "RESD": "rt", "RD": "rt", "AT90": "rt", "HDRS": "rt",
    "DT": "dt", "DTC": "dt", "DTCO": "dt", "SONIC": "dt",
    "CALI": "caliper", "CAL": "caliper", "HCAL": "caliper",
    "SP": "sp",
    "DRHO": "drho", "DPHI": "dphi",
    "PE": "pe", "PEF": "pe",
}

# Lithology matrix parameters for crossplots
LITHOLOGY = {
    "sandstone":  {"rho_ma": 2.65, "nphi_ma": -0.02, "dt_ma": 55.5},
    "limestone":  {"rho_ma": 2.71, "nphi_ma": 0.00, "dt_ma": 47.5},
    "dolomite":   {"rho_ma": 2.87, "nphi_ma": 0.02, "dt_ma": 43.5},
}
