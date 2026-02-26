"""Stability index, vibration map (2D), and 3D survey-coupled vibration map.

References:
- Dunayevsky (1993): Stability of BHA in directional wells
- Paslay & Dawson (1984): Drillstring lateral vibrations and whirl
"""
import math
from typing import Dict, Any, List, Optional

from .critical_speeds import (
    calculate_critical_rpm_axial,
    calculate_critical_rpm_lateral,
    STEEL_E,
)
from .stick_slip import calculate_stick_slip_severity
from .mse import calculate_mse


def calculate_stability_index(
    axial_result: Dict[str, Any],
    lateral_result: Dict[str, Any],
    stick_slip_result: Dict[str, Any],
    mse_result: Dict[str, Any],
    operating_rpm: float
) -> Dict[str, Any]:
    """
    Calculate combined stability index from all vibration modes.

    Index = weighted combination of all modes (0-100, higher = more stable).

    Args:
        axial_result: output from calculate_critical_rpm_axial
        lateral_result: output from calculate_critical_rpm_lateral
        stick_slip_result: output from calculate_stick_slip_severity
        mse_result: output from calculate_mse
        operating_rpm: current operating RPM

    Returns:
        Dict with stability index, per-mode scores, overall status
    """
    scores = {}

    # Axial score: distance from critical RPM (closer = worse)
    axial_crit = axial_result.get("critical_rpm_1st", 999)
    if axial_crit > 0:
        axial_ratio = abs(operating_rpm - axial_crit) / axial_crit
        scores["axial"] = min(100, axial_ratio * 100)
    else:
        scores["axial"] = 50

    # Lateral score: operating below critical = better
    lateral_crit = lateral_result.get("critical_rpm", 999)
    if lateral_crit > 0:
        if operating_rpm < lateral_crit * 0.85:
            scores["lateral"] = 90
        elif operating_rpm < lateral_crit:
            scores["lateral"] = 60
        elif operating_rpm < lateral_crit * 1.15:
            scores["lateral"] = 30  # near resonance
        else:
            scores["lateral"] = 50  # above resonance
    else:
        scores["lateral"] = 50

    # Stick-slip score
    ss_severity = stick_slip_result.get("severity_index", 0)
    scores["torsional"] = max(0, 100 - ss_severity * 66.7)

    # MSE score
    mse_val = mse_result.get("mse_total_psi", 50000)
    if mse_val < 20000:
        scores["mse"] = 95
    elif mse_val < 50000:
        scores["mse"] = 70
    elif mse_val < 100000:
        scores["mse"] = 40
    else:
        scores["mse"] = 15

    # Weighted overall
    weights = {"axial": 0.20, "lateral": 0.30, "torsional": 0.35, "mse": 0.15}
    overall = sum(scores[k] * weights[k] for k in scores)

    if overall >= 80:
        status = "Stable"
        color = "green"
    elif overall >= 60:
        status = "Marginal"
        color = "yellow"
    elif overall >= 40:
        status = "Unstable"
        color = "orange"
    else:
        status = "Critical"
        color = "red"

    return {
        "stability_index": round(overall, 1),
        "status": status,
        "color": color,
        "mode_scores": {k: round(v, 1) for k, v in scores.items()},
        "weights": weights,
        "operating_rpm": operating_rpm,
    }


def generate_vibration_map(
    bit_diameter_in: float,
    bha_od_in: float,
    bha_id_in: float,
    bha_weight_lbft: float,
    bha_length_ft: float,
    hole_diameter_in: float,
    mud_weight_ppg: float = 10.0,
    wob_range: Optional[List[float]] = None,
    rpm_range: Optional[List[float]] = None,
    torque_base_ftlb: float = 10000,
    rop_base_fph: float = 50,
    stabilizer_spacing_ft: Optional[float] = None,
    ucs_psi: Optional[float] = None,
    total_depth_ft: Optional[float] = None,
    dp_od_in: float = 5.0,
    dp_id_in: float = 4.276,
) -> Dict[str, Any]:
    """
    Generate RPM vs WOB vibration stability map (heatmap data).

    For each (RPM, WOB) combination, calculate stability and classify
    into zones: Stable (green), Marginal (yellow), Unstable (red).

    Args:
        Standard BHA and wellbore parameters
        wob_range: list of WOB values (klb) to test
        rpm_range: list of RPM values to test

    Returns:
        Dict with heatmap data, optimal zone, boundary curves
    """
    if wob_range is None:
        wob_range = [5, 10, 15, 20, 25, 30, 35, 40]
    if rpm_range is None:
        rpm_range = [40, 60, 80, 100, 120, 140, 160, 180, 200]

    # Pre-calculate critical RPMs (independent of WOB/RPM operating point)
    axial = calculate_critical_rpm_axial(
        bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft, mud_weight_ppg
    )
    lateral = calculate_critical_rpm_lateral(
        bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft,
        hole_diameter_in, mud_weight_ppg,
        stabilizer_spacing_ft=stabilizer_spacing_ft,
    )

    map_data = []
    optimal_point = {"wob": 0, "rpm": 0, "score": 0}

    for wob in wob_range:
        for rpm in rpm_range:
            # Estimate torque: T ~ T_base * (WOB/WOB_base) * (RPM_factor)
            torque_est = torque_base_ftlb * (wob / 20.0) * (1.0 + 0.002 * (rpm - 100))
            torque_est = max(1000, torque_est)

            # Estimate ROP: simplified D-exponent influence
            rop_est = max(5, rop_base_fph * (wob / 20.0) * (rpm / 120.0))

            stick_slip = calculate_stick_slip_severity(
                surface_rpm=rpm, wob_klb=wob, torque_ftlb=torque_est,
                bit_diameter_in=bit_diameter_in, bha_length_ft=bha_length_ft,
                bha_od_in=bha_od_in, bha_id_in=bha_id_in, mud_weight_ppg=mud_weight_ppg,
                total_depth_ft=total_depth_ft,
                dp_od_in=dp_od_in, dp_id_in=dp_id_in,
            )
            mse = calculate_mse(
                wob_klb=wob, torque_ftlb=torque_est, rpm=rpm,
                rop_fph=rop_est, bit_diameter_in=bit_diameter_in,
            )
            stability = calculate_stability_index(
                axial, lateral, stick_slip, mse, rpm
            )

            score = stability["stability_index"]
            point = {
                "wob_klb": wob, "rpm": rpm,
                "stability_index": score,
                "status": stability["status"],
                "stick_slip_severity": stick_slip.get("severity_index", 0),
                "mse_psi": mse.get("mse_total_psi", 0),
            }
            map_data.append(point)

            if score > optimal_point["score"]:
                optimal_point = {"wob": wob, "rpm": rpm, "score": score}

    return {
        "map_data": map_data,
        "wob_range": wob_range,
        "rpm_range": rpm_range,
        "optimal_point": optimal_point,
        "critical_rpm_axial": axial.get("critical_rpm_1st", 0),
        "critical_rpm_lateral": lateral.get("critical_rpm", 0),
    }


def calculate_vibration_map_3d(
    survey_stations: List[Dict[str, float]],
    bha_od_in: float = 6.75,
    bha_id_in: float = 2.813,
    bha_weight_lbft: float = 83.0,
    bha_length_ft: float = 300.0,
    hole_diameter_in: float = 8.5,
    mud_weight_ppg: float = 10.0,
    rpm_range: Optional[List[float]] = None,
    wob_klb: float = 20.0
) -> Dict[str, Any]:
    """
    Generate a 3D vibration risk map: critical RPM as function of measured depth.

    Uses the Paslay-Dawson formula with depth-varying inclination from the
    actual survey to produce a critical-RPM vs MD profile, plus a risk matrix
    (MD x RPM) classifying each cell as green/yellow/red.

    Args:
        survey_stations: list of {md_ft, inclination_deg, azimuth_deg}
        bha_od_in, bha_id_in, bha_weight_lbft, bha_length_ft: BHA geometry
        hole_diameter_in: hole / casing ID
        mud_weight_ppg: mud weight (ppg)
        rpm_range: list of RPMs to evaluate (default 40-220 step 20)
        wob_klb: weight on bit (klbs)

    Returns:
        Dict with critical_rpm_by_depth, risk_map, safe_rpm_windows.
    """
    if not survey_stations:
        return {"error": "No survey stations provided"}

    if rpm_range is None:
        rpm_range = list(range(40, 240, 20))

    bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)
    i_moment = math.pi * (bha_od_in ** 4 - bha_id_in ** 4) / 64.0
    w_buoyed = bha_weight_lbft * bf
    e = STEEL_E

    critical_by_depth = []
    risk_map = []

    for station in survey_stations:
        md = station.get("md_ft", 0)
        inc = station.get("inclination_deg", 0)

        # Paslay-Dawson with inclination correction
        # Weight component perpendicular to bore: w_lat = w * sin(inc)
        inc_rad = math.radians(inc)
        w_lateral = w_buoyed * max(math.sin(inc_rad), 0.05)  # min 0.05 to avoid singularity

        # DLS amplification -- look at curvature between consecutive stations
        dls = station.get("dls_deg_100ft", 0)
        dls_factor = 1.0 + 0.1 * min(dls, 10.0)  # Higher DLS -> lower effective critical RPM

        # Lateral critical RPM (Paslay-Dawson, gravity-loaded beam)
        denom = bha_length_ft * math.sqrt(w_lateral / (e * i_moment))
        rpm_crit_lateral = (4760.0 / denom / dls_factor) if denom > 0 else 999

        # Axial critical (same formula as base, independent of inc)
        rpm_crit_axial = calculate_critical_rpm_axial(
            bha_length_ft, bha_od_in, bha_id_in, bha_weight_lbft, mud_weight_ppg
        ).get("critical_rpm_1st", 999)

        critical_by_depth.append({
            "md_ft": md,
            "inclination_deg": inc,
            "critical_rpm_lateral": round(rpm_crit_lateral, 0),
            "critical_rpm_axial": round(rpm_crit_axial, 0),
            "dls_factor": round(dls_factor, 3),
        })

        # Risk row for this depth across all RPMs
        for rpm_val in rpm_range:
            # Distance from lateral critical
            ratio_lat = abs(rpm_val - rpm_crit_lateral) / rpm_crit_lateral if rpm_crit_lateral > 0 else 1
            ratio_ax = abs(rpm_val - rpm_crit_axial) / rpm_crit_axial if rpm_crit_axial > 0 else 1

            # Stick-slip tendency increases with inc and wob
            ss_tendency = (wob_klb / 30.0) * (1.0 + 0.5 * math.sin(inc_rad))
            ss_reduction = max(0, 1.0 - rpm_val / 150.0)
            ss_risk = ss_tendency * ss_reduction

            # Combined risk score 0-1 (0 = safe, 1 = dangerous)
            risk_lateral = max(0, 1.0 - ratio_lat / 0.2) if ratio_lat < 0.2 else 0
            risk_axial = max(0, 1.0 - ratio_ax / 0.15) if ratio_ax < 0.15 else 0
            risk_ss = min(1.0, ss_risk)
            combined_risk = min(1.0, 0.4 * risk_lateral + 0.25 * risk_axial + 0.35 * risk_ss)

            if combined_risk < 0.3:
                zone = "green"
            elif combined_risk < 0.6:
                zone = "yellow"
            else:
                zone = "red"

            risk_map.append({
                "md_ft": md,
                "rpm": rpm_val,
                "risk_score": round(combined_risk, 3),
                "zone": zone,
            })

    # Determine safe RPM windows per depth
    safe_windows = []
    for cd in critical_by_depth:
        md = cd["md_ft"]
        cr_lat = cd["critical_rpm_lateral"]
        cr_ax = cd["critical_rpm_axial"]
        # Safe: far from both criticals
        bands = []
        lower = min(cr_lat, cr_ax)
        if lower > 40:
            bands.append({"min_rpm": 40, "max_rpm": round(lower * 0.85)})
        upper_low = max(cr_lat, cr_ax)
        if upper_low * 1.15 < 220:
            bands.append({"min_rpm": round(upper_low * 1.15), "max_rpm": 220})
        safe_windows.append({"md_ft": md, "safe_bands": bands})

    return {
        "critical_rpm_by_depth": critical_by_depth,
        "risk_map": risk_map,
        "safe_rpm_windows": safe_windows,
        "rpm_range": rpm_range,
        "num_stations": len(survey_stations),
        "method": "Paslay-Dawson with 3D survey coupling",
    }
