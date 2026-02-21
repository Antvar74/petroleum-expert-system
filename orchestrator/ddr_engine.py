"""
DDR Engine — KPI calculations, validation, and summary generation
for Daily Drilling Reports, Completion Reports, and Termination Reports.
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta
import math


# IADC operation codes reference
IADC_CODES = {
    "DR": "Drilling",
    "DV": "Deviation / Directional Work",
    "TT": "Tripping",
    "TO": "Tripping Out",
    "TI": "Tripping In",
    "WC": "Well Control",
    "CS": "Casing / Liner",
    "CM": "Cementing",
    "LG": "Logging",
    "CT": "Coring",
    "ST": "DST / Testing",
    "CP": "Completion",
    "FL": "Fishing",
    "RR": "Rig Repair",
    "WW": "Waiting on Weather",
    "WO": "Waiting on Orders",
    "MV": "Rig Move",
    "OT": "Other",
    "CI": "Circulating",
    "RM": "Reaming",
    "WP": "Wiper Trip",
    "SV": "Survey",
    "BOP": "BOP Test",
    "MU": "Make-up / Break-out",
}

# NPT codes reference
NPT_CODES = {
    "NPT-ST": "Stuck Pipe",
    "NPT-KO": "Kick / Well Control Event",
    "NPT-LO": "Lost Circulation",
    "NPT-EQ": "Equipment Failure",
    "NPT-WW": "Waiting on Weather",
    "NPT-WO": "Waiting on Orders / Materials",
    "NPT-RR": "Rig Repair",
    "NPT-FL": "Fishing Operations",
    "NPT-FO": "Formation Issue",
    "NPT-HU": "Human Error",
    "NPT-SU": "Supply Chain Delay",
    "NPT-RD": "Rig Down / Move",
    "NPT-EN": "Environmental Shutdown",
    "NPT-OT": "Other NPT",
}

# NPT category groups
NPT_CATEGORIES = {
    "Mechanical": ["NPT-EQ", "NPT-RR"],
    "Wellbore": ["NPT-ST", "NPT-KO", "NPT-LO", "NPT-FO", "NPT-FL"],
    "Weather": ["NPT-WW", "NPT-EN"],
    "Logistics": ["NPT-WO", "NPT-SU", "NPT-RD"],
    "Human": ["NPT-HU"],
    "Other": ["NPT-OT"],
}


class DDREngine:
    """Engine for DDR KPI calculations, validation, and summary generation."""

    # -----------------------------------------------------------------
    # Daily Summary KPIs
    # -----------------------------------------------------------------
    @staticmethod
    def calculate_daily_summary(report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate daily KPIs from a single report.
        Returns: {footage_drilled, avg_rop, rotating_hours, npt_hours, connection_time,
                  productive_hours, npt_percentage, cost_per_foot, daily_kpis[]}
        """
        depth_start = report_data.get("depth_md_start", 0) or 0
        depth_end = report_data.get("depth_md_end", 0) or 0
        footage = max(0, depth_end - depth_start)

        # Parse operations log
        ops_log = report_data.get("operations_log") or []
        total_hours = 0
        drilling_hours = 0
        tripping_hours = 0
        connection_hours = 0
        npt_hours = 0
        circulating_hours = 0
        casing_hours = 0
        other_hours = 0

        for op in ops_log:
            hrs = op.get("hours", 0) or 0
            total_hours += hrs
            cat = (op.get("category") or "").lower()
            iadc = (op.get("iadc_code") or "").upper()
            is_npt = op.get("is_npt", False)

            if is_npt:
                npt_hours += hrs
            elif iadc in ("DR", "DV", "RM") or "drill" in cat:
                drilling_hours += hrs
            elif iadc in ("TT", "TO", "TI", "WP") or "trip" in cat:
                tripping_hours += hrs
            elif iadc == "MU" or "connect" in cat:
                connection_hours += hrs
            elif iadc == "CI" or "circulat" in cat:
                circulating_hours += hrs
            elif iadc in ("CS", "CM") or "cas" in cat or "cement" in cat:
                casing_hours += hrs
            else:
                other_hours += hrs

        productive_hours = total_hours - npt_hours
        avg_rop = footage / drilling_hours if drilling_hours > 0 else 0
        npt_pct = (npt_hours / total_hours * 100) if total_hours > 0 else 0

        # Cost per foot
        cost = report_data.get("cost_summary") or {}
        total_day_cost = cost.get("total_day", 0) or 0
        cost_per_foot = total_day_cost / footage if footage > 0 else 0

        # Drilling params summary
        params = report_data.get("drilling_params") or {}

        # NPT events breakdown
        npt_list = report_data.get("npt_events") or []
        npt_by_code = {}
        for evt in npt_list:
            code = evt.get("npt_code", "NPT-OT")
            npt_by_code[code] = npt_by_code.get(code, 0) + (evt.get("hours", 0) or 0)

        return {
            "footage_drilled": round(footage, 1),
            "depth_start": depth_start,
            "depth_end": depth_end,
            "avg_rop": round(avg_rop, 2),
            "total_hours": round(total_hours, 2),
            "drilling_hours": round(drilling_hours, 2),
            "tripping_hours": round(tripping_hours, 2),
            "connection_hours": round(connection_hours, 2),
            "circulating_hours": round(circulating_hours, 2),
            "casing_hours": round(casing_hours, 2),
            "npt_hours": round(npt_hours, 2),
            "other_hours": round(other_hours, 2),
            "productive_hours": round(productive_hours, 2),
            "npt_percentage": round(npt_pct, 1),
            "cost_per_foot": round(cost_per_foot, 2),
            "total_day_cost": total_day_cost,
            "npt_breakdown": npt_by_code,
            "drilling_params": {
                "wob": params.get("wob"),
                "rpm": params.get("rpm"),
                "flow_rate": params.get("flow_rate"),
                "spp": params.get("spp"),
                "torque": params.get("torque"),
                "rop": params.get("rop"),
                "ecd": params.get("ecd"),
            },
            "hours_breakdown": {
                "Drilling": round(drilling_hours, 2),
                "Tripping": round(tripping_hours, 2),
                "Connections": round(connection_hours, 2),
                "Circulating": round(circulating_hours, 2),
                "Casing/Cementing": round(casing_hours, 2),
                "NPT": round(npt_hours, 2),
                "Other": round(other_hours, 2),
            },
        }

    # -----------------------------------------------------------------
    # Cumulative Statistics (across multiple reports)
    # -----------------------------------------------------------------
    @staticmethod
    def calculate_cumulative_stats(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate cumulative statistics from all reports for a well.
        reports: list of report dicts with result data.
        """
        if not reports:
            return {
                "total_days": 0, "total_footage": 0, "current_depth": 0,
                "total_npt_hours": 0, "total_cost": 0, "avg_rop_overall": 0,
                "avg_npt_pct": 0, "avg_cost_per_foot": 0,
            }

        total_footage = 0
        total_drilling_hours = 0
        total_npt_hours = 0
        total_cost = 0
        max_depth = 0

        for r in reports:
            summary = r.get("_summary") or DDREngine.calculate_daily_summary(r)
            total_footage += summary.get("footage_drilled", 0)
            total_drilling_hours += summary.get("drilling_hours", 0)
            total_npt_hours += summary.get("npt_hours", 0)
            total_cost += summary.get("total_day_cost", 0)
            depth_end = r.get("depth_md_end", 0) or 0
            if depth_end > max_depth:
                max_depth = depth_end

        total_days = len(reports)
        avg_rop = total_footage / total_drilling_hours if total_drilling_hours > 0 else 0
        total_hours = total_days * 24
        avg_npt_pct = (total_npt_hours / total_hours * 100) if total_hours > 0 else 0
        avg_cpf = total_cost / total_footage if total_footage > 0 else 0

        return {
            "total_days": total_days,
            "total_footage": round(total_footage, 1),
            "current_depth": round(max_depth, 1),
            "total_drilling_hours": round(total_drilling_hours, 2),
            "total_npt_hours": round(total_npt_hours, 2),
            "total_cost": round(total_cost, 2),
            "avg_rop_overall": round(avg_rop, 2),
            "avg_npt_pct": round(avg_npt_pct, 1),
            "avg_cost_per_foot": round(avg_cpf, 2),
        }

    # -----------------------------------------------------------------
    # Time vs Depth Curve
    # -----------------------------------------------------------------
    @staticmethod
    def generate_time_depth_curve(reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate Time vs Depth data for chart.
        Returns: [{day, date, depth_start, depth_end, planned_depth (if available)}]
        """
        sorted_reports = sorted(reports, key=lambda r: r.get("report_date", ""))
        curve = []

        for i, r in enumerate(sorted_reports):
            header = r.get("header_data") or {}
            curve.append({
                "day": i + 1,
                "date": str(r.get("report_date", "")),
                "depth_start": r.get("depth_md_start", 0) or 0,
                "depth_end": r.get("depth_md_end", 0) or 0,
                "planned_depth": header.get("planned_depth"),
                "footage": max(0, (r.get("depth_md_end", 0) or 0) - (r.get("depth_md_start", 0) or 0)),
            })

        return curve

    # -----------------------------------------------------------------
    # NPT Breakdown Analysis
    # -----------------------------------------------------------------
    @staticmethod
    def calculate_npt_breakdown(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate NPT across all reports by code and category.
        """
        by_code: Dict[str, float] = {}
        by_category: Dict[str, float] = {}
        total_npt = 0

        for r in reports:
            npt_list = r.get("npt_events") or []
            ops_log = r.get("operations_log") or []

            # From explicit NPT events
            for evt in npt_list:
                code = evt.get("npt_code", "NPT-OT")
                hrs = evt.get("hours", 0) or 0
                by_code[code] = by_code.get(code, 0) + hrs
                total_npt += hrs

            # Also check operations marked as NPT
            for op in ops_log:
                if op.get("is_npt"):
                    code = op.get("npt_code", "NPT-OT")
                    hrs = op.get("hours", 0) or 0
                    # Avoid double counting if already in npt_events
                    if not npt_list:
                        by_code[code] = by_code.get(code, 0) + hrs
                        total_npt += hrs

        # Map codes to categories
        for cat, codes in NPT_CATEGORIES.items():
            cat_total = sum(by_code.get(c, 0) for c in codes)
            if cat_total > 0:
                by_category[cat] = round(cat_total, 2)

        return {
            "total_npt_hours": round(total_npt, 2),
            "by_code": {k: round(v, 2) for k, v in sorted(by_code.items(), key=lambda x: -x[1])},
            "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
            "code_labels": {k: NPT_CODES.get(k, k) for k in by_code.keys()},
        }

    # -----------------------------------------------------------------
    # Cost Tracking
    # -----------------------------------------------------------------
    @staticmethod
    def calculate_cost_tracking(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate daily and cumulative cost tracking vs AFE.
        """
        sorted_reports = sorted(reports, key=lambda r: r.get("report_date", ""))
        daily_costs = []
        cumulative = 0
        afe_budget = None

        for i, r in enumerate(sorted_reports):
            cost = r.get("cost_summary") or {}
            header = r.get("header_data") or {}
            day_cost = cost.get("total_day", 0) or 0
            cumulative += day_cost

            if afe_budget is None and header.get("afe_budget"):
                afe_budget = header["afe_budget"]

            daily_costs.append({
                "day": i + 1,
                "date": str(r.get("report_date", "")),
                "daily_cost": round(day_cost, 2),
                "cumulative_cost": round(cumulative, 2),
                "afe_budget": afe_budget,
                "afe_remaining": round(afe_budget - cumulative, 2) if afe_budget else None,
                "breakdown": {
                    "rig": cost.get("rig_cost", 0) or 0,
                    "services": cost.get("services", 0) or 0,
                    "consumables": cost.get("consumables", 0) or 0,
                    "mud_chemicals": cost.get("mud_chemicals", 0) or 0,
                    "logistics": cost.get("logistics", 0) or 0,
                    "other": cost.get("other", 0) or 0,
                },
            })

        return {
            "daily_costs": daily_costs,
            "total_cost": round(cumulative, 2),
            "afe_budget": afe_budget,
            "afe_remaining": round(afe_budget - cumulative, 2) if afe_budget else None,
            "over_budget": cumulative > afe_budget if afe_budget else False,
        }

    # -----------------------------------------------------------------
    # Report Validation
    # -----------------------------------------------------------------
    @staticmethod
    def validate_report(report_data: Dict[str, Any], report_type: str = "drilling") -> Dict[str, Any]:
        """
        Validate report fields. Returns {valid: bool, errors: [], warnings: []}.
        """
        errors = []
        warnings = []

        # Required fields
        if not report_data.get("report_date"):
            errors.append("Report date is required")
        if not report_data.get("report_type"):
            errors.append("Report type is required")

        # Depth validation
        depth_start = report_data.get("depth_md_start")
        depth_end = report_data.get("depth_md_end")
        if depth_start is not None and depth_end is not None:
            if depth_end < depth_start:
                warnings.append("End depth is less than start depth (may indicate backfill or sidetrack)")
            if depth_end > 40000:
                warnings.append("End depth exceeds 40,000 ft — verify value")

        # Operations log: check 24-hour consistency
        ops_log = report_data.get("operations_log") or []
        if ops_log:
            total_hours = sum(op.get("hours", 0) or 0 for op in ops_log)
            if abs(total_hours - 24.0) > 0.5:
                errors.append(f"Operations total {total_hours:.1f} hours — should sum to 24.0")

            # Check time continuity
            for i, op in enumerate(ops_log):
                ft = op.get("from_time", 0)
                tt = op.get("to_time", 0)
                if ft is not None and tt is not None and tt < ft:
                    warnings.append(f"Operation #{i+1}: end time ({tt}) < start time ({ft})")

        # Mud properties sanity checks
        mud = report_data.get("mud_properties") or {}
        density = mud.get("density")
        if density is not None:
            if density < 6.0 or density > 22.0:
                warnings.append(f"Mud density {density} ppg outside typical range (6-22 ppg)")

        # NPT validation
        npt_list = report_data.get("npt_events") or []
        for i, evt in enumerate(npt_list):
            if not evt.get("npt_code"):
                warnings.append(f"NPT event #{i+1} missing NPT code")

        # Completion-specific
        if report_type == "completion":
            comp = report_data.get("completion_data") or {}
            if not comp:
                warnings.append("Completion report has no completion_data section")

        # Termination-specific
        if report_type == "termination":
            term = report_data.get("termination_data") or {}
            if not term:
                warnings.append("Termination report has no termination_data section")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "field_count": DDREngine._count_populated_fields(report_data),
        }

    # -----------------------------------------------------------------
    # Generate KPI metrics list (for AI panel display)
    # -----------------------------------------------------------------
    @staticmethod
    def generate_daily_kpis(report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate key metrics in the format expected by AIAnalysisPanel.
        Returns: [{label, value, unit}]
        """
        summary = DDREngine.calculate_daily_summary(report_data)
        metrics = []

        metrics.append({"label": "Daily Footage", "value": str(summary["footage_drilled"]), "unit": "ft"})
        metrics.append({"label": "Average ROP", "value": str(summary["avg_rop"]), "unit": "ft/hr"})
        metrics.append({"label": "Drilling Hours", "value": str(summary["drilling_hours"]), "unit": "hrs"})
        metrics.append({"label": "NPT Hours", "value": str(summary["npt_hours"]), "unit": "hrs"})
        metrics.append({"label": "NPT %", "value": str(summary["npt_percentage"]), "unit": "%"})
        metrics.append({"label": "Connection Time", "value": str(summary["connection_hours"]), "unit": "hrs"})

        if summary["cost_per_foot"] > 0:
            metrics.append({"label": "Cost/ft", "value": f"${summary['cost_per_foot']:,.0f}", "unit": "USD/ft"})
        if summary["total_day_cost"] > 0:
            metrics.append({"label": "Daily Cost", "value": f"${summary['total_day_cost']:,.0f}", "unit": "USD"})

        return metrics

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    @staticmethod
    def _count_populated_fields(data: Dict[str, Any]) -> int:
        """Count non-null, non-empty fields in report data."""
        count = 0
        for key, val in data.items():
            if val is None:
                continue
            if isinstance(val, (dict, list)):
                if len(val) > 0:
                    count += 1
            elif isinstance(val, str):
                if val.strip():
                    count += 1
            else:
                count += 1
        return count

    @staticmethod
    def get_iadc_codes() -> Dict[str, str]:
        """Return IADC codes dictionary for frontend dropdowns."""
        return IADC_CODES

    @staticmethod
    def get_npt_codes() -> Dict[str, str]:
        """Return NPT codes dictionary for frontend dropdowns."""
        return NPT_CODES

    @staticmethod
    def get_operation_categories() -> List[str]:
        """Return standard operation categories."""
        return [
            "Drilling", "Tripping", "Connection", "Circulating",
            "Casing", "Cementing", "Logging", "Coring", "Testing",
            "Completion", "Fishing", "Rig Repair", "NPT",
            "Waiting", "Rig Move", "Survey", "BOP Test", "Other",
        ]
