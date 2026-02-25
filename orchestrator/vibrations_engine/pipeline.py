"""Full vibration analysis pipeline -- orchestrates all sub-modules."""
from typing import Dict, Any, Optional

from .critical_speeds import (
    calculate_critical_rpm_axial,
    calculate_critical_rpm_lateral,
)
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse
from .stability import calculate_stability_index, generate_vibration_map


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
    )

    # 5. Combined stability
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
    if mse.get("is_founder_point", False):
        alerts.append("Founder point detected — MSE excessive, check bit condition")
    if stability["stability_index"] < 40:
        alerts.append(f"Critical stability index {stability['stability_index']:.0f} — modify drilling parameters")

    # Summary
    summary = {
        "stability_index": stability["stability_index"],
        "stability_status": stability["status"],
        "critical_rpm_axial": axial.get("critical_rpm_1st", 0),
        "critical_rpm_lateral": lateral.get("critical_rpm", 0),
        "stick_slip_severity": stick_slip.get("severity_index", 0),
        "stick_slip_class": stick_slip.get("classification", "N/A"),
        "mse_psi": mse.get("mse_total_psi", 0),
        "mse_efficiency_pct": mse.get("efficiency_pct", 0),
        "optimal_wob": vib_map["optimal_point"]["wob"],
        "optimal_rpm": vib_map["optimal_point"]["rpm"],
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "axial_vibrations": axial,
        "lateral_vibrations": lateral,
        "stick_slip": stick_slip,
        "mse": mse,
        "stability": stability,
        "vibration_map": vib_map,
        "alerts": alerts,
    }
