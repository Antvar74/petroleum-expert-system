# orchestrator/data_ingest.py
"""
DataIngestionService — Unified data pipeline for LAS and DLIS sources.

Normalizes all well log data to a common format: List[Dict[str, float]]
with standardized mnemonic keys (md, gr, rhob, nphi, rt, etc.).
"""
import os
from typing import Dict, Any, List

try:
    import lasio
    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False


class DataIngestionService:
    """Unified data ingestion for LAS and DLIS sources."""

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

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            with dlisio.dlis.load(file_path) as (f, *_):
                curves_out = []
                units_out = {}
                data_out = []

                for frame in f.frames:
                    channels = frame.channels
                    curve_names = [ch.name for ch in channels]
                    curves_out = curve_names
                    units_out = {ch.name: ch.units for ch in channels}

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

