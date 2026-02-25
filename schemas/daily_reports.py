"""
Pydantic request schemas for Daily Reports routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateDailyReportRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/daily-reports``."""

    report_date: str = Field(..., description="Report date (YYYY-MM-DD)")
    report_type: str = Field(default="drilling", description="Report type: mobilization | drilling | completion | termination")
    depth_md_start: Optional[float] = Field(default=None, description="Start measured depth (ft)")
    depth_md_end: Optional[float] = Field(default=None, description="End measured depth (ft)")
    depth_tvd: Optional[float] = Field(default=None, description="True vertical depth (ft)")
    header_data: Optional[Dict[str, Any]] = Field(default=None, description="Header/well info data")
    operations_log: Optional[List[Dict[str, Any]]] = Field(default=None, description="Operations log entries")
    drilling_params: Optional[Dict[str, Any]] = Field(default=None, description="Drilling parameters")
    mud_properties: Optional[Dict[str, Any]] = Field(default=None, description="Mud properties")
    mud_inventory: Optional[Dict[str, Any]] = Field(default=None, description="Mud inventory data")
    bha_data: Optional[Dict[str, Any]] = Field(default=None, description="BHA data")
    gas_monitoring: Optional[Dict[str, Any]] = Field(default=None, description="Gas monitoring data")
    npt_events: Optional[List[Dict[str, Any]]] = Field(default=None, description="NPT events")
    hsse_data: Optional[Dict[str, Any]] = Field(default=None, description="HSSE data")
    cost_summary: Optional[Dict[str, Any]] = Field(default=None, description="Cost summary")
    completion_data: Optional[Dict[str, Any]] = Field(default=None, description="Completion data")
    termination_data: Optional[Dict[str, Any]] = Field(default=None, description="Termination data")
    status: str = Field(default="draft", description="Report status: draft | submitted | approved")
    created_by: Optional[str] = Field(default=None, description="Creator username")


class UpdateDailyReportRequest(BaseModel):
    """Body for ``PUT /wells/{well_id}/daily-reports/{report_id}``."""

    report_date: Optional[str] = Field(default=None, description="Report date (YYYY-MM-DD)")
    depth_md_start: Optional[float] = Field(default=None, description="Start measured depth (ft)")
    depth_md_end: Optional[float] = Field(default=None, description="End measured depth (ft)")
    depth_tvd: Optional[float] = Field(default=None, description="True vertical depth (ft)")
    header_data: Optional[Dict[str, Any]] = Field(default=None, description="Header/well info data")
    operations_log: Optional[List[Dict[str, Any]]] = Field(default=None, description="Operations log entries")
    drilling_params: Optional[Dict[str, Any]] = Field(default=None, description="Drilling parameters")
    mud_properties: Optional[Dict[str, Any]] = Field(default=None, description="Mud properties")
    mud_inventory: Optional[Dict[str, Any]] = Field(default=None, description="Mud inventory data")
    bha_data: Optional[Dict[str, Any]] = Field(default=None, description="BHA data")
    gas_monitoring: Optional[Dict[str, Any]] = Field(default=None, description="Gas monitoring data")
    npt_events: Optional[List[Dict[str, Any]]] = Field(default=None, description="NPT events")
    hsse_data: Optional[Dict[str, Any]] = Field(default=None, description="HSSE data")
    cost_summary: Optional[Dict[str, Any]] = Field(default=None, description="Cost summary")
    completion_data: Optional[Dict[str, Any]] = Field(default=None, description="Completion data")
    termination_data: Optional[Dict[str, Any]] = Field(default=None, description="Termination data")
    status: Optional[str] = Field(default=None, description="Report status")
    approved_by: Optional[str] = Field(default=None, description="Approver username")
