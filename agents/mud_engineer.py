"""
Mud Engineer Agent
Specialized agent for drilling fluids and hydraulics analysis
"""

from agents.base_agent import BaseAgent
from typing import Dict


class MudEngineerAgent(BaseAgent):
    """
    Mud Engineer / Fluids Specialist agent
    Expert in drilling fluids properties and hydraulics
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/mud-engineer-fluids-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Mud Engineer / Drilling Fluids Specialist."
        super().__init__(
            name="mud_engineer",
            role="Mud Engineer / Fluids Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/fluids/"
        )

    def analyze_differential_sticking_risk(self, mud_data: Dict, pressure_data: Dict) -> Dict:
        """
        Analyze differential sticking risk
        
        Args:
            mud_data: Mud properties data
            pressure_data: Pressure data from hydrologist
            
        Returns:
            Risk analysis dictionary
        """
        problem = f"""
Evalúa el riesgo de differential sticking con los siguientes datos:

PROPIEDADES DEL LODO:
- Tipo de lodo: {mud_data.get('type', 'N/A')}
- Densidad: {mud_data.get('density_ppg', 'N/A')} ppg
- Viscosidad Marsh: {mud_data.get('funnel_viscosity', 'N/A')} seg
- PV: {mud_data.get('pv', 'N/A')} cp
- YP: {mud_data.get('yp', 'N/A')} lb/100ft²
- Filtrado API: {mud_data.get('api_filtrate', 'N/A')} ml
- Espesor de cake: {mud_data.get('cake_thickness_32nds', 'N/A')}/32"

DATOS DE PRESIÓN:
- Presión de poro: {pressure_data.get('pore_pressure_ppg', 'N/A')} ppg EMW
- Presión hidrostática: {pressure_data.get('hydrostatic_ppg', 'N/A')} ppg
- Sobrebalance: {pressure_data.get('overbalance_psi', 'N/A')} psi

Proporciona:
1. Evaluación cuantitativa del riesgo
2. Propiedades del lodo que requieren ajuste
3. Tratamiento recomendado
4. Procedimiento de prevención
"""
        context = {
            "mud_data": mud_data,
            "pressure_data": pressure_data
        }
        return self.analyze(problem, context)
    
    def analyze_hole_cleaning(self, drilling_params: Dict, mud_properties: Dict) -> Dict:
        """
        Analyze hole cleaning efficiency
        
        Args:
            drilling_params: Drilling parameters (ROP, RPM, flow rate, etc.)
            mud_properties: Current mud properties
            
        Returns:
            Hole cleaning analysis
        """
        problem = f"""
Analiza la eficiencia de limpieza del pozo:

PARÁMETROS DE PERFORACIÓN:
- ROP: {drilling_params.get('rop_ft_hr', 'N/A')} ft/hr
- Flow rate: {drilling_params.get('flow_rate_gpm', 'N/A')} gpm
- RPM: {drilling_params.get('rpm', 'N/A')}
- Inclinación: {drilling_params.get('inclination_deg', 'N/A')}°

PROPIEDADES DEL LODO:
- Densidad: {mud_properties.get('density_ppg', 'N/A')} ppg
- PV: {mud_properties.get('pv', 'N/A')} cp
- YP: {mud_properties.get('yp', 'N/A')} lb/100ft²

Evalúa:
1. ¿La velocidad anular es suficiente?
2. ¿Hay riesgo de acumulación de recortes?
3. ¿Qué ajustes recomiendas en flujo o propiedades?
"""
        context = {
            "drilling_params": drilling_params,
            "mud_properties": mud_properties
        }
        return self.analyze(problem, context)
