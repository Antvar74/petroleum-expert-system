"""
Petrophysics Engine — LAS File Parsing.

LAS 2.0/3.0 file parsing via lasio library.
Standardizes mnemonic names using MNEMONIC_MAP.
"""
import math
import os
from typing import Dict, Any

from .constants import MNEMONIC_MAP

try:
    import lasio
    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False


def parse_las_file(file_path: str) -> Dict[str, Any]:
    """
    Parse LAS 2.0/3.0 file using lasio library.

    Args:
        file_path: path to .las file

    Returns:
        Dict with well_info, curves (list of mnemonic names),
        data (list of dicts with standardized keys), units, stats
    """
    if not HAS_LASIO:
        return {"error": "lasio library not installed. Run: pip install lasio"}

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        las = lasio.read(file_path)
    except Exception as e:
        return {"error": f"Cannot parse LAS file: {str(e)}"}

    return _process_lasio_object(las)


def parse_las_content(content: str) -> Dict[str, Any]:
    """
    Parse LAS content from string (for frontend upload without file).

    Args:
        content: LAS file content as string

    Returns:
        Same structure as parse_las_file
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

    return _process_lasio_object(las)


def _process_lasio_object(las) -> Dict[str, Any]:
    """Process a lasio.LASFile object into standardized output."""
    # Extract well info
    well_info = {}
    for item in las.well:
        well_info[item.mnemonic] = item.value

    # Extract curve info and map mnemonics
    curves = []
    curve_mapping = {}
    units = {}
    for curve in las.curves:
        mnem = curve.mnemonic.upper().strip()
        std_name = MNEMONIC_MAP.get(mnem, mnem.lower())
        curves.append(mnem)
        curve_mapping[mnem] = std_name
        units[std_name] = curve.unit

    # Extract data rows
    data = []
    null_val = las.well.NULL.value if hasattr(las.well, 'NULL') else -999.25
    try:
        null_val = float(null_val)
    except (ValueError, TypeError):
        null_val = -999.25

    for i in range(len(las[las.curves[0].mnemonic])):
        row = {}
        for curve in las.curves:
            mnem = curve.mnemonic.upper().strip()
            std_name = curve_mapping.get(mnem, mnem.lower())
            val = float(las[curve.mnemonic][i])
            # Replace null values and NaN with None
            if math.isnan(val) or abs(val - null_val) < 0.01:
                row[std_name] = None
            else:
                row[std_name] = round(val, 6)
        data.append(row)

    # Compute basic stats per curve
    stats = {}
    for curve in las.curves:
        mnem = curve.mnemonic.upper().strip()
        std_name = curve_mapping.get(mnem, mnem.lower())
        valid_vals = [d[std_name] for d in data if d.get(std_name) is not None]
        if valid_vals:
            stats[std_name] = {
                "min": round(min(valid_vals), 4),
                "max": round(max(valid_vals), 4),
                "mean": round(sum(valid_vals) / len(valid_vals), 4),
                "count": len(valid_vals),
            }

    return {
        "well_info": well_info,
        "curves": curves,
        "curve_mapping": curve_mapping,
        "units": units,
        "data": data,
        "stats": stats,
        "depth_range": {
            "min": data[0].get("md") if data else None,
            "max": data[-1].get("md") if data else None,
            "points": len(data),
        },
    }
