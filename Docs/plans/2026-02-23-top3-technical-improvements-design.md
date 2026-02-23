# PetroExpert — Top 3 Technical Improvements: Design Document

> **Date:** 2026-02-23
> **Goal:** Implement WITSML SOAP real client, drift-flux multiphase kick model, and DLIS parser — unified through a DataIngestion pipeline. Target: investor-ready architecture.
> **Approach:** Enfoque B — Pipeline de datos unificado.

---

## Context

### Debilidades identificadas (estado post-fase-5)

| Debilidad | Avance | Siguiente paso |
|-----------|--------|----------------|
| Simulacion transitoria | 70% | Drift-flux Zuber-Findlay |
| Petrofisica avanzada | 75% | DLIS parser |
| Validacion de campo | 50% | (fuera de scope esta iteracion) |
| Certificaciones API/ISO | 10% | (organizacional, fuera de scope) |
| WITSML real-time | 65% | SOAP real con zeep + mock mode |

### Decisiones de diseno

- **Pipeline unificado:** Un solo `DataIngestionService` normaliza LAS, DLIS y WITSML a formato comun
- **Mock-first WITSML:** Sin servidor real disponible, el client opera en mock mode para demos
- **Drift-flux basico:** Zuber-Findlay sin balance termico — suficiente para demo y paper SPE
- **Backward compatible:** Nada existente se rompe; todo es aditivo

---

## Architecture

```
                    +------------------------------+
                    |     DataIngestion Layer       |
                    |  (orchestrator/data_ingest.py)|
                    +------+-------+-------+-------+
                           |       |       |
                    +------+-+ +---+---+ +-+------+
                    |  LAS   | | DLIS  | | WITSML |
                    | (lasio)| |(dlisio| | (zeep) |
                    +---+----+ +--+----+ +---+----+
                        |         |          |
                        v         v          v
                    +-----------------------------+
                    |   Unified Dict/List Output   |
                    |  {md, gr, rhob, nphi, rt,    |
                    |   hookload, torque, rpm, ...} |
                    +-------------+---------------+
                                  |
                    +-------------+-------------+
                    v             v             v
              PetrophysicsEngine TransientFlow  RealTimeMonitor
              (Sw, Pickett)      (drift-flux)   (KPIs, alarms)
```

---

## Component 1: DataIngestionService

**File:** `orchestrator/data_ingest.py` (NEW)

### Responsibilities
- Parse LAS files via `lasio` and normalize column names
- Parse DLIS files via `dlisio` (graceful fallback if not installed)
- Accept pre-parsed WITSML data from WITSMLClient
- Output unified format: `List[Dict[str, float]]` with standardized keys

### Mnemonic normalization map
```python
MNEMONIC_MAP = {
    # Depth
    "DEPT": "md", "DEPTH": "md", "MD": "md",
    # Gamma Ray
    "GR": "gr", "SGR": "gr", "CGR": "gr",
    # Density
    "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob",
    # Neutron
    "NPHI": "nphi", "TNPH": "nphi", "NEU": "nphi",
    # Resistivity
    "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt",
    # Drilling
    "ROP": "rop", "WOB": "wob", "RPM": "rpm",
    "TRQ": "torque", "TORQUE": "torque",
    "HKLD": "hookload", "SPP": "spp",
    "ECD": "ecd", "FLOW": "flow_rate",
}
```

### Key methods
```python
class DataIngestionService:
    @staticmethod
    def parse_las(file_content: str | bytes) -> Dict[str, Any]:
        """Parse LAS file, return {curves: [...], units: {...}, well_info: {...}, data: [...]}"""

    @staticmethod
    def parse_dlis(file_path: str) -> Dict[str, Any]:
        """Parse DLIS file. Raises ImportError hint if dlisio not installed."""

    @staticmethod
    def normalize(raw_data: List[Dict], source_format: str) -> List[Dict[str, float]]:
        """Apply mnemonic map, drop unknowns, return standardized records."""

    @staticmethod
    def from_witsml(parsed_log: Dict) -> List[Dict[str, float]]:
        """Convert WITSMLClient.parse_log_response() output to standard format."""
```

### Test file: `tests/unit/test_data_ingest.py` (~12 tests)
- LAS parse + normalization
- DLIS parse with mock (or skip if dlisio not available)
- WITSML conversion
- Unknown mnemonic handling (dropped, not errored)
- Empty input handling

---

## Component 2: WITSML SOAP Client

**File:** `orchestrator/witsml_client.py` (MODIFY — add WITSMLSoapClient class)

### Current state
- `WITSMLClient.connect()` is a stub returning `{"status": "stub"}`
- XML parsing works (21 tests passing)

### Design
```python
class WITSMLSoapClient:
    """SOAP 1.1 client for WITSML 1.4.1 servers.

    Operates in two modes:
    - Real mode: uses zeep library for actual SOAP calls
    - Mock mode: returns predefined XML responses for demo/testing
    """

    def __init__(self, url: str, username: str, password: str, mock_mode: bool = False):
        self.url = url
        self.username = username
        self.password = password
        self.mock_mode = mock_mode
        self._client = None  # zeep.Client instance (lazy init)

    def connect(self) -> Dict[str, Any]:
        """Test connection. In mock mode, always succeeds."""

    def get_cap(self) -> Dict[str, Any]:
        """WMLS_GetCap — discover server capabilities."""

    def get_from_store(self, witsml_type: str, query_xml: str) -> str:
        """WMLS_GetFromStore — the main WITSML query method.
        witsml_type: "log", "trajectory", "mudLog", "well", "wellbore"
        Returns: raw XML response string
        """

    def fetch_latest_log(self, well_uid, wellbore_uid, mnemonics, last_index=None):
        """Convenience: build query + call get_from_store + parse response.
        Used by RealTimeMonitor for polling."""

    # Mock responses (class-level constants)
    MOCK_LOG_XML = "..."  # reuse from test fixtures
    MOCK_TRAJECTORY_XML = "..."
```

### Zeep dependency handling
```python
def _init_zeep_client(self):
    try:
        from zeep import Client as ZeepClient
        from zeep.transports import Transport
        from requests import Session
        session = Session()
        session.auth = (self.username, self.password)
        transport = Transport(session=session, timeout=30)
        self._client = ZeepClient(wsdl=self.url, transport=transport)
    except ImportError:
        if not self.mock_mode:
            raise ImportError(
                "zeep library required for real WITSML connections. "
                "Install: pip install zeep. Or use mock_mode=True."
            )
```

### Update to existing connect()
The static `WITSMLClient.connect()` now creates a `WITSMLSoapClient` and attempts connection.

### Test file: `tests/unit/test_witsml_soap.py` (~8 tests)
- Mock mode connect success
- Mock mode get_from_store returns valid XML
- Mock mode fetch_latest_log returns parsed data
- Real mode raises ImportError without zeep
- get_cap returns capabilities dict
- Polling with last_index filters data

---

## Component 3: Multiphase Drift-Flux Model

**File:** `orchestrator/transient_flow_engine.py` (MODIFY — add simulate_kick_migration_multiphase)

### Current state
- `simulate_kick_migration()` — single-phase, fixed migration rate, no slip

### Zuber-Findlay model
```
Gas velocity:    v_g = C0 * v_m + v_d
Drift velocity:  v_d = 0.35 * sqrt(g * D * (rho_l - rho_g) / rho_l)
Mixture vel:     v_m = (Q_gas + Q_liquid) / A_annular
Holdup:          H_g = Q_gas / (v_g * A_annular)
Mixture density: rho_mix = rho_l * (1 - H_g) + rho_g * H_g
```

Where:
- C0 = 1.2 (distribution coefficient for pipe flow)
- g = 32.174 ft/s^2
- D = annular hydraulic diameter (ft)
- rho_l = mud density (lb/ft^3)
- rho_g = gas density from Z-factor and local P,T

### Key method
```python
@staticmethod
def simulate_kick_migration_multiphase(
    well_depth_tvd: float,
    mud_weight: float,
    kick_volume_bbl: float,
    sidpp: float,
    sicp: float,
    annular_id_in: float,        # NEW: annular ID for geometry
    pipe_od_in: float,            # NEW: pipe OD for geometry
    gas_gravity: float = 0.65,
    time_steps_min: int = 120,
    dt_sec: float = 60.0,         # time step
    surface_temp_f: float = 80.0,
    temp_gradient: float = 1.5,
    n_cells: int = 50,            # number of spatial cells
) -> Dict[str, Any]:
    """
    Multiphase kick migration using Zuber-Findlay drift-flux.

    Discretizes the annulus into n_cells. Each cell tracks:
    - gas holdup (volume fraction)
    - pressure (hydrostatic + surface pressure)
    - gas density (from Z-factor)
    - mixture density

    Returns:
        {
            "time_series": [{
                "time_min", "casing_pressure_psi", "drillpipe_pressure_psi",
                "kick_top_tvd", "kick_volume_bbl", "max_gas_velocity_ft_min",
                "max_holdup", "mixture_density_profile": [...]
            }],
            "max_casing_pressure",
            "surface_arrival_min",
            "model": "zuber_findlay_drift_flux",
        }
    """
```

### Spatial discretization
- Divide annulus into `n_cells` from surface to TD
- Each cell: depth, pressure, temperature, gas_holdup, gas_density, mud_density
- Time loop: advance gas holdup using drift-flux velocity
- Pressure update: integrate mixture density from surface downward

### Test file: `tests/unit/test_multiphase_kick.py` (~8 tests)
- Gas rises faster than single-phase model (drift-flux adds slip velocity)
- Holdup increases near surface (gas expansion)
- Mixture density decreases where gas accumulates
- Casing pressure increases over time
- Surface arrival time shorter than single-phase (gas moves faster)
- Z-factor varies with depth (higher Z near surface)
- Conservation: total gas mass stays constant
- n_cells sensitivity: more cells = smoother profile

---

## API Routes (New)

| Route | Method | Purpose |
|-------|--------|---------|
| `POST /data/ingest/las` | Parse LAS, return normalized data | DataIngestionService.parse_las |
| `POST /data/ingest/dlis` | Parse DLIS, return normalized data | DataIngestionService.parse_dlis |
| `POST /witsml/soap/connect` | SOAP connection (real or mock) | WITSMLSoapClient.connect |
| `POST /witsml/soap/fetch` | GetFromStore via SOAP | WITSMLSoapClient.get_from_store |
| `POST /witsml/soap/poll` | Fetch latest log data since index | WITSMLSoapClient.fetch_latest_log |
| `POST /calculate/well-control/kick-migration-multiphase` | Drift-flux simulation | TransientFlowEngine.simulate_kick_migration_multiphase |

---

## Files Summary

| Action | File | Description |
|--------|------|-------------|
| CREATE | `orchestrator/data_ingest.py` | DataIngestionService — unified LAS/DLIS/WITSML parser |
| MODIFY | `orchestrator/witsml_client.py` | Add WITSMLSoapClient class with mock mode |
| MODIFY | `orchestrator/transient_flow_engine.py` | Add drift-flux multiphase kick simulation |
| MODIFY | `api_main.py` | Add 6 new API routes |
| MODIFY | `requirements.txt` | Add zeep as optional dependency |
| CREATE | `tests/unit/test_data_ingest.py` | ~12 tests |
| CREATE | `tests/unit/test_witsml_soap.py` | ~8 tests |
| CREATE | `tests/unit/test_multiphase_kick.py` | ~8 tests |

**Total: 2 new files, 4 modified files, ~28 new tests, 6 new API routes.**

---

## Dependencies

```
Component 1 (DataIngest) <-- independent, build first
Component 2 (WITSML SOAP) <-- depends on Component 1 for normalize()
Component 3 (Drift-Flux) <-- independent of 1 and 2
API routes <-- depends on all 3 components
```

Build order: Component 1 -> Component 3 (parallel with 2) -> Component 2 -> API routes -> Integration test

---

## Success Criteria

1. `python3 -m pytest tests/ -v` — all new tests pass, no regressions
2. `npm run build` — frontend builds clean
3. Mock WITSML connection works end-to-end in RealTimeMonitor
4. Drift-flux model produces physically reasonable results (gas rises faster with slip)
5. DLIS parse works when dlisio is installed, graceful error when not
6. V&V report regenerated with updated test count
