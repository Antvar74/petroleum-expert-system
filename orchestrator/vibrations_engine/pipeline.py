"""Full vibration analysis pipeline -- orchestrates all sub-modules."""
from typing import Dict, Any, Optional, List

from .critical_speeds import (
    calculate_critical_rpm_axial,
    calculate_critical_rpm_lateral,
    calculate_critical_rpm_lateral_multi,
)
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
from .stability import calculate_stability_index, generate_vibration_map
from .bit_excitation import calculate_bit_excitation, check_resonance


def calculate_full_vibration_analysis(
    wob_klb: float,
    rpm: float,
    rop_fph: float,
    torque_ftlb: float,
    bit_diameter_in: float,
    dp_od_in: float = 5.0,
    dp_id_in: float = 4.276,
    dp_weight_lbft: float = 19.5,
    bha_length_ft: float = 300,
    bha_od_in: float = 6.75,
    bha_id_in: float = 2.813,
    bha_weight_lbft: float = 83.0,
    mud_weight_ppg: float = 10.0,
    hole_diameter_in: float = 8.5,
    inclination_deg: float = 0.0,
    friction_factor: float = 0.25,
    stabilizer_spacing_ft: Optional[float] = None,
    ucs_psi: Optional[float] = None,
    n_blades: Optional[int] = None,
    bha_components: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Complete vibration analysis combining all modes.

    Returns:
        Dict with all vibration analyses, stability index, vibration map, alerts
    """
    # 1. Axial vibrations
    axial = calculate_critical_rpm_axial(
        bha_length_ft=bha_length_ft,
        bha_od_in=bha_od_in,
        bha_id_in=bha_id_in,
        bha_weight_lbft=bha_weight_lbft,
        mud_weight_ppg=mud_weight_ppg,
    )

    # 2. Lateral vibrations
    if bha_components:
        lateral = calculate_critical_rpm_lateral_multi(
            bha_components=bha_components,
            mud_weight_ppg=mud_weight_ppg,
            hole_diameter_in=hole_diameter_in,
        )
        # Extract critical RPM for stability index (use mode 1)
        lateral_crit_rpm = lateral.get("mode_1_critical_rpm", 999)
        # Add a "critical_rpm" key for consistency with stability_index expectations
        lateral["critical_rpm"] = lateral_crit_rpm
    else:
        lateral = calculate_critical_rpm_lateral(
            bha_length_ft=bha_length_ft,
            bha_od_in=bha_od_in,
            bha_id_in=bha_id_in,
            bha_weight_lbft=bha_weight_lbft,
            hole_diameter_in=hole_diameter_in,
            mud_weight_ppg=mud_weight_ppg,
            inclination_deg=inclination_deg,
            stabilizer_spacing_ft=stabilizer_spacing_ft,
        )

    # 3. Stick-slip
    stick_slip = calculate_stick_slip_severity(
        surface_rpm=rpm,
        wob_klb=wob_klb,
        torque_ftlb=torque_ftlb,
        bit_diameter_in=bit_diameter_in,
        bha_length_ft=bha_length_ft,
        bha_od_in=bha_od_in,
        bha_id_in=bha_id_in,
        mud_weight_ppg=mud_weight_ppg,
        friction_factor=friction_factor,
    )

    # 4. MSE
    mse = calculate_mse(
        wob_klb=wob_klb,
        torque_ftlb=torque_ftlb,
        rpm=rpm,
        rop_fph=rop_fph,
        bit_diameter_in=bit_diameter_in,
        ucs_psi=ucs_psi,
    )

    # 5. Bit excitation & resonance (when n_blades provided)
    bit_excite = None
    resonance = None
    if n_blades and n_blades > 0:
        bit_excite = calculate_bit_excitation(
            bit_type="pdc",
            num_blades_or_cones=n_blades,
            rpm=rpm,
            wob_klb=wob_klb,
            rock_ucs_psi=ucs_psi or 15000.0,
            bit_diameter_in=bit_diameter_in,
            rop_fph=rop_fph,
        )
        # Collect BHA natural frequencies for resonance check
        natural_freqs = []
        axial_freq = axial.get("critical_rpm_1st", 0)
        if axial_freq > 0:
            natural_freqs.append(axial_freq / 60.0)  # RPM → Hz
        lateral_freq = lateral.get("critical_rpm", 0)
        if lateral_freq > 0:
            natural_freqs.append(lateral_freq / 60.0)
        if natural_freqs:
            resonance = check_resonance(
                excitation_freq_hz=bit_excite["excitation_freq_hz"],
                natural_freqs_hz=natural_freqs,
            )

    # 6. Combined stability  (renumbered from 5)
    stability = calculate_stability_index(
        axial_result=axial,
        lateral_result=lateral,
        stick_slip_result=stick_slip,
        mse_result=mse,
        operating_rpm=rpm,
    )

    # 6. Vibration map
    vib_map = generate_vibration_map(
        bit_diameter_in=bit_diameter_in,
        bha_od_in=bha_od_in,
        bha_id_in=bha_id_in,
        bha_weight_lbft=bha_weight_lbft,
        bha_length_ft=bha_length_ft,
        hole_diameter_in=hole_diameter_in,
        mud_weight_ppg=mud_weight_ppg,
        torque_base_ftlb=torque_ftlb,
        rop_base_fph=rop_fph,
        stabilizer_spacing_ft=stabilizer_spacing_ft,
    )

    # Alerts
    alerts = []
    axial_crit = axial.get("critical_rpm_1st", 999)
    if abs(rpm - axial_crit) < axial_crit * 0.1:
        alerts.append(f"Operating near axial resonance ({axial_crit:.0f} RPM) — risk of bit bounce")
    lateral_crit = lateral.get("critical_rpm", 999)
    if abs(rpm - lateral_crit) < lateral_crit * 0.15:
        alerts.append(f"Operating near lateral critical RPM ({lateral_crit:.0f}) — whirl risk")
    ss_sev = stick_slip.get("severity_index", 0)
    if ss_sev > 1.0:
        alerts.append(f"Stick-slip severity {ss_sev:.2f} — {stick_slip.get('recommendation', '')}")
    if mse.get("mse_total_psi", 0) > 100000:
        alerts.append("Excessive MSE detected — check bit condition and drilling parameters")
    if stability["stability_index"] < 40:
        alerts.append(f"Critical stability index {stability['stability_index']:.0f} — modify drilling parameters")
    if resonance and resonance.get("resonance_risk") in ("critical", "high"):
        alerts.append(f"Bit excitation near BHA resonance (mode {resonance['nearest_mode']}, risk: {resonance['resonance_risk']}) — adjust RPM")

    # Summary
    summary = {
        "stability_index": stability["stability_index"],
        "stability_status": stability["status"],
        "critical_rpm_axial": axial.get("critical_rpm_1st", 0),
        "critical_rpm_lateral": lateral.get("critical_rpm", 0),
        "stick_slip_severity": stick_slip.get("severity_index", 0),
        "stick_slip_class": stick_slip.get("classification", "N/A"),
        "mse_psi": mse.get("mse_total_psi", 0),
        "mse_efficiency_pct": mse.get("efficiency_pct"),
        "optimal_wob": vib_map["optimal_point"]["wob"],
        "optimal_rpm": vib_map["optimal_point"]["rpm"],
        "alerts": alerts,
    }

    result = {
        "summary": summary,
        "axial_vibrations": axial,
        "lateral_vibrations": lateral,
        "stick_slip": stick_slip,
        "mse": mse,
        "stability": stability,
        "vibration_map": vib_map,
        "alerts": alerts,
    }
    if bit_excite:
        result["bit_excitation"] = bit_excite
    if resonance:
        result["resonance_check"] = resonance
    return result
