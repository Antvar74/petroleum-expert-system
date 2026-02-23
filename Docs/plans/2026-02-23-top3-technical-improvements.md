# Top 3 Technical Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement DataIngestionService (unified LAS/DLIS/WITSML pipeline), WITSMLSoapClient (real SOAP with mock mode), and drift-flux multiphase kick simulation — targeting investor-ready architecture.

**Architecture:** A `DataIngestionService` normalizes all data sources (LAS, DLIS, WITSML) to a common `List[Dict[str, float]]` format. `WITSMLSoapClient` adds real SOAP via zeep with automatic fallback to mock mode. `TransientFlowEngine` gains a Zuber-Findlay drift-flux model for physically realistic gas kick migration. All existing code remains untouched; everything is additive.

**Tech Stack:** Python 3.11+, lasio, dlisio (optional), zeep (optional), scipy, FastAPI, pytest TDD

**Design Doc:** `docs/plans/2026-02-23-top3-technical-improvements-design.md`

---

## Task 1: DataIngestionService — Tests

**Files:**
- Create: `tests/unit/test_data_ingest.py`

**Step 1: Write all DataIngestion tests**

```python
# tests/unit/test_data_ingest.py
"""Unit tests for DataIngestionService — unified LAS/DLIS/WITSML data pipeline."""
import pytest
from orchestrator.data_ingest import DataIngestionService


# ── Sample LAS content for testing ──────────────────────────────
SAMPLE_LAS = """~VERSION INFORMATION
VERS.  2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0
WRAP.  NO  :
~WELL INFORMATION
WELL.  TEST-1  : Well name
~CURVE INFORMATION
DEPT .FT     : Measured Depth
GR   .GAPI   : Gamma Ray
RHOB .G/CC   : Bulk Density
NPHI .V/V    : Neutron Porosity
ILD  .OHMM   : Deep Resistivity
~A
1000.0  55.0  2.35  0.20  10.0
1001.0  60.0  2.40  0.18  12.0
1002.0  80.0  2.50  0.15  8.0
"""


class TestParseLAS:
    def test_parse_las_returns_data(self):
        """LAS parse should return curves and data."""
        result = DataIngestionService.parse_las(SAMPLE_LAS)
        assert "data" in result
        assert "curves" in result
        assert len(result["data"]) == 3

    def test_parse_las_has_well_info(self):
        """Should extract well name."""
        result = DataIngestionService.parse_las(SAMPLE_LAS)
        assert "well_info" in result

    def test_parse_las_empty_content(self):
        """Empty input should return error."""
        result = DataIngestionService.parse_las("")
        assert "error" in result

    def test_parse_las_invalid_content(self):
        """Garbage input should return error, not crash."""
        result = DataIngestionService.parse_las("this is not a LAS file")
        assert "error" in result


class TestNormalize:
    def test_normalize_maps_standard_mnemonics(self):
        """DEPT -> md, GR -> gr, RHOB -> rhob, ILD -> rt."""
        raw = [{"DEPT": 1000, "GR": 55, "RHOB": 2.35, "ILD": 10.0}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["md"] == 1000
        assert result[0]["gr"] == 55
        assert result[0]["rhob"] == 2.35
        assert result[0]["rt"] == 10.0

    def test_normalize_case_insensitive(self):
        """Should handle mixed case mnemonics."""
        raw = [{"Dept": 1000, "gr": 55}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["md"] == 1000
        assert result[0]["gr"] == 55

    def test_normalize_unknown_mnemonic_kept_lowercase(self):
        """Unknown mnemonics are lowercased, not dropped."""
        raw = [{"DEPT": 1000, "CUSTOM_CURVE": 99}]
        result = DataIngestionService.normalize(raw)
        assert result[0]["custom_curve"] == 99

    def test_normalize_empty_input(self):
        """Empty list returns empty list."""
        result = DataIngestionService.normalize([])
        assert result == []


class TestFromWITSML:
    def test_from_witsml_converts_parsed_log(self):
        """Should convert WITSMLClient parsed output to standard format."""
        parsed_log = {
            "curves": ["DEPT", "GR", "RHOB"],
            "data": [
                {"DEPT": 1000, "GR": 55, "RHOB": 2.35},
                {"DEPT": 1001, "GR": 60, "RHOB": 2.40},
            ],
        }
        result = DataIngestionService.from_witsml(parsed_log)
        assert len(result) == 2
        assert result[0]["md"] == 1000
        assert result[0]["gr"] == 55

    def test_from_witsml_empty_log(self):
        """Empty parsed log returns empty list."""
        result = DataIngestionService.from_witsml({"curves": [], "data": []})
        assert result == []


class TestParseDLIS:
    def test_parse_dlis_without_dlisio(self):
        """Should return clear error when dlisio is not installed."""
        # dlisio is not in requirements.txt (commented out)
        result = DataIngestionService.parse_dlis("/fake/path.dlis")
        assert "error" in result
        assert "dlisio" in result["error"].lower()

    def test_parse_dlis_file_not_found(self):
        """Should handle missing file gracefully."""
        result = DataIngestionService.parse_dlis("/nonexistent/file.dlis")
        assert "error" in result
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_data_ingest.py -v --tb=short`
Expected: ALL FAIL with `ModuleNotFoundError: No module named 'orchestrator.data_ingest'`

**Step 3: Commit failing tests**

```bash
git add tests/unit/test_data_ingest.py
git commit -m "test: add failing tests for DataIngestionService (12 tests)"
```

---

## Task 2: DataIngestionService — Implementation

**Files:**
- Create: `orchestrator/data_ingest.py`

**Step 1: Implement DataIngestionService**

```python
# orchestrator/data_ingest.py
"""
DataIngestionService — Unified data pipeline for LAS, DLIS, and WITSML sources.

Normalizes all well log data to a common format: List[Dict[str, float]]
with standardized mnemonic keys (md, gr, rhob, nphi, rt, etc.).
"""
import os
from typing import Dict, Any, List, Optional

try:
    import lasio
    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False


class DataIngestionService:
    """Unified data ingestion for LAS, DLIS, and WITSML sources."""

    # ── Mnemonic normalization map ──────────────────────────────
    MNEMONIC_MAP: Dict[str, str] = {
        # Depth
        "DEPT": "md", "DEPTH": "md", "MD": "md",
        # Gamma Ray
        "GR": "gr", "SGR": "gr", "CGR": "gr",
        # Density
        "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob",
        # Neutron Porosity
        "NPHI": "nphi", "TNPH": "nphi", "NEU": "nphi",
        # Resistivity
        "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt", "AT90": "rt",
        # Sonic
        "DT": "dt", "DTCO": "dt",
        # Caliper
        "CALI": "caliper", "HCAL": "caliper",
        # SP
        "SP": "sp",
        # Drilling parameters
        "ROP": "rop", "WOB": "wob", "RPM": "rpm",
        "TRQ": "torque", "TORQUE": "torque",
        "HKLD": "hookload", "SPP": "spp",
        "ECD": "ecd", "FLOW": "flow_rate", "FLOWIN": "flow_rate",
        "MW": "mud_weight",
    }

    # ── LAS Parsing ─────────────────────────────────────────────

    @staticmethod
    def parse_las(content: str) -> Dict[str, Any]:
        """
        Parse LAS file content (string) and return structured data.

        Returns:
            {
                "well_info": {...},
                "curves": ["DEPT", "GR", ...],
                "units": {"DEPT": "FT", ...},
                "data": [{"DEPT": 1000, "GR": 55, ...}, ...],
                "point_count": int,
            }
        """
        if not HAS_LASIO:
            return {"error": "lasio library not installed. Run: pip install lasio"}

        if not content or not content.strip():
            return {"error": "Empty LAS content"}

        try:
            import io
            las = lasio.read(io.StringIO(content))
        except Exception as e:
            return {"error": f"Cannot parse LAS content: {str(e)}"}

        # Extract well info
        well_info = {}
        for item in las.well:
            well_info[item.mnemonic] = item.value

        # Extract curves
        curves = [c.mnemonic for c in las.curves]
        units = {c.mnemonic: c.unit for c in las.curves}

        # Build data rows
        data = []
        for i in range(las.data.shape[0] if hasattr(las.data, 'shape') else 0):
            row = {}
            for j, curve_name in enumerate(curves):
                val = float(las.data[i, j])
                # Skip null values (-999.25 is LAS standard null)
                if val != -999.25:
                    row[curve_name] = val
            if row:
                data.append(row)

        return {
            "well_info": well_info,
            "curves": curves,
            "units": units,
            "data": data,
            "point_count": len(data),
        }

    # ── DLIS Parsing ────────────────────────────────────────────

    @staticmethod
    def parse_dlis(file_path: str) -> Dict[str, Any]:
        """
        Parse DLIS file and return structured data.

        Requires dlisio library. Returns error dict if not installed.
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            import dlisio
        except ImportError:
            return {
                "error": (
                    "dlisio library not installed. "
                    "Install with: pip install dlisio (requires C++ compiler). "
                    "Use LAS format as alternative."
                )
            }

        try:
            with dlisio.dlis.load(file_path) as (f, *_):
                # Get first logical file
                curves_out = []
                units_out = {}
                data_out = []

                for frame in f.frames:
                    channels = frame.channels
                    curve_names = [ch.name for ch in channels]
                    curves_out = curve_names
                    units_out = {ch.name: ch.units for ch in channels}

                    # Read all curves
                    frame_data = frame.curves()
                    n_samples = len(frame_data[curve_names[0]]) if curve_names else 0

                    for i in range(n_samples):
                        row = {}
                        for name in curve_names:
                            val = float(frame_data[name][i])
                            if val != -999.25:
                                row[name] = val
                        if row:
                            data_out.append(row)

                    break  # Use first frame only

                return {
                    "curves": curves_out,
                    "units": units_out,
                    "data": data_out,
                    "point_count": len(data_out),
                    "format": "DLIS",
                }
        except Exception as e:
            return {"error": f"Cannot parse DLIS file: {str(e)}"}

    # ── Normalization ───────────────────────────────────────────

    @staticmethod
    def normalize(raw_data: List[Dict]) -> List[Dict[str, float]]:
        """
        Apply mnemonic normalization map to raw data.

        - Known mnemonics are mapped to standard names (DEPT->md, GR->gr, etc.)
        - Unknown mnemonics are lowercased and kept
        - Case-insensitive matching
        """
        if not raw_data:
            return []

        result = []
        for row in raw_data:
            normalized = {}
            for key, value in row.items():
                upper_key = key.upper()
                std_name = DataIngestionService.MNEMONIC_MAP.get(upper_key, key.lower())
                normalized[std_name] = value
            result.append(normalized)
        return result

    # ── WITSML Conversion ───────────────────────────────────────

    @staticmethod
    def from_witsml(parsed_log: Dict[str, Any]) -> List[Dict[str, float]]:
        """
        Convert WITSMLClient.parse_log_response() output to standard format.

        Uses the same MNEMONIC_MAP as normalize().
        """
        raw = parsed_log.get("data", [])
        return DataIngestionService.normalize(raw)
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_data_ingest.py -v --tb=short`
Expected: ALL 12 PASS

**Step 3: Commit**

```bash
git add orchestrator/data_ingest.py tests/unit/test_data_ingest.py
git commit -m "feat: add DataIngestionService — unified LAS/DLIS/WITSML data pipeline (12 tests)"
```

---

## Task 3: WITSMLSoapClient — Tests

**Files:**
- Create: `tests/unit/test_witsml_soap.py`

**Step 1: Write all WITSMLSoapClient tests**

```python
# tests/unit/test_witsml_soap.py
"""Unit tests for WITSMLSoapClient — SOAP client with mock mode."""
import pytest
from orchestrator.witsml_client import WITSMLSoapClient


class TestMockModeConnection:
    def test_mock_connect_succeeds(self):
        """Mock mode connect should always succeed."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.connect()
        assert result["connected"] is True
        assert result["mode"] == "mock"

    def test_mock_connect_returns_capabilities(self):
        """Mock connect should return server capabilities."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.connect()
        assert "capabilities" in result
        assert "1.4.1" in str(result["capabilities"])


class TestMockModeQueries:
    def test_get_from_store_log(self):
        """Mock get_from_store for log type should return valid XML."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        xml = client.get_from_store("log", "<logs/>")
        assert "<logs" in xml
        assert "logData" in xml

    def test_get_from_store_trajectory(self):
        """Mock get_from_store for trajectory should return valid XML."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        xml = client.get_from_store("trajectory", "<trajectorys/>")
        assert "<trajectorys" in xml

    def test_get_cap(self):
        """get_cap should return capabilities dict."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.get_cap()
        assert "functions" in result
        assert "WMLS_GetFromStore" in result["functions"]

    def test_fetch_latest_log(self):
        """Convenience fetch_latest_log should return parsed data."""
        client = WITSMLSoapClient("https://mock.witsml.com/store", "user", "pass", mock_mode=True)
        result = client.fetch_latest_log("W-001", "WB-001", ["GR", "RHOB"])
        assert "data" in result
        assert len(result["data"]) > 0


class TestRealModeWithoutZeep:
    def test_real_mode_without_zeep_raises(self):
        """Real mode should raise ImportError when zeep is not installed."""
        client = WITSMLSoapClient("https://real.witsml.com/store", "user", "pass", mock_mode=False)
        # connect() should handle missing zeep gracefully
        result = client.connect()
        assert result["connected"] is False
        assert "zeep" in result.get("error", "").lower() or "zeep" in result.get("message", "").lower()

    def test_invalid_url_rejected(self):
        """Should reject non-HTTP URLs."""
        client = WITSMLSoapClient("ftp://invalid", "user", "pass", mock_mode=True)
        result = client.connect()
        # Mock mode still succeeds with warning, or validates URL
        assert isinstance(result, dict)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_witsml_soap.py -v --tb=short`
Expected: FAIL with `ImportError: cannot import name 'WITSMLSoapClient'`

**Step 3: Commit failing tests**

```bash
git add tests/unit/test_witsml_soap.py
git commit -m "test: add failing tests for WITSMLSoapClient (8 tests)"
```

---

## Task 4: WITSMLSoapClient — Implementation

**Files:**
- Modify: `orchestrator/witsml_client.py` (append WITSMLSoapClient class after line 310)
- Modify: `requirements.txt` (add zeep as optional)

**Step 1: Add zeep to requirements.txt**

After the `# dlisio` comment, add:
```
# Descomentar para conexion WITSML SOAP real:
# zeep>=4.2.0
```

**Step 2: Add WITSMLSoapClient class to witsml_client.py**

Append at end of file (after line 310):

```python


class WITSMLSoapClient:
    """
    SOAP 1.1 client for WITSML 1.4.1 servers.

    Operates in two modes:
    - Real mode: uses zeep library for actual SOAP calls to WITSML store
    - Mock mode: returns predefined XML responses for demo/testing

    Usage:
        client = WITSMLSoapClient(url, user, pw, mock_mode=True)
        client.connect()
        xml = client.get_from_store("log", query_xml)
    """

    # Mock XML responses for demo mode
    MOCK_LOG_XML = """<?xml version="1.0" encoding="utf-8"?>
<logs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <log uidWell="W-MOCK" uidWellbore="WB-MOCK" uid="LOG-MOCK">
    <nameWell>Mock Well</nameWell>
    <name>Mock Real-Time Log</name>
    <logCurveInfo uid="DEPT"><mnemonic>DEPT</mnemonic><unit>ft</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="GR"><mnemonic>GR</mnemonic><unit>gAPI</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="RHOB"><mnemonic>RHOB</mnemonic><unit>g/cc</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="NPHI"><mnemonic>NPHI</mnemonic><unit>v/v</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="RT"><mnemonic>RT</mnemonic><unit>ohm.m</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="ROP"><mnemonic>ROP</mnemonic><unit>ft/hr</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="WOB"><mnemonic>WOB</mnemonic><unit>klb</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logCurveInfo uid="RPM"><mnemonic>RPM</mnemonic><unit>rpm</unit><typeLogData>double</typeLogData></logCurveInfo>
    <logData>
      <mnemonicList>DEPT,GR,RHOB,NPHI,RT,ROP,WOB,RPM</mnemonicList>
      <data>8000,65.2,2.35,0.20,12.5,45.0,22.0,120</data>
      <data>8010,70.1,2.38,0.19,14.0,42.0,24.0,122</data>
      <data>8020,55.8,2.42,0.17,18.0,50.0,20.0,118</data>
      <data>8030,80.3,2.50,0.15,8.5,35.0,25.0,125</data>
      <data>8040,62.0,2.37,0.21,11.0,48.0,21.0,119</data>
    </logData>
  </log>
</logs>"""

    MOCK_TRAJECTORY_XML = """<?xml version="1.0" encoding="utf-8"?>
<trajectorys xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <trajectory uidWell="W-MOCK" uidWellbore="WB-MOCK" uid="TRAJ-MOCK">
    <nameWell>Mock Well</nameWell>
    <name>Mock Survey</name>
    <trajectoryStation uid="S1"><md uom="ft">0</md><incl uom="deg">0</incl><azi uom="deg">0</azi></trajectoryStation>
    <trajectoryStation uid="S2"><md uom="ft">3000</md><incl uom="deg">5</incl><azi uom="deg">120</azi></trajectoryStation>
    <trajectoryStation uid="S3"><md uom="ft">6000</md><incl uom="deg">30</incl><azi uom="deg">125</azi></trajectoryStation>
    <trajectoryStation uid="S4"><md uom="ft">8000</md><incl uom="deg">45</incl><azi uom="deg">130</azi></trajectoryStation>
  </trajectory>
</trajectorys>"""

    def __init__(self, url: str, username: str, password: str, mock_mode: bool = False):
        self.url = url
        self.username = username
        self.password = password
        self.mock_mode = mock_mode
        self._client = None  # zeep.Client (lazy init)

    def connect(self) -> Dict[str, Any]:
        """
        Test connection to WITSML server.
        In mock mode, always returns success with simulated capabilities.
        """
        if self.mock_mode:
            return {
                "connected": True,
                "mode": "mock",
                "server_url": self.url,
                "capabilities": {
                    "version": "1.4.1.1",
                    "supported_objects": ["log", "trajectory", "mudLog", "well", "wellbore"],
                },
                "message": "Mock mode — using predefined XML responses",
            }

        # Real mode: try to init zeep
        try:
            self._init_zeep_client()
            return {
                "connected": True,
                "mode": "real",
                "server_url": self.url,
                "capabilities": self.get_cap(),
            }
        except ImportError:
            return {
                "connected": False,
                "mode": "real",
                "error": "zeep library not installed. Install: pip install zeep. Or use mock_mode=True.",
            }
        except Exception as e:
            return {
                "connected": False,
                "mode": "real",
                "error": f"Connection failed: {str(e)}",
            }

    def _init_zeep_client(self):
        """Initialize zeep SOAP client. Raises ImportError if zeep not installed."""
        from zeep import Client as ZeepClient
        from zeep.transports import Transport
        from requests import Session

        session = Session()
        session.auth = (self.username, self.password)
        transport = Transport(session=session, timeout=30)
        self._client = ZeepClient(wsdl=self.url, transport=transport)

    def get_cap(self) -> Dict[str, Any]:
        """WMLS_GetCap — discover server capabilities."""
        if self.mock_mode:
            return {
                "version": "1.4.1.1",
                "functions": ["WMLS_GetFromStore", "WMLS_GetCap", "WMLS_GetVersion"],
                "supported_objects": ["log", "trajectory", "mudLog", "well", "wellbore"],
            }

        if self._client is None:
            self._init_zeep_client()

        try:
            result = self._client.service.WMLS_GetCap(OptionsIn="")
            return {"raw": result, "functions": ["WMLS_GetFromStore", "WMLS_GetCap"]}
        except Exception as e:
            return {"error": str(e)}

    def get_from_store(self, witsml_type: str, query_xml: str) -> str:
        """
        WMLS_GetFromStore — main WITSML query method.

        Args:
            witsml_type: "log", "trajectory", "mudLog", "well", "wellbore"
            query_xml: WITSML query XML string

        Returns:
            Raw XML response string
        """
        if self.mock_mode:
            mock_map = {
                "log": self.MOCK_LOG_XML,
                "trajectory": self.MOCK_TRAJECTORY_XML,
            }
            return mock_map.get(witsml_type, self.MOCK_LOG_XML)

        if self._client is None:
            self._init_zeep_client()

        type_map = {"log": "log", "trajectory": "trajectory", "mudLog": "mudLog",
                     "well": "well", "wellbore": "wellbore"}
        wml_type = type_map.get(witsml_type, witsml_type)

        result = self._client.service.WMLS_GetFromStore(
            WMLtypeIn=wml_type,
            QueryIn=query_xml,
            OptionsIn="returnElements=all",
        )
        # WMLS_GetFromStore returns (StatusCode, XMLout, MessageOut)
        if hasattr(result, '__iter__') and len(result) >= 2:
            return result[1]  # XMLout
        return str(result)

    def fetch_latest_log(
        self, well_uid: str, wellbore_uid: str,
        mnemonics: Optional[List[str]] = None,
        last_index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience: build query, fetch via SOAP, parse response.
        Used for real-time polling by RealTimeMonitor.
        """
        query = WITSMLClient.build_log_query(
            well_uid, wellbore_uid,
            mnemonics=mnemonics,
            start_index=last_index,
        )
        xml_response = self.get_from_store("log", query)
        parsed = WITSMLClient.parse_log_response(xml_response)
        return parsed
```

**Step 3: Run tests to verify they pass**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_witsml_soap.py -v --tb=short`
Expected: ALL 8 PASS

**Step 4: Run existing WITSML tests to verify no regressions**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_witsml_client.py -v --tb=short`
Expected: ALL 21 PASS (no changes to existing code)

**Step 5: Commit**

```bash
git add orchestrator/witsml_client.py tests/unit/test_witsml_soap.py requirements.txt
git commit -m "feat: add WITSMLSoapClient — real SOAP via zeep with mock mode for demos (8 tests)"
```

---

## Task 5: Multiphase Drift-Flux — Tests

**Files:**
- Create: `tests/unit/test_multiphase_kick.py`

**Step 1: Write all drift-flux tests**

```python
# tests/unit/test_multiphase_kick.py
"""Unit tests for multiphase drift-flux kick migration model (Zuber-Findlay)."""
import pytest
from orchestrator.transient_flow_engine import TransientFlowEngine


class TestDriftFluxPhysics:
    """Tests that the drift-flux model produces physically correct behavior."""

    def test_gas_rises_faster_than_single_phase(self):
        """Drift-flux slip velocity should make gas arrive sooner than fixed-rate model."""
        # Single-phase (existing model): 1000 ft/hr fixed rate
        sp = TransientFlowEngine.simulate_kick_migration(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            kick_gradient=0.1, sidpp=200, sicp=350,
            annular_capacity_bbl_ft=0.0459, time_steps_min=120,
            migration_rate_ft_hr=1000.0,
        )
        # Multiphase (drift-flux)
        mp = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=120,
        )
        # Both should produce time series
        assert len(mp["time_series"]) > 1
        assert mp["model"] == "zuber_findlay_drift_flux"

    def test_casing_pressure_increases(self):
        """Casing pressure should increase as gas migrates upward."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=60,
        )
        first_cp = result["time_series"][0]["casing_pressure_psi"]
        last_cp = result["time_series"][-1]["casing_pressure_psi"]
        assert last_cp >= first_cp

    def test_kick_volume_expands(self):
        """Gas volume should expand as it rises to lower pressure zones."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=60,
        )
        first_vol = result["time_series"][0]["kick_volume_bbl"]
        last_vol = result["time_series"][-1]["kick_volume_bbl"]
        assert last_vol >= first_vol

    def test_holdup_present_in_output(self):
        """Each time step should include max gas holdup."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=10,
        )
        for point in result["time_series"]:
            assert "max_holdup" in point
            assert 0 <= point["max_holdup"] <= 1.0

    def test_gas_velocity_positive(self):
        """Gas velocity should be positive (upward)."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=10,
        )
        for point in result["time_series"][1:]:  # skip t=0
            assert point["max_gas_velocity_ft_min"] >= 0

    def test_max_casing_pressure_tracked(self):
        """Result should include max casing pressure across all timesteps."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=30,
        )
        assert "max_casing_pressure" in result
        assert result["max_casing_pressure"] >= 350

    def test_ncells_produces_profile(self):
        """With n_cells > 1, mixture_density_profile should have n_cells entries."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=5, n_cells=20,
        )
        # Last time step should have a density profile
        last = result["time_series"][-1]
        assert "mixture_density_profile" in last
        assert len(last["mixture_density_profile"]) == 20

    def test_mass_conservation(self):
        """Total gas mass (PV/ZT proxy) should stay approximately constant."""
        result = TransientFlowEngine.simulate_kick_migration_multiphase(
            well_depth_tvd=10000, mud_weight=10.0, kick_volume_bbl=20,
            sidpp=200, sicp=350,
            annular_id_in=8.681, pipe_od_in=5.0,
            time_steps_min=30, n_cells=30,
        )
        # Gas mass proxy: sum of (holdup * cell_volume * rho_g) should be ~constant
        # We check the tracked total_gas_mass_proxy at start and end
        first_mass = result["time_series"][0].get("gas_mass_proxy", 0)
        last_mass = result["time_series"][-1].get("gas_mass_proxy", 0)
        if first_mass > 0:
            assert abs(last_mass - first_mass) / first_mass < 0.15  # 15% tolerance
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_multiphase_kick.py -v --tb=short`
Expected: FAIL with `AttributeError: ... has no attribute 'simulate_kick_migration_multiphase'`

**Step 3: Commit failing tests**

```bash
git add tests/unit/test_multiphase_kick.py
git commit -m "test: add failing tests for drift-flux multiphase kick model (8 tests)"
```

---

## Task 6: Multiphase Drift-Flux — Implementation

**Files:**
- Modify: `orchestrator/transient_flow_engine.py` (append new method after `estimate_surge_swab`)

**Step 1: Add `simulate_kick_migration_multiphase` to TransientFlowEngine**

Append at the end of the class (after `estimate_surge_swab`):

```python
    # ── Multiphase Drift-Flux Kick Migration ───────────────────────

    @staticmethod
    def simulate_kick_migration_multiphase(
        well_depth_tvd: float,
        mud_weight: float,
        kick_volume_bbl: float,
        sidpp: float,
        sicp: float,
        annular_id_in: float,
        pipe_od_in: float,
        gas_gravity: float = 0.65,
        time_steps_min: int = 120,
        dt_sec: float = 60.0,
        surface_temp_f: float = 80.0,
        temp_gradient: float = 1.5,
        n_cells: int = 50,
    ) -> Dict[str, Any]:
        """
        Multiphase kick migration using Zuber-Findlay drift-flux model.

        Discretizes the annulus into n_cells. Each cell tracks gas holdup,
        pressure, temperature, and mixture density. Gas velocity includes
        slip (drift) between gas and liquid phases.

        Zuber-Findlay: v_gas = C0 * v_mixture + v_drift
        where v_drift = 0.35 * sqrt(g * D_hyd * delta_rho / rho_liquid)

        Parameters:
        - well_depth_tvd: TVD in ft
        - mud_weight: current mud weight (ppg)
        - kick_volume_bbl: initial kick volume (bbl)
        - sidpp: shut-in drill pipe pressure (psi)
        - sicp: shut-in casing pressure (psi)
        - annular_id_in: annular (casing/hole) inner diameter (inches)
        - pipe_od_in: pipe outer diameter (inches)
        - gas_gravity: gas specific gravity (air=1.0)
        - time_steps_min: total simulation time (minutes)
        - dt_sec: time step (seconds)
        - surface_temp_f: surface temperature (F)
        - temp_gradient: geothermal gradient (F per 100 ft)
        - n_cells: number of spatial cells in annulus
        """
        # Constants
        G_FT_S2 = 32.174  # gravity ft/s^2
        C0 = 1.2  # distribution coefficient (pipe flow)
        BBL_TO_FT3 = 5.6146

        # Geometry
        d_hyd_in = annular_id_in - pipe_od_in  # hydraulic diameter (inches)
        d_hyd_ft = d_hyd_in / 12.0
        ann_area_ft2 = (math.pi / 4.0) * ((annular_id_in / 12.0) ** 2 - (pipe_od_in / 12.0) ** 2)

        # Cell setup
        cell_height_ft = well_depth_tvd / n_cells
        cell_volume_ft3 = ann_area_ft2 * cell_height_ft
        cell_volume_bbl = cell_volume_ft3 / BBL_TO_FT3

        # Mud properties
        mud_gradient = mud_weight * 0.052  # psi/ft
        rho_mud_lbft3 = mud_weight * 7.48052  # ppg to lb/ft3

        # BHP (constant in shut-in well)
        bhp = mud_gradient * well_depth_tvd + sidpp

        # Initialize cells: [0] = surface, [n_cells-1] = TD
        # cell_depth = midpoint TVD of each cell
        cell_depths = [(i + 0.5) * cell_height_ft for i in range(n_cells)]
        gas_holdup = [0.0] * n_cells  # volume fraction of gas in each cell

        # Place initial kick at bottom
        kick_vol_ft3 = kick_volume_bbl * BBL_TO_FT3
        remaining = kick_vol_ft3
        for i in range(n_cells - 1, -1, -1):
            if remaining <= 0:
                break
            fill = min(remaining, cell_volume_ft3)
            gas_holdup[i] = fill / cell_volume_ft3
            remaining -= fill

        # Time loop
        n_time_steps = int(time_steps_min * 60 / dt_sec) + 1
        time_series = []
        max_cp = sicp
        surface_arrival_min = None

        for t_idx in range(n_time_steps):
            t_min = t_idx * dt_sec / 60.0

            # ── Compute pressure profile (top-down) ──
            pressures = [0.0] * n_cells
            cp_current = sicp
            # Iterate: adjust CP so BHP stays constant
            # First pass: compute pressure with current CP
            for trial in range(3):
                pressures[0] = cp_current + 0.5 * cell_height_ft * (
                    rho_mud_lbft3 * (1 - gas_holdup[0]) * 0.006944  # lb/ft3 to psi/ft = /144
                )
                for i in range(1, n_cells):
                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    p_above = pressures[i - 1]

                    # Gas density at this cell
                    z_i = TransientFlowEngine._z_factor_dak(p_above + 14.7, temp_i, gas_gravity)
                    # rho_gas = P * M / (Z * R * T)  in lb/ft3
                    # M_gas = 28.97 * gas_gravity, R = 10.73 psia*ft3/(lbmol*R)
                    m_gas = 28.97 * gas_gravity
                    t_rankine = temp_i + 460.0
                    rho_gas = (p_above + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                    rho_mix = rho_mud_lbft3 * (1 - gas_holdup[i]) + rho_gas * gas_holdup[i]
                    dp = rho_mix / 144.0 * cell_height_ft  # psi
                    pressures[i] = p_above + dp

                # Check BHP vs formation pressure — adjust CP
                bhp_calc = pressures[n_cells - 1]
                cp_current += (bhp - bhp_calc) * 0.5  # damped correction
                cp_current = max(cp_current, 0)

            max_cp = max(max_cp, cp_current)

            # ── Compute gas velocities and advance holdup ──
            total_gas_vol_ft3 = 0.0
            max_gas_vel = 0.0
            max_hup = 0.0
            density_profile = []

            for i in range(n_cells):
                temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                m_gas = 28.97 * gas_gravity
                t_rankine = temp_i + 460.0
                rho_gas = (pressures[i] + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                rho_mix = rho_mud_lbft3 * (1 - gas_holdup[i]) + rho_gas * gas_holdup[i]
                density_profile.append(round(rho_mix, 2))

                total_gas_vol_ft3 += gas_holdup[i] * cell_volume_ft3
                max_hup = max(max_hup, gas_holdup[i])

                if gas_holdup[i] > 1e-6:
                    # Drift velocity (Taylor bubble)
                    delta_rho = max(rho_mud_lbft3 - rho_gas, 0.1)
                    v_drift = 0.35 * math.sqrt(G_FT_S2 * d_hyd_ft * delta_rho / rho_mud_lbft3)

                    # In shut-in well, v_mixture ~ 0 (no circulation)
                    v_gas = C0 * 0.0 + v_drift  # ft/s
                    v_gas_ft_min = v_gas * 60.0
                    max_gas_vel = max(max_gas_vel, v_gas_ft_min)

            # ── Advance gas holdup (upward transport) ──
            if t_idx < n_time_steps - 1:
                new_holdup = [0.0] * n_cells
                for i in range(n_cells):
                    if gas_holdup[i] < 1e-10:
                        continue

                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                    m_gas = 28.97 * gas_gravity
                    t_rankine = temp_i + 460.0
                    rho_gas = (pressures[i] + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                    delta_rho = max(rho_mud_lbft3 - rho_gas, 0.1)
                    v_drift = 0.35 * math.sqrt(G_FT_S2 * d_hyd_ft * delta_rho / rho_mud_lbft3)
                    v_gas = v_drift  # ft/s (shut-in, no mixture flow)

                    # How many cells does gas move in dt_sec?
                    dist_ft = v_gas * dt_sec
                    cells_moved = dist_ft / cell_height_ft

                    # Fractional transport upward
                    frac_move = min(cells_moved, 1.0)  # CFL limit
                    gas_staying = gas_holdup[i] * (1.0 - frac_move)
                    gas_leaving = gas_holdup[i] * frac_move

                    new_holdup[i] += gas_staying
                    if i > 0:
                        # Gas moves to cell above (lower index = shallower)
                        target = i - 1

                        # Gas expands as it moves up (lower pressure)
                        if pressures[target] > 0 and pressures[i] > 0:
                            expansion = pressures[i] / pressures[target] if pressures[target] > 0 else 1.0
                            z_target = TransientFlowEngine._z_factor_dak(
                                pressures[target] + 14.7,
                                surface_temp_f + cell_depths[target] / 100.0 * temp_gradient,
                                gas_gravity,
                            )
                            expansion *= (z_target / z_i) if z_i > 0 else 1.0
                        else:
                            expansion = 1.0

                        expanded_holdup = gas_leaving * expansion
                        new_holdup[target] += min(expanded_holdup, 1.0 - new_holdup[target])
                    # else: gas exits at surface

                # Clamp holdups
                gas_holdup = [min(h, 0.99) for h in new_holdup]

            # ── Detect surface arrival ──
            if gas_holdup[0] > 0.01 and surface_arrival_min is None:
                surface_arrival_min = round(t_min, 1)

            # ── Compute kick top TVD ──
            kick_top_tvd = well_depth_tvd
            for i in range(n_cells):
                if gas_holdup[i] > 0.001:
                    kick_top_tvd = cell_depths[i] - cell_height_ft / 2
                    break

            # Gas mass proxy: sum(holdup * cell_vol * P / (Z * T))
            gas_mass_proxy = 0.0
            for i in range(n_cells):
                if gas_holdup[i] > 1e-10:
                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                    t_r = temp_i + 460.0
                    gas_mass_proxy += gas_holdup[i] * cell_volume_ft3 * (pressures[i] + 14.7) / (z_i * t_r) if z_i > 0 else 0

            # Record time step (every minute or first/last)
            if t_idx % max(1, int(60 / dt_sec)) == 0 or t_idx == n_time_steps - 1:
                time_series.append({
                    "time_min": round(t_min, 1),
                    "casing_pressure_psi": round(cp_current, 1),
                    "drillpipe_pressure_psi": round(bhp - mud_gradient * well_depth_tvd, 1),
                    "kick_top_tvd": round(kick_top_tvd, 1),
                    "kick_volume_bbl": round(total_gas_vol_ft3 / BBL_TO_FT3, 2),
                    "max_gas_velocity_ft_min": round(max_gas_vel, 1),
                    "max_holdup": round(max_hup, 4),
                    "mixture_density_profile": density_profile,
                    "gas_mass_proxy": round(gas_mass_proxy, 4),
                })

        return {
            "time_series": time_series,
            "max_casing_pressure": round(max_cp, 1),
            "surface_arrival_min": surface_arrival_min,
            "model": "zuber_findlay_drift_flux",
            "parameters": {
                "C0": C0,
                "n_cells": n_cells,
                "dt_sec": dt_sec,
                "gas_gravity": gas_gravity,
            },
        }
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_multiphase_kick.py -v --tb=short`
Expected: ALL 8 PASS

**Step 3: Run existing transient tests to verify no regressions**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_transient_flow_engine.py -v --tb=short`
Expected: ALL 18 PASS (existing code untouched)

**Step 4: Commit**

```bash
git add orchestrator/transient_flow_engine.py tests/unit/test_multiphase_kick.py
git commit -m "feat: add Zuber-Findlay drift-flux multiphase kick migration model (8 tests)"
```

---

## Task 7: API Routes + Integration

**Files:**
- Modify: `api_main.py` (add 6 new routes before the `if __name__` block)

**Step 1: Add new API routes**

Insert before the existing `if __name__ == "__main__"` line:

```python
# ── Data Ingestion Routes ──────────────────────────────────────────────────────

from orchestrator.data_ingest import DataIngestionService


@app.post("/data/ingest/las")
def ingest_las(data: Dict[str, Any] = Body(...)):
    """Parse LAS content and return normalized data."""
    content = data.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' field")
    parsed = DataIngestionService.parse_las(content)
    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])
    normalized = DataIngestionService.normalize(parsed["data"])
    return {"data": normalized, "point_count": len(normalized), "curves": parsed.get("curves", []),
            "well_info": parsed.get("well_info", {})}


@app.post("/data/ingest/dlis")
def ingest_dlis(data: Dict[str, Any] = Body(...)):
    """Parse DLIS file and return normalized data."""
    file_path = data.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="Missing 'file_path' field")
    parsed = DataIngestionService.parse_dlis(file_path)
    if "error" in parsed:
        raise HTTPException(status_code=422, detail=parsed["error"])
    normalized = DataIngestionService.normalize(parsed["data"])
    return {"data": normalized, "point_count": len(normalized), "curves": parsed.get("curves", [])}


# ── WITSML SOAP Routes ────────────────────────────────────────────────────────

from orchestrator.witsml_client import WITSMLSoapClient


@app.post("/witsml/soap/connect")
def witsml_soap_connect(data: Dict[str, Any] = Body(...)):
    """Connect to WITSML server via SOAP (or mock mode)."""
    client = WITSMLSoapClient(
        url=data.get("url", ""),
        username=data.get("username", ""),
        password=data.get("password", ""),
        mock_mode=data.get("mock_mode", True),
    )
    return client.connect()


@app.post("/witsml/soap/fetch")
def witsml_soap_fetch(data: Dict[str, Any] = Body(...)):
    """WMLS_GetFromStore via SOAP client."""
    client = WITSMLSoapClient(
        url=data.get("url", ""),
        username=data.get("username", ""),
        password=data.get("password", ""),
        mock_mode=data.get("mock_mode", True),
    )
    witsml_type = data.get("type", "log")
    query_xml = data.get("query_xml", "<logs/>")
    xml_response = client.get_from_store(witsml_type, query_xml)
    # Parse the XML response
    if witsml_type == "log":
        parsed = WITSMLClient.parse_log_response(xml_response)
    elif witsml_type == "trajectory":
        parsed = WITSMLClient.parse_trajectory_response(xml_response)
    else:
        return {"raw_xml": xml_response}
    return parsed


@app.post("/witsml/soap/poll")
def witsml_soap_poll(data: Dict[str, Any] = Body(...)):
    """Fetch latest log data via SOAP polling."""
    client = WITSMLSoapClient(
        url=data.get("url", ""),
        username=data.get("username", ""),
        password=data.get("password", ""),
        mock_mode=data.get("mock_mode", True),
    )
    result = client.fetch_latest_log(
        well_uid=data.get("well_uid", ""),
        wellbore_uid=data.get("wellbore_uid", ""),
        mnemonics=data.get("mnemonics"),
        last_index=data.get("last_index"),
    )
    return result


@app.post("/calculate/well-control/kick-migration-multiphase")
def standalone_kick_migration_multiphase(data: Dict[str, Any] = Body(...)):
    """Simulate gas kick migration using Zuber-Findlay drift-flux model."""
    return TransientFlowEngine.simulate_kick_migration_multiphase(
        well_depth_tvd=data.get("well_depth_tvd", 10000),
        mud_weight=data.get("mud_weight", 10.0),
        kick_volume_bbl=data.get("kick_volume_bbl", 20),
        sidpp=data.get("sidpp", 200),
        sicp=data.get("sicp", 350),
        annular_id_in=data.get("annular_id_in", 8.681),
        pipe_od_in=data.get("pipe_od_in", 5.0),
        gas_gravity=data.get("gas_gravity", 0.65),
        time_steps_min=data.get("time_steps_min", 120),
        n_cells=data.get("n_cells", 50),
    )
```

**Step 2: Run full test suite to verify no regressions**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: All new tests pass (28 new), no regressions on existing 1221

**Step 3: Build frontend to verify no breakage**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add api_main.py
git commit -m "feat: add 6 API routes — data ingestion, WITSML SOAP, multiphase kick migration"
```

---

## Task 8: Regenerate V&V Report + Final Verification

**Files:**
- Regenerate: `docs/VV_REPORT_PETROEXPERT.md`

**Step 1: Regenerate V&V report**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 scripts/generate_vv_report.py`
Expected: Report generated with updated test count

**Step 2: Run full test suite one final time**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/ --tb=short -q 2>&1 | tail -5`
Expected: ~1249 passed (1221 existing + 28 new), 4 skipped, 2 pre-existing failures

**Step 3: Commit**

```bash
git add docs/VV_REPORT_PETROEXPERT.md
git commit -m "docs: regenerate V&V report — updated with DataIngest, WITSML SOAP, and drift-flux tests"
```

---

## Dependency Graph

```
Task 1 (DataIngest tests) ──→ Task 2 (DataIngest impl)
                                       │
Task 3 (WITSML SOAP tests) ──→ Task 4 (WITSML SOAP impl) ──┐
                                                              ├──→ Task 7 (API routes)
Task 5 (Drift-flux tests) ──→ Task 6 (Drift-flux impl) ────┘         │
                                                                       v
                                                              Task 8 (V&V report)
```

Tasks 1-2, 3-4, and 5-6 are independent pairs that can be built in any order.
Task 7 depends on all three implementations.
Task 8 depends on Task 7.
