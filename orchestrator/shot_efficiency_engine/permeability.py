"""Permeability estimation and hydrocarbon type classification."""
import math
from typing import Dict, Any


def calculate_permeability_timur(
    porosity: float,
    sw_irreducible: float
) -> Dict[str, Any]:
    """
    Timur (1968) permeability from porosity and irreducible Sw.

    k = 0.136 * phi^4.4 / Swirr^2  (mD)

    Best for sandstones.

    Args:
        porosity: total porosity (v/v fraction)
        sw_irreducible: irreducible water saturation (v/v fraction)

    Returns:
        Dict with k_md, method
    """
    if porosity <= 0 or sw_irreducible <= 0:
        return {"k_md": 0.0, "method": "timur",
                "note": "Invalid inputs \u2014 zero permeability"}

    # Timur formula (phi in fraction)
    k = 0.136 * (porosity ** 4.4) / (sw_irreducible ** 2)
    # Convert: original formula uses phi in %, so scale
    # Actually Timur (1968) with phi in fraction: k = 8.58e4 * phi^4.4 / Swirr^2
    k = 8.58e4 * (porosity ** 4.4) / (sw_irreducible ** 2)

    # Classify
    if k > 1000:
        perm_class = "Very High"
    elif k > 100:
        perm_class = "High"
    elif k > 10:
        perm_class = "Moderate"
    elif k > 1:
        perm_class = "Low"
    else:
        perm_class = "Very Low / Tight"

    return {
        "k_md": round(k, 3),
        "perm_class": perm_class,
        "porosity": round(porosity, 4),
        "sw_irreducible": round(sw_irreducible, 4),
        "method": "timur",
    }


def calculate_permeability_coates(
    porosity: float,
    sw_irreducible: float
) -> Dict[str, Any]:
    """
    Coates-Dumanoir permeability estimation.

    k = [(100*phi)^2 * (1-Swirr)/Swirr]^2 / 10000  (mD)

    Good for carbonates and mixed lithologies.

    Args:
        porosity: total porosity (v/v fraction)
        sw_irreducible: irreducible water saturation (v/v fraction)

    Returns:
        Dict with k_md, method
    """
    if porosity <= 0 or sw_irreducible <= 0 or sw_irreducible >= 1.0:
        return {"k_md": 0.0, "method": "coates",
                "note": "Invalid inputs \u2014 zero permeability"}

    ratio = (1.0 - sw_irreducible) / sw_irreducible
    k = ((100.0 * porosity) ** 2 * ratio) ** 2 / 10000.0

    if k > 1000:
        perm_class = "Very High"
    elif k > 100:
        perm_class = "High"
    elif k > 10:
        perm_class = "Moderate"
    elif k > 1:
        perm_class = "Low"
    else:
        perm_class = "Very Low / Tight"

    return {
        "k_md": round(k, 3),
        "perm_class": perm_class,
        "porosity": round(porosity, 4),
        "sw_irreducible": round(sw_irreducible, 4),
        "method": "coates",
    }


def classify_hydrocarbon_type(
    phi_density: float,
    phi_neutron: float,
    rt: float,
    rxo: float = 0.0,
    sw: float = 0.5,
    sxo: float = 0.7
) -> Dict[str, Any]:
    """
    Discriminate oil vs gas vs water using crossplot indicators.

    Key indicators:
    - Density-neutron separation: gas pulls neutron left, density right
    - Moveable HC Index (MHI): phi * (1 - Sw/Sxo)
    - Bulk Volume Water (BVW): phi * Sw

    Args:
        phi_density: density-derived porosity (v/v)
        phi_neutron: neutron porosity (v/v)
        rt: deep resistivity (ohm-m)
        rxo: shallow/flushed resistivity (ohm-m), 0 = not available
        sw: water saturation (v/v)
        sxo: flushed zone water saturation (v/v)

    Returns:
        Dict with type classification, confidence, MHI, BVW
    """
    phi_avg = (phi_density + phi_neutron) / 2.0 if (phi_density + phi_neutron) > 0 else 0.01

    # Density-neutron separation (gas effect)
    dn_separation = phi_density - phi_neutron

    # MHI: Moveable Hydrocarbon Index
    if sxo > 0 and phi_avg > 0:
        MHI = phi_avg * (1.0 - sw / sxo) if sw <= sxo else 0.0
    else:
        MHI = 0.0
    MHI = max(0.0, MHI)

    # BVW: Bulk Volume Water
    BVW = phi_avg * sw

    # Classification logic
    confidence = 0.0
    hc_type = "water"

    if sw > 0.80:
        hc_type = "water"
        confidence = min(1.0, sw)
    elif dn_separation > 0.04 and phi_neutron < phi_density:
        # Gas: neutron reads lower than density (gas pulls neutron down)
        hc_type = "gas"
        confidence = min(1.0, dn_separation / 0.10)
        if sw < 0.40:
            confidence = min(1.0, confidence + 0.2)
    elif sw < 0.60:
        hc_type = "oil"
        confidence = min(1.0, (0.60 - sw) / 0.40 + 0.3)
        if MHI > 0.02:
            confidence = min(1.0, confidence + 0.15)
    else:
        hc_type = "water_with_hc"
        confidence = 0.5

    # Resistivity ratio check (if Rxo available)
    if rxo > 0 and rt > 0:
        ri_ratio = rt / rxo
        if ri_ratio > 2.0 and hc_type in ("oil", "gas"):
            confidence = min(1.0, confidence + 0.1)

    return {
        "type": hc_type,
        "confidence": round(confidence, 3),
        "MHI": round(MHI, 4),
        "BVW": round(BVW, 4),
        "dn_separation": round(dn_separation, 4),
        "phi_density": round(phi_density, 4),
        "phi_neutron": round(phi_neutron, 4),
        "sw": round(sw, 4),
    }
