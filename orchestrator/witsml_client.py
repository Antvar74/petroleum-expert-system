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
