"""
CT Hydraulics — Bingham plastic pressure loss for pipe and annular flow.

References:
- Bourgoyne et al.: Applied Drilling Engineering (1986), §4.2
- ICoTA Coiled Tubing Manual
"""
from typing import Dict, Any


def calculate_ct_pressure_loss(
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    ct_od: float,
    ct_id: float,
    ct_length: float,
    hole_id: float,
    annular_length: float,
) -> Dict[str, Any]:
    """
    Calculate CT pressure losses through pipe and annulus using Bingham Plastic model.
    Adapts standard hydraulics for small CT diameters (1.5"–3.5").

    Args:
        flow_rate: pump rate (gpm) — typical CT: 0.5–4 bpm (21–168 gpm)
        mud_weight: fluid density (ppg)
        pv: plastic viscosity (cP)
        yp: yield point (lb/100ft²)
        ct_od: coiled tubing OD (inches)
        ct_id: coiled tubing ID (inches)
        ct_length: total CT length (ft)
        hole_id: wellbore/casing ID (inches)
        annular_length: annular length (ft)

    Returns:
        Dict with pipe_loss, annular_loss, total_loss, velocities, regime
    """
    if flow_rate <= 0 or ct_length <= 0:
        return {
            "pipe_loss_psi": 0.0,
            "annular_loss_psi": 0.0,
            "total_loss_psi": 0.0,
            "pipe_velocity_ftmin": 0.0,
            "annular_velocity_ftmin": 0.0,
            "pipe_regime": "none",
            "annular_regime": "none",
        }

    # --- Pipe flow (inside CT) ---
    d_eff_pipe = ct_id
    if d_eff_pipe <= 0:
        v_pipe = 0.0
        dp_pipe = 0.0
        re_pipe = 0.0
        regime_pipe = "none"
    else:
        v_pipe = 24.5 * flow_rate / (d_eff_pipe ** 2)
        re_pipe = 928.0 * mud_weight * v_pipe * d_eff_pipe / pv if pv > 0 else 99999
        he_pipe = 37100.0 * mud_weight * yp * d_eff_pipe ** 2 / (pv ** 2) if pv > 0 else 0
        re_crit_pipe = 2100.0 + 7.3 * (he_pipe ** 0.58) if he_pipe > 0 else 2100.0

        regime_pipe = "laminar" if re_pipe < re_crit_pipe else "turbulent"

        if regime_pipe == "laminar":
            dp_pipe = (pv * v_pipe * ct_length) / (1500.0 * d_eff_pipe ** 2) + \
                      (yp * ct_length) / (225.0 * d_eff_pipe)
        else:
            f = 0.0791 / (re_pipe ** 0.25) if re_pipe > 0 else 0.01
            v_pipe_fps = v_pipe / 60.0  # ft/min → ft/s
            # Bourgoyne et al. (1986) Bingham plastic turbulent correction: add YP yield term
            dp_pipe = (f * mud_weight * v_pipe_fps ** 2 * ct_length) / (25.8 * d_eff_pipe) + \
                      (yp * ct_length) / (225.0 * d_eff_pipe)

    # --- Annular flow (CT in wellbore) ---
    d_eff_ann = hole_id - ct_od
    if d_eff_ann <= 0 or annular_length <= 0:
        v_ann = 0.0
        dp_ann = 0.0
        re_ann = 0.0
        regime_ann = "none"
    else:
        v_ann = 24.5 * flow_rate / (hole_id ** 2 - ct_od ** 2)
        re_ann = 757.0 * mud_weight * v_ann * d_eff_ann / pv if pv > 0 else 99999
        he_ann = 37100.0 * mud_weight * yp * d_eff_ann ** 2 / (pv ** 2) if pv > 0 else 0
        re_crit_ann = 2100.0 + 7.3 * (he_ann ** 0.58) if he_ann > 0 else 2100.0

        regime_ann = "laminar" if re_ann < re_crit_ann else "turbulent"

        if regime_ann == "laminar":
            dp_ann = (pv * v_ann * annular_length) / (1000.0 * d_eff_ann ** 2) + \
                     (yp * annular_length) / (200.0 * d_eff_ann)
        else:
            f = 0.0791 / (re_ann ** 0.25) if re_ann > 0 else 0.01
            v_ann_fps = v_ann / 60.0  # ft/min → ft/s
            # Bourgoyne et al. (1986) Bingham plastic turbulent correction: add YP yield term
            dp_ann = (f * mud_weight * v_ann_fps ** 2 * annular_length) / (21.1 * d_eff_ann) + \
                     (yp * annular_length) / (200.0 * d_eff_ann)

    total_loss = dp_pipe + dp_ann

    return {
        "pipe_loss_psi": round(dp_pipe, 1),
        "annular_loss_psi": round(dp_ann, 1),
        "total_loss_psi": round(total_loss, 1),
        "pipe_velocity_ftmin": round(v_pipe, 1),
        "annular_velocity_ftmin": round(v_ann, 1),
        "pipe_reynolds": round(re_pipe, 0),
        "annular_reynolds": round(re_ann, 0),
        "pipe_regime": regime_pipe,
        "annular_regime": regime_ann,
    }
