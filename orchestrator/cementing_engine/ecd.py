"""
Cementing Engine — ECD during cementing job (multi-fluid column).

References:
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 3 (hydraulics basis)
- Nelson & Guillot: Well Cementing Ch. 12 (ECD during displacement)
"""
from typing import List, Dict, Any, Optional


def calculate_ecd_during_job(
    casing_shoe_tvd_ft: float,
    hole_id_in: float,
    casing_od_in: float,
    mud_weight_ppg: float,
    spacer_density_ppg: float,
    lead_cement_density_ppg: float,
    tail_cement_density_ppg: float,
    annular_sections: Optional[List[Dict[str, Any]]] = None,
    pump_rate_bbl_min: float = 5.0,
    pv_mud: float = 15.0,
    yp_mud: float = 10.0,
    fracture_gradient_ppg: float = 16.5,
    pore_pressure_ppg: float = 9.0,
    num_snapshots: int = 8,
) -> Dict[str, Any]:
    """
    Calculate ECD at shoe during cementing as different fluids
    pass through the annulus.

    The annular column is a stack of fluid segments, each with
    its own density. Hydrostatic = sum(rho_i * 0.052 * h_i).
    Friction losses are approximated using Bingham model.

    Parameters:
    - annular_sections: optional custom sections; if None uses uniform annulus
    - num_snapshots: number of time steps to capture ECD evolution
    """
    if casing_shoe_tvd_ft <= 0:
        return {"error": "Invalid TVD"}

    ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
    if ann_cap <= 0:
        return {"error": "Invalid annular geometry"}

    total_annular_bbl = casing_shoe_tvd_ft * ann_cap

    snapshots = []
    v_ann = 0.0  # annular velocity (ft/min) — set inside loop
    for i in range(num_snapshots + 1):
        fill_fraction = i / num_snapshots

        cement_height_ft = fill_fraction * casing_shoe_tvd_ft
        mud_height_ft = casing_shoe_tvd_ft - cement_height_ft

        # Weight the cement column with lead/tail split (80% lead, 20% tail)
        tail_frac = 0.2
        tail_h = min(cement_height_ft, casing_shoe_tvd_ft * tail_frac)
        lead_h = cement_height_ft - tail_h

        p_hydro = (
            mud_weight_ppg * 0.052 * mud_height_ft
            + lead_cement_density_ppg * 0.052 * lead_h
            + tail_cement_density_ppg * 0.052 * tail_h
        )

        # Friction loss (Bingham approximation for annular flow)
        d_eff = hole_id_in - casing_od_in
        if d_eff > 0 and pump_rate_bbl_min > 0:
            q_gpm = pump_rate_bbl_min * 42.0
            v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)
            dp_friction = (
                (pv_mud * v_ann * casing_shoe_tvd_ft) / (1000.0 * d_eff ** 2)
                + (yp_mud * casing_shoe_tvd_ft) / (200.0 * d_eff)
            )
        else:
            dp_friction = 0.0
            v_ann = 0.0

        ecd_psi = p_hydro + dp_friction
        ecd_ppg = ecd_psi / (0.052 * casing_shoe_tvd_ft) if casing_shoe_tvd_ft > 0 else 0

        pump_vol_bbl = fill_fraction * total_annular_bbl
        snapshots.append({
            "fill_pct": round(fill_fraction * 100, 1),
            "cement_height_ft": round(cement_height_ft, 0),
            "mud_height_ft": round(mud_height_ft, 0),
            "hydrostatic_psi": round(p_hydro, 0),
            "friction_psi": round(dp_friction, 0),
            "bhp_psi": round(ecd_psi, 0),
            "ecd_ppg": round(ecd_ppg, 2),
            "fracture_margin_ppg": round(fracture_gradient_ppg - ecd_ppg, 2),
            "pp_margin_ppg": round(ecd_ppg - pore_pressure_ppg, 2),
            "pump_volume_bbl": round(pump_vol_bbl, 1),
            "elapsed_min": round(pump_vol_bbl / pump_rate_bbl_min, 1) if pump_rate_bbl_min > 0 else 0.0,
        })

    max_ecd = max(s["ecd_ppg"] for s in snapshots)
    min_fg_margin = min(s["fracture_margin_ppg"] for s in snapshots)
    min_pp_margin = min(s["pp_margin_ppg"] for s in snapshots)

    if min_fg_margin < 0:
        status = "CRITICAL — ECD exceeds fracture gradient!"
    elif min_pp_margin < 0:
        status = "CRITICAL — ECD below pore pressure — influx risk!"
    elif min_fg_margin < 0.5:
        status = "WARNING — Tight margin to fracture gradient"
    elif min_fg_margin < 1.0:
        status = "CAUTION — Monitor closely"
    else:
        status = "OK — Within fracture window"

    alerts = []
    if min_fg_margin < 0:
        alerts.append(f"ECD exceeds fracture gradient by {abs(min_fg_margin):.2f} ppg — risk of losses!")
    if max_ecd > fracture_gradient_ppg:
        alerts.append("Reduce pump rate or use lighter lead cement")
    if min_pp_margin < 0:
        alerts.append(f"ECD drops below pore pressure by {abs(min_pp_margin):.2f} ppg — risk of influx!")

    return {
        "snapshots": snapshots,
        "max_ecd_ppg": round(max_ecd, 2),
        "min_fracture_margin_ppg": round(min_fg_margin, 2),
        "min_pp_margin_ppg": round(min_pp_margin, 2),
        "fracture_gradient_ppg": fracture_gradient_ppg,
        "pore_pressure_ppg": pore_pressure_ppg,
        "annular_velocity_ft_min": round(v_ann, 1),
        "status": status,
        "alerts": alerts,
    }
