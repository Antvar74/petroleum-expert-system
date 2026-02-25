import math
from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import HydraulicSection, BitNozzle, HydraulicResult
from orchestrator.hydraulics_engine import HydraulicsEngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.hydraulics import (
    BitNozzlesRequest, HydraulicsCalcRequest, SurgeSwabRequest,
    BHABreakdownRequest, PressureWaterfallRequest, HerschelBulkleyFitRequest,
)

router = APIRouter(tags=["Hydraulics"])

module_analyzer = ModuleAnalysisEngine()


@router.post("/wells/{well_id}/hydraulic-sections")
def upload_hydraulic_sections(well_id: int, sections: List[Dict[str, Any]] = Body(...), db: Session = Depends(get_db)):
    """Define hydraulic circuit sections."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    db.query(HydraulicSection).filter(HydraulicSection.well_id == well_id).delete()

    for sec in sections:
        db.add(HydraulicSection(
            well_id=well_id,
            section_type=sec["section_type"],
            length=sec["length"],
            od=sec["od"],
            id_inner=sec["id_inner"]
        ))

    db.commit()
    return {"well_id": well_id, "sections_count": len(sections)}


@router.post("/wells/{well_id}/bit-nozzles")
def upload_bit_nozzles(well_id: int, data: BitNozzlesRequest, db: Session = Depends(get_db)):
    """Define bit nozzle configuration."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    db.query(BitNozzle).filter(BitNozzle.well_id == well_id).delete()

    nozzle_sizes = data.nozzle_sizes
    tfa = sum(math.pi / 4.0 * (n / 32.0) ** 2 for n in nozzle_sizes)

    nozzle = BitNozzle(
        well_id=well_id,
        nozzle_count=len(nozzle_sizes),
        nozzle_sizes=nozzle_sizes,
        tfa=round(tfa, 4),
        bit_diameter=data.bit_diameter
    )
    db.add(nozzle)
    db.commit()

    return {"well_id": well_id, "nozzle_count": len(nozzle_sizes), "tfa": round(tfa, 4)}


@router.post("/wells/{well_id}/hydraulics/calculate")
def calculate_hydraulics(well_id: int, data: HydraulicsCalcRequest, db: Session = Depends(get_db)):
    """Full hydraulic circuit calculation."""
    # Get sections
    sec_rows = db.query(HydraulicSection).filter(HydraulicSection.well_id == well_id).all()
    if not sec_rows:
        raise HTTPException(status_code=400, detail="No hydraulic sections defined")

    sections = [{"section_type": s.section_type, "length": s.length, "od": s.od, "id_inner": s.id_inner}
                for s in sec_rows]

    # Get nozzles
    nozzle = db.query(BitNozzle).filter(BitNozzle.well_id == well_id).first()
    nozzle_sizes = nozzle.nozzle_sizes if nozzle else (data.nozzle_sizes or [12, 12, 12])

    result = HydraulicsEngine.calculate_full_circuit(
        sections=sections,
        nozzle_sizes=nozzle_sizes,
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        tvd=data.tvd,
        rheology_model=data.rheology_model,
        n=data.n,
        k=data.k,
        surface_equipment_loss=data.surface_equipment_loss
    )

    # Save result
    hyd_result = HydraulicResult(
        well_id=well_id,
        event_id=data.event_id,
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        rheology_model=data.rheology_model,
        result_data=result.get("section_results"),
        bit_hydraulics=result.get("bit_hydraulics"),
        summary=result.get("summary")
    )
    db.add(hyd_result)
    db.commit()

    return result


@router.post("/wells/{well_id}/hydraulics/surge-swab")
def calculate_surge_swab(well_id: int, data: SurgeSwabRequest, db: Session = Depends(get_db)):
    """Calculate surge and swab pressures."""
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


@router.post("/hydraulics/bha-breakdown")
def calculate_bha_breakdown(data: BHABreakdownRequest):
    """Calculate pressure loss breakdown for individual BHA tools."""
    return HydraulicsEngine.calculate_bha_pressure_breakdown(
        bha_tools=data.bha_tools,
        flow_rate=data.flow_rate,
        mud_weight=data.mud_weight,
        pv=data.pv,
        yp=data.yp,
        rheology_model=data.rheology_model,
        n=data.n,
        k=data.k,
        tau_0=data.tau_0,
        k_hb=data.k_hb,
        n_hb=data.n_hb
    )


@router.post("/hydraulics/pressure-waterfall")
def generate_pressure_waterfall(data: PressureWaterfallRequest):
    """Generate pressure waterfall from circuit results."""
    circuit_result = data.circuit_result
    bha_breakdown = data.bha_breakdown
    return HydraulicsEngine.generate_pressure_waterfall(circuit_result, bha_breakdown)


@router.post("/hydraulics/fit-herschel-bulkley")
def fit_herschel_bulkley(data: HerschelBulkleyFitRequest):
    """Fit Herschel-Bulkley model from FANN viscometer readings."""
    return HydraulicsEngine.fit_herschel_bulkley(
        fann_readings=data.fann_readings
    )


@router.post("/wells/{well_id}/hydraulics/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_hydraulics(request: Request, well_id: int, data: AIAnalysisRequest, db: Session = Depends(get_db)):
    """AI executive analysis of Hydraulics/ECD results via mud_engineer agent."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    language = data.language
    provider = data.provider
    return await module_analyzer.analyze_hydraulics(
        result_data=data.result_data,
        well_name=well.name,
        params=data.params,
        language=language,
        provider=provider
    )
