"""
Drilling Optimization & Mechanics Specialist Agent

Combines VibrationsEngine, CompletionDesignEngine, and ShotEfficiencyEngine
with LLM reasoning for intelligent parameter recommendations.

Capabilities:
- RPM/WOB optimization via vibration stability maps
- MSE trend analysis for founder-point detection
- Completion design optimization with sensitivity analysis
- Shot Efficiency → Completion Design synergy pipeline
- Depth-of-cut and drilling efficiency checks
"""
import math
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from orchestrator.vibrations_engine import VibrationsEngine
from orchestrator.completion_design_engine import CompletionDesignEngine
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine


class OptimizationEngineerAgent(BaseAgent):
    """
    Drilling Optimization & Mechanics Specialist Agent

    Expert in:
    - ROP Maximization
    - Mechanical Specific Energy (MSE)
    - Vibration Analysis (Stick-slip, Whirl)
    - Bit Selection & Dismantling
    - Completion-Shot Efficiency Synergy
    """

    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/drilling-optimization-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Drilling Optimization Specialist."

        super().__init__(
            name="optimization_engineer",
            role="Drilling Optimization Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/optimization/"
        )

    # -----------------------------------------------------------------------
    # Static computation methods (no LLM needed)
    # -----------------------------------------------------------------------

    @staticmethod
    def recommend_drilling_parameters(
        wob_klb: float,
        rpm: int,
        rop_fph: float,
        torque_ftlb: float,
        bit_diameter_in: float = 8.5,
        bha_length_ft: float = 300,
        bha_od_in: float = 6.75,
        bha_id_in: float = 2.813,
        bha_weight_lbft: float = 83.0,
        hole_diameter_in: float = 8.5,
        mud_weight_ppg: float = 10.0,
        inclination_deg: float = 0.0,
        friction_factor: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Run full vibration analysis and recommend optimal drilling parameters.

        Uses the VibrationEngine stability map to find the best WOB/RPM
        operating point, then compares current vs. optimal.

        Returns:
            Dict with current_analysis, optimal_point, recommendations, delta_mse
        """
        # Full vibration analysis at current operating point
        current = VibrationsEngine.calculate_full_vibration_analysis(
            wob_klb=wob_klb, rpm=rpm, rop_fph=rop_fph,
            torque_ftlb=torque_ftlb, bit_diameter_in=bit_diameter_in,
            bha_length_ft=bha_length_ft, bha_od_in=bha_od_in,
            bha_id_in=bha_id_in, bha_weight_lbft=bha_weight_lbft,
            hole_diameter_in=hole_diameter_in, mud_weight_ppg=mud_weight_ppg,
            inclination_deg=inclination_deg, friction_factor=friction_factor,
        )

        optimal = current.get("vibration_map", {}).get("optimal_point", {})
        recommendations = []

        # Compare current vs optimal
        opt_rpm = optimal.get("rpm", rpm)
        opt_wob = optimal.get("wob", wob_klb)
        stability_now = current.get("stability", {}).get("stability_index", 50)

        if opt_rpm != rpm:
            delta_rpm = opt_rpm - rpm
            direction = "Aumentar" if delta_rpm > 0 else "Reducir"
            recommendations.append(
                f"{direction} RPM de {rpm} a {opt_rpm} ({abs(delta_rpm):+d} RPM)"
            )

        if abs(opt_wob - wob_klb) > 1:
            delta_wob = opt_wob - wob_klb
            direction = "Aumentar" if delta_wob > 0 else "Reducir"
            recommendations.append(
                f"{direction} WOB de {wob_klb:.0f} a {opt_wob:.0f} klb ({delta_wob:+.0f} klb)"
            )

        # Stick-slip check
        ss = current.get("stick_slip", {})
        if ss.get("severity_index", 0) > 1.0:
            recommendations.append(
                f"⚠️ Stick-slip severo ({ss['classification']}): "
                f"aumentar RPM o reducir WOB para mitigar"
            )

        # MSE check
        mse = current.get("mse", {})
        if mse.get("is_founder_point", False):
            recommendations.append(
                "⚠️ Punto de founder detectado: MSE excesivo. "
                "Reducir WOB y/o cambiar broca."
            )
        elif mse.get("efficiency_pct", 100) < 30:
            recommendations.append(
                f"MSE eficiencia baja ({mse['efficiency_pct']}%): "
                f"verificar estado de la broca"
            )

        # Near-resonance check
        axial_crit = current.get("axial_vibrations", {}).get("critical_rpm_1st", 0)
        if axial_crit > 0 and abs(rpm - axial_crit) / axial_crit < 0.10:
            recommendations.append(
                f"⚠️ RPM actual ({rpm}) cerca de resonancia axial "
                f"({axial_crit:.0f}): ajustar ±15%"
            )

        if not recommendations:
            recommendations.append("✅ Parámetros actuales dentro de rango óptimo")

        return {
            "current_stability_index": stability_now,
            "current_mse_psi": mse.get("mse_total_psi", 0),
            "current_mse_efficiency": mse.get("efficiency_pct", 0),
            "optimal_wob_klb": opt_wob,
            "optimal_rpm": opt_rpm,
            "optimal_stability_score": optimal.get("score", 0),
            "stick_slip_severity": ss.get("severity_index", 0),
            "stick_slip_class": ss.get("classification", "Unknown"),
            "recommendations": recommendations,
            "full_analysis": current,
        }

    @staticmethod
    def optimize_completion(
        casing_id_in: float,
        formation_permeability_md: float,
        formation_thickness_ft: float,
        reservoir_pressure_psi: float,
        wellbore_pressure_psi: float,
        depth_tvd_ft: float,
        overburden_stress_psi: float,
        pore_pressure_psi: float,
        sigma_min_psi: float,
        sigma_max_psi: float,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Wrap CompletionDesignEngine full design with decision-support layer.

        Adds risk scoring, decision recommendations, and cost-efficiency hints.
        """
        design = CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=casing_id_in,
            formation_permeability_md=formation_permeability_md,
            formation_thickness_ft=formation_thickness_ft,
            reservoir_pressure_psi=reservoir_pressure_psi,
            wellbore_pressure_psi=wellbore_pressure_psi,
            depth_tvd_ft=depth_tvd_ft,
            overburden_stress_psi=overburden_stress_psi,
            pore_pressure_psi=pore_pressure_psi,
            sigma_min_psi=sigma_min_psi,
            sigma_max_psi=sigma_max_psi,
            **kwargs,
        )

        # Decision support layer
        decisions = []
        risk_score = 0  # 0-100, higher = riskier

        # Underbalance risk
        ub = design.get("underbalance", {})
        if ub.get("status") == "Overbalanced":
            risk_score += 25
            decisions.append("Considerar TCP o técnica de underbalance activo")
        elif ub.get("status") == "Excessive Underbalance":
            risk_score += 30
            decisions.append("Reducir underbalance para evitar colapso de arena")

        # Fracture risk
        frac = design.get("fracture_initiation", {})
        if frac.get("breakdown_pressure_psi", 99999) < reservoir_pressure_psi * 1.05:
            risk_score += 20
            decisions.append("Riesgo de fractura no intencional: presión de breakdown cercana a presión de yacimiento")

        # Gun selection
        gun = design.get("gun_selection", {})
        if gun.get("total_compatible_guns", 0) == 0:
            risk_score += 15
            decisions.append("Sin cañones compatibles: considerar TCP o cañón alternativo")
        elif gun.get("total_compatible_guns", 0) == 1:
            decisions.append("Solo 1 cañón compatible: sin alternativa de respaldo")

        # Penetration efficiency
        pen = design.get("penetration", {})
        if pen.get("efficiency_pct", 100) < 65:
            risk_score += 10
            decisions.append(
                f"Eficiencia de penetración baja ({pen['efficiency_pct']:.0f}%): "
                f"considerar fluido ácido o técnica de limpieza pre-disparo"
            )

        if not decisions:
            decisions.append("✅ Diseño de terminación dentro de parámetros óptimos")

        return {
            "design": design,
            "risk_score": min(risk_score, 100),
            "risk_level": (
                "Bajo" if risk_score < 25 else
                "Medio" if risk_score < 50 else
                "Alto" if risk_score < 75 else
                "Crítico"
            ),
            "decisions": decisions,
        }

    @staticmethod
    def synergy_shot_to_completion(
        log_entries: List[Dict],
        casing_id_in: float = 6.276,
        reservoir_pressure_psi: float = 5000,
        wellbore_pressure_psi: float = 4200,
        depth_tvd_ft: float = 10000,
        overburden_stress_psi: float = 10000,
        pore_pressure_psi: float = 4500,
        sigma_min_psi: float = 5500,
        sigma_max_psi: float = 8000,
        archie_params: Optional[Dict] = None,
        matrix_params: Optional[Dict] = None,
        cutoff_params: Optional[Dict] = None,
        perf_params: Optional[Dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Pipeline: Shot Efficiency → Completion Design.

        1. Run ShotEfficiencyEngine on log data to identify best interval
        2. Extract avg_phi, thickness, and estimated permeability
        3. Feed into CompletionDesignEngine for optimized completion design

        Permeability estimated via Kozeny-Carman:
            k = (d_grain^2 * phi^3) / (180 * (1-phi)^2)  [Darcy]

        Args:
            log_entries: Raw log data for Shot Efficiency
            casing_id_in: Casing ID for completion design
            reservoir/wellbore/stress params: For fracture/underbalance analysis

        Returns:
            Dict with shot_efficiency, completion_design, synergy_summary
        """
        engine_se = ShotEfficiencyEngine()

        # Step 1: Run shot efficiency
        se_result = engine_se.calculate_full_shot_efficiency(
            log_entries,
            archie_params=archie_params,
            matrix_params=matrix_params,
            cutoff_params=cutoff_params,
            perf_params=perf_params,
        )

        # Step 2: Extract best interval properties
        rankings = se_result.get("rankings", {})
        best = rankings.get("best")
        net_pay = se_result.get("net_pay", {})
        summary_se = se_result.get("summary", {})

        if not best:
            return {
                "shot_efficiency": se_result,
                "completion_design": None,
                "synergy_summary": {
                    "status": "No net pay intervals identified",
                    "recommendation": "Review cutoff parameters or acquire additional log data",
                },
            }

        avg_phi = best.get("avg_phi", 0.15)
        thickness = net_pay.get("total_net_pay_ft", best.get("thickness_ft", 10))

        # Step 3: Estimate permeability via Kozeny-Carman (grain size ~ 0.2 mm for sandstone)
        d_grain_cm = 0.02  # 0.2 mm = 0.02 cm
        if avg_phi > 0 and avg_phi < 1:
            k_darcy = (d_grain_cm ** 2 * avg_phi ** 3) / (180 * (1 - avg_phi) ** 2)
            k_md = k_darcy * 1000  # Convert Darcy to milliDarcy
        else:
            k_md = 50  # fallback

        # Step 4: Run completion design with SE-derived parameters
        cd_result = CompletionDesignEngine.calculate_full_completion_design(
            casing_id_in=casing_id_in,
            formation_permeability_md=k_md,
            formation_thickness_ft=thickness,
            reservoir_pressure_psi=reservoir_pressure_psi,
            wellbore_pressure_psi=wellbore_pressure_psi,
            depth_tvd_ft=depth_tvd_ft,
            overburden_stress_psi=overburden_stress_psi,
            pore_pressure_psi=pore_pressure_psi,
            sigma_min_psi=sigma_min_psi,
            sigma_max_psi=sigma_max_psi,
            **kwargs,
        )

        # Step 5: Build synergy summary
        cd_summary = cd_result.get("summary", {})
        return {
            "shot_efficiency": se_result,
            "completion_design": cd_result,
            "synergy_summary": {
                "status": "Pipeline completo",
                "best_interval": {
                    "top_md": best.get("top_md"),
                    "base_md": best.get("base_md"),
                    "thickness_ft": best.get("thickness_ft"),
                    "avg_phi": avg_phi,
                    "avg_sw": best.get("avg_sw"),
                    "score": best.get("score"),
                },
                "estimated_permeability_md": round(k_md, 2),
                "kozeny_carman_grain_size_mm": d_grain_cm * 10,
                "net_pay_ft": thickness,
                "recommended_gun": cd_summary.get("recommended_gun"),
                "optimal_spf": cd_summary.get("optimal_spf"),
                "productivity_ratio": cd_summary.get("productivity_ratio"),
                "underbalance_psi": cd_summary.get("underbalance_psi"),
                "total_alerts": len(se_result.get("alerts", [])) + len(cd_result.get("alerts", [])),
            },
        }

    @staticmethod
    def analyze_mse_trend(
        data_points: List[Dict[str, float]],
        bit_diameter_in: float = 8.5,
    ) -> Dict[str, Any]:
        """
        Analyze MSE trend over multiple depth points to detect founder point.

        Each data_point: {depth_ft, wob_klb, rpm, rop_fph, torque_ftlb}

        Returns:
            Dict with mse_values, trend_slope, founder_detected, recommendations
        """
        if not data_points or len(data_points) < 2:
            return {"error": "Se requieren al menos 2 puntos de datos para análisis de tendencia"}

        mse_values = []
        for pt in data_points:
            result = VibrationsEngine.calculate_mse(
                wob_klb=pt.get("wob_klb", 20),
                rpm=pt.get("rpm", 120),
                rop_fph=pt.get("rop_fph", 50),
                torque_ftlb=pt.get("torque_ftlb", 10000),
                bit_diameter_in=bit_diameter_in,
            )
            mse_values.append({
                "depth_ft": pt.get("depth_ft", 0),
                "mse_psi": result.get("mse_total_psi", 0),
                "efficiency_pct": result.get("efficiency_pct", 0),
                "is_founder": result.get("is_founder_point", False),
            })

        # Linear regression for trend
        n = len(mse_values)
        x = [v["depth_ft"] for v in mse_values]
        y = [v["mse_psi"] for v in mse_values]
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))
        slope = num / den if den > 0 else 0

        # Detect founder points
        founder_depths = [v["depth_ft"] for v in mse_values if v["is_founder"]]
        avg_efficiency = sum(v["efficiency_pct"] for v in mse_values) / n

        recommendations = []
        if slope > 50:  # MSE rising > 50 psi/ft
            recommendations.append(
                f"MSE en tendencia ascendente ({slope:.1f} psi/ft): "
                "considerar cambio de broca"
            )
        if founder_depths:
            recommendations.append(
                f"Puntos de founder detectados en: {founder_depths}"
            )
        if avg_efficiency < 25:
            recommendations.append(
                f"Eficiencia promedio muy baja ({avg_efficiency:.0f}%): "
                "posible broca desgastada o formación de alta resistencia"
            )
        if not recommendations:
            recommendations.append("✅ MSE estable — rendimiento de perforación aceptable")

        return {
            "mse_values": mse_values,
            "trend_slope_psi_per_ft": round(slope, 2),
            "trend_direction": "Rising" if slope > 10 else "Falling" if slope < -10 else "Stable",
            "avg_mse_psi": round(y_mean, 0),
            "avg_efficiency_pct": round(avg_efficiency, 1),
            "founder_detected": len(founder_depths) > 0,
            "founder_depths_ft": founder_depths,
            "total_points": n,
            "recommendations": recommendations,
        }

    @staticmethod
    def quick_parameter_check(
        wob_klb: float,
        rpm: int,
        rop_fph: float,
        torque_ftlb: float,
        bit_diameter_in: float = 8.5,
    ) -> Dict[str, Any]:
        """
        Lightweight MSE + depth-of-cut check without full vibration analysis.
        Useful for real-time monitoring dashboards.

        Returns:
            Dict with mse, doc, efficiency, status, quick_recommendations
        """
        mse = VibrationsEngine.calculate_mse(
            wob_klb=wob_klb, rpm=rpm, rop_fph=rop_fph,
            torque_ftlb=torque_ftlb, bit_diameter_in=bit_diameter_in,
        )

        # Depth of cut (DOC) = ROP / (RPM * 60) in inches/rev
        doc_in_per_rev = (rop_fph * 12) / (rpm * 60) if rpm > 0 else 0

        # Typical DOC targets: PDC 0.02-0.10 in/rev, Roller Cone 0.01-0.05
        doc_status = (
            "Óptimo" if 0.02 <= doc_in_per_rev <= 0.10 else
            "Bajo — aumentar WOB" if doc_in_per_rev < 0.02 else
            "Alto — posible daño a cortadores"
        )

        quick_recs = []
        if mse.get("is_founder_point", False):
            quick_recs.append("FOUNDER POINT: Reducir WOB inmediatamente")
        if mse.get("efficiency_pct", 100) < 20:
            quick_recs.append("Eficiencia crítica: verificar broca y formación")
        if doc_in_per_rev < 0.01:
            quick_recs.append("DOC muy bajo: aumentar WOB o reducir RPM")
        if not quick_recs:
            quick_recs.append("✅ Parámetros dentro de rango aceptable")

        return {
            "mse_total_psi": mse.get("mse_total_psi", 0),
            "mse_efficiency_pct": mse.get("efficiency_pct", 0),
            "is_founder_point": mse.get("is_founder_point", False),
            "doc_in_per_rev": round(doc_in_per_rev, 4),
            "doc_status": doc_status,
            "status": "OK" if not mse.get("is_founder_point") and mse.get("efficiency_pct", 0) > 20 else "WARNING",
            "quick_recommendations": quick_recs,
        }

    # -----------------------------------------------------------------------
    # LLM-powered analysis methods
    # -----------------------------------------------------------------------

    def analyze_problem(self, problem_description: str) -> dict:
        """
        Analyze a drilling optimization problem using the expert system prompt.

        Args:
            problem_description: Description of the drilling problem

        Returns:
            dict: Analysis results with formatted query for LLM
        """
        return self.analyze_interactive(problem_description)

    def analyze_with_data(
        self,
        problem_description: str,
        wob_klb: float = 20,
        rpm: int = 120,
        rop_fph: float = 50,
        torque_ftlb: float = 10000,
        bit_diameter_in: float = 8.5,
    ) -> dict:
        """
        Analyze problem enriched with actual engine calculations.
        Combines numerical results with LLM reasoning.

        Args:
            problem_description: Description of the issue
            wob_klb, rpm, etc.: Current operating parameters

        Returns:
            dict with engine_data + llm_query for AI analysis
        """
        # Get engine data
        engine_data = self.recommend_drilling_parameters(
            wob_klb=wob_klb, rpm=rpm, rop_fph=rop_fph,
            torque_ftlb=torque_ftlb, bit_diameter_in=bit_diameter_in,
        )

        # Build enriched context for LLM
        context = (
            f"DATOS DEL MOTOR DE CÁLCULO:\n"
            f"- Estabilidad actual: {engine_data['current_stability_index']:.1f}/100\n"
            f"- MSE: {engine_data['current_mse_psi']:.0f} psi "
            f"(eficiencia: {engine_data['current_mse_efficiency']:.0f}%)\n"
            f"- Stick-Slip: {engine_data['stick_slip_class']} "
            f"(severidad: {engine_data['stick_slip_severity']:.2f})\n"
            f"- Punto óptimo: WOB={engine_data['optimal_wob_klb']:.0f} klb, "
            f"RPM={engine_data['optimal_rpm']}\n"
            f"\nRecomendaciones del motor:\n"
        )
        for rec in engine_data["recommendations"]:
            context += f"  • {rec}\n"

        enriched_query = f"{problem_description}\n\n{context}"
        llm_result = self.analyze_interactive(enriched_query)

        return {
            "engine_data": engine_data,
            "llm_analysis": llm_result,
        }
