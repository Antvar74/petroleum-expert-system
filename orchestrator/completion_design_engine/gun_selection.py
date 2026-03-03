"""
Completion Design Engine — gun selection (simple catalog + expanded catalog).

References:
- Schlumberger PowerJet, Halliburton Piranha-class, Baker Atlas public specs
- API RP 19B: minimum clearance and performance criteria
"""
from typing import Dict, Any, List

from .constants import GUN_DATABASE, GUN_CATALOG


def select_gun_configuration(
    casing_id_in: float,
    tubing_od_in: float = 0.0,
    max_pressure_psi: float = 15000,
    target_spf: int = 0,
    conveyed_by: str = "wireline",
) -> Dict[str, Any]:
    """
    Select optimal gun configuration based on casing geometry.

    Args:
        casing_id_in: casing inner diameter (inches)
        tubing_od_in: tubing OD if through-tubing (0 = casing guns)
        max_pressure_psi: maximum bottomhole pressure rating needed
        target_spf: desired shots per foot (0 = auto)
        conveyed_by: "wireline", "tubing", "coiled_tubing", "tcp"

    Returns:
        Dict with recommended guns, clearance check, alternatives
    """
    is_through_tubing = tubing_od_in > 0

    compatible_guns: List[Dict[str, Any]] = []
    for name, spec in GUN_DATABASE.items():
        clearance = casing_id_in - spec["od_in"]
        if clearance < 0.25:   # minimum clearance 0.25"
            continue
        if is_through_tubing and spec["od_in"] > (tubing_od_in - 0.5):
            continue
        compatible_guns.append({
            "gun_size": name,
            "od_in": spec["od_in"],
            "clearance_in": round(clearance, 3),
            "typical_spf": spec["typical_spf"],
            "available_phasing": spec["phasing"],
            "score": clearance * 0.3 + spec["typical_spf"] * 0.7,
        })

    compatible_guns.sort(key=lambda g: g["score"], reverse=True)
    recommended = compatible_guns[0] if compatible_guns else None

    convey_notes = {
        "wireline":     "Standard deployment. Max gun length ~60 ft per run.",
        "tubing":       "Tubing-conveyed perforating (TCP). Allows long intervals.",
        "coiled_tubing": "CT-conveyed. Good for horizontal wells.",
        "tcp":          "TCP with packer. Allows underbalanced perforating.",
    }

    return {
        "recommended": recommended,
        "alternatives": compatible_guns[1:3] if len(compatible_guns) > 1 else [],
        "all_compatible": compatible_guns,
        "casing_id_in": casing_id_in,
        "is_through_tubing": is_through_tubing,
        "conveyed_by": conveyed_by,
        "conveyance_notes": convey_notes.get(conveyed_by, "Standard wireline."),
        "total_compatible_guns": len(compatible_guns),
    }


def select_gun_from_catalog(
    casing_id_in: float,
    max_pressure_psi: float = 15000.0,
    max_temperature_f: float = 400.0,
    gun_type_filter: str = "",
    min_penetration_in: float = 0.0,
    target_spf: int = 0,
    conveyed_by: str = "",
) -> Dict[str, Any]:
    """
    Select optimal gun from expanded GUN_CATALOG with pressure/temp/type filters.

    Args:
        casing_id_in: casing inner diameter (inches)
        max_pressure_psi: maximum BHP the gun must withstand (psi)
        max_temperature_f: maximum BHT the gun must withstand (°F)
        gun_type_filter: filter by type: "wireline", "tcp", "coiled_tubing", "" = all
        min_penetration_in: minimum required Berea penetration (inches)
        target_spf: desired SPF (0 = any)
        conveyed_by: preferred conveyance method (maps to gun_type)

    Returns:
        Dict with ranked compatible guns, best selection, filters applied
    """
    type_filter = gun_type_filter.lower() if gun_type_filter else ""
    if conveyed_by and not type_filter:
        conv_map = {
            "wireline": "wireline", "tubing": "tcp", "tcp": "tcp",
            "coiled_tubing": "coiled_tubing", "ct": "coiled_tubing",
        }
        type_filter = conv_map.get(conveyed_by.lower(), "")

    compatible: List[Dict[str, Any]] = []
    for gun in GUN_CATALOG:
        clearance = casing_id_in - gun["od_in"]
        if clearance < 0.25:
            continue
        if gun["max_pressure_psi"] < max_pressure_psi:
            continue
        if gun["max_temp_f"] < max_temperature_f:
            continue
        if type_filter and gun["gun_type"] != type_filter:
            continue
        if min_penetration_in > 0 and gun["penetration_berea_in"] < min_penetration_in:
            continue
        if target_spf > 0 and gun["spf"] != target_spf:
            continue

        score = (gun["penetration_berea_in"] * 0.4
                 + gun["spf"] * 0.3
                 + clearance * 0.2
                 + gun["ehd_in"] * 10.0 * 0.1)

        compatible.append({
            "name": gun["name"],
            "od_in": gun["od_in"],
            "gun_type": gun["gun_type"],
            "penetration_berea_in": gun["penetration_berea_in"],
            "ehd_in": gun["ehd_in"],
            "spf": gun["spf"],
            "phasing": gun["phasing"],
            "max_pressure_psi": gun["max_pressure_psi"],
            "max_temp_f": gun["max_temp_f"],
            "clearance_in": round(clearance, 3),
            "score": round(score, 3),
        })

    compatible.sort(key=lambda g: g["score"], reverse=True)

    return {
        "recommended": compatible[0] if compatible else None,
        "alternatives": compatible[1:5] if len(compatible) > 1 else [],
        "all_compatible": compatible,
        "total_compatible": len(compatible),
        "filters_applied": {
            "casing_id_in": casing_id_in,
            "max_pressure_psi": max_pressure_psi,
            "max_temperature_f": max_temperature_f,
            "gun_type_filter": type_filter or "all",
            "min_penetration_in": min_penetration_in,
            "target_spf": target_spf,
        },
        "catalog_size": len(GUN_CATALOG),
    }
