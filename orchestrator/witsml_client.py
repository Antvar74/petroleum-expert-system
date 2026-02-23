"""
WITSML 1.4.1.1 Client for real-time drilling data ingestion.
Supports parsing: log, trajectory, mudLog objects.
Protocol: SOAP/XML query builder + XML response parser.
No external dependencies — uses stdlib xml.etree.ElementTree.
"""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional


class WITSMLClient:
    """WITSML data parser and query builder for drilling data exchange."""

    WITSML_NS = "http://www.witsml.org/schemas/1series"
    NS = {"witsml": WITSML_NS}

    # ── Namespace-aware helpers ───────────────────────────────────

    @staticmethod
    def _find(parent, tag, ns=None):
        """Find element trying with namespace first, then without."""
        if ns is None:
            ns = WITSMLClient.NS
        el = parent.find(f"witsml:{tag}", ns)
        if el is None:
            el = parent.find(tag)
        return el

    @staticmethod
    def _findall(parent, tag, ns=None):
        """Findall trying with namespace first, then without."""
        if ns is None:
            ns = WITSMLClient.NS
        result = parent.findall(f"witsml:{tag}", ns)
        if not result:
            result = parent.findall(tag)
        return result

    @staticmethod
    def _find_deep(parent, tag, ns=None):
        """Deep find (.//tag) trying with namespace first, then without."""
        if ns is None:
            ns = WITSMLClient.NS
        el = parent.find(f".//witsml:{tag}", ns)
        if el is None:
            el = parent.find(f".//{tag}")
        return el

    # ── XML Response Parsers ──────────────────────────────────────

    @staticmethod
    def parse_log_response(xml_str: str) -> Dict[str, Any]:
        """
        Parse WITSML log XML response into structured data.

        Returns:
            {
                "well_uid": str,
                "wellbore_uid": str,
                "log_name": str,
                "curves": [str],
                "units": [str],
                "data": [dict],
                "point_count": int,
            }
        """
        root = ET.fromstring(xml_str)
        log = WITSMLClient._find_deep(root, "log")
        if log is None:
            return {"error": "No <log> element found in XML"}

        well_uid = log.get("uidWell", "")
        wellbore_uid = log.get("uidWellbore", "")

        # Log name
        name_el = WITSMLClient._find(log, "name")
        log_name = name_el.text if name_el is not None and name_el.text else ""

        # Curve info
        curves = []
        units = []
        for lci in WITSMLClient._findall(log, "logCurveInfo"):
            mnem = WITSMLClient._find(lci, "mnemonic")
            unit = WITSMLClient._find(lci, "unit")
            if mnem is not None and mnem.text:
                curves.append(mnem.text.strip())
                units.append(unit.text.strip() if unit is not None and unit.text else "")

        # Log data
        data_rows = []
        log_data = WITSMLClient._find(log, "logData")
        if log_data is not None:
            for data_el in WITSMLClient._findall(log_data, "data"):
                if data_el.text:
                    vals = data_el.text.split(",")
                    row = {}
                    for i, curve in enumerate(curves):
                        if i < len(vals):
                            try:
                                row[curve] = float(vals[i].strip())
                            except (ValueError, IndexError):
                                row[curve] = vals[i].strip()
                    data_rows.append(row)

        return {
            "well_uid": well_uid,
            "wellbore_uid": wellbore_uid,
            "log_name": log_name,
            "curves": curves,
            "units": units,
            "data": data_rows,
            "point_count": len(data_rows),
        }

    @staticmethod
    def parse_trajectory_response(xml_str: str) -> Dict[str, Any]:
        """
        Parse WITSML trajectory XML into survey stations.

        Returns:
            {
                "well_uid": str,
                "stations": [{"md": float, "inclination": float, "azimuth": float}],
                "station_count": int,
            }
        """
        root = ET.fromstring(xml_str)
        traj = WITSMLClient._find_deep(root, "trajectory")
        if traj is None:
            return {"error": "No <trajectory> element found", "stations": []}

        well_uid = traj.get("uidWell", "")

        stations = []
        for ts in WITSMLClient._findall(traj, "trajectoryStation"):
            md_el = WITSMLClient._find(ts, "md")
            inc_el = WITSMLClient._find(ts, "incl")
            azi_el = WITSMLClient._find(ts, "azi")

            station = {
                "md": float(md_el.text) if md_el is not None and md_el.text else 0.0,
                "inclination": float(inc_el.text) if inc_el is not None and inc_el.text else 0.0,
                "azimuth": float(azi_el.text) if azi_el is not None and azi_el.text else 0.0,
            }
            stations.append(station)

        return {
            "well_uid": well_uid,
            "stations": stations,
            "station_count": len(stations),
        }

    @staticmethod
    def parse_mudlog_response(xml_str: str) -> Dict[str, Any]:
        """
        Parse WITSML mudLog XML for lithology and shows.

        Returns:
            {
                "intervals": [{"top_md": float, "base_md": float, "lithology": str, "description": str}],
            }
        """
        root = ET.fromstring(xml_str)
        mudlog = WITSMLClient._find_deep(root, "mudLog")
        if mudlog is None:
            return {"error": "No <mudLog> element found", "intervals": []}

        intervals = []
        for gi in WITSMLClient._findall(mudlog, "geologyInterval"):
            top = WITSMLClient._find(gi, "mdTop")
            base = WITSMLClient._find(gi, "mdBottom")
            desc = WITSMLClient._find(gi, "description")
            lith_el = WITSMLClient._find_deep(gi, "lithology")
            lith_type = lith_el.get("type", "") if lith_el is not None else ""

            intervals.append({
                "top_md": float(top.text) if top is not None and top.text else 0.0,
                "base_md": float(base.text) if base is not None and base.text else 0.0,
                "lithology": lith_type,
                "description": desc.text if desc is not None and desc.text else "",
            })

        return {"intervals": intervals}

    # ── WITSML Query Builders ─────────────────────────────────────

    @staticmethod
    def build_log_query(
        well_uid: str,
        wellbore_uid: str,
        log_uid: str = "",
        mnemonics: Optional[List[str]] = None,
        start_index: Optional[str] = None,
        end_index: Optional[str] = None,
    ) -> str:
        """Build WITSML GetFromStore query XML for log objects."""
        mnem_section = ""
        if mnemonics:
            for m in mnemonics:
                mnem_section += f'      <logCurveInfo><mnemonic>{m}</mnemonic></logCurveInfo>\n'

        index_range = ""
        if start_index:
            index_range += f'      <startIndex uom="ft">{start_index}</startIndex>\n'
        if end_index:
            index_range += f'      <endIndex uom="ft">{end_index}</endIndex>\n'

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<logs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <log uidWell="{well_uid}" uidWellbore="{wellbore_uid}" uid="{log_uid}">
    <name/>
{index_range}{mnem_section}    <logData/>
  </log>
</logs>"""

    @staticmethod
    def build_trajectory_query(
        well_uid: str,
        wellbore_uid: str,
    ) -> str:
        """Build WITSML GetFromStore query XML for trajectory objects."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<trajectorys xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <trajectory uidWell="{well_uid}" uidWellbore="{wellbore_uid}">
    <name/>
    <trajectoryStation>
      <md uom="ft"/>
      <incl uom="deg"/>
      <azi uom="deg"/>
      <tvd uom="ft"/>
    </trajectoryStation>
  </trajectory>
</trajectorys>"""

    # ── Data Conversion Helpers ───────────────────────────────────

    @staticmethod
    def witsml_log_to_petro_format(parsed_log: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert parsed WITSML log data to PetroExpert standard format.
        Maps common WITSML mnemonics to PetroExpert field names.
        """
        MNEMONIC_MAP = {
            "DEPT": "md", "DEPTH": "md",
            "GR": "gr", "SGR": "gr",
            "RHOB": "rhob", "RHOZ": "rhob",
            "NPHI": "nphi", "TNPH": "nphi",
            "RT": "rt", "ILD": "rt", "LLD": "rt", "AT90": "rt",
            "DT": "dt", "DTCO": "dt",
            "CALI": "caliper", "HCAL": "caliper",
            "SP": "sp",
            "HKLD": "hookload",
            "WOB": "wob",
            "RPM": "rpm",
            "TORQUE": "torque", "TRQ": "torque",
            "ROP": "rop",
            "SPP": "spp",
            "FLOW": "flow_rate", "FLOWIN": "flow_rate",
            "MW": "mud_weight", "ECD": "ecd",
        }

        result = []
        for row in parsed_log.get("data", []):
            mapped = {}
            for mnem, value in row.items():
                std_name = MNEMONIC_MAP.get(mnem.upper(), mnem.lower())
                mapped[std_name] = value
            result.append(mapped)
        return result

    @staticmethod
    def witsml_trajectory_to_survey(parsed_traj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert parsed WITSML trajectory to PetroExpert survey format."""
        return [
            {
                "md": s["md"],
                "inclination": s["inclination"],
                "azimuth": s["azimuth"],
            }
            for s in parsed_traj.get("stations", [])
        ]

    # ── Connection (Stub for SOAP) ────────────────────────────────

    @staticmethod
    def connect(url: str, username: str, password: str) -> Dict[str, Any]:
        """
        Connect to a WITSML server via SOAP.
        Returns server capabilities.

        Note: Full SOAP implementation requires the 'zeep' library.
        This stub validates connection parameters and returns a status.
        """
        if not url or not url.startswith(("http://", "https://")):
            return {"connected": False, "error": "Invalid URL"}

        return {
            "connected": False,
            "status": "stub",
            "message": (
                "WITSML SOAP connection requires the 'zeep' library. "
                "Install with: pip install zeep. "
                "XML parsing and query building work without it."
            ),
            "server_url": url,
            "capabilities": {
                "supported_objects": ["log", "trajectory", "mudLog", "tubular"],
                "version": "1.4.1.1",
            },
        }


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
