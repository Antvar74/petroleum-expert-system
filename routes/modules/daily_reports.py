"""
Daily Reports routes for PETROEXPERT.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from starlette.requests import Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from models import get_db, Well
from middleware.rate_limit import limiter, LLM_LIMIT
from models.models_v2 import DailyReport, ReportOperation
from orchestrator.ddr_engine import DDREngine
from orchestrator.module_analysis_engine import ModuleAnalysisEngine

from schemas.common import AIAnalysisRequest
from schemas.daily_reports import CreateDailyReportRequest, UpdateDailyReportRequest

router = APIRouter(tags=["daily-reports"])
ddr_engine = DDREngine()


@router.post("/wells/{well_id}/daily-reports")
def create_daily_report(well_id: int, data: CreateDailyReportRequest, db: Session = Depends(get_db)):
    """Create a new daily report (DDR, Completion, or Termination)."""
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")

    from datetime import date as date_type
    report_date_str = data.report_date
    if not report_date_str:
        raise HTTPException(status_code=400, detail="report_date is required")

    # Parse date
    if isinstance(report_date_str, str):
        try:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid report_date format. Use YYYY-MM-DD")
    else:
        report_date = report_date_str

    report_type = data.report_type
    if report_type not in ("mobilization", "drilling", "completion", "termination"):
        raise HTTPException(status_code=400, detail="report_type must be: mobilization, drilling, completion, or termination")

    # Auto-increment report number
    last_report = db.query(DailyReport).filter(
        DailyReport.well_id == well_id,
        DailyReport.report_type == report_type
    ).order_by(DailyReport.report_number.desc()).first()
    report_number = (last_report.report_number or 0) + 1 if last_report else 1

    # Validate the report data — build a plain dict for the engine
    data_dict = data.model_dump()
    validation = DDREngine.validate_report(data_dict, report_type)

    # Create report
    report = DailyReport(
        well_id=well_id,
        report_type=report_type,
        report_date=report_date,
        report_number=report_number,
        depth_md_start=data.depth_md_start,
        depth_md_end=data.depth_md_end,
        depth_tvd=data.depth_tvd,
        header_data=data.header_data,
        operations_log=data.operations_log,
        drilling_params=data.drilling_params,
        mud_properties=data.mud_properties,
        mud_inventory=data.mud_inventory,
        bha_data=data.bha_data,
        gas_monitoring=data.gas_monitoring,
        npt_events=data.npt_events,
        hsse_data=data.hsse_data,
        cost_summary=data.cost_summary,
        completion_data=data.completion_data,
        termination_data=data.termination_data,
        status=data.status,
        created_by=data.created_by,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Create normalized operations from operations_log
    ops_log = data.operations_log or []
    for op_data in ops_log:
        op = ReportOperation(
            report_id=report.id,
            from_time=op_data.get("from_time"),
            to_time=op_data.get("to_time"),
            hours=op_data.get("hours"),
            iadc_code=op_data.get("iadc_code"),
            category=op_data.get("category"),
            description=op_data.get("description"),
            depth_start=op_data.get("depth_start"),
            depth_end=op_data.get("depth_end"),
            is_npt=op_data.get("is_npt", False),
            npt_code=op_data.get("npt_code"),
        )
        db.add(op)
    db.commit()

    # Calculate daily summary
    summary = DDREngine.calculate_daily_summary(data_dict)

    return {
        "id": report.id,
        "report_number": report_number,
        "report_type": report_type,
        "report_date": str(report_date),
        "status": report.status,
        "summary": summary,
        "validation": validation,
    }


@router.get("/wells/{well_id}/daily-reports")
def list_daily_reports(
    well_id: int,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List daily reports for a well, optionally filtered by type and status."""
    query = db.query(DailyReport).filter(DailyReport.well_id == well_id)
    if report_type:
        query = query.filter(DailyReport.report_type == report_type)
    if status:
        query = query.filter(DailyReport.status == status)

    reports = query.order_by(DailyReport.report_date.desc()).all()
    result = []
    for r in reports:
        report_data = {
            "depth_md_start": r.depth_md_start,
            "depth_md_end": r.depth_md_end,
            "operations_log": r.operations_log or [],
            "drilling_params": r.drilling_params or {},
            "npt_events": r.npt_events or [],
            "cost_summary": r.cost_summary or {},
        }
        summary = DDREngine.calculate_daily_summary(report_data)
        result.append({
            "id": r.id,
            "report_type": r.report_type,
            "report_date": str(r.report_date),
            "report_number": r.report_number,
            "depth_md_start": r.depth_md_start,
            "depth_md_end": r.depth_md_end,
            "status": r.status,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "summary": {
                "footage_drilled": summary["footage_drilled"],
                "avg_rop": summary["avg_rop"],
                "npt_hours": summary["npt_hours"],
                "npt_percentage": summary["npt_percentage"],
            },
        })
    return result


@router.get("/wells/{well_id}/daily-reports/{report_id}")
def get_daily_report(well_id: int, report_id: int, db: Session = Depends(get_db)):
    """Get a specific daily report with all sections."""
    report = db.query(DailyReport).filter(
        DailyReport.id == report_id,
        DailyReport.well_id == well_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    operations = db.query(ReportOperation).filter(
        ReportOperation.report_id == report_id
    ).order_by(ReportOperation.from_time).all()

    report_data = {
        "depth_md_start": report.depth_md_start,
        "depth_md_end": report.depth_md_end,
        "operations_log": report.operations_log or [],
        "drilling_params": report.drilling_params or {},
        "npt_events": report.npt_events or [],
        "cost_summary": report.cost_summary or {},
    }
    summary = DDREngine.calculate_daily_summary(report_data)

    return {
        "id": report.id,
        "well_id": report.well_id,
        "report_type": report.report_type,
        "report_date": str(report.report_date),
        "report_number": report.report_number,
        "depth_md_start": report.depth_md_start,
        "depth_md_end": report.depth_md_end,
        "depth_tvd": report.depth_tvd,
        "header_data": report.header_data,
        "operations_log": report.operations_log,
        "drilling_params": report.drilling_params,
        "mud_properties": report.mud_properties,
        "mud_inventory": report.mud_inventory,
        "bha_data": report.bha_data,
        "gas_monitoring": report.gas_monitoring,
        "npt_events": report.npt_events,
        "hsse_data": report.hsse_data,
        "cost_summary": report.cost_summary,
        "completion_data": report.completion_data,
        "termination_data": report.termination_data,
        "ai_summary": report.ai_summary,
        "status": report.status,
        "created_by": report.created_by,
        "approved_by": report.approved_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        "summary": summary,
        "kpis": DDREngine.generate_daily_kpis(report_data),
        "operations": [
            {
                "id": op.id, "from_time": op.from_time, "to_time": op.to_time,
                "hours": op.hours, "iadc_code": op.iadc_code, "category": op.category,
                "description": op.description, "depth_start": op.depth_start,
                "depth_end": op.depth_end, "is_npt": op.is_npt, "npt_code": op.npt_code,
            }
            for op in operations
        ],
    }


@router.put("/wells/{well_id}/daily-reports/{report_id}")
def update_daily_report(well_id: int, report_id: int, data: UpdateDailyReportRequest, db: Session = Depends(get_db)):
    """Update an existing daily report."""
    report = db.query(DailyReport).filter(
        DailyReport.id == report_id,
        DailyReport.well_id == well_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert to dict to iterate updatable fields, excluding unset values
    data_dict = data.model_dump(exclude_unset=True)

    # Update fields if provided
    updatable_fields = [
        "depth_md_start", "depth_md_end", "depth_tvd",
        "header_data", "operations_log", "drilling_params", "mud_properties",
        "mud_inventory", "bha_data", "gas_monitoring", "npt_events",
        "hsse_data", "cost_summary", "completion_data", "termination_data",
        "status", "approved_by",
    ]
    for field in updatable_fields:
        if field in data_dict:
            setattr(report, field, data_dict[field])

    # Parse report_date if provided
    if "report_date" in data_dict and data_dict["report_date"] is not None:
        rd = data_dict["report_date"]
        if isinstance(rd, str):
            report.report_date = datetime.strptime(rd, "%Y-%m-%d").date()

    report.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Re-sync operations if operations_log was updated
    if "operations_log" in data_dict:
        db.query(ReportOperation).filter(ReportOperation.report_id == report_id).delete()
        for op_data in (data_dict["operations_log"] or []):
            op = ReportOperation(
                report_id=report.id,
                from_time=op_data.get("from_time"),
                to_time=op_data.get("to_time"),
                hours=op_data.get("hours"),
                iadc_code=op_data.get("iadc_code"),
                category=op_data.get("category"),
                description=op_data.get("description"),
                depth_start=op_data.get("depth_start"),
                depth_end=op_data.get("depth_end"),
                is_npt=op_data.get("is_npt", False),
                npt_code=op_data.get("npt_code"),
            )
            db.add(op)
        db.commit()

    return {"message": "Report updated", "id": report.id, "status": report.status}


@router.delete("/wells/{well_id}/daily-reports/{report_id}")
def delete_daily_report(well_id: int, report_id: int, db: Session = Depends(get_db)):
    """Delete a daily report and its operations."""
    report = db.query(DailyReport).filter(
        DailyReport.id == report_id,
        DailyReport.well_id == well_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)  # cascade deletes operations
    db.commit()
    return {"message": "Report deleted"}


# --- DDR Statistics & KPI Endpoints ---

@router.get("/wells/{well_id}/daily-reports/stats")
def get_daily_report_stats(
    well_id: int,
    report_type: Optional[str] = Query(default="drilling"),
    db: Session = Depends(get_db)
):
    """Get cumulative KPI statistics for a well's reports."""
    query = db.query(DailyReport).filter(DailyReport.well_id == well_id)
    if report_type:
        query = query.filter(DailyReport.report_type == report_type)
    reports = query.order_by(DailyReport.report_date).all()

    report_dicts = []
    for r in reports:
        report_dicts.append({
            "report_date": str(r.report_date),
            "depth_md_start": r.depth_md_start,
            "depth_md_end": r.depth_md_end,
            "operations_log": r.operations_log or [],
            "drilling_params": r.drilling_params or {},
            "npt_events": r.npt_events or [],
            "cost_summary": r.cost_summary or {},
            "header_data": r.header_data or {},
        })

    return DDREngine.calculate_cumulative_stats(report_dicts)


@router.get("/wells/{well_id}/daily-reports/time-depth")
def get_time_depth_curve(
    well_id: int,
    report_type: Optional[str] = Query(default="drilling"),
    db: Session = Depends(get_db)
):
    """Get Time vs Depth curve data for charts."""
    query = db.query(DailyReport).filter(DailyReport.well_id == well_id)
    if report_type:
        query = query.filter(DailyReport.report_type == report_type)
    reports = query.order_by(DailyReport.report_date).all()

    report_dicts = [{
        "report_date": str(r.report_date),
        "depth_md_start": r.depth_md_start,
        "depth_md_end": r.depth_md_end,
        "header_data": r.header_data or {},
    } for r in reports]

    return DDREngine.generate_time_depth_curve(report_dicts)


@router.get("/wells/{well_id}/daily-reports/npt-breakdown")
def get_npt_breakdown(
    well_id: int,
    report_type: Optional[str] = Query(default="drilling"),
    db: Session = Depends(get_db)
):
    """Get NPT breakdown by code and category."""
    query = db.query(DailyReport).filter(DailyReport.well_id == well_id)
    if report_type:
        query = query.filter(DailyReport.report_type == report_type)
    reports = query.order_by(DailyReport.report_date).all()

    report_dicts = [{
        "npt_events": r.npt_events or [],
        "operations_log": r.operations_log or [],
    } for r in reports]

    return DDREngine.calculate_npt_breakdown(report_dicts)


@router.get("/wells/{well_id}/daily-reports/cost-tracking")
def get_cost_tracking(
    well_id: int,
    report_type: Optional[str] = Query(default="drilling"),
    db: Session = Depends(get_db)
):
    """Get daily and cumulative cost tracking vs AFE."""
    query = db.query(DailyReport).filter(DailyReport.well_id == well_id)
    if report_type:
        query = query.filter(DailyReport.report_type == report_type)
    reports = query.order_by(DailyReport.report_date).all()

    report_dicts = [{
        "report_date": str(r.report_date),
        "cost_summary": r.cost_summary or {},
        "header_data": r.header_data or {},
    } for r in reports]

    return DDREngine.calculate_cost_tracking(report_dicts)


# --- DDR Reference Data ---

@router.get("/ddr/iadc-codes")
def get_iadc_codes():
    """Get IADC operation codes for dropdown menus."""
    return DDREngine.get_iadc_codes()


@router.get("/ddr/npt-codes")
def get_npt_codes():
    """Get NPT codes for dropdown menus."""
    return DDREngine.get_npt_codes()


@router.get("/ddr/operation-categories")
def get_operation_categories():
    """Get standard operation categories."""
    return DDREngine.get_operation_categories()


# --- DDR AI Analysis ---

@router.post("/wells/{well_id}/daily-reports/analyze")
@limiter.limit(LLM_LIMIT)
async def analyze_daily_report(
    request: Request,
    well_id: int,
    data: AIAnalysisRequest,
    language: str = Query(default="en"),
    provider: str = Query(default="auto"),
    db: Session = Depends(get_db)
):
    """Run AI analysis on daily report data."""
    well = db.query(Well).filter(Well.id == well_id).first()
    well_name = well.name if well else f"Well-{well_id}"

    engine = ModuleAnalysisEngine()

    result = await engine.analyze_daily_report(
        result_data=data.result_data,
        well_name=well_name,
        params=data.params,
        language=language,
        provider=provider,
    )
    return result
