"""
Pipeline — orchestrates all wellbore cleanup sub-calculations.

References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Moore correlation for slip velocity
- Luo et al. (1992): Hole Cleaning Index (HCI)
- Larsen et al. (1997): SPE 36383 cuttings transport in deviated wells
"""
from typing import Dict, Any

from .constants import MIN_AV_VERTICAL, MIN_AV_HIGH_ANGLE
from .annular import calculate_annular_velocity, calculate_minimum_flow_rate
from .slip_velocity import calculate_slip_velocity, calculate_slip_velocity_larsen
from .transport import calculate_ctr, calculate_transport_velocity, calculate_cuttings_concentration
from .hci import calculate_hole_cleaning_index
from .sweep import design_sweep_pill
from .ecd import calculate_cuttings_ecd_contribution


def calculate_full_cleanup(
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    hole_id: float,
    pipe_od: float,
    inclination: float,
    rop: float = 60.0,
    cutting_size: float = 0.25,
    cutting_density: float = 21.0,
    rpm: float = 0.0,
    annular_length: float = 1000.0,
) -> Dict[str, Any]:
    """
    Complete wellbore cleanup analysis combining all calculations.

    Args:
        flow_rate: pump rate (gpm)
        mud_weight: mud density (ppg)
        pv: plastic viscosity (cP)
        yp: yield point (lb/100ft²)
        hole_id: hole diameter (inches)
        pipe_od: pipe OD (inches)
        inclination: wellbore inclination (degrees)
        rop: rate of penetration (ft/hr)
        cutting_size: mean cutting diameter (inches)
        cutting_density: cutting density (ppg)
        rpm: drillstring rotation (RPM)
        annular_length: length of annulus (ft)

    Returns:
        Dict with summary, ecd_contribution, sweep_pill, parameters, alerts.
    """
    # Core calculations
    va = calculate_annular_velocity(flow_rate, hole_id, pipe_od)

    # Auto-select slip velocity correlation: Larsen for inc >= 30°, Moore otherwise
    if inclination >= 30.0:
        vs_result = calculate_slip_velocity_larsen(
            mud_weight, pv, yp, cutting_size, cutting_density,
            inclination, rpm, hole_id, pipe_od, va
        )
        vs = vs_result["slip_velocity_ftmin"]
        slip_correlation = "larsen"
    else:
        vs = calculate_slip_velocity(mud_weight, pv, yp, cutting_size, cutting_density)
        vs_result = None
        slip_correlation = "moore"

    ctr = calculate_ctr(va, vs)
    vt = calculate_transport_velocity(va, vs)
    min_q = calculate_minimum_flow_rate(hole_id, pipe_od, inclination)
    hci = calculate_hole_cleaning_index(
        va, rpm, inclination, mud_weight, cutting_density, pv, yp
    )
    cc = calculate_cuttings_concentration(rop, hole_id, pipe_od, flow_rate, max(vt, 0.1))

    # Cuttings-ECD bridge: calculate ECD contribution from cuttings
    ecd_contrib = calculate_cuttings_ecd_contribution(cc, cutting_density, mud_weight)

    # Annular volume per foot
    ann_area_in2 = hole_id ** 2 - pipe_od ** 2
    annular_vol_per_ft = ann_area_in2 / 1029.4 if ann_area_in2 > 0 else 0.0

    # Sweep pill design
    sweep = design_sweep_pill(annular_vol_per_ft, annular_length, mud_weight)

    # Bottoms-up time (KB checklist §8 item 10)
    annular_volume_bbl = annular_vol_per_ft * annular_length
    bottoms_up_min = (annular_volume_bbl * 42.0 / flow_rate) if flow_rate > 0 else 0.0

    # Evaluate cleaning quality — Luo (1992) / KB §4
    if hci > 0.90:
        cleaning_quality = "Excellent"
    elif hci >= 0.70:
        cleaning_quality = "Good"
    elif hci >= 0.50:
        cleaning_quality = "Fair"
    else:
        cleaning_quality = "Poor"

    # Alerts
    alerts = []
    if va < MIN_AV_VERTICAL and inclination < 30:
        alerts.append(f"Annular velocity {va:.0f} ft/min below minimum {MIN_AV_VERTICAL:.0f} ft/min for vertical section")
    if va < MIN_AV_HIGH_ANGLE and inclination > 60:
        alerts.append(f"Annular velocity {va:.0f} ft/min below minimum {MIN_AV_HIGH_ANGLE:.0f} ft/min for high-angle section")
    if ctr < 0.55:
        alerts.append(f"CTR {ctr:.2f} below recommended 0.55 — risk of cuttings accumulation")
    if vt <= 0:
        alerts.append("Negative transport velocity — cuttings falling back!")
    if flow_rate < min_q:
        alerts.append(f"Flow rate {flow_rate:.0f} gpm below minimum {min_q:.0f} gpm")
    if hci < 0.50:
        alerts.append(f"HCI {hci:.2f} indicates poor hole cleaning — immediate action required")
    elif hci < 0.70:
        alerts.append(f"HCI {hci:.2f} indicates fair hole cleaning — increase AV or RPM")
    if cc > 5.0:
        alerts.append(f"High cuttings concentration {cc:.1f}% — consider increasing flow rate or sweeps")
    if inclination > 30 and rpm == 0:
        alerts.append("No pipe rotation in deviated section — rotation significantly improves cleaning")
    # Bed erosion alert (Larsen)
    if vs_result is not None and vs_result["bed_erosion_velocity_ftmin"] > 0:
        if va < vs_result["bed_erosion_velocity_ftmin"]:
            alerts.append(
                f"Annular velocity {va:.0f} ft/min below bed erosion velocity "
                f"{vs_result['bed_erosion_velocity_ftmin']:.0f} ft/min — cuttings bed will not be eroded"
            )

    summary = {
        "annular_velocity_ftmin": round(va, 1),
        "slip_velocity_ftmin": round(vs, 1),
        "transport_velocity_ftmin": round(vt, 1),
        "cuttings_transport_ratio": round(ctr, 3),
        "minimum_flow_rate_gpm": round(min_q, 0),
        "hole_cleaning_index": hci,
        "cuttings_concentration_pct": cc,
        "cleaning_quality": cleaning_quality,
        "flow_rate_adequate": flow_rate >= min_q,
        "slip_velocity_correlation": slip_correlation,
        "cuttings_ecd_ppg": ecd_contrib["cuttings_ecd_ppg"],
        "effective_mud_weight_ppg": ecd_contrib["effective_mud_weight_ppg"],
        "bottoms_up_min": round(bottoms_up_min, 1),
        "annular_volume_bbl": round(annular_volume_bbl, 1),
        "alerts": alerts,
    }

    return {
        "summary": summary,
        "ecd_contribution": ecd_contrib,
        "sweep_pill": sweep,
        "parameters": {
            "flow_rate_gpm": flow_rate,
            "mud_weight_ppg": mud_weight,
            "pv_cp": pv,
            "yp_lb100ft2": yp,
            "hole_id_in": hole_id,
            "pipe_od_in": pipe_od,
            "inclination_deg": inclination,
            "rop_fthr": rop,
            "cutting_size_in": cutting_size,
            "cutting_density_ppg": cutting_density,
            "rpm": rpm,
            "annular_length_ft": annular_length,
        },
        "alerts": alerts,
    }
