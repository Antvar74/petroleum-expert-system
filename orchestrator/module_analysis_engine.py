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
    },
    "es": {
        "Hookload": "Carga en Gancho", "Torque": "Torque", "Max Side Force": "Fuerza Lateral Máx",
        "Buoyancy Factor": "Factor de Flotación", "ECD at TD": "ECD en TD", "Total SPP": "SPP Total",
        "HSI": "HSI", "% at Bit": "% en Barrena", "Surge Margin": "Margen de Surgencia",
        "Mechanism": "Mecanismo", "Risk Level": "Nivel de Riesgo", "Risk Score": "Puntaje de Riesgo",
        "Free Point": "Punto Libre", "Pf": "Pf", "KMW": "PMM", "ICP": "PCI", "FCP": "PCF",
        "MAASP": "MAASP", "Influx Type": "Tipo de Influjo",
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

        return []
