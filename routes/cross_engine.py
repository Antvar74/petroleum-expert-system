"""
Cross-engine correlation routes for PETROEXPERT.

Bridges calculations between different engineering modules.

Provides:
  POST /cross-engine/cement-ecd-to-collapse   — Cementing ECD → Casing collapse
  POST /cross-engine/casing-id-to-completion  — Casing ID → Completion gun selection
  POST /cross-engine/ipr-skin-to-shot         — IPR + Skin → Shot Efficiency
  POST /cross-engine/vibrations-to-td         — Vibrations → T&D friction
  POST /cross-engine/packer-apb-to-casing     — Packer APB → Casing burst
  POST /cross-engine/td-to-packer-landing     — T&D → Packer landing conditions
"""
from fastapi import APIRouter, Body
from typing import Dict, Any

from orchestrator.cementing_engine import CementingEngine
from orchestrator.casing_design_engine import CasingDesignEngine
from orchestrator.completion_design_engine import CompletionDesignEngine
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine
from orchestrator.vibrations_engine import VibrationsEngine
from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.packer_forces_engine import PackerForcesEngine
from schemas.cross_engine import (
    CementECDToCollapseRequest, CasingIDToCompletionRequest, IPRSkinToShotRequest,
    VibrationsToTDRequest, PackerAPBToCasingRequest, TDToPackerLandingRequest,
)

router = APIRouter(tags=["cross-engine"])


@router.post("/cross-engine/cement-ecd-to-collapse")
def cross_cementing_ecd_to_casing_collapse(data: CementECDToCollapseRequest):
    """Bridge: Cementing ECD → Casing collapse scenario (external pressure from fresh cement)."""
    cem = CementingEngine.calculate_ecd_during_job(
        casing_shoe_tvd_ft=data.casing_shoe_tvd_ft,
        hole_id_in=data.hole_id_in,
        casing_od_in=data.casing_od_in,
        mud_weight_ppg=data.mud_weight_ppg,
        spacer_density_ppg=data.spacer_density_ppg,
        lead_cement_density_ppg=data.lead_cement_density_ppg,
        tail_cement_density_ppg=data.tail_cement_density_ppg,
        pump_rate_bbl_min=data.pump_rate_bbl_min,
        pv_mud=data.pv_mud, yp_mud=data.yp_mud,
    )
    ecd_ppg = cem.get("ecd_ppg", data.tail_cement_density_ppg)
    tvd = data.casing_shoe_tvd_ft
    external_p = ecd_ppg * 0.052 * tvd
    csg = CasingDesignEngine.calculate_collapse_rating(
        casing_od_in=data.casing_od_in,
        wall_thickness_in=data.wall_thickness_in,
        yield_strength_psi=data.yield_strength_psi,
    )
    collapse_rating = csg.get("collapse_rating_psi", 5000)
    sf = collapse_rating / external_p if external_p > 0 else 99
    return {
        "ecd_ppg": round(ecd_ppg, 2),
        "external_pressure_psi": round(external_p, 0),
        "collapse_rating_psi": collapse_rating,
        "collapse_sf_during_cementing": round(sf, 2),
        "cement_ecd_detail": cem,
        "casing_collapse_detail": csg,
    }


@router.post("/cross-engine/casing-id-to-completion")
def cross_casing_id_to_completion(data: CasingIDToCompletionRequest):
    """Bridge: Casing ID → Completion gun selection (diameter restriction)."""
    casing_id = data.casing_id_in
    max_pressure = data.max_pressure_psi
    max_temp = data.max_temperature_f
    gun_type = data.gun_type_filter
    guns = CompletionDesignEngine.select_gun_from_catalog(
        casing_id_in=casing_id,
        max_pressure_psi=max_pressure,
        max_temperature_f=max_temp,
        gun_type_filter=gun_type,
    )
    return {
        "casing_id_in": casing_id,
        "compatible_guns": guns,
        "num_compatible": len(guns.get("compatible_guns", [])) if "compatible_guns" in guns else 0,
    }


@router.post("/cross-engine/ipr-skin-to-shot")
def cross_ipr_skin_to_shot(data: IPRSkinToShotRequest):
    """Bridge: IPR + Skin → Shot Efficiency (kh from intervals as IPR input)."""
    kh = data.kh_md_ft
    h = data.net_pay_ft
    k = kh / h if h > 0 else 100
    ipr = CompletionDesignEngine.calculate_ipr_darcy(
        permeability_md=k, net_pay_ft=h,
        Bo=data.Bo, mu_oil_cp=data.mu_oil_cp,
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        drainage_radius_ft=data.drainage_radius_ft,
        wellbore_radius_ft=data.wellbore_radius_ft,
        skin=data.skin,
    )
    return {"kh_md_ft": kh, "permeability_md": round(k, 1), "net_pay_ft": h, "ipr": ipr}


@router.post("/cross-engine/vibrations-to-td")
def cross_vibrations_to_td(data: VibrationsToTDRequest):
    """Bridge: Vibrations drag → T&D (extra lateral contact from whirl)."""
    vib = VibrationsEngine.calculate_full_vibration_analysis(
        wob_klb=data.wob_klb, rpm=data.rpm,
        rop_fph=data.rop_fph, torque_ftlb=data.torque_ftlb,
        bit_diameter_in=data.bit_diameter_in,
        bha_od_in=data.bha_od_in, bha_id_in=data.bha_id_in,
        bha_weight_lbft=data.bha_weight_lbft, bha_length_ft=data.bha_length_ft,
        mud_weight_ppg=data.mud_weight_ppg, hole_diameter_in=data.hole_diameter_in,
    )
    ss_severity = vib.get("stick_slip", {}).get("severity_index", 0)
    stability = vib.get("stability", {}).get("stability_index", 50)
    friction_increase = 0.05 * (1.0 - stability / 100.0)
    base_friction = data.base_friction_factor
    effective_friction = base_friction + friction_increase
    return {
        "vibration_summary": vib.get("summary", {}),
        "stick_slip_severity": ss_severity,
        "stability_index": stability,
        "base_friction_factor": base_friction,
        "vibration_friction_increase": round(friction_increase, 4),
        "effective_friction_factor": round(effective_friction, 4),
        "recommendation": "Use effective_friction_factor in T&D calculations for more realistic drag estimates",
    }


@router.post("/cross-engine/packer-apb-to-casing")
def cross_packer_apb_to_casing(data: PackerAPBToCasingRequest):
    """Bridge: Packer APB → Casing burst (APB as additional load on casing)."""
    apb = PackerForcesEngine.calculate_apb(
        annular_fluid_type=data.annular_fluid_type,
        delta_t_avg=data.delta_t_avg,
        annular_volume_bbl=data.annular_volume_bbl,
        casing_od=data.casing_od,
        casing_id=data.casing_id,
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        annular_length_ft=data.annular_length_ft,
    )
    csg = CasingDesignEngine.calculate_burst_rating(
        casing_od_in=data.casing_od_in,
        wall_thickness_in=data.wall_thickness_in,
        yield_strength_psi=data.yield_strength_psi,
    )
    burst_rating = csg.get("burst_rating_psi", 6000)
    apb_psi = apb.get("apb_psi", 0)
    sf = burst_rating / apb_psi if apb_psi > 0 else 99
    return {
        "apb_psi": apb_psi,
        "casing_burst_rating_psi": burst_rating,
        "burst_sf_with_apb": round(sf, 2),
        "apb_detail": apb,
        "casing_burst_detail": csg,
    }


@router.post("/cross-engine/td-to-packer-landing")
def cross_td_to_packer_landing(data: TDToPackerLandingRequest):
    """Bridge: T&D drag → Packer landing conditions (drag for tubing run-in)."""
    tubing_sections = data.tubing_sections
    survey = data.survey_stations
    landing = PackerForcesEngine.calculate_landing_conditions(
        tubing_sections=tubing_sections,
        survey_stations=survey,
        mud_weight_ppg=data.mud_weight_ppg,
        friction_factor=data.friction_factor,
        packer_depth_tvd_ft=data.packer_depth_tvd_ft,
        set_down_weight_lbs=data.set_down_weight_lbs,
    )
    return landing
