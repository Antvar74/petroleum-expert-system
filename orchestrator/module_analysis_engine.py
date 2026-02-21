"""
Module Analysis Engine.

Orchestrates EXISTING specialized agents (well_engineer, mud_engineer, drilling_engineer)
via APICoordinator.run_automated_step() to produce executive/managerial AI analyses
of the 4 engineering module results: Torque & Drag, Hydraulics/ECD, Stuck Pipe, Well Control.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from orchestrator.api_coordinator import APICoordinator


# Metric label translations
METRIC_LABELS = {
    "en": {
        "Hookload": "Hookload", "Torque": "Torque", "Max Side Force": "Max Side Force",
        "Buoyancy Factor": "Buoyancy Factor", "ECD at TD": "ECD at TD", "Total SPP": "Total SPP",
        "HSI": "HSI", "% at Bit": "% at Bit", "Surge Margin": "Surge Margin",
        "Mechanism": "Mechanism", "Risk Level": "Risk Level", "Risk Score": "Risk Score",
        "Free Point": "Free Point", "Pf": "Pf", "KMW": "KMW", "ICP": "ICP", "FCP": "FCP",
        "MAASP": "MAASP", "Influx Type": "Influx Type",
        "Annular Velocity": "Annular Velocity", "CTR": "CTR", "HCI": "HCI",
        "Cleaning Quality": "Cleaning Quality", "Cuttings Concentration": "Cuttings Concentration",
        "Total Force": "Total Force", "Buckling Status": "Buckling Status",
        "Piston Force": "Piston Force", "Temperature Force": "Temperature Force",
        "Total Pressure Loss": "Total Pressure Loss", "Buoyed Weight": "Buoyed Weight",
        "Snubbing Force": "Snubbing Force", "Max Reach": "Max Reach",
        "Kill Weight": "Kill Weight", "Pipe Light": "Pipe Light",
        "D50": "D50", "Sanding Risk": "Sanding Risk",
        "Critical Drawdown": "Critical Drawdown", "Recommended Gravel": "Recommended Gravel",
        "Skin Total": "Skin Total", "Recommended Completion": "Recommended Completion",
        "Total Cement": "Total Cement", "Max ECD": "Max ECD",
        "Fracture Margin": "Fracture Margin", "Job Time": "Job Time",
        "Free-Fall": "Free-Fall", "Lift Pressure": "Lift Pressure",
        "Selected Grade": "Selected Grade", "SF Burst": "SF Burst",
        "SF Collapse": "SF Collapse", "SF Tension": "SF Tension",
        "Triaxial Status": "Triaxial Status", "Overall Status": "Overall Status",
    },
    "es": {
        "Hookload": "Carga en Gancho", "Torque": "Torque", "Max Side Force": "Fuerza Lateral Máx",
        "Buoyancy Factor": "Factor de Flotación", "ECD at TD": "ECD en TD", "Total SPP": "SPP Total",
        "HSI": "HSI", "% at Bit": "% en Barrena", "Surge Margin": "Margen de Surgencia",
        "Mechanism": "Mecanismo", "Risk Level": "Nivel de Riesgo", "Risk Score": "Puntaje de Riesgo",
        "Free Point": "Punto Libre", "Pf": "Pf", "KMW": "PMM", "ICP": "PCI", "FCP": "PCF",
        "MAASP": "MAASP", "Influx Type": "Tipo de Influjo",
        "Annular Velocity": "Velocidad Anular", "CTR": "CTR", "HCI": "HCI",
        "Cleaning Quality": "Calidad de Limpieza", "Cuttings Concentration": "Concentración de Recortes",
        "Total Force": "Fuerza Total", "Buckling Status": "Estado de Pandeo",
        "Piston Force": "Fuerza Pistón", "Temperature Force": "Fuerza Temperatura",
        "Total Pressure Loss": "Pérdida Presión Total", "Buoyed Weight": "Peso Flotado",
        "Snubbing Force": "Fuerza de Snubbing", "Max Reach": "Alcance Máximo",
        "Kill Weight": "Peso de Control", "Pipe Light": "Tubería Liviana",
        "D50": "D50", "Sanding Risk": "Riesgo de Arenamiento",
        "Critical Drawdown": "Drawdown Crítico", "Recommended Gravel": "Grava Recomendada",
        "Skin Total": "Skin Total", "Recommended Completion": "Completación Recomendada",
        "Total Cement": "Cemento Total", "Max ECD": "ECD Máximo",
        "Fracture Margin": "Margen de Fractura", "Job Time": "Tiempo de Trabajo",
        "Free-Fall": "Caída Libre", "Lift Pressure": "Presión de Levantamiento",
        "Selected Grade": "Grado Seleccionado", "SF Burst": "FS Estallido",
        "SF Collapse": "FS Colapso", "SF Tension": "FS Tensión",
        "Triaxial Status": "Estado Triaxial", "Overall Status": "Estado General",
    },
}


class ModuleAnalysisEngine:
    """
    Orchestrates existing specialized agents to analyze
    results from the 4 engineering modules.

    Agent mapping:
      - Torque & Drag  → well_engineer (soft-string, buckling, keyseating expertise)
      - Hydraulics/ECD  → mud_engineer (ECD, hydraulics, surge/swab, hole cleaning)
      - Stuck Pipe      → drilling_engineer (stuck pipe RCA, STOPS, differential sticking)
      - Well Control    → drilling_engineer (kick investigation, barriers, kill procedures)
    """

    def __init__(self):
        self.coordinator = APICoordinator()

    # ================================================================
    # Public analysis methods — one per module
    # ================================================================

    async def analyze_torque_drag(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze T&D results using well_engineer agent."""
        problem = self._build_td_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "torque_drag", result_data, well_name, language, provider)

    async def analyze_hydraulics(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Hydraulics/ECD results using mud_engineer agent."""
        problem = self._build_hyd_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("mud_engineer", problem, context, provider=provider)
        return self._package(analysis, "hydraulics", result_data, well_name, language, provider)

    async def analyze_stuck_pipe(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Stuck Pipe results using drilling_engineer agent."""
        problem = self._build_sp_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("drilling_engineer", problem, context, provider=provider)
        return self._package(analysis, "stuck_pipe", result_data, well_name, language, provider)

    async def analyze_well_control(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Well Control results using drilling_engineer agent."""
        problem = self._build_wc_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("drilling_engineer", problem, context, provider=provider)
        return self._package(analysis, "well_control", result_data, well_name, language, provider)

    async def analyze_wellbore_cleanup(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Wellbore Cleanup results using mud_engineer agent."""
        problem = self._build_cu_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("mud_engineer", problem, context, provider=provider)
        return self._package(analysis, "wellbore_cleanup", result_data, well_name, language, provider)

    async def analyze_packer_forces(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Packer Forces results using well_engineer agent."""
        problem = self._build_pf_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "packer_forces", result_data, well_name, language, provider)

    async def analyze_workover_hydraulics(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Workover Hydraulics results using well_engineer agent."""
        problem = self._build_wh_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "workover_hydraulics", result_data, well_name, language, provider)

    async def analyze_sand_control(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Sand Control results using well_engineer agent."""
        problem = self._build_sc_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "sand_control", result_data, well_name, language, provider)

    async def analyze_cementing(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Cementing results using cementing_engineer agent."""
        problem = self._build_cem_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("cementing_engineer", problem, context, provider=provider)
        return self._package(analysis, "cementing", result_data, well_name, language, provider)

    async def analyze_casing_design(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Casing Design results using well_engineer agent."""
        problem = self._build_csg_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "casing_design", result_data, well_name, language, provider)

    # ================================================================
    # Generic dispatcher (for modules 9+)
    # ================================================================

    async def analyze_module(self, module: str, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Generic dispatcher that routes to the appropriate analyze_X method."""
        method_map = {
            "completion_design": self.analyze_completion_design,
            "shot_efficiency": self.analyze_shot_efficiency,
            "vibrations": self.analyze_vibrations,
            "cementing": self.analyze_cementing,
            "casing_design": self.analyze_casing_design,
            "daily_report": self.analyze_daily_report,
        }
        handler = method_map.get(module)
        if handler:
            return await handler(result_data, well_name, params, language, provider)

        # Fallback: generic analysis using well_engineer
        problem = self._build_generic_problem(module, result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, module, result_data, well_name, language, provider)

    async def analyze_completion_design(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Completion Design results using well_engineer agent."""
        problem = self._build_cd_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "completion_design", result_data, well_name, language, provider)

    async def analyze_shot_efficiency(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Shot Efficiency results using well_engineer agent."""
        problem = self._build_se_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "shot_efficiency", result_data, well_name, language, provider)

    async def analyze_vibrations(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Vibrations results using optimization_engineer agent."""
        problem = self._build_vb_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("optimization_engineer", problem, context, provider=provider)
        return self._package(analysis, "vibrations", result_data, well_name, language, provider)

    async def analyze_daily_report(self, result_data: Dict, well_name: str, params: Dict, language: str = "en", provider: str = "auto") -> Dict:
        """Analyze Daily Drilling Report for operational efficiency, trends, and recommendations."""
        problem = self._build_ddr_problem(result_data, well_name, params, language)
        context = {"well_data": {"name": well_name, **params}}
        analysis = await self.coordinator.run_automated_step("well_engineer", problem, context, provider=provider)
        return self._package(analysis, "daily_report", result_data, well_name, language, provider)

    # ================================================================
    # Language helpers
    # ================================================================

    def _get_language_prefix(self, language: str) -> str:
        if language == "es":
            return "IMPORTANTE: Responde COMPLETAMENTE en español latinoamericano.\n\n"
        return ""

    def _get_instruction_block(self, language: str = "en") -> str:
        if language == "es":
            return """Genera un análisis ejecutivo/gerencial con estas secciones:
1. RESUMEN EJECUTIVO (3-5 oraciones)
2. HALLAZGOS CLAVE (puntos con valores)
3. ALERTAS Y RIESGOS
4. RECOMENDACIONES OPERATIVAS
5. CONCLUSIÓN GERENCIAL"""
        return """Generate an executive/managerial analysis with these sections:
1. EXECUTIVE SUMMARY (3-5 sentences)
2. KEY FINDINGS (bullets with values)
3. ALERTS AND RISKS
4. OPERATIONAL RECOMMENDATIONS
5. MANAGERIAL CONCLUSION"""

    def _ml(self, key: str, language: str) -> str:
        """Get metric label in the specified language."""
        return METRIC_LABELS.get(language, METRIC_LABELS["en"]).get(key, key)

    # ================================================================
    # Problem builders — serialize module results for the agent
    # ================================================================

    def _build_td_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        stations = result_data.get("station_results", [])
        critical = [s for s in stations if s.get("buckling_status") not in ("OK", None)]
        max_drag = {}
        if stations:
            max_drag = max(stations, key=lambda s: abs(s.get("normal_force", 0)), default={})

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Torque & Drag Module — Well: {well_name}

Operation: {params.get('operation', 'N/A')}
Friction (cased/open): {params.get('friction_cased', 'N/A')} / {params.get('friction_open', 'N/A')}
Mud Weight: {params.get('mud_weight', 'N/A')} ppg | WOB: {params.get('wob', 0)} klb | RPM: {params.get('rpm', 0)}
Casing Shoe MD: {params.get('casing_shoe_md', 'N/A')} ft

SOFT-STRING MODEL RESULTS (Johancsik):
- Surface Hookload: {summary.get('surface_hookload_klb', 'N/A')} klb
- Surface Torque: {summary.get('surface_torque_ftlb', 'N/A')} ft-lb
- Max Side Force: {summary.get('max_side_force_lb', 'N/A')} lb
- Buoyancy Factor: {summary.get('buoyancy_factor', 'N/A')}
- Buoyed Weight: {summary.get('buoyed_weight_klb', 'N/A')} klb
- Alerts: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

STATIONS WITH BUCKLING: {len(critical)} of {len(stations)}
{json.dumps(critical[:5], indent=2, ensure_ascii=False) if critical else 'None'}

STATION WITH MAX DRAG: {json.dumps(max_drag, indent=2, ensure_ascii=False) if max_drag else 'N/A'}

{self._get_instruction_block(language)}"""

    def _build_hyd_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        hyd = result_data.get("hydraulics", {})
        surge = result_data.get("surge", {})
        summary = hyd.get("summary", {})
        bit_hyd = hyd.get("bit_hydraulics", {})
        section_results = hyd.get("section_results", [])

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Hydraulics / ECD Module — Well: {well_name}

Flow Rate: {params.get('flow_rate', 'N/A')} gpm | Mud Weight: {params.get('mud_weight', 'N/A')} ppg
PV: {params.get('pv', 'N/A')} cP | YP: {params.get('yp', 'N/A')} lb/100ft2
TVD: {params.get('tvd', 'N/A')} ft | Rheology Model: {params.get('rheology_model', 'N/A')}

HYDRAULIC CIRCUIT SUMMARY:
- Total SPP: {summary.get('total_system_pressure_psi', 'N/A')} psi
- ECD at TD: {summary.get('ecd_at_td_ppg', 'N/A')} ppg
- Annular Pressure Loss: {summary.get('annular_pressure_loss_psi', 'N/A')} psi
- HSI: {summary.get('hsi', 'N/A')}
- Percent Pressure at Bit: {summary.get('percent_at_bit', 'N/A')}%

BIT HYDRAULICS:
- Bit Pressure Drop: {bit_hyd.get('bit_pressure_drop_psi', 'N/A')} psi
- Jet Velocity: {bit_hyd.get('jet_velocity_fps', 'N/A')} ft/s
- Impact Force: {bit_hyd.get('impact_force_lbs', 'N/A')} lbs
- HSI: {bit_hyd.get('hsi', 'N/A')}

SECTION RESULTS: {len(section_results)} sections calculated
{json.dumps(section_results[:5], indent=2, ensure_ascii=False) if section_results else 'N/A'}

SURGE/SWAB ANALYSIS:
- Surge ECD: {surge.get('surge_ecd_ppg', 'N/A')} ppg
- Swab ECD: {surge.get('swab_ecd_ppg', 'N/A')} ppg
- Surge Margin: {surge.get('surge_margin', 'N/A')}
- Swab Margin: {surge.get('swab_margin', 'N/A')}

{self._get_instruction_block(language)}"""

    def _build_sp_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        diagnosis = result_data.get("diagnosis", {})
        risk = result_data.get("risk", {})
        free_point = result_data.get("freePoint", {})

        mechanism = diagnosis.get("mechanism") or params.get("mechanism", "Unknown")
        risk_level = risk.get("risk_level", "N/A")
        risk_score = risk.get("risk_score", "N/A")

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Stuck Pipe Module — Well: {well_name}

Mud Weight: {params.get('mud_weight', 'N/A')} ppg

DIAGNOSIS RESULT:
- Mechanism: {mechanism}
- Confidence: {diagnosis.get('confidence', 'N/A')}
- Decision Path: {json.dumps(diagnosis.get('decision_path', []), ensure_ascii=False)}

RISK ASSESSMENT:
- Risk Level: {risk_level}
- Risk Score: {risk_score}
- Contributing Factors: {json.dumps(risk.get('contributing_factors', {}), indent=2, ensure_ascii=False)}

FREE POINT CALCULATION:
- Free Point Depth: {free_point.get('free_point_depth_ft', 'N/A')} ft
- Stuck Point Depth: {free_point.get('stuck_point_depth_ft', 'N/A')} ft
- Pipe Stretch: {free_point.get('stretch_inches', 'N/A')} in
- Pull Force: {free_point.get('pull_force_lbs', 'N/A')} lbs
- Yield %: {free_point.get('percent_yield', 'N/A')}%

RECOMMENDED ACTIONS:
{json.dumps(risk.get('recommended_actions', diagnosis.get('actions', [])), indent=2, ensure_ascii=False)}

{self._get_instruction_block(language)}"""

    def _build_wc_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        kill = result_data.get("kill", {})
        vol = result_data.get("volumetric", {})
        bullhead = result_data.get("bullhead", {})

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Well Control Module — Well: {well_name}

PRE-RECORDED DATA:
- Depth MD: {params.get('depth_md', 'N/A')} ft | TVD: {params.get('depth_tvd', 'N/A')} ft
- Original MW: {params.get('original_mud_weight', 'N/A')} ppg
- Casing Shoe TVD: {params.get('casing_shoe_tvd', 'N/A')} ft
- LOT EMW: {params.get('lot_emw', 'N/A')} ppg

KILL SHEET CALCULATIONS:
- Formation Pressure: {kill.get('formation_pressure_psi', 'N/A')} psi
- Kill Mud Weight: {kill.get('kill_mud_weight_ppg', 'N/A')} ppg
- ICP: {kill.get('icp_psi', 'N/A')} psi | FCP: {kill.get('fcp_psi', 'N/A')} psi
- MAASP: {kill.get('maasp_psi', 'N/A')} psi
- Influx Type: {kill.get('influx_type', 'N/A')}
- Influx Gradient: {kill.get('influx_gradient_psi_ft', 'N/A')} psi/ft
- SIDPP: {kill.get('sidpp', params.get('sidpp', 'N/A'))} | SICP: {kill.get('sicp', params.get('sicp', 'N/A'))}
- Pit Gain: {kill.get('pit_gain', params.get('pit_gain', 'N/A'))} bbl
- Alerts: {json.dumps(kill.get('alerts', []), ensure_ascii=False)}
- Kill Method Detail: {json.dumps(kill.get('method_detail', {}), indent=2, ensure_ascii=False)[:500]}

VOLUMETRIC METHOD:
- Method: {vol.get('method', 'N/A')}
- Cycles: {len(vol.get('cycles', []))}
- Working Pressure: {vol.get('initial_conditions', {}).get('working_pressure_psi', 'N/A')} psi

BULLHEAD:
- Shoe Safe: {bullhead.get('shoe_integrity', {}).get('safe', 'N/A')}
- Pump Pressure: {bullhead.get('calculations', {}).get('required_pump_pressure_psi', 'N/A')} psi
- Warnings: {json.dumps(bullhead.get('warnings', []), ensure_ascii=False)}

{self._get_instruction_block(language)}"""

    def _build_cu_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        sweep = result_data.get("sweep_pill", {})
        alerts = summary.get("alerts", [])

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Wellbore Cleanup Module — Well: {well_name}

Flow Rate: {params.get('flow_rate', 'N/A')} gpm | Mud Weight: {params.get('mud_weight', 'N/A')} ppg
PV: {params.get('pv', 'N/A')} cP | YP: {params.get('yp', 'N/A')} lb/100ft²
Hole ID: {params.get('hole_id', 'N/A')}" | Pipe OD: {params.get('pipe_od', 'N/A')}"
Inclination: {params.get('inclination', 'N/A')}° | RPM: {params.get('rpm', 'N/A')}
ROP: {params.get('rop', 'N/A')} ft/hr | Cutting Size: {params.get('cutting_size', 'N/A')}"

HOLE CLEANING RESULTS:
- Annular Velocity: {summary.get('annular_velocity_ftmin', 'N/A')} ft/min
- Slip Velocity: {summary.get('slip_velocity_ftmin', 'N/A')} ft/min
- Transport Velocity: {summary.get('transport_velocity_ftmin', 'N/A')} ft/min
- Cuttings Transport Ratio (CTR): {summary.get('cuttings_transport_ratio', 'N/A')}
- Hole Cleaning Index (HCI): {summary.get('hole_cleaning_index', 'N/A')}
- Cleaning Quality: {summary.get('cleaning_quality', 'N/A')}
- Cuttings Concentration: {summary.get('cuttings_concentration_pct', 'N/A')}%
- Minimum Flow Rate Required: {summary.get('minimum_flow_rate_gpm', 'N/A')} gpm
- Flow Rate Adequate: {summary.get('flow_rate_adequate', 'N/A')}

SWEEP PILL DESIGN:
- Pill Volume: {sweep.get('pill_volume_bbl', 'N/A')} bbl
- Pill Weight: {sweep.get('pill_weight_ppg', 'N/A')} ppg
- Pill Length: {sweep.get('pill_length_ft', 'N/A')} ft

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_pf_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        forces = result_data.get("force_components", {})
        movements = result_data.get("movements", {})
        alerts = summary.get("alerts", [])

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Packer Forces Module — Well: {well_name}

Tubing: {params.get('tubing_od', 'N/A')}" OD x {params.get('tubing_id', 'N/A')}" ID, {params.get('tubing_weight', 'N/A')} lb/ft
Packer Depth TVD: {params.get('packer_depth_tvd', 'N/A')} ft
Seal Bore ID: {params.get('seal_bore_id', 'N/A')}"
ΔT: {params.get('delta_t_f', summary.get('delta_t_f', 'N/A'))}°F
ΔPi: {params.get('delta_pi_psi', 'N/A')} psi | ΔPo: {params.get('delta_po_psi', 'N/A')} psi

FORCE COMPONENTS (Lubinski Method):
- Piston Force: {forces.get('piston', 'N/A')} lbs
- Ballooning Force: {forces.get('ballooning', 'N/A')} lbs
- Temperature Force: {forces.get('temperature', 'N/A')} lbs
- TOTAL Force: {forces.get('total', 'N/A')} lbs ({summary.get('force_direction', 'N/A')})

TUBING MOVEMENTS:
- Piston: {movements.get('piston_in', 'N/A')}" | Ballooning: {movements.get('ballooning_in', 'N/A')}"
- Thermal: {movements.get('thermal_in', 'N/A')}" | Total: {movements.get('total_in', 'N/A')}"

BUCKLING CHECK:
- Status: {summary.get('buckling_status', 'N/A')}
- Critical Buckling Load: {summary.get('buckling_critical_load_lbs', 'N/A')} lbs

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_wh_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        hydraulics = result_data.get("hydraulics", {})
        snubbing = result_data.get("snubbing", {})
        reach = result_data.get("max_reach", {})
        kill_data = result_data.get("kill_data", {})
        alerts = summary.get("alerts", [])

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Workover Hydraulics Module — Well: {well_name}

CT String: {params.get('ct_od', 'N/A')}" OD × {params.get('wall_thickness', 'N/A')}" wall, Length: {params.get('ct_length', 'N/A')} ft
Wellbore: {params.get('hole_id', 'N/A')}" ID, TVD: {params.get('tvd', 'N/A')} ft, Inclination: {params.get('inclination', 'N/A')}°
Fluid: {params.get('mud_weight', 'N/A')} ppg, PV: {params.get('pv', 'N/A')} cP, YP: {params.get('yp', 'N/A')} lb/100ft²

HYDRAULICS:
- Total Pressure Loss: {summary.get('total_pressure_loss_psi', 'N/A')} psi (Pipe: {summary.get('pipe_loss_psi', 'N/A')} + Annular: {summary.get('annular_loss_psi', 'N/A')})
- Pipe Regime: {hydraulics.get('pipe_regime', 'N/A')} | Annular Regime: {hydraulics.get('annular_regime', 'N/A')}

FORCE ANALYSIS:
- Buoyed Weight: {summary.get('buoyed_weight_lb', 'N/A')} lb
- Drag Force: {summary.get('drag_force_lb', 'N/A')} lb
- Snubbing Force: {snubbing.get('snubbing_force_lb', 'N/A')} lb | Pipe Light: {snubbing.get('pipe_light', 'N/A')}
- Light/Heavy Point: {snubbing.get('light_heavy_depth_ft', 'N/A')} ft

MAX REACH:
- Estimated: {reach.get('max_reach_ft', 'N/A')} ft
- Limiting Factor: {reach.get('limiting_factor', 'N/A')}
- Helical Buckling Load: {reach.get('helical_buckling_load_lb', 'N/A')} lb

KILL DATA:
- Kill Weight: {kill_data.get('kill_weight_ppg', 'N/A')} ppg | Status: {kill_data.get('status', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_sc_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        psd = result_data.get("psd", {})
        gravel = result_data.get("gravel", {})
        screen = result_data.get("screen", {})
        drawdown = result_data.get("drawdown", {})
        completion = result_data.get("completion", {})
        skin = result_data.get("skin", {})
        alerts = summary.get("alerts", [])

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Sand Control Module — Well: {well_name}

Formation: UCS={params.get('ucs_psi', 'N/A')} psi, φ={params.get('friction_angle_deg', 'N/A')}°
Reservoir: P={params.get('reservoir_pressure_psi', 'N/A')} psi, k={params.get('formation_permeability_md', 'N/A')} mD
Completion: {params.get('wellbore_type', 'N/A')}, Interval: {params.get('interval_length', 'N/A')} ft

GRAIN SIZE DISTRIBUTION:
- D50: {psd.get('d50_mm', 'N/A')} mm | D10: {psd.get('d10_mm', 'N/A')} mm | D90: {psd.get('d90_mm', 'N/A')} mm
- Cu: {psd.get('uniformity_coefficient', 'N/A')} | Sorting: {psd.get('sorting', 'N/A')}

GRAVEL SELECTION (Saucier):
- Recommended: {gravel.get('recommended_pack', 'N/A')} mesh
- Range: {gravel.get('gravel_min_mm', 'N/A')}-{gravel.get('gravel_max_mm', 'N/A')} mm

SCREEN: Slot {screen.get('recommended_standard_slot_in', 'N/A')}" ({screen.get('screen_type', 'N/A')})

SANDING ANALYSIS:
- Critical Drawdown: {drawdown.get('critical_drawdown_psi', 'N/A')} psi
- Risk: {drawdown.get('sanding_risk', 'N/A')}

SKIN: Total={skin.get('skin_total', 'N/A')} (Perf={skin.get('skin_perforation', 'N/A')}, Gravel={skin.get('skin_gravel', 'N/A')}, Damage={skin.get('skin_damage', 'N/A')})

RECOMMENDED: {completion.get('recommended', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_cd_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Completion Design Module — Well: {well_name}

PR: {summary.get('productivity_ratio', 'N/A')} | Quality: {summary.get('quality', 'N/A')}
Pen Depth: {summary.get('corrected_depth_in', 'N/A')}" | SPF: {params.get('spf', 'N/A')} | Phasing: {params.get('phasing_deg', 'N/A')}°
Fracture: P_init={summary.get('fracture_initiation_psi', 'N/A')} psi | FG={summary.get('fracture_gradient_ppg', 'N/A')} ppg

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_se_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Shot Efficiency Module — Well: {well_name}

Net Pay: {summary.get('total_net_pay_ft', 'N/A')} ft | Intervals: {summary.get('net_pay_intervals', 'N/A')}
Avg Porosity: {summary.get('avg_porosity', 'N/A')} | Avg Sw: {summary.get('avg_sw', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_vb_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Vibrations / Stability Module — Well: {well_name}

WOB: {params.get('wob_klb', 'N/A')} klb | RPM: {params.get('rpm', 'N/A')}
MSE: {summary.get('mse_total_psi', 'N/A')} psi | Efficiency: {summary.get('efficiency_pct', 'N/A')}%
Stability: {summary.get('stability_index', 'N/A')} | Stick-Slip: {summary.get('stick_slip_severity', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_cem_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Cementing Simulation Module — Well: {well_name}

Casing: {params.get('casing_od_in', 'N/A')}" OD × {params.get('hole_id_in', 'N/A')}" hole
Shoe MD: {params.get('casing_shoe_md_ft', 'N/A')} ft | TOC: {params.get('toc_md_ft', 'N/A')} ft

VOLUMES:
- Total Cement: {summary.get('total_cement_bbl', 'N/A')} bbl ({summary.get('total_cement_sacks', 'N/A')} sacks)
- Displacement: {summary.get('displacement_bbl', 'N/A')} bbl
- Total Pump: {summary.get('total_pump_bbl', 'N/A')} bbl

JOB PARAMETERS:
- Job Time: {summary.get('job_time_hrs', 'N/A')} hrs
- Max ECD: {summary.get('max_ecd_ppg', 'N/A')} ppg | Fracture Margin: {summary.get('fracture_margin_ppg', 'N/A')} ppg
- Max BHP: {summary.get('max_bhp_psi', 'N/A')} psi
- Lift Pressure: {summary.get('lift_pressure_psi', 'N/A')} psi
- Free-Fall: {summary.get('free_fall_ft', 'N/A')} ft
- U-Tube: {summary.get('utube_psi', 'N/A')} psi

STATUS: {summary.get('ecd_status', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_csg_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Casing Design Module — Well: {well_name}

Casing: {params.get('casing_od_in', 'N/A')}" OD, {params.get('casing_weight_ppf', 'N/A')} ppf
TVD: {params.get('tvd_ft', 'N/A')} ft | MW: {params.get('mud_weight_ppg', 'N/A')} ppg

LOADS:
- Max Burst: {summary.get('max_burst_load_psi', 'N/A')} psi
- Max Collapse: {summary.get('max_collapse_load_psi', 'N/A')} psi
- Total Tension: {summary.get('total_tension_lbs', 'N/A')} lbs

RATINGS ({summary.get('selected_grade', 'N/A')}):
- Burst: {summary.get('burst_rating_psi', 'N/A')} psi | SF: {summary.get('sf_burst', 'N/A')}
- Collapse: {summary.get('collapse_rating_psi', 'N/A')} psi ({summary.get('collapse_zone', 'N/A')}) | SF: {summary.get('sf_collapse', 'N/A')}
- Tension: {summary.get('tension_rating_lbs', 'N/A')} lbs | SF: {summary.get('sf_tension', 'N/A')}

TRIAXIAL VME: {summary.get('triaxial_status', 'N/A')} (Utilization: {summary.get('triaxial_utilization_pct', 'N/A')}%)
OVERALL: {summary.get('overall_status', 'N/A')}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    def _build_ddr_problem(self, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        from orchestrator.ddr_engine import DDREngine
        summary = DDREngine.calculate_daily_summary(result_data) if result_data else {}
        report_type = result_data.get("report_type", "drilling")
        ops_log = result_data.get("operations_log") or []
        npt_events = result_data.get("npt_events") or []
        mud = result_data.get("mud_properties") or {}
        gas = result_data.get("gas_monitoring") or {}
        hsse = result_data.get("hsse_data") or {}
        cost = result_data.get("cost_summary") or {}

        ops_summary = ""
        for op in ops_log[:10]:
            ops_summary += f"  {op.get('from_time', '?')}-{op.get('to_time', '?')}h: [{op.get('iadc_code', 'OT')}] {op.get('description', '')[:80]}\n"

        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — Daily Operations Report — Well: {well_name}

REPORT TYPE: {report_type.upper()}
DATE: {result_data.get('report_date', 'N/A')}
DEPTH: {result_data.get('depth_md_start', 'N/A')} → {result_data.get('depth_md_end', 'N/A')} ft MD | TVD: {result_data.get('depth_tvd', 'N/A')} ft

DAILY KPIs:
- Footage Drilled: {summary.get('footage_drilled', 0)} ft
- Average ROP: {summary.get('avg_rop', 0)} ft/hr
- Drilling Hours: {summary.get('drilling_hours', 0)} hrs
- NPT Hours: {summary.get('npt_hours', 0)} hrs ({summary.get('npt_percentage', 0)}%)
- Connection Time: {summary.get('connection_hours', 0)} hrs
- Productive Hours: {summary.get('productive_hours', 0)} / 24 hrs

OPERATIONS LOG ({len(ops_log)} entries):
{ops_summary if ops_summary else 'No operations logged'}

NPT EVENTS: {len(npt_events)} events, {summary.get('npt_hours', 0)} total hours
{json.dumps(npt_events[:5], indent=2, ensure_ascii=False) if npt_events else 'None'}

MUD PROPERTIES: Density={mud.get('density', 'N/A')} ppg, PV={mud.get('pv', 'N/A')} cP, YP={mud.get('yp', 'N/A')} lb/100ft2

GAS MONITORING: Background={gas.get('background_gas', 'N/A')}%, H2S={gas.get('h2s', 'N/A')} ppm

HSSE: Incidents={hsse.get('incidents', 0)}, LTI Hours={hsse.get('lti_hours', 'N/A')}

COST: Day=${cost.get('total_day', 0):,.0f}, Cumulative=${cost.get('total_cumulative', 0):,.0f}

{self._get_instruction_block(language)}"""

    def _build_generic_problem(self, module: str, result_data: Dict, well_name: str, params: Dict, language: str = "en") -> str:
        summary = result_data.get("summary", {})
        alerts = summary.get("alerts", [])
        return f"""{self._get_language_prefix(language)}EXECUTIVE ANALYSIS REQUIRED — {module.replace('_', ' ').title()} Module — Well: {well_name}

RESULTS SUMMARY:
{json.dumps(summary, indent=2, ensure_ascii=False, default=str)[:2000]}

ALERTS: {json.dumps(alerts, ensure_ascii=False) if alerts else 'None'}

{self._get_instruction_block(language)}"""

    # ================================================================
    # Packaging and metrics extraction
    # ================================================================

    def _package(self, analysis: Dict, module: str, result_data: Dict, well_name: str, language: str = "en", provider: str = "auto") -> Dict:
        return {
            "module": module,
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis.get("analysis", ""),
            "confidence": analysis.get("confidence", "MEDIUM"),
            "agent_used": analysis.get("agent", ""),
            "agent_role": analysis.get("role", ""),
            "key_metrics": self._extract_key_metrics(module, result_data, language),
            "well_name": well_name,
            "language": language,
            "provider_used": provider,
        }

    def _extract_key_metrics(self, module: str, result_data: Dict, language: str = "en") -> List[Dict]:
        """Extract key performance indicators per module for the executive report."""
        if module == "torque_drag":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Hookload", language), "value": summary.get("surface_hookload_klb", 0), "unit": "klb"},
                {"label": self._ml("Torque", language), "value": summary.get("surface_torque_ftlb", 0), "unit": "ft-lb"},
                {"label": self._ml("Max Side Force", language), "value": summary.get("max_side_force_lb", 0), "unit": "lb"},
                {"label": self._ml("Buoyancy Factor", language), "value": summary.get("buoyancy_factor", 0), "unit": ""},
            ]

        elif module == "hydraulics":
            hyd = result_data.get("hydraulics", {})
            surge = result_data.get("surge", {})
            summary = hyd.get("summary", {})
            return [
                {"label": self._ml("ECD at TD", language), "value": summary.get("ecd_at_td_ppg", 0), "unit": "ppg"},
                {"label": self._ml("Total SPP", language), "value": summary.get("total_system_pressure_psi", 0), "unit": "psi"},
                {"label": self._ml("HSI", language), "value": summary.get("hsi", 0), "unit": ""},
                {"label": self._ml("% at Bit", language), "value": summary.get("percent_at_bit", 0), "unit": "%"},
                {"label": self._ml("Surge Margin", language), "value": surge.get("surge_margin", "N/A"), "unit": ""},
            ]

        elif module == "stuck_pipe":
            diagnosis = result_data.get("diagnosis", {})
            risk = result_data.get("risk", {})
            free_point = result_data.get("freePoint", {})
            return [
                {"label": self._ml("Mechanism", language), "value": diagnosis.get("mechanism", "N/A"), "unit": ""},
                {"label": self._ml("Risk Level", language), "value": risk.get("risk_level", "N/A"), "unit": ""},
                {"label": self._ml("Risk Score", language), "value": risk.get("risk_score", 0), "unit": ""},
                {"label": self._ml("Free Point", language), "value": free_point.get("free_point_depth_ft", "N/A"), "unit": "ft"},
            ]

        elif module == "well_control":
            kill = result_data.get("kill", {})
            return [
                {"label": self._ml("Pf", language), "value": kill.get("formation_pressure_psi", 0), "unit": "psi"},
                {"label": self._ml("KMW", language), "value": kill.get("kill_mud_weight_ppg", 0), "unit": "ppg"},
                {"label": self._ml("ICP", language), "value": kill.get("icp_psi", 0), "unit": "psi"},
                {"label": self._ml("FCP", language), "value": kill.get("fcp_psi", 0), "unit": "psi"},
                {"label": self._ml("MAASP", language), "value": kill.get("maasp_psi", 0), "unit": "psi"},
                {"label": self._ml("Influx Type", language), "value": kill.get("influx_type", "N/A"), "unit": ""},
            ]

        elif module == "wellbore_cleanup":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Annular Velocity", language), "value": summary.get("annular_velocity_ftmin", 0), "unit": "ft/min"},
                {"label": self._ml("CTR", language), "value": summary.get("cuttings_transport_ratio", 0), "unit": ""},
                {"label": self._ml("HCI", language), "value": summary.get("hole_cleaning_index", 0), "unit": ""},
                {"label": self._ml("Cleaning Quality", language), "value": summary.get("cleaning_quality", "N/A"), "unit": ""},
                {"label": self._ml("Cuttings Concentration", language), "value": summary.get("cuttings_concentration_pct", 0), "unit": "%"},
            ]

        elif module == "packer_forces":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Total Force", language), "value": summary.get("total_force_lbs", 0), "unit": "lbs"},
                {"label": self._ml("Piston Force", language), "value": summary.get("piston_force_lbs", 0), "unit": "lbs"},
                {"label": self._ml("Temperature Force", language), "value": summary.get("temperature_force_lbs", 0), "unit": "lbs"},
                {"label": self._ml("Buckling Status", language), "value": summary.get("buckling_status", "N/A"), "unit": ""},
            ]

        elif module == "workover_hydraulics":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Total Pressure Loss", language), "value": summary.get("total_pressure_loss_psi", 0), "unit": "psi"},
                {"label": self._ml("Buoyed Weight", language), "value": summary.get("buoyed_weight_lb", 0), "unit": "lb"},
                {"label": self._ml("Snubbing Force", language), "value": summary.get("snubbing_force_lb", 0), "unit": "lb"},
                {"label": self._ml("Max Reach", language), "value": summary.get("max_reach_ft", 0), "unit": "ft"},
                {"label": self._ml("Kill Weight", language), "value": summary.get("kill_weight_ppg", 0), "unit": "ppg"},
                {"label": self._ml("Pipe Light", language), "value": summary.get("pipe_light", "N/A"), "unit": ""},
            ]

        elif module == "sand_control":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("D50", language), "value": summary.get("d50_mm", 0), "unit": "mm"},
                {"label": self._ml("Sanding Risk", language), "value": summary.get("sanding_risk", "N/A"), "unit": ""},
                {"label": self._ml("Critical Drawdown", language), "value": summary.get("critical_drawdown_psi", 0), "unit": "psi"},
                {"label": self._ml("Recommended Gravel", language), "value": summary.get("recommended_gravel", "N/A"), "unit": ""},
                {"label": self._ml("Skin Total", language), "value": summary.get("skin_total", 0), "unit": ""},
                {"label": self._ml("Recommended Completion", language), "value": summary.get("recommended_completion", "N/A"), "unit": ""},
            ]

        elif module == "cementing":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Total Cement", language), "value": summary.get("total_cement_bbl", 0), "unit": "bbl"},
                {"label": self._ml("Max ECD", language), "value": summary.get("max_ecd_ppg", 0), "unit": "ppg"},
                {"label": self._ml("Fracture Margin", language), "value": summary.get("fracture_margin_ppg", 0), "unit": "ppg"},
                {"label": self._ml("Job Time", language), "value": summary.get("job_time_hrs", 0), "unit": "hrs"},
                {"label": self._ml("Free-Fall", language), "value": summary.get("free_fall_ft", 0), "unit": "ft"},
                {"label": self._ml("Lift Pressure", language), "value": summary.get("lift_pressure_psi", 0), "unit": "psi"},
            ]

        elif module == "casing_design":
            summary = result_data.get("summary", {})
            return [
                {"label": self._ml("Selected Grade", language), "value": summary.get("selected_grade", "N/A"), "unit": ""},
                {"label": self._ml("SF Burst", language), "value": summary.get("sf_burst", 0), "unit": ""},
                {"label": self._ml("SF Collapse", language), "value": summary.get("sf_collapse", 0), "unit": ""},
                {"label": self._ml("SF Tension", language), "value": summary.get("sf_tension", 0), "unit": ""},
                {"label": self._ml("Triaxial Status", language), "value": summary.get("triaxial_status", "N/A"), "unit": ""},
                {"label": self._ml("Overall Status", language), "value": summary.get("overall_status", "N/A"), "unit": ""},
            ]

        elif module == "daily_report":
            from orchestrator.ddr_engine import DDREngine
            return DDREngine.generate_daily_kpis(result_data)

        return []
