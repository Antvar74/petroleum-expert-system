from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import KillSheet
from orchestrator.well_control_engine import WellControlEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine
from orchestrator.transient_flow_engine import TransientFlowEngine

from schemas.common import AIAnalysisRequest
from schemas.well_control import (
    KillSheetPreRecordRequest, KillSheetCalculateRequest, VolumetricRequest,
    BullheadRequest, KickToleranceRequest, BariteRequirementsRequest,
    ZFactorRequest, KickMigrationRequest, KillSimulationRequest,
    KickMigrationMultiphaseRequest,
)

router = APIRouter(tags=["Well Control"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/kill-sheet/pre-record")
def pre_record_kill_sheet(well_id: int, data: KillSheetPreRecordRequest, db: Session = Depends(get_db)):
    """Pre-record static kill sheet data."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    result = WellControlEngine.pre_record_kill_sheet(
        well_name=well.name,
        depth_md=data.depth_md,
        depth_tvd=data.depth_tvd,
        original_mud_weight=data.original_mud_weight,
        casing_shoe_tvd=data.casing_shoe_tvd,
        casing_id=data.casing_id,
        dp_od=data.dp_od,
        dp_id=data.dp_id,
        dp_length=data.dp_length,
        dc_od=data.dc_od,
        dc_id=data.dc_id,
        dc_length=data.dc_length,
        scr_pressure=data.scr_pressure,
        scr_rate=data.scr_rate,
        lot_emw=data.lot_emw,
        pump_output=data.pump_output,
        hole_size=data.hole_size
    )

    # Save to DB
    ks = KillSheet(
        well_id=well_id,
        well_name=well.name,
        depth_md=data.depth_md,
        depth_tvd=data.depth_tvd,
        original_mud_weight=data.original_mud_weight,
        casing_shoe_tvd=data.casing_shoe_tvd,
        casing_id=data.casing_id,
        dp_capacity=result["capacities_bbl_ft"]["dp_capacity"],
        annular_capacity=result["capacities_bbl_ft"]["annular_oh_dp"],
        scr_pressure=data.scr_pressure,
        scr_rate=data.scr_rate,
        strokes_surface_to_bit=result["strokes"]["strokes_surface_to_bit"],
        strokes_bit_to_surface=result["strokes"]["strokes_bit_to_surface"],
        total_strokes=result["strokes"]["total_strokes"],
        lot_emw=data.lot_emw,
        calculations=result,
        status="pre-recorded"
    )
    db.add(ks)
    db.commit()

    return result


@router.get("/wells/{well_id}/kill-sheet")
def get_kill_sheet(well_id: int, db: Session = Depends(get_db)):
    """Get the latest kill sheet for a well."""
    ks = db.query(KillSheet).filter(KillSheet.well_id == well_id).order_by(KillSheet.id.desc()).first()
    if not ks:
        raise HTTPException(status_code=404, detail="No kill sheet found for this well")

    return {
        "id": ks.id, "well_id": ks.well_id, "well_name": ks.well_name,
        "depth_md": ks.depth_md, "depth_tvd": ks.depth_tvd,
        "original_mud_weight": ks.original_mud_weight,
        "casing_shoe_tvd": ks.casing_shoe_tvd,
        "dp_capacity": ks.dp_capacity, "annular_capacity": ks.annular_capacity,
        "scr_pressure": ks.scr_pressure, "scr_rate": ks.scr_rate,
        "strokes_surface_to_bit": ks.strokes_surface_to_bit,
        "lot_emw": ks.lot_emw,
        "sidpp": ks.sidpp, "sicp": ks.sicp, "pit_gain": ks.pit_gain,
        "calculations": ks.calculations,
        "pressure_schedule": ks.pressure_schedule,
        "kill_method": ks.kill_method,
        "status": ks.status
    }


@router.post("/wells/{well_id}/kill-sheet/calculate")
def calculate_kill_sheet(well_id: int, data: KillSheetCalculateRequest, db: Session = Depends(get_db)):
    """Calculate kill sheet with kick data."""
    # Get pre-recorded data
    ks = db.query(KillSheet).filter(KillSheet.well_id == well_id).order_by(KillSheet.id.desc()).first()
    if not ks:
        raise HTTPException(status_code=400, detail="No pre-recorded kill sheet. Pre-record first.")

    result = WellControlEngine.calculate_kill_sheet(
        depth_md=ks.depth_md,
        depth_tvd=ks.depth_tvd,
        original_mud_weight=ks.original_mud_weight,
        casing_shoe_tvd=ks.casing_shoe_tvd,
        sidpp=data.sidpp,
        sicp=data.sicp,
        pit_gain=data.pit_gain,
        scr_pressure=ks.scr_pressure or 0,
        scr_rate=ks.scr_rate or 0,
        dp_capacity=ks.dp_capacity or 0,
        annular_capacity=ks.annular_capacity or 0,
        strokes_surface_to_bit=ks.strokes_surface_to_bit or 0,
        lot_emw=ks.lot_emw or 14.0,
        casing_id=ks.casing_id or 0
    )

    # Update kill sheet with kick data
    ks.sidpp = data.sidpp
    ks.sicp = data.sicp
    ks.pit_gain = data.pit_gain
    ks.calculations = result
    ks.pressure_schedule = result.get("pressure_schedule")
    ks.kill_method = data.kill_method
    ks.status = "active"
    db.commit()

    # Add kill method details
    if data.kill_method == "drillers":
        method_detail = WellControlEngine.calculate_drillers_method(result, ks.scr_pressure or 0)
    else:
        method_detail = WellControlEngine.calculate_wait_and_weight(result)

    return {**result, "method_detail": method_detail}


@router.post("/kill-sheet/volumetric")
def calculate_volumetric(data: VolumetricRequest):
    """Volumetric method calculation (no circulation)."""
    return WellControlEngine.calculate_volumetric(
        mud_weight=data.mud_weight,
        sicp=data.sicp,
        tvd=data.tvd,
        annular_capacity=data.annular_capacity,
        lot_emw=data.lot_emw,
        casing_shoe_tvd=data.casing_shoe_tvd,
        safety_margin_psi=data.safety_margin_psi,
        pressure_increment_psi=data.pressure_increment_psi
    )


@router.post("/kill-sheet/bullhead")
def calculate_bullhead(data: BullheadRequest):
    """Bullhead calculation."""
    return WellControlEngine.calculate_bullhead(
        mud_weight=data.mud_weight,
        kill_mud_weight=data.kill_mud_weight,
        depth_tvd=data.depth_tvd,
        casing_shoe_tvd=data.casing_shoe_tvd,
        lot_emw=data.lot_emw,
        dp_capacity=data.dp_capacity,
        depth_md=data.depth_md,
        formation_pressure=data.formation_pressure
    )


@router.post("/well-control/kick-tolerance")
def calculate_kick_tolerance(data: KickToleranceRequest):
    """Calculate kick tolerance (max influx volume before shoe fracture)."""
    return WellControlEngine.calculate_kick_tolerance(
        mud_weight=data.mud_weight,
        shoe_tvd=data.shoe_tvd,
        lot_emw=data.lot_emw,
        well_depth_tvd=data.well_depth_tvd,
        gas_gravity=data.gas_gravity,
        bht=data.bht,
        annular_capacity=data.annular_capacity,
        influx_type=data.influx_type
    )


@router.post("/well-control/barite-requirements")
def calculate_barite_requirements(data: BariteRequirementsRequest):
    """Calculate barite weighting material requirements."""
    return WellControlEngine.calculate_barite_requirements(
        current_mud_weight=data.current_mud_weight,
        target_mud_weight=data.target_mud_weight,
        system_volume_bbl=data.system_volume_bbl,
        barite_sg=data.barite_sg,
        sack_weight_lbs=data.sack_weight_lbs
    )


@router.post("/well-control/z-factor")
def calculate_z_factor(data: ZFactorRequest):
    """Calculate real gas Z-factor (Dranchuk-Abou-Kassem)."""
    return WellControlEngine.calculate_z_factor(
        pressure=data.pressure,
        temperature=data.temperature,
        gas_gravity=data.gas_gravity
    )


@router.post("/wells/{well_id}/well-control/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_well_control(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Well Control results via drilling_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_well_control(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )


@router.post("/calculate/well-control/kick-migration")
def standalone_kick_migration(data: KickMigrationRequest):
    """Simulate gas kick migration in a shut-in well."""
    return TransientFlowEngine.simulate_kick_migration(
        well_depth_tvd=data.well_depth_tvd,
        mud_weight=data.mud_weight,
        kick_volume_bbl=data.kick_volume_bbl,
        kick_gradient=data.kick_gradient,
        sidpp=data.sidpp,
        sicp=data.sicp,
        annular_capacity_bbl_ft=data.annular_capacity_bbl_ft,
        time_steps_min=data.time_steps_min,
        gas_gravity=data.gas_gravity,
        migration_rate_ft_hr=data.migration_rate_ft_hr,
    )


@router.post("/calculate/well-control/kill-simulation")
def standalone_kill_simulation(data: KillSimulationRequest):
    """Simulate kill circulation step-by-step."""
    return TransientFlowEngine.simulate_kill_circulation(
        well_depth_tvd=data.well_depth_tvd,
        mud_weight=data.mud_weight,
        kill_mud_weight=data.kill_mud_weight,
        sidpp=data.sidpp,
        scr=data.scr,
        strokes_to_bit=data.strokes_to_bit,
        strokes_bit_to_surface=data.strokes_bit_to_surface,
        method=data.method,
        step_size=data.step_size,
    )


@router.post("/calculate/well-control/kick-migration-multiphase")
def standalone_kick_migration_multiphase(data: KickMigrationMultiphaseRequest):
    """Simulate gas kick migration using Zuber-Findlay drift-flux model."""
    return TransientFlowEngine.simulate_kick_migration_multiphase(
        well_depth_tvd=data.well_depth_tvd,
        mud_weight=data.mud_weight,
        kick_volume_bbl=data.kick_volume_bbl,
        sidpp=data.sidpp,
        sicp=data.sicp,
        annular_id_in=data.annular_id_in,
        pipe_od_in=data.pipe_od_in,
        gas_gravity=data.gas_gravity,
        time_steps_min=data.time_steps_min,
        n_cells=data.n_cells,
    )
