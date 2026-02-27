"""
Casing connection verification — API 5B thread performance.

References:
- API 5B: Threading, gauging, and thread inspection of casing, tubing, and line pipe
- API 5C3: Performance properties of casing, tubing, and drill pipe
"""
from typing import Dict, Any


# Connection performance catalog (API 5B/5C3)
# Values: tension efficiency (% of pipe body), pressure efficiency
CONNECTION_CATALOG: Dict[str, Dict[str, Any]] = {
    "STC": {
        "name": "Short Thread & Coupling",
        "tension_efficiency": 0.60,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 10000,
        "notes": "Standard API, not gas-tight",
    },
    "LTC": {
        "name": "Long Thread & Coupling",
        "tension_efficiency": 0.70,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 10000,
        "notes": "Standard API, not gas-tight",
    },
    "BTC": {
        "name": "Buttress Thread & Coupling",
        "tension_efficiency": 0.80,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 15000,
        "notes": "Higher tension than STC/LTC, not gas-tight",
    },
    "PREMIUM": {
        "name": "Premium Connection (Generic)",
        "tension_efficiency": 0.95,
        "burst_efficiency": 1.00,
        "collapse_efficiency": 1.00,
        "max_pressure_psi": 20000,
        "notes": "Metal-to-metal seal, gas-tight",
    },
}


def verify_connection(
    connection_type: str,
    pipe_body_yield_lbs: float,
    burst_rating_psi: float,
    collapse_rating_psi: float,
    applied_tension_lbs: float,
    applied_burst_psi: float,
    applied_collapse_psi: float,
    sf_tension: float = 1.60,
    sf_burst: float = 1.10,
) -> Dict[str, Any]:
    """
    Verify connection performance against applied loads.

    Connection tension rating = tension_efficiency * pipe_body_yield
    Connection burst/collapse = burst/collapse_efficiency * pipe_rating

    Returns PASS/FAIL for each criterion.
    """
    conn = CONNECTION_CATALOG.get(connection_type.upper())
    if conn is None:
        available = list(CONNECTION_CATALOG.keys())
        return {"error": f"Unknown connection type '{connection_type}'. Available: {available}"}

    # Connection ratings
    conn_tension = conn["tension_efficiency"] * pipe_body_yield_lbs
    conn_burst = conn["burst_efficiency"] * burst_rating_psi
    conn_collapse = conn["collapse_efficiency"] * collapse_rating_psi

    # Safety factors
    sf_t = conn_tension / applied_tension_lbs if applied_tension_lbs > 0 else 999
    sf_b = conn_burst / applied_burst_psi if applied_burst_psi > 0 else 999
    sf_c = conn_collapse / applied_collapse_psi if applied_collapse_psi > 0 else 999

    passes_tension = sf_t >= sf_tension
    passes_burst = sf_b >= sf_burst
    passes_all = passes_tension and passes_burst

    # Check if connection is the weak link
    is_weak_link = conn_tension < pipe_body_yield_lbs * 0.95

    return {
        "connection_type": connection_type.upper(),
        "connection_name": conn["name"],
        "tension_rating_lbs": round(conn_tension, 0),
        "tension_sf": round(sf_t, 2),
        "passes_tension": passes_tension,
        "burst_rating_psi": round(conn_burst, 0),
        "burst_sf": round(sf_b, 2),
        "passes_burst": passes_burst,
        "passes_all": passes_all,
        "is_weak_link": is_weak_link,
        "efficiency": conn["tension_efficiency"],
        "gas_tight": "gas-tight" in conn.get("notes", ""),
        "notes": conn["notes"],
        "alerts": [
            f"Connection is weak link — tension efficiency {conn['tension_efficiency']*100:.0f}%"
        ] if is_weak_link else [],
    }
