"""Bit-rock excitation frequency and resonance check.

References:
- PDC blade-passing and roller-cone tooth-striking excitation models
"""
import math
from typing import Dict, Any, List


def calculate_bit_excitation(
    bit_type: str,
    num_blades_or_cones: int,
    rpm: float,
    wob_klb: float,
    rock_ucs_psi: float = 15000.0,
    bit_diameter_in: float = 8.5,
    rop_fph: float = 50.0
) -> Dict[str, Any]:
    """
    Calculate bit-rock excitation frequencies and cutting forces.

    PDC bit: excitation at N_blades * RPM/60 (blade-passing frequency)
    Roller-cone: excitation at N_teeth * RPM/60 * 3 cones (tooth-striking)

    Resonance risk is assessed by proximity to BHA natural frequencies.

    Args:
        bit_type: 'pdc' or 'roller_cone'
        num_blades_or_cones: number of blades (PDC) or teeth per cone (roller)
        rpm: rotary speed (RPM)
        wob_klb: weight on bit (klb)
        rock_ucs_psi: rock unconfined compressive strength (psi)
        bit_diameter_in: bit diameter (inches)
        rop_fph: rate of penetration (ft/hr)

    Returns:
        Dict with excitation frequency, depth of cut, cutting force, harmonics.
    """
    if rpm <= 0 or bit_diameter_in <= 0:
        return {"error": "RPM and bit diameter must be > 0"}

    wob_lbs = wob_klb * 1000.0
    bit_area = math.pi * bit_diameter_in ** 2 / 4.0  # in^2

    # Depth of cut per revolution
    rop_ipm = rop_fph * 12.0 / 60.0  # in/min
    doc_in = rop_ipm / rpm if rpm > 0 else 0  # in/rev

    # Cutting force estimate: F_c ~ UCS * A_contact
    # A_contact ~ DOC * bit_diameter (simplified ribbon area)
    a_contact = doc_in * bit_diameter_in  # in^2
    cutting_force = rock_ucs_psi * a_contact  # lbs

    # Excitation frequency
    bit_type_lower = bit_type.lower().replace("-", "_").replace(" ", "_")
    if bit_type_lower in ("pdc", "fixed_cutter"):
        n_blades = max(1, num_blades_or_cones)
        excitation_freq_hz = n_blades * rpm / 60.0
        excitation_desc = f"PDC blade-passing: {n_blades} blades × {rpm} RPM"
    elif bit_type_lower in ("roller_cone", "tricone", "rc"):
        n_teeth = max(1, num_blades_or_cones)
        excitation_freq_hz = n_teeth * rpm / 60.0 * 3  # 3 cones
        excitation_desc = f"Roller-cone tooth-striking: {n_teeth} teeth × 3 cones × {rpm} RPM"
    else:
        excitation_freq_hz = num_blades_or_cones * rpm / 60.0
        excitation_desc = f"Generic: {num_blades_or_cones} elements × {rpm} RPM"

    # Harmonics
    harmonics = [
        {"harmonic": h, "freq_hz": round(excitation_freq_hz * h, 2)}
        for h in [1, 2, 3]
    ]

    return {
        "excitation_freq_hz": round(excitation_freq_hz, 2),
        "excitation_description": excitation_desc,
        "depth_of_cut_in": round(doc_in, 5),
        "cutting_force_lbs": round(cutting_force, 0),
        "contact_area_in2": round(a_contact, 4),
        "bit_type": bit_type_lower,
        "harmonics": harmonics,
        "rpm": rpm,
        "wob_klb": wob_klb,
        "rock_ucs_psi": rock_ucs_psi,
    }


def check_resonance(
    excitation_freq_hz: float,
    natural_freqs_hz: List[float],
    tolerance_pct: float = 15.0
) -> Dict[str, Any]:
    """
    Check if bit excitation frequency is near any BHA natural frequency.

    Resonance occurs when f_excitation ~ f_natural (within tolerance).
    Returns risk level and recommended RPM adjustments.

    Args:
        excitation_freq_hz: bit excitation frequency (Hz)
        natural_freqs_hz: list of BHA natural frequencies (Hz)
        tolerance_pct: proximity threshold for resonance warning (%)

    Returns:
        Dict with resonance_risk, nearest_mode, detuning recommendations.
    """
    if excitation_freq_hz <= 0 or not natural_freqs_hz:
        return {
            "resonance_risk": "low",
            "nearest_mode": None,
            "frequency_ratio": 0,
            "detuning_rpm_recommended": None,
            "color": "green",
        }

    nearest_mode = None
    min_ratio_diff = float("inf")
    nearest_freq = 0

    for idx, fn in enumerate(natural_freqs_hz):
        if fn <= 0:
            continue
        ratio = excitation_freq_hz / fn
        diff = abs(ratio - 1.0)
        if diff < min_ratio_diff:
            min_ratio_diff = diff
            nearest_mode = idx + 1
            nearest_freq = fn

    tol_frac = tolerance_pct / 100.0

    if min_ratio_diff < tol_frac * 0.5:
        risk = "critical"
        color = "red"
    elif min_ratio_diff < tol_frac:
        risk = "high"
        color = "orange"
    elif min_ratio_diff < tol_frac * 2:
        risk = "moderate"
        color = "yellow"
    else:
        risk = "low"
        color = "green"

    # Suggest detuning: shift RPM so excitation moves away from natural freq
    # f_excite = N * RPM/60 -> RPM = f_excite * 60 / N
    # To move to 0.80 * fn: RPM_low = 0.80 * fn * 60 / N_blades (approx)
    # We suggest +/-20% away from resonant RPM
    detuning_rpm = None
    if risk in ("critical", "high", "moderate") and nearest_freq > 0:
        resonant_rpm = nearest_freq * 60.0  # approximate (1:1 ratio)
        detuning_rpm = {
            "decrease_to": round(resonant_rpm * 0.80),
            "increase_to": round(resonant_rpm * 1.20),
        }

    return {
        "resonance_risk": risk,
        "nearest_mode": nearest_mode,
        "nearest_natural_freq_hz": round(nearest_freq, 2) if nearest_freq > 0 else None,
        "excitation_freq_hz": round(excitation_freq_hz, 2),
        "frequency_ratio": round(excitation_freq_hz / nearest_freq, 3) if nearest_freq > 0 else 0,
        "min_frequency_gap_pct": round(min_ratio_diff * 100, 1),
        "detuning_rpm_recommended": detuning_rpm,
        "color": color,
    }
