"""
Hydraulics Engine — Full Hydraulic Circuit Calculation.

Surface → Drill Pipe → BHA → Bit → Annular sections.

References:
- Bourgoyne et al., Applied Drilling Engineering (SPE Textbook)
- API RP 13D: Rheology and Hydraulics of Oil-Well Drilling Fluids
"""
from typing import Dict, Any, List, Optional

from .pt_corrections import correct_density_pt, correct_viscosity_pt
from .rheology import (
    pressure_loss_bingham,
    pressure_loss_power_law,
    pressure_loss_herschel_bulkley,
    fit_herschel_bulkley,
)
from .bit_hydraulics import calculate_bit_hydraulics
from .ecd import calculate_ecd_dynamic


def calculate_full_circuit(
    sections: List[Dict[str, Any]],
    nozzle_sizes: List[float],
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    tvd: float,
    rheology_model: str = "bingham_plastic",
    n: float = 0.5,
    k: float = 300.0,
    surface_equipment_loss: float = 80.0,
    tau_0: float = 0.0,
    k_hb: float = 0.0,
    n_hb: float = 0.5,
    fann_readings: Optional[Dict[str, float]] = None,
    use_pt_correction: bool = False,
    fluid_type: str = "wbm",
    t_surface: float = 80.0,
    geothermal_gradient: float = 0.012,
    annular_tvds: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Calculate full hydraulic circuit: Surface -> DP -> BHA -> Bit -> Annular

    Parameters:
    - sections: list of {section_type, length, od, id_inner}
      section_type: 'drill_pipe', 'hwdp', 'collar', 'annulus_dp', 'annulus_dc', 'annulus_hwdp'
    - rheology_model: 'bingham_plastic', 'power_law', or 'herschel_bulkley'
    - tau_0, k_hb, n_hb: Herschel-Bulkley parameters (used if rheology_model='herschel_bulkley')
    - fann_readings: optional FANN viscometer readings for auto-fit H-B parameters
    - use_pt_correction: if True, apply P/T density and viscosity corrections per section
    - fluid_type: 'wbm' or 'obm' (for P/T correction coefficients)
    - t_surface: surface temperature (°F, for geothermal gradient)
    - geothermal_gradient: °F per ft (typical 0.010-0.015)
    - annular_tvds: optional list of TVD (ft) for each annular section (for accurate ECD)
    """
    # Auto-fit Herschel-Bulkley if FANN readings provided
    if rheology_model == "herschel_bulkley" and fann_readings is not None:
        hb_fit = fit_herschel_bulkley(fann_readings)
        tau_0 = hb_fit["tau_0"]
        k_hb = hb_fit["k_hb"]
        n_hb = hb_fit["n_hb"]

    section_results = []
    total_pipe_loss = surface_equipment_loss
    total_annular_loss = 0.0

    # Cumulative depth tracker for P/T correction
    cum_depth = 0.0

    for sec in sections:
        is_annular = "annulus" in sec.get("section_type", "")

        # Estimate mid-section TVD for P/T correction
        sec_length = sec["length"]
        mid_depth = cum_depth + sec_length / 2.0
        cum_depth += sec_length

        # Apply P/T corrections if enabled
        mw_local = mud_weight
        pv_local = pv
        yp_local = yp
        if use_pt_correction:
            t_local = t_surface + geothermal_gradient * mid_depth
            p_local = 0.052 * mud_weight * mid_depth  # hydrostatic estimate
            rho_corr = correct_density_pt(
                mud_weight, p_local, t_local, fluid_type
            )
            mw_local = rho_corr["rho_corrected"]
            pv_corr = correct_viscosity_pt(pv, t_local)
            pv_local = pv_corr["pv_corrected"]
            # YP scales similarly to PV with temperature
            yp_corr_factor = pv_corr["correction_factor"]
            yp_local = yp * yp_corr_factor

        if rheology_model == "herschel_bulkley":
            result = pressure_loss_herschel_bulkley(
                flow_rate=flow_rate,
                mud_weight=mw_local,
                tau_0=tau_0, k_hb=k_hb, n_hb=n_hb,
                length=sec["length"],
                od=sec["od"],
                id_inner=sec["id_inner"],
                is_annular=is_annular
            )
        elif rheology_model == "power_law":
            result = pressure_loss_power_law(
                flow_rate=flow_rate,
                mud_weight=mw_local,
                n=n, k=k,
                length=sec["length"],
                od=sec["od"],
                id_inner=sec["id_inner"],
                is_annular=is_annular
            )
        else:
            result = pressure_loss_bingham(
                flow_rate=flow_rate,
                mud_weight=mw_local,
                pv=pv_local, yp=yp_local,
                length=sec["length"],
                od=sec["od"],
                id_inner=sec["id_inner"],
                is_annular=is_annular
            )

        result["section_type"] = sec["section_type"]
        result["length"] = sec["length"]
        section_results.append(result)

        if is_annular:
            total_annular_loss += result["pressure_loss_psi"]
        else:
            total_pipe_loss += result["pressure_loss_psi"]

    # Bit hydraulics
    total_system_loss = total_pipe_loss + total_annular_loss
    bit_result = calculate_bit_hydraulics(
        flow_rate=flow_rate,
        mud_weight=mud_weight,
        nozzle_sizes=nozzle_sizes,
        total_system_loss=total_system_loss
    )

    bit_loss = bit_result.get("pressure_drop_psi", 0)
    total_spp = total_pipe_loss + bit_loss + total_annular_loss

    # ECD
    ecd_result = calculate_ecd_dynamic(
        mud_weight=mud_weight,
        tvd=tvd,
        annular_pressure_loss=total_annular_loss
    )

    # Multi-diameter annular analysis
    annular_analysis_sections = []
    annular_idx = 0
    for sec in section_results:
        if "annulus" in sec.get("section_type", ""):
            sec_velocity = sec.get("velocity_ft_min", 0.0)

            # Get TVD for this annular section if provided
            if annular_tvds and annular_idx < len(annular_tvds):
                sec_tvd = annular_tvds[annular_idx]
            else:
                sec_tvd = tvd  # fallback to total TVD

            # Local ECD for this section
            if sec_tvd > 0:
                ecd_local = mud_weight + sec["pressure_loss_psi"] / (0.052 * sec_tvd)
            else:
                ecd_local = mud_weight

            annular_analysis_sections.append({
                "section_type": sec.get("section_type", ""),
                "velocity_ftmin": round(sec_velocity, 1),
                "ecd_local_ppg": round(ecd_local, 2),
                "pressure_loss_psi": round(sec["pressure_loss_psi"], 1),
                "tvd_ft": round(sec_tvd, 0)
            })
            annular_idx += 1

    # Identify critical annular section (lowest velocity or highest ECD)
    critical_section = None
    min_velocity = float("inf")
    if annular_analysis_sections:
        for asec in annular_analysis_sections:
            if 0 < asec["velocity_ftmin"] < min_velocity:
                min_velocity = asec["velocity_ftmin"]
                critical_section = asec["section_type"]

    annular_analysis = {
        "sections": annular_analysis_sections,
        "critical_section": critical_section,
        "min_velocity_ftmin": round(min_velocity, 1) if min_velocity < float("inf") else 0.0
    }

    # ECD profile at various depths (improved with TVDs when available)
    ecd_profile = []
    cum_annular = 0.0
    annular_secs_reversed = [s for s in reversed(section_results)
                              if "annulus" in s.get("section_type", "")]
    for i, sec in enumerate(annular_secs_reversed):
        cum_annular += sec["pressure_loss_psi"]

        # Use real TVD if available, else estimate from depth fraction
        if annular_tvds and i < len(annular_tvds):
            est_tvd = annular_tvds[len(annular_tvds) - 1 - i]
        else:
            depth_frac = cum_annular / total_annular_loss if total_annular_loss > 0 else 0
            est_tvd = tvd * (1 - depth_frac)

        if est_tvd > 0:
            ecd_at_depth = mud_weight + cum_annular / (0.052 * est_tvd)
            ecd_profile.append({
                "tvd": round(est_tvd, 0),
                "ecd": round(ecd_at_depth, 2)
            })

    summary = {
        "total_spp_psi": round(total_spp, 0),
        "surface_equipment_psi": round(surface_equipment_loss, 0),
        "pipe_loss_psi": round(total_pipe_loss - surface_equipment_loss, 0),
        "bit_loss_psi": round(bit_loss, 0),
        "annular_loss_psi": round(total_annular_loss, 0),
        "ecd_at_td": ecd_result["ecd_ppg"],
        "ecd_status": ecd_result["status"],
        "flow_rate": flow_rate,
        "mud_weight": mud_weight,
        "rheology_model": rheology_model
    }

    return {
        "section_results": section_results,
        "bit_hydraulics": bit_result,
        "ecd": ecd_result,
        "ecd_profile": ecd_profile,
        "annular_analysis": annular_analysis,
        "summary": summary
    }
