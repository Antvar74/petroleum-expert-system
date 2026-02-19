"""
Cementing & Zonal Isolation Specialist Agent

Combines CementingEngine and CasingDesignEngine with LLM reasoning
for intelligent cement job planning, ECD management, and casing selection.

Capabilities:
- Full cement job simulation (volumes, displacement, ECD, BHP)
- Free-fall & U-tube equilibrium analysis
- ECD management vs fracture gradient
- Casing design with API 5C3 burst/collapse/tension
- Biaxial correction and triaxial VME verification
- Grade selection optimization
- Cement-casing integrated analysis
"""
import math
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent


class CementingEngineerAgent(BaseAgent):
    """
    Cementing & Zonal Isolation Specialist Agent

    Expert in:
    - Slurry Design & Chemistry (Nelson & Guillot)
    - Displacement Mechanics & ECD Management
    - Barrier Evaluation (CBL/VDL)
    - Casing Design (API TR 5C3 / ISO 10400)
    - Zonal Isolation Forensics
    - Free-Fall & U-Tube Equilibrium
    """

    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/cementing-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Cementing & Zonal Isolation Specialist."

        super().__init__(
            name="cementing_engineer",
            role="Cementing & Zonal Isolation Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/cementing/"
        )

    # ===================================================================
    # Lazy imports to avoid circular dependency (agents ↔ orchestrator)
    # ===================================================================

    @staticmethod
    def _get_cementing_engine():
        from orchestrator.cementing_engine import CementingEngine
        return CementingEngine

    @staticmethod
    def _get_casing_engine():
        from orchestrator.casing_design_engine import CasingDesignEngine
        return CasingDesignEngine

    # ===================================================================
    # Static computation methods — Cementing
    # ===================================================================

    @staticmethod
    def plan_cement_job(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_shoe_md_ft: float = 10000,
        casing_shoe_tvd_ft: float = 9500,
        toc_md_ft: float = 5000,
        toc_tvd_ft: float = 4750,
        float_collar_md_ft: float = 9900,
        mud_weight_ppg: float = 10.5,
        spacer_density_ppg: float = 11.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500,
        spacer_volume_bbl: float = 25,
        excess_pct: float = 50,
        rat_hole_ft: float = 50,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15,
        yp_mud: float = 10,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
    ) -> Dict[str, Any]:
        """
        Run full cement job simulation and return comprehensive analysis.

        Returns dict with: volumes, displacement, ecd_during_job, free_fall,
        utube, bhp_schedule, lift_pressure, summary, recommendations.
        """
        result = CementingEngineerAgent._get_cementing_engine().calculate_full_cementing(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            hole_id_in=hole_id_in, casing_shoe_md_ft=casing_shoe_md_ft,
            casing_shoe_tvd_ft=casing_shoe_tvd_ft, toc_md_ft=toc_md_ft,
            toc_tvd_ft=toc_tvd_ft, float_collar_md_ft=float_collar_md_ft,
            mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            tail_length_ft=tail_length_ft, spacer_volume_bbl=spacer_volume_bbl,
            excess_pct=excess_pct, rat_hole_ft=rat_hole_ft,
            pump_rate_bbl_min=pump_rate_bbl_min,
            pv_mud=pv_mud, yp_mud=yp_mud,
            fracture_gradient_ppg=fracture_gradient_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
        )

        # Build recommendations
        recs = CementingEngineerAgent._generate_cementing_recommendations(result)
        result["recommendations"] = recs
        return result

    @staticmethod
    def evaluate_ecd_risk(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_shoe_tvd_ft: float = 9500,
        toc_tvd_ft: float = 4750,
        mud_weight_ppg: float = 10.5,
        spacer_density_ppg: float = 11.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500,
        spacer_volume_bbl: float = 25,
        excess_pct: float = 50,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15,
        yp_mud: float = 10,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
    ) -> Dict[str, Any]:
        """
        Focused ECD risk analysis during cementing.

        Evaluates fracture margin at each job stage and returns
        critical stages, margin timeline, and mitigation strategies.
        """
        ecd_result = CementingEngineerAgent._get_cementing_engine().calculate_ecd_during_job(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            hole_id_in=hole_id_in, casing_od_in=casing_od_in,
            mud_weight_ppg=mud_weight_ppg,
            spacer_density_ppg=spacer_density_ppg,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            pump_rate_bbl_min=pump_rate_bbl_min,
            pv_mud=pv_mud, yp_mud=yp_mud,
            fracture_gradient_ppg=fracture_gradient_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
        )

        # Identify critical stages
        snapshots = ecd_result.get("snapshots", [])
        critical_stages = []
        min_margin = float("inf")
        for snap in snapshots:
            margin = fracture_gradient_ppg - snap.get("ecd_ppg", 0)
            if margin < min_margin:
                min_margin = margin
            if margin < 0.5:
                critical_stages.append({
                    "stage": snap.get("stage"),
                    "ecd_ppg": snap.get("ecd_ppg"),
                    "margin_ppg": round(margin, 2),
                    "cumulative_bbl": snap.get("cumulative_bbl"),
                })

        # Mitigation strategies
        mitigations = []
        if min_margin < 0:
            mitigations.append("CRITICAL: ECD exceeds fracture gradient. Reduce cement density or pump rate immediately.")
        if min_margin < 0.3:
            mitigations.append("Reduce pump rate during critical stage to lower friction ECD component.")
            mitigations.append("Consider lighter lead slurry (foam cement or microspheres).")
        if min_margin < 0.5:
            mitigations.append("Implement staged cementing to reduce hydrostatic column.")
            mitigations.append("Increase spacer volume to create buffer between heavy fluids.")
        if min_margin < 1.0:
            mitigations.append("Monitor annular pressure in real-time during job.")

        return {
            "ecd_analysis": ecd_result,
            "critical_stages": critical_stages,
            "minimum_margin_ppg": round(min_margin, 2),
            "fracture_gradient_ppg": fracture_gradient_ppg,
            "risk_level": "CRITICAL" if min_margin < 0 else "HIGH" if min_margin < 0.3 else "MEDIUM" if min_margin < 0.5 else "LOW",
            "mitigations": mitigations,
        }

    @staticmethod
    def analyze_free_fall_utube(
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_od_in: float = 9.625,
        casing_shoe_md_ft: float = 10000,
        casing_shoe_tvd_ft: float = 9500,
        float_collar_md_ft: float = 9900,
        mud_weight_ppg: float = 10.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500,
        toc_md_ft: float = 5000,
        toc_tvd_ft: float = 4750,
        spacer_volume_bbl: float = 25,
        excess_pct: float = 50,
        rat_hole_ft: float = 50,
    ) -> Dict[str, Any]:
        """
        Analyze free-fall and U-tube equilibrium.

        Returns height of free-fall, U-tube pressure imbalance,
        and operational recommendations.
        """
        ff = CementingEngineerAgent._get_cementing_engine().calculate_free_fall(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            mud_weight_ppg=mud_weight_ppg,
            cement_density_ppg=lead_cement_density_ppg,
            casing_id_in=casing_id_in,
            hole_id_in=hole_id_in,
            casing_od_in=casing_od_in,
        )

        # Volumes needed for U-tube
        volumes = CementingEngineerAgent._get_cementing_engine().calculate_fluid_volumes(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            hole_id_in=hole_id_in, casing_shoe_md_ft=casing_shoe_md_ft,
            toc_md_ft=toc_md_ft, float_collar_md_ft=float_collar_md_ft,
            tail_length_ft=tail_length_ft, spacer_volume_bbl=spacer_volume_bbl,
            excess_pct=excess_pct, rat_hole_ft=rat_hole_ft,
        )

        ut = CementingEngineerAgent._get_cementing_engine().calculate_utube_effect(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            mud_weight_ppg=mud_weight_ppg,
            cement_density_ppg=lead_cement_density_ppg,
            cement_top_tvd_ft=toc_tvd_ft,
            casing_id_in=casing_id_in,
            hole_id_in=hole_id_in,
            casing_od_in=casing_od_in,
        )

        lp = CementingEngineerAgent._get_cementing_engine().calculate_lift_pressure(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            toc_tvd_ft=toc_tvd_ft,
            cement_density_ppg=lead_cement_density_ppg,
            mud_weight_ppg=mud_weight_ppg,
            hole_id_in=hole_id_in,
            casing_od_in=casing_od_in,
            casing_id_in=casing_id_in,
        )

        # Operational recommendations
        recommendations = []
        if ff.get("free_fall_occurs"):
            ff_h = ff.get("free_fall_height_ft", 0)
            if ff_h > 500:
                recommendations.append(f"Significant free-fall ({ff_h} ft). Use stage-collar or top-plug system.")
            else:
                recommendations.append(f"Moderate free-fall ({ff_h} ft). Monitor returns during displacement.")
        if ut.get("utube_occurs"):
            recommendations.append("U-tube effect detected. Maintain back-pressure during WOC.")
            recommendations.append("Consider float equipment check valve integrity.")

        return {
            "free_fall": ff,
            "utube": ut,
            "lift_pressure": lp,
            "volumes": volumes,
            "recommendations": recommendations,
        }

    @staticmethod
    def optimize_pump_rate(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_shoe_tvd_ft: float = 9500,
        toc_tvd_ft: float = 4750,
        mud_weight_ppg: float = 10.5,
        spacer_density_ppg: float = 11.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500,
        spacer_volume_bbl: float = 25,
        excess_pct: float = 50,
        pv_mud: float = 15,
        yp_mud: float = 10,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
        rate_min: float = 2.0,
        rate_max: float = 10.0,
        rate_step: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Find optimal pump rate that maximizes displacement efficiency
        while staying within ECD / fracture gradient limits.

        Sweeps pump rates from rate_min to rate_max and evaluates
        ECD margin at each rate.

        Returns: list of rate/ecd/margin evaluations and optimal rate.
        """
        evaluations: List[Dict[str, Any]] = []
        best_rate = rate_min
        best_margin = -999.0

        rate = rate_min
        while rate <= rate_max + 0.01:
            ecd_result = CementingEngineerAgent._get_cementing_engine().calculate_ecd_during_job(
                casing_shoe_tvd_ft=casing_shoe_tvd_ft,
                hole_id_in=hole_id_in, casing_od_in=casing_od_in,
                mud_weight_ppg=mud_weight_ppg,
                spacer_density_ppg=spacer_density_ppg,
                lead_cement_density_ppg=lead_cement_density_ppg,
                tail_cement_density_ppg=tail_cement_density_ppg,
                pump_rate_bbl_min=rate,
                pv_mud=pv_mud, yp_mud=yp_mud,
                fracture_gradient_ppg=fracture_gradient_ppg,
                pore_pressure_ppg=pore_pressure_ppg,
            )
            max_ecd = ecd_result.get("max_ecd_ppg", 0)
            margin = round(fracture_gradient_ppg - max_ecd, 2)

            evaluations.append({
                "pump_rate_bbl_min": round(rate, 1),
                "max_ecd_ppg": max_ecd,
                "margin_ppg": margin,
                "within_limits": margin > 0,
            })

            # Best rate = highest rate that stays within limits
            if margin > 0 and rate > best_rate:
                best_rate = round(rate, 1)
                best_margin = margin
            elif margin > 0 and best_margin < 0:
                best_rate = round(rate, 1)
                best_margin = margin

            rate += rate_step

        return {
            "evaluations": evaluations,
            "optimal_pump_rate_bbl_min": best_rate,
            "optimal_margin_ppg": best_margin,
            "fracture_gradient_ppg": fracture_gradient_ppg,
            "recommendation": (
                f"Optimal pump rate: {best_rate} bbl/min with {best_margin} ppg margin to fracture."
                if best_margin > 0
                else "WARNING: No pump rate within range keeps ECD below fracture gradient."
            ),
        }

    # ===================================================================
    # Static computation methods — Casing Design
    # ===================================================================

    @staticmethod
    def design_casing(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        wall_thickness_in: float = 0.472,
        casing_weight_ppf: float = 47.0,
        casing_length_ft: float = 10000,
        tvd_ft: float = 9500,
        mud_weight_ppg: float = 10.5,
        pore_pressure_ppg: float = 9.0,
        fracture_gradient_ppg: float = 16.5,
        gas_gradient_psi_ft: float = 0.1,
        cement_top_tvd_ft: float = 5000,
        cement_density_ppg: float = 16.0,
        bending_dls: float = 3.0,
        overpull_lbs: float = 50000,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
    ) -> Dict[str, Any]:
        """
        Run full casing design analysis per API 5C3.

        Returns burst/collapse/tension loads, ratings, biaxial correction,
        triaxial VME, grade selection, safety factors, and recommendations.
        """
        result = CementingEngineerAgent._get_casing_engine().calculate_full_casing_design(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            wall_thickness_in=wall_thickness_in,
            casing_weight_ppf=casing_weight_ppf,
            casing_length_ft=casing_length_ft,
            tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
            fracture_gradient_ppg=fracture_gradient_ppg,
            gas_gradient_psi_ft=gas_gradient_psi_ft,
            cement_top_tvd_ft=cement_top_tvd_ft,
            cement_density_ppg=cement_density_ppg,
            bending_dls=bending_dls, overpull_lbs=overpull_lbs,
            sf_burst=sf_burst, sf_collapse=sf_collapse,
            sf_tension=sf_tension,
        )

        # Add recommendations
        recs = CementingEngineerAgent._generate_casing_recommendations(result)
        result["recommendations"] = recs
        return result

    @staticmethod
    def compare_casing_grades(
        casing_od_in: float = 9.625,
        wall_thickness_in: float = 0.472,
        casing_weight_ppf: float = 47.0,
        casing_length_ft: float = 10000,
        tvd_ft: float = 9500,
        mud_weight_ppg: float = 10.5,
        pore_pressure_ppg: float = 9.0,
        fracture_gradient_ppg: float = 16.5,
        gas_gradient_psi_ft: float = 0.1,
        bending_dls: float = 3.0,
        overpull_lbs: float = 50000,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
        grades_to_compare: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple casing grades for a given well scenario.

        Returns a table of safety factors per grade and overall ranking.
        """
        if grades_to_compare is None:
            grades_to_compare = ["L80", "N80", "C90", "T95", "P110"]

        casing_id_in = casing_od_in - 2 * wall_thickness_in

        # Get load profile (same for all grades)
        burst_load = CementingEngineerAgent._get_casing_engine().calculate_burst_load(
            tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
            gas_gradient_psi_ft=gas_gradient_psi_ft,
        )
        collapse_load = CementingEngineerAgent._get_casing_engine().calculate_collapse_load(
            tvd_ft=tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
        )
        tension_load = CementingEngineerAgent._get_casing_engine().calculate_tension_load(
            casing_weight_ppf=casing_weight_ppf,
            casing_length_ft=casing_length_ft,
            mud_weight_ppg=mud_weight_ppg,
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            bending_load_dls=bending_dls,
            overpull_lbs=overpull_lbs,
        )

        all_grades = CementingEngineerAgent._get_casing_engine().CASING_GRADES
        comparisons = []

        for grade_name in grades_to_compare:
            grade = all_grades.get(grade_name)
            if not grade:
                continue

            yield_psi = grade["yield_psi"]
            burst_rating = CementingEngineerAgent._get_casing_engine().calculate_burst_rating(
                casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
                yield_strength_psi=yield_psi,
            )
            collapse_rating = CementingEngineerAgent._get_casing_engine().calculate_collapse_rating(
                casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
                yield_strength_psi=yield_psi,
            )

            max_burst = burst_load.get("max_burst_psi", 0)
            max_collapse = collapse_load.get("max_collapse_psi", 0)
            total_tension = tension_load.get("total_tension_lbs", 0)
            tensile_strength = yield_psi * (math.pi / 4) * (casing_od_in**2 - casing_id_in**2)

            sf_b = round(burst_rating["burst_rating_psi"] / max(max_burst, 1), 2)
            sf_c = round(collapse_rating["collapse_rating_psi"] / max(max_collapse, 1), 2)
            sf_t = round(tensile_strength / max(total_tension, 1), 2)

            comparisons.append({
                "grade": grade_name,
                "yield_psi": yield_psi,
                "burst_rating_psi": burst_rating["burst_rating_psi"],
                "collapse_rating_psi": collapse_rating["collapse_rating_psi"],
                "collapse_zone": collapse_rating.get("collapse_zone", ""),
                "sf_burst": sf_b,
                "sf_collapse": sf_c,
                "sf_tension": sf_t,
                "burst_pass": sf_b >= sf_burst,
                "collapse_pass": sf_c >= sf_collapse,
                "tension_pass": sf_t >= sf_tension,
                "all_pass": sf_b >= sf_burst and sf_c >= sf_collapse and sf_t >= sf_tension,
                "color": grade.get("color", "#ffffff"),
            })

        # Rank: passing grades first, then by lowest yield (cost optimization)
        passing = [c for c in comparisons if c["all_pass"]]
        failing = [c for c in comparisons if not c["all_pass"]]
        passing.sort(key=lambda x: x["yield_psi"])
        failing.sort(key=lambda x: x["yield_psi"])

        recommended = passing[0]["grade"] if passing else None

        return {
            "comparisons": comparisons,
            "recommended_grade": recommended,
            "loads": {
                "max_burst_psi": burst_load.get("max_burst_psi"),
                "max_collapse_psi": collapse_load.get("max_collapse_psi"),
                "total_tension_lbs": tension_load.get("total_tension_lbs"),
            },
            "design_factors": {
                "sf_burst": sf_burst,
                "sf_collapse": sf_collapse,
                "sf_tension": sf_tension,
            },
        }

    @staticmethod
    def evaluate_biaxial_impact(
        casing_od_in: float = 9.625,
        wall_thickness_in: float = 0.472,
        casing_weight_ppf: float = 47.0,
        casing_length_ft: float = 10000,
        tvd_ft: float = 9500,
        mud_weight_ppg: float = 10.5,
        yield_strength_psi: float = 80000,
        bending_dls: float = 3.0,
        overpull_lbs: float = 50000,
    ) -> Dict[str, Any]:
        """
        Evaluate biaxial correction impact on collapse resistance.

        Shows how axial tension reduces collapse rating per API 5C3.
        Returns original vs corrected collapse and design implications.
        """
        casing_id_in = casing_od_in - 2 * wall_thickness_in

        tension = CementingEngineerAgent._get_casing_engine().calculate_tension_load(
            casing_weight_ppf=casing_weight_ppf,
            casing_length_ft=casing_length_ft,
            mud_weight_ppg=mud_weight_ppg,
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            bending_load_dls=bending_dls,
            overpull_lbs=overpull_lbs,
        )

        collapse_orig = CementingEngineerAgent._get_casing_engine().calculate_collapse_rating(
            casing_od_in=casing_od_in, wall_thickness_in=wall_thickness_in,
            yield_strength_psi=yield_strength_psi,
        )

        # Compute axial stress from tension load and cross-sectional area
        cross_area = (math.pi / 4) * (casing_od_in**2 - casing_id_in**2)
        axial_stress = tension["total_tension_lbs"] / cross_area if cross_area > 0 else 0

        biaxial = CementingEngineerAgent._get_casing_engine().calculate_biaxial_correction(
            collapse_rating_psi=collapse_orig["collapse_rating_psi"],
            axial_stress_psi=axial_stress,
            yield_strength_psi=yield_strength_psi,
        )

        reduction_pct = round(
            (1 - biaxial["reduction_factor"]) * 100, 1
        )

        return {
            "tension_load": tension,
            "original_collapse": collapse_orig,
            "biaxial_correction": biaxial,
            "reduction_percentage": reduction_pct,
            "recommendation": (
                f"Biaxial effect reduces collapse rating by {reduction_pct}%. "
                + ("This is significant — consider upgrading grade or weight."
                   if reduction_pct > 15
                   else "Within acceptable range for standard operations.")
            ),
        }

    # ===================================================================
    # Integrated Cement + Casing Analysis
    # ===================================================================

    @staticmethod
    def integrated_cement_casing_analysis(
        # Cementing params
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_shoe_md_ft: float = 10000,
        casing_shoe_tvd_ft: float = 9500,
        toc_md_ft: float = 5000,
        toc_tvd_ft: float = 4750,
        float_collar_md_ft: float = 9900,
        mud_weight_ppg: float = 10.5,
        spacer_density_ppg: float = 11.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500,
        spacer_volume_bbl: float = 25,
        excess_pct: float = 50,
        rat_hole_ft: float = 50,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15,
        yp_mud: float = 10,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
        # Casing params
        wall_thickness_in: float = 0.472,
        casing_weight_ppf: float = 47.0,
        gas_gradient_psi_ft: float = 0.1,
        bending_dls: float = 3.0,
        overpull_lbs: float = 50000,
        sf_burst: float = 1.10,
        sf_collapse: float = 1.00,
        sf_tension: float = 1.60,
    ) -> Dict[str, Any]:
        """
        Run full integrated cement + casing analysis.

        Checks that the casing can withstand cement job pressures
        (BHP during displacement) and that ECD stays within limits.
        """
        cement_result = CementingEngineerAgent._get_cementing_engine().calculate_full_cementing(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            hole_id_in=hole_id_in, casing_shoe_md_ft=casing_shoe_md_ft,
            casing_shoe_tvd_ft=casing_shoe_tvd_ft, toc_md_ft=toc_md_ft,
            toc_tvd_ft=toc_tvd_ft, float_collar_md_ft=float_collar_md_ft,
            mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            tail_length_ft=tail_length_ft, spacer_volume_bbl=spacer_volume_bbl,
            excess_pct=excess_pct, rat_hole_ft=rat_hole_ft,
            pump_rate_bbl_min=pump_rate_bbl_min,
            pv_mud=pv_mud, yp_mud=yp_mud,
            fracture_gradient_ppg=fracture_gradient_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
        )

        casing_result = CementingEngineerAgent._get_casing_engine().calculate_full_casing_design(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            wall_thickness_in=wall_thickness_in,
            casing_weight_ppf=casing_weight_ppf,
            casing_length_ft=casing_shoe_md_ft,
            tvd_ft=casing_shoe_tvd_ft, mud_weight_ppg=mud_weight_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
            fracture_gradient_ppg=fracture_gradient_ppg,
            gas_gradient_psi_ft=gas_gradient_psi_ft,
            cement_top_tvd_ft=toc_tvd_ft,
            cement_density_ppg=tail_cement_density_ppg,
            bending_dls=bending_dls, overpull_lbs=overpull_lbs,
            sf_burst=sf_burst, sf_collapse=sf_collapse,
            sf_tension=sf_tension,
        )

        # Cross-check: max BHP during cement job vs burst rating
        max_bhp = cement_result.get("summary", {}).get("max_bhp_psi", 0)
        burst_rating = casing_result.get("burst_rating", {}).get("burst_rating_psi", 99999)
        bhp_vs_burst_margin = round(burst_rating - max_bhp, 0) if max_bhp and burst_rating else None

        # Integration alerts
        integration_alerts = []
        if bhp_vs_burst_margin is not None and bhp_vs_burst_margin < 0:
            integration_alerts.append(
                f"CRITICAL: Max BHP during cement job ({max_bhp} psi) exceeds casing burst rating ({burst_rating} psi)!"
            )
        if bhp_vs_burst_margin is not None and bhp_vs_burst_margin < 1000:
            integration_alerts.append(
                f"WARNING: Tight margin between cement BHP ({max_bhp} psi) and burst rating ({burst_rating} psi). Margin: {bhp_vs_burst_margin} psi."
            )

        ecd_status = cement_result.get("summary", {}).get("ecd_status", "")
        if "CRITICAL" in str(ecd_status):
            integration_alerts.append("CRITICAL: ECD during cementing exceeds fracture gradient.")

        casing_status = casing_result.get("summary", {}).get("overall_status", "")
        if casing_status != "ALL PASS":
            integration_alerts.append(f"Casing design does not pass all criteria: {casing_status}")

        return {
            "cementing": cement_result,
            "casing_design": casing_result,
            "integration": {
                "max_bhp_during_cement_psi": max_bhp,
                "casing_burst_rating_psi": burst_rating,
                "bhp_vs_burst_margin_psi": bhp_vs_burst_margin,
                "alerts": integration_alerts,
                "overall_status": "PASS" if not integration_alerts else "REVIEW REQUIRED",
            },
        }

    # ===================================================================
    # LLM-assisted analysis methods
    # ===================================================================

    def analyze_cement_job(self, job_data: Dict) -> Dict:
        """
        Use LLM to analyze a completed or planned cement job.

        Args:
            job_data: Dictionary with cement job parameters and results

        Returns:
            Analysis dictionary for manual execution in Claude
        """
        problem = f"""
Analiza el siguiente trabajo de cementación:

VOLÚMENES:
- Cemento Lead: {job_data.get('volumes', {}).get('lead_cement_bbl', 'N/A')} bbl ({job_data.get('volumes', {}).get('lead_cement_sacks', 'N/A')} sacos)
- Cemento Tail: {job_data.get('volumes', {}).get('tail_cement_bbl', 'N/A')} bbl ({job_data.get('volumes', {}).get('tail_cement_sacks', 'N/A')} sacos)
- Spacer: {job_data.get('volumes', {}).get('spacer_volume_bbl', 'N/A')} bbl
- Desplazamiento: {job_data.get('volumes', {}).get('displacement_volume_bbl', 'N/A')} bbl

ECD:
- Max ECD: {job_data.get('summary', {}).get('max_ecd_ppg', 'N/A')} ppg
- Gradiente Fractura: {job_data.get('ecd_during_job', {}).get('fracture_gradient_ppg', 'N/A')} ppg
- Margen: {job_data.get('summary', {}).get('fracture_margin_ppg', 'N/A')} ppg
- Status: {job_data.get('summary', {}).get('ecd_status', 'N/A')}

FREE-FALL & U-TUBE:
- Free-Fall: {job_data.get('free_fall', {}).get('free_fall_height_ft', 'N/A')} ft
- U-Tube: {job_data.get('utube', {}).get('pressure_imbalance_psi', 'N/A')} psi

BHP:
- Max BHP: {job_data.get('summary', {}).get('max_bhp_psi', 'N/A')} psi

Evalúa:
1. ¿Los volúmenes son adecuados para el intervalo?
2. ¿El ECD es manejable respecto al gradiente de fractura?
3. ¿El free-fall y U-tube representan riesgo operacional?
4. ¿Qué recomendaciones darías para optimizar el trabajo?
5. ¿Qué contingencias debe tener el operador?
"""
        context = {"job_data": job_data}
        return self.analyze_interactive(problem, context)

    def analyze_casing_selection(self, design_data: Dict) -> Dict:
        """
        Use LLM to analyze casing grade selection and design.
        """
        problem = f"""
Analiza el diseño de casing según API 5C3:

GRADO SELECCIONADO: {design_data.get('summary', {}).get('selected_grade', 'N/A')}

FACTORES DE SEGURIDAD:
- SF Burst: {design_data.get('summary', {}).get('sf_burst', 'N/A')}
- SF Collapse: {design_data.get('summary', {}).get('sf_collapse', 'N/A')}
- SF Tension: {design_data.get('summary', {}).get('sf_tension', 'N/A')}

CARGAS DE DISEÑO:
- Max Burst: {design_data.get('summary', {}).get('max_burst_load_psi', 'N/A')} psi
- Max Collapse: {design_data.get('summary', {}).get('max_collapse_load_psi', 'N/A')} psi
- Tensión Total: {design_data.get('summary', {}).get('total_tension_lbs', 'N/A')} lbs

TRIAXIAL VME:
- Status: {design_data.get('summary', {}).get('triaxial_status', 'N/A')}
- Zona Collapse: {design_data.get('summary', {}).get('collapse_zone', 'N/A')}

Evalúa:
1. ¿El grado seleccionado es óptimo (no sobre-diseñado ni sub-diseñado)?
2. ¿Los factores de seguridad son adecuados para las condiciones?
3. ¿La corrección biaxial tiene impacto significativo?
4. ¿El triaxial VME pasa con margen suficiente?
5. ¿Qué grado alternativo podrías considerar y por qué?
"""
        context = {"design_data": design_data}
        return self.analyze_interactive(problem, context)

    def troubleshoot_cement_failure(self, failure_data: Dict) -> Dict:
        """
        Use LLM to diagnose cement failure root causes.
        """
        problem = f"""
Diagnóstico de falla de cementación:

EVIDENCIA:
- CBL Bond Quality: {failure_data.get('cbl_quality', 'N/A')}
- VDL Interpretation: {failure_data.get('vdl_interpretation', 'N/A')}
- Gas Migration: {failure_data.get('gas_migration', 'N/A')}
- Sustained Casing Pressure: {failure_data.get('scp_psi', 'N/A')} psi
- Interval: {failure_data.get('interval_ft', 'N/A')} ft

CONDICIONES DEL TRABAJO ORIGINAL:
- Densidad lechada: {failure_data.get('slurry_density_ppg', 'N/A')} ppg
- Exceso: {failure_data.get('excess_pct', 'N/A')}%
- Pump rate: {failure_data.get('pump_rate', 'N/A')} bbl/min
- WOC time: {failure_data.get('woc_hours', 'N/A')} hrs

Analiza:
1. ¿Cuál es la causa raíz más probable de la falla?
2. ¿Fue un problema de diseño, ejecución, o ambos?
3. ¿Qué evidencia soporta tu diagnóstico?
4. ¿Qué opciones de remediación recomiendas?
5. ¿Cómo prevenir esta falla en futuros pozos?
"""
        context = {"failure_data": failure_data}
        return self.analyze_interactive(problem, context)

    # ===================================================================
    # Internal recommendation generators
    # ===================================================================

    @staticmethod
    def _generate_cementing_recommendations(result: Dict) -> List[str]:
        """Generate operational recommendations from cementing results."""
        recs = []
        summary = result.get("summary", {})

        # ECD management
        margin = summary.get("fracture_margin_ppg", 999)
        if margin < 0:
            recs.append("CRITICAL: ECD exceeds fracture gradient. Reduce pump rate or cement density.")
        elif margin < 0.3:
            recs.append("Tight ECD margin — consider reducing pump rate during cement displacement.")
        elif margin < 0.5:
            recs.append("Monitor ECD closely during tail cement placement.")

        # Free-fall
        ff = result.get("free_fall", {})
        if ff.get("free_fall_occurs"):
            h = ff.get("free_fall_height_ft", 0)
            if h > 1000:
                recs.append(f"Significant free-fall ({h} ft). Use staged cementing or low-density lead.")
            elif h > 300:
                recs.append(f"Moderate free-fall ({h} ft). Monitor returns and pressures carefully.")

        # U-tube
        ut = result.get("utube", {})
        if ut.get("utube_occurs"):
            recs.append("U-tube effect detected. Hold back-pressure after displacement.")

        # Volume check
        volumes = result.get("volumes", {})
        total = volumes.get("total_cement_bbl", 0)
        if total > 600:
            recs.append("Large cement volume — verify mixing capacity and bulk storage.")

        # Job time
        job_time = summary.get("job_time_hrs", 0)
        if job_time > 4:
            recs.append("Extended job time — verify slurry thickening time exceeds job duration + safety.")

        if not recs:
            recs.append("All parameters within normal operating range. Standard execution recommended.")

        return recs

    @staticmethod
    def _generate_casing_recommendations(result: Dict) -> List[str]:
        """Generate design recommendations from casing analysis results."""
        recs = []
        summary = result.get("summary", {})

        sf_burst = summary.get("sf_burst", 0)
        sf_collapse = summary.get("sf_collapse", 0)
        sf_tension = summary.get("sf_tension", 0)

        if summary.get("overall_status") != "ALL PASS":
            recs.append("FAIL: One or more design criteria not met. Upgrade grade or wall thickness.")

        if sf_burst > 3.0:
            recs.append(f"SF Burst ({sf_burst}) is very high — may be over-designed. Consider lighter grade.")
        if sf_collapse > 4.0:
            recs.append(f"SF Collapse ({sf_collapse}) is very high — consider cost optimization.")
        if sf_tension > 3.0:
            recs.append(f"SF Tension ({sf_tension}) is very high — verify overpull assumption.")

        if sf_burst < 1.2:
            recs.append("SF Burst is marginal. Verify gas migration scenario assumptions.")
        if sf_collapse < 1.1:
            recs.append("SF Collapse is marginal. Verify evacuation scenario and biaxial correction.")

        triaxial = summary.get("triaxial_status", "")
        if triaxial == "FAIL":
            recs.append("CRITICAL: Triaxial VME check fails. Upgrade grade immediately.")

        collapse_zone = summary.get("collapse_zone", "")
        if collapse_zone == "Elastic":
            recs.append("Collapse in elastic zone — thin-walled behavior. Consider heavier weight.")

        if not recs:
            recs.append("Design passes all criteria with adequate margins.")

        return recs
