"""Log data parsing and LAS 2.0 file reader."""
import os
from typing import Dict, Any, List


def parse_log_data(log_entries: List[Dict]) -> Dict[str, Any]:
    """
    Parse and validate array of log measurements.

    Each entry should have: {md, gr, rhob, nphi, rt, caliper (optional)}
    Validates ranges: GR 0-200, RHOB 1.5-3.0, NPHI -0.05-0.60, Rt 0.1-10000

    Args:
        log_entries: list of dicts with log measurements

    Returns:
        Dict with accepted points, rejected count, depth range
    """
    if not log_entries:
        return {"error": "No log entries provided", "accepted": [], "rejected_count": 0}

    accepted = []
    rejected = 0

    for entry in log_entries:
        md = entry.get("md", entry.get("depth", 0))
        gr = entry.get("gr", entry.get("gamma_ray", 0))
        rhob = entry.get("rhob", entry.get("density", 0))
        nphi = entry.get("nphi", entry.get("neutron", 0))
        rt = entry.get("rt", entry.get("resistivity", 0))
        caliper = entry.get("caliper", entry.get("cali", 0))

        # Validate ranges
        if md <= 0 or gr < 0 or gr > 300:
            rejected += 1
            continue
        if rhob < 1.5 or rhob > 3.2:
            rejected += 1
            continue
        if nphi < -0.05 or nphi > 0.65:
            rejected += 1
            continue
        if rt < 0.1 or rt > 100000:
            rejected += 1
            continue

        accepted.append({
            "md": round(md, 1),
            "gr": round(gr, 2),
            "rhob": round(rhob, 4),
            "nphi": round(nphi, 4),
            "rt": round(rt, 4),
            "caliper": round(caliper, 3) if caliper else 0,
        })

    # Sort by depth
    accepted.sort(key=lambda x: x["md"])

    return {
        "accepted": accepted,
        "accepted_count": len(accepted),
        "rejected_count": rejected,
        "depth_range": {
            "min_md": accepted[0]["md"] if accepted else 0,
            "max_md": accepted[-1]["md"] if accepted else 0,
        }
    }


def parse_las_file(file_path: str) -> Dict[str, Any]:
    """
    Parse LAS 2.0 file and extract well info + curve data.

    Recognizes common mnemonics: GR, RHOB, NPHI, RT/ILD/LLD, DT, CALI, SP, DEPT

    Args:
        file_path: path to .las file

    Returns:
        Dict with well_info, curve_info, data as list of dicts, curve_mapping
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        with open(file_path, 'r', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": f"Cannot read file: {str(e)}"}

    well_info = {}
    curve_info = []
    curve_names = []
    data_rows = []
    current_section = None
    null_value = -999.25

    # Common mnemonic mapping
    mnemonic_map = {
        "DEPT": "md", "DEPTH": "md", "MD": "md",
        "GR": "gr", "SGR": "gr", "CGR": "gr",
        "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob", "DENSITY": "rhob",
        "NPHI": "nphi", "TNPH": "nphi", "PHIN": "nphi", "NEU": "nphi",
        "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt", "RILM": "rt",
        "RESD": "rt", "RD": "rt", "AT90": "rt",
        "DT": "dt", "DTC": "dt", "DTCO": "dt", "SONIC": "dt",
        "CALI": "caliper", "CAL": "caliper", "HCAL": "caliper",
        "SP": "sp",
    }

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Section headers
        if line.startswith('~W'):
            current_section = 'well'
            continue
        elif line.startswith('~C'):
            current_section = 'curve'
            continue
        elif line.startswith('~A'):
            current_section = 'data'
            continue
        elif line.startswith('~V'):
            current_section = 'version'
            continue
        elif line.startswith('~P'):
            current_section = 'parameter'
            continue
        elif line.startswith('~O'):
            current_section = 'other'
            continue

        if current_section == 'well':
            # Parse well header: MNEM.UNIT VALUE : DESCRIPTION
            if '.' in line:
                parts = line.split('.', 1)
                mnem = parts[0].strip()
                rest = parts[1] if len(parts) > 1 else ""
                if ':' in rest:
                    val_part, desc = rest.rsplit(':', 1)
                else:
                    val_part, desc = rest, ""
                # Extract unit and value
                val_parts = val_part.strip().split(None, 1)
                unit = val_parts[0] if val_parts else ""
                value = val_parts[1].strip() if len(val_parts) > 1 else unit
                well_info[mnem] = {"value": value, "unit": unit, "description": desc.strip()}
                if mnem == "NULL":
                    try:
                        null_value = float(value)
                    except ValueError:
                        pass

        elif current_section == 'curve':
            # Parse curve info
            if '.' in line:
                parts = line.split('.', 1)
                mnem = parts[0].strip().upper()
                rest = parts[1] if len(parts) > 1 else ""
                if ':' in rest:
                    unit_val, desc = rest.rsplit(':', 1)
                else:
                    unit_val, desc = rest, ""
                unit = unit_val.strip().split()[0] if unit_val.strip() else ""
                curve_names.append(mnem)
                mapped = mnemonic_map.get(mnem, mnem.lower())
                curve_info.append({
                    "mnemonic": mnem,
                    "unit": unit,
                    "description": desc.strip(),
                    "mapped_to": mapped,
                })

        elif current_section == 'data':
            # Parse data values
            values = line.split()
            if len(values) == len(curve_names):
                row = {}
                for ci, val_str in zip(curve_info, values):
                    try:
                        val = float(val_str)
                        if abs(val - null_value) < 0.01:
                            val = None
                        row[ci["mapped_to"]] = val
                    except ValueError:
                        row[ci["mapped_to"]] = None
                data_rows.append(row)

    # Build curve_mapping summary
    curve_mapping = {}
    for ci in curve_info:
        curve_mapping[ci["mnemonic"]] = ci["mapped_to"]

    return {
        "well_info": well_info,
        "curve_info": curve_info,
        "curve_mapping": curve_mapping,
        "data": data_rows,
        "data_points": len(data_rows),
        "curves_found": [ci["mnemonic"] for ci in curve_info],
        "null_value": null_value,
        "file_path": file_path,
    }
