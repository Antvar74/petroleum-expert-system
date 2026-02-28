"""
Standalone calculation routes for PETROEXPERT.

These routes run engineering calculations without well context (no DB lookup).
They duplicate the well-scoped routes but exist for the frontend quick-calculator feature.

# TODO: consider deduplication with well-scoped routes in routes/modules/
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any

from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine
from orchestrator.packer_forces_engine import PackerForcesEngine
from orchestrator.workover_hydraulics_engine import WorkoverHydraulicsEngine
from orchestrator.sand_control_engine import SandControlEngine
from orchestrator.completion_design_engine import CompletionDesignEngine
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine
from orchestrator.vibrations_engine import VibrationsEngine
from orchestrator.cementing_engine import CementingEngine
from orchestrator.casing_design_engine import CasingDesignEngine
from orchestrator.torque_drag_engine import TorqueDragEngine
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.well_control_engine import WellControlEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import StandaloneAnalysisRequest
from schemas.wellbore_cleanup import WellboreCleanupCalculateRequest
from schemas.packer_forces import PackerForcesCalculateRequest
from schemas.workover import WorkoverHydraulicsCalculateRequest
from schemas.sand_control import SandControlCalculateRequest
from schemas.completion import CompletionDesignCalculateRequest
from schemas.shot_efficiency import ShotEfficiencyCalculateRequest
from schemas.vibrations import VibrationsCalcRequest
from schemas.cementing import CementingCalculateRequest
from schemas.casing_design import CasingDesignCalculateRequest
from schemas.hydraulics import SurgeSwabRequest
from schemas.well_control import KillSheetPreRecordRequest

router = APIRouter(tags=["calculations"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/calculate/wellbore-cleanup")
def standalone_wellbore_cleanup(data: WellboreCleanupCalculateRequest):
    """Run wellbore cleanup calculation without well context."""
    result = WellboreCleanupEngine.calculate_full_cleanup(
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        hole_id=data.hole_id,
        pipe_od=data.pipe_od,
        inclination=data.inclination,
        rop=data.rop,
        cutting_size=data.cutting_size,
        cutting_density=data.cutting_density,
        rpm=data.rpm,
        annular_length=data.annular_length
    )
    return result


@router.post("/calculate/packer-forces")
def standalone_packer_forces(data: PackerForcesCalculateRequest):
    """Run packer forces calculation without well context."""
    result = PackerForcesEngine.calculate_total_packer_force(
        tubing_od=data.tubing_od,
        tubing_id=data.tubing_id,
        tubing_weight=data.tubing_weight,
        tubing_length=data.tubing_length,
        seal_bore_id=data.seal_bore_id,
        initial_tubing_pressure=data.initial_tubing_pressure,
        final_tubing_pressure=data.final_tubing_pressure,
        initial_annulus_pressure=data.initial_annulus_pressure,
        final_annulus_pressure=data.final_annulus_pressure,
        initial_temperature=data.initial_temperature,
        final_temperature=data.final_temperature,
        packer_depth_tvd=data.packer_depth_tvd,
        mud_weight_tubing=data.mud_weight_tubing,
        mud_weight_annulus=data.mud_weight_annulus,
        poisson_ratio=data.poisson_ratio,
        thermal_expansion=data.thermal_expansion
    )
    return result


@router.post("/calculate/workover-hydraulics")
def standalone_workover_hydraulics(data: WorkoverHydraulicsCalculateRequest):
    """Run workover/CT hydraulics calculation without well context."""
    result = WorkoverHydraulicsEngine.calculate_full_workover(
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        ct_od=data.ct_od,
        wall_thickness=data.wall_thickness,
        ct_length=data.ct_length,
        hole_id=data.hole_id,
        tvd=data.tvd,
        inclination=data.inclination,
        friction_factor=data.friction_factor,
        wellhead_pressure=data.wellhead_pressure,
        reservoir_pressure=data.reservoir_pressure,
        yield_strength_psi=data.yield_strength_psi
    )
    return result


@router.post("/calculate/sand-control")
def standalone_sand_control(data: SandControlCalculateRequest):
    """Run sand control / gravel pack calculation without well context."""
    result = SandControlEngine.calculate_full_sand_control(
        sieve_sizes_mm=data.sieve_sizes_mm,
        cumulative_passing_pct=data.cumulative_passing_pct,
        hole_id=data.hole_id,
        screen_od=data.screen_od,
        interval_length=data.interval_length,
        ucs_psi=data.ucs_psi,
        friction_angle_deg=data.friction_angle_deg,
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        overburden_stress_psi=data.overburden_stress_psi,
        formation_permeability_md=data.formation_permeability_md,
        wellbore_radius_ft=data.wellbore_radius_ft,
        wellbore_type=data.wellbore_type,
        gravel_permeability_md=data.gravel_permeability_md,
        pack_factor=data.pack_factor,
        washout_factor=data.washout_factor
    )
    return result


@router.post("/calculate/completion-design")
def standalone_completion_design(data: CompletionDesignCalculateRequest):
    """Run completion design / frac calculation without well context."""
    result = CompletionDesignEngine.calculate_full_completion_design(
        casing_id_in=data.casing_id_in,
        formation_permeability_md=data.formation_permeability_md,
        formation_thickness_ft=data.formation_thickness_ft,
        reservoir_pressure_psi=data.reservoir_pressure_psi,
        wellbore_pressure_psi=data.wellbore_pressure_psi,
        depth_tvd_ft=data.depth_tvd_ft,
        overburden_stress_psi=data.overburden_stress_psi,
        pore_pressure_psi=data.pore_pressure_psi,
        sigma_min_psi=data.sigma_min_psi,
        sigma_max_psi=data.sigma_max_psi,
        tensile_strength_psi=data.tensile_strength_psi,
        poisson_ratio=data.poisson_ratio,
        penetration_berea_in=data.penetration_berea_in,
        effective_stress_psi=data.effective_stress_psi,
        temperature_f=data.temperature_f,
        completion_fluid=data.completion_fluid,
        wellbore_radius_ft=data.wellbore_radius_ft,
        kv_kh_ratio=data.kv_kh_ratio,
        tubing_od_in=data.tubing_od_in,
        damage_radius_ft=data.damage_radius_ft,
        damage_permeability_md=data.damage_permeability_md,
        formation_type=data.formation_type
    )
    return result


@router.post("/calculate/shot-efficiency")
def standalone_shot_efficiency(data: ShotEfficiencyCalculateRequest):
    """Run shot efficiency / petrophysics calculation without well context."""
    result = ShotEfficiencyEngine.calculate_full_shot_efficiency(
        log_entries=data.log_entries,
        archie_params=data.archie_params,
        matrix_params=data.matrix_params,
        cutoffs=data.cutoffs,
        perf_params=data.perf_params,
        reservoir_params=data.reservoir_params,
        sw_model=data.sw_model,
        rsh=data.rsh,
        estimate_permeability=data.estimate_permeability,
        sw_irreducible=data.sw_irreducible
    )
    return result


@router.post("/calculate/vibrations")
def standalone_vibrations(data: VibrationsCalcRequest):
    """Run vibration analysis calculation without well context."""
    result = VibrationsEngine.calculate_full_vibration_analysis(
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        rop_fph=data.rop_fph,
        torque_ftlb=data.torque_ftlb,
        bit_diameter_in=data.bit_diameter_in,
        dp_od_in=data.dp_od_in,
        dp_id_in=data.dp_id_in,
        dp_weight_lbft=data.dp_weight_lbft,
        bha_length_ft=data.bha_length_ft,
        bha_od_in=data.bha_od_in,
        bha_id_in=data.bha_id_in,
        bha_weight_lbft=data.bha_weight_lbft,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        inclination_deg=data.inclination_deg,
        friction_factor=data.friction_factor,
        stabilizer_spacing_ft=data.stabilizer_spacing_ft,
        ucs_psi=data.ucs_psi,
        total_depth_ft=data.total_depth_ft,
        n_blades=data.n_blades,
        bha_components=data.bha_components,
    )
    return result


@router.post("/calculate/cementing")
def standalone_cementing(data: CementingCalculateRequest):
    """Run cementing simulation calculation without well context."""
    result = CementingEngine.calculate_full_cementing(
        casing_od_in=data.casing_od_in,
        casing_id_in=data.casing_id_in,
        hole_id_in=data.hole_id_in,
        casing_shoe_md_ft=data.casing_shoe_md_ft,
        casing_shoe_tvd_ft=data.casing_shoe_tvd_ft,
        toc_md_ft=data.toc_md_ft,
        toc_tvd_ft=data.toc_tvd_ft,
        float_collar_md_ft=data.float_collar_md_ft,
        mud_weight_ppg=data.mud_weight_ppg,
        spacer_density_ppg=data.spacer_density_ppg,
        lead_cement_density_ppg=data.lead_cement_density_ppg,
        tail_cement_density_ppg=data.tail_cement_density_ppg,
        tail_length_ft=data.tail_length_ft,
        spacer_volume_bbl=data.spacer_volume_bbl,
        excess_pct=data.excess_pct,
        rat_hole_ft=data.rat_hole_ft,
        pump_rate_bbl_min=data.pump_rate_bbl_min,
        pv_mud=data.pv_mud,
        yp_mud=data.yp_mud,
        fracture_gradient_ppg=data.fracture_gradient_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg
    )
    return result


@router.post("/calculate/casing-design")
def standalone_casing_design(data: CasingDesignCalculateRequest):
    """Run casing design calculation without well context."""
    result = CasingDesignEngine.calculate_full_casing_design(
        casing_od_in=data.casing_od_in,
        casing_id_in=data.casing_id_in,
        wall_thickness_in=data.wall_thickness_in,
        casing_weight_ppf=data.casing_weight_ppf,
        casing_length_ft=data.casing_length_ft,
        tvd_ft=data.tvd_ft,
        mud_weight_ppg=data.mud_weight_ppg,
        pore_pressure_ppg=data.pore_pressure_ppg,
        fracture_gradient_ppg=data.fracture_gradient_ppg,
        gas_gradient_psi_ft=data.gas_gradient_psi_ft,
        cement_top_tvd_ft=data.cement_top_tvd_ft,
        cement_density_ppg=data.cement_density_ppg,
        bending_dls=data.bending_dls,
        overpull_lbs=data.overpull_lbs,
        sf_burst=data.sf_burst,
        sf_collapse=data.sf_collapse,
        sf_tension=data.sf_tension,
        connection_type=data.connection_type,
        wear_pct=data.wear_pct,
        corrosion_rate_in_yr=data.corrosion_rate_in_yr,
        design_life_years=data.design_life_years,
        bottomhole_temp_f=data.bottomhole_temp_f,
        tubing_pressure_psi=data.tubing_pressure_psi,
        internal_fluid_density_ppg=data.internal_fluid_density_ppg,
        evacuation_level_ft=data.evacuation_level_ft,
        h2s_partial_pressure_psi=data.h2s_partial_pressure_psi,
        co2_partial_pressure_psi=data.co2_partial_pressure_psi,
    )
    return result


@router.post("/calculate/torque-drag")
def standalone_torque_drag(data: Dict[str, Any] = Body(...)):
    """Run torque & drag calculation without well context."""
    survey = data.get("survey", [])
    drillstring = data.get("drillstring", [])
    if len(survey) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 survey stations in body")
    if not drillstring:
        raise HTTPException(status_code=400, detail="No drillstring provided in body")

    result = TorqueDragEngine.compute_torque_drag(
        survey=survey,
        drillstring=drillstring,
        friction_cased=data.get("friction_cased", 0.25),
        friction_open=data.get("friction_open", 0.35),
        operation=data.get("operation", "trip_out"),
        mud_weight=data.get("mud_weight", 10.0),
        wob=data.get("wob", 0.0),
        rpm=data.get("rpm", 0.0),
        casing_shoe_md=data.get("casing_shoe_md", 0.0)
    )
    return result


@router.post("/calculate/torque-drag/compare")
def standalone_torque_drag_compare(data: Dict[str, Any] = Body(...)):
    """Run T&D for multiple operations without well context."""
    survey = data.get("survey", [])
    drillstring = data.get("drillstring", [])
    if len(survey) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 survey stations in body")
    if not drillstring:
        raise HTTPException(status_code=400, detail="No drillstring provided in body")

    operations = data.get("operations", ["trip_out", "trip_in", "rotating", "sliding"])
    friction_cased = data.get("friction_cased", 0.25)
    friction_open = data.get("friction_open", 0.35)
    mud_weight = data.get("mud_weight", 10.0)
    wob = data.get("wob", 0.0)
    rpm = data.get("rpm", 0.0)
    casing_shoe_md = data.get("casing_shoe_md", 0.0)

    results = {}
    summary_comparison = []

    for op in operations:
        try:
            result = TorqueDragEngine.compute_torque_drag(
                survey=survey, drillstring=drillstring,
                friction_cased=friction_cased, friction_open=friction_open,
                mud_weight=mud_weight, operation=op,
                wob=wob, rpm=rpm, casing_shoe_md=casing_shoe_md,
            )
            results[op] = result.get("station_results", [])
            summary_comparison.append({
                "operation": op,
                "hookload_klb": result.get("summary", {}).get("surface_hookload_klb", 0),
                "torque_ftlb": result.get("summary", {}).get("surface_torque_ftlb", 0),
            })
        except Exception:
            results[op] = []
            summary_comparison.append({"operation": op, "hookload_klb": 0, "torque_ftlb": 0})

    combined = []
    if results.get(operations[0]):
        for i, station in enumerate(results[operations[0]]):
            row = {"md": station.get("md", 0)}
            for op in operations:
                op_stations = results.get(op, [])
                if i < len(op_stations):
                    row[op] = op_stations[i].get("axial_force", 0)
            combined.append(row)

    return {
        "operations": results,
        "combined": combined,
        "summary_comparison": summary_comparison,
    }


@router.post("/calculate/torque-drag/back-calculate")
def standalone_back_calculate_friction(data: Dict[str, Any] = Body(...)):
    """Back-calculate friction factor without well context."""
    survey = data.get("survey", [])
    drillstring = data.get("drillstring", [])
    if len(survey) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 survey stations in body")
    if not drillstring:
        raise HTTPException(status_code=400, detail="No drillstring provided in body")

    result = TorqueDragEngine.back_calculate_friction(
        survey=survey,
        drillstring=drillstring,
        measured_hookload=data.get("measured_hookload", 0),
        operation=data.get("operation", "trip_out"),
        mud_weight=data.get("mud_weight", 10.0),
        wob=data.get("wob", 0.0),
        casing_shoe_md=data.get("casing_shoe_md", 0.0)
    )
    return result


@router.post("/calculate/hydraulics")
def standalone_hydraulics(data: Dict[str, Any] = Body(...)):
    """Run hydraulics calculation without well context."""
    sections = data.get("sections", [])
    nozzle_sizes = data.get("nozzle_sizes", [12, 12, 12])
    if not sections:
        raise HTTPException(status_code=400, detail="No hydraulic sections provided in body")

    result = HydraulicsEngine.calculate_full_circuit(
        sections=sections,
        nozzle_sizes=nozzle_sizes,
        flow_rate=data.get("flow_rate", 400),
        mud_weight=data.get("mud_weight", 10.0),
        pv=data.get("pv", 15),
        yp=data.get("yp", 10),
        tvd=data.get("tvd", 10000),
        rheology_model=data.get("rheology_model", "bingham_plastic"),
        n=data.get("n", 0.5),
        k=data.get("k", 300),
        surface_equipment_loss=data.get("surface_equipment_loss", 80.0)
    )
    return result


@router.post("/calculate/hydraulics/surge-swab")
def standalone_surge_swab(data: SurgeSwabRequest):
    """Run surge/swab calculation without well context."""
    result = HydraulicsEngine.calculate_surge_swab(
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        tvd=data.tvd,
        pipe_od=data.pipe_od,
        pipe_id=data.pipe_id,
        hole_id=data.hole_id,
        pipe_velocity_fpm=data.pipe_velocity_fpm,
        pipe_open=data.pipe_open
    )
    return result


@router.post("/calculate/kill-sheet/pre-record")
def standalone_kill_sheet_pre_record(data: KillSheetPreRecordRequest):
    """Run kill sheet pre-record calculation without well context."""
    result = WellControlEngine.pre_record_kill_sheet(
        well_name="Standalone",
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
    return result


@router.post("/calculate/kill-sheet/calculate")
def standalone_kill_sheet_calculate(data: Dict[str, Any] = Body(...)):
    """Run kill sheet kick calculation without well context."""
    result = WellControlEngine.calculate_kill_sheet(
        depth_md=data.get("depth_md", 0),
        depth_tvd=data.get("depth_tvd", 0),
        original_mud_weight=data.get("original_mud_weight", 10.0),
        casing_shoe_tvd=data.get("casing_shoe_tvd", 0),
        sidpp=data.get("sidpp", 0),
        sicp=data.get("sicp", 0),
        pit_gain=data.get("pit_gain", 0),
        scr_pressure=data.get("scr_pressure", 0),
        scr_rate=data.get("scr_rate", 0),
        dp_capacity=data.get("dp_capacity", 0),
        annular_capacity=data.get("annular_capacity", 0),
        strokes_surface_to_bit=data.get("strokes_surface_to_bit", 0),
        lot_emw=data.get("lot_emw", 14.0),
        casing_id=data.get("casing_id", 0.0),
        strokes_bit_to_surface=data.get("strokes_bit_to_surface", 0.0),
        total_strokes=data.get("total_strokes", 0.0)
    )
    return result


@router.post("/analyze/module")
async def standalone_analyze_module(data: StandaloneAnalysisRequest):
    """Generic standalone AI analysis — well_name is optional in body."""
    module = data.module
    well_name = data.well_name
    result_data = data.result_data
    params = data.params
    language = data.language
    provider = data.provider

    analyze_fn_map = {
        "torque-drag": module_analyzer.analyze_torque_drag,
        "hydraulics": module_analyzer.analyze_hydraulics,
        "stuck-pipe": module_analyzer.analyze_stuck_pipe,
        "well-control": module_analyzer.analyze_well_control,
        "wellbore-cleanup": module_analyzer.analyze_wellbore_cleanup,
        "packer-forces": module_analyzer.analyze_packer_forces,
        "workover-hydraulics": module_analyzer.analyze_workover_hydraulics,
        "sand-control": module_analyzer.analyze_sand_control,
        "completion-design": module_analyzer.analyze_completion_design,
        "shot-efficiency": module_analyzer.analyze_shot_efficiency,
        "vibrations": module_analyzer.analyze_vibrations,
        "cementing": module_analyzer.analyze_cementing,
        "casing-design": module_analyzer.analyze_casing_design,
    }

    fn = analyze_fn_map.get(module)
    if not fn:
        raise HTTPException(status_code=400, detail=f"Unknown module: {module}")

    return await fn(
        result_data=result_data,
        well_name=well_name,
        params=params,
        language=language,
        provider=provider
    )
