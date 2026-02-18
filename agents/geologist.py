"""
Geologist Agent
Specialized agent for formation characterization and wellbore stability
"""

from agents.base_agent import BaseAgent
from typing import Dict


class GeologistAgent(BaseAgent):
    """
    Geologist / Petrophysicist agent
    Expert in formation characterization and rock mechanics
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/geologist-petrophysicist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Geologist / Petrophysicist."
        super().__init__(
            name="geologist",
            role="Geologist / Petrophysicist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/geology/"
        )

    def analyze_formation_stability(self, formation_data: Dict, exposure_time: float) -> Dict:
        """
        Analyze formation stability over time
        
        Args:
            formation_data: Formation properties
            exposure_time: Hours of exposure
            
        Returns:
            Stability analysis
        """
        problem = f"""
Analiza la estabilidad de la formación:

DATOS DE FORMACIÓN:
- Litología: {formation_data.get('lithology', 'N/A')}
- Edad geológica: {formation_data.get('age', 'N/A')}
- Propiedades mecánicas: {formation_data.get('mechanical_properties', 'N/A')}
- Mineralogía: {formation_data.get('mineralogy', 'N/A')}

EXPOSICIÓN:
- Tiempo de exposición: {exposure_time} horas

Evalúa:
1. ¿Qué tipo de inestabilidad es más probable?
2. ¿Cómo evoluciona con el tiempo de exposición?
3. ¿Qué medidas preventivas o correctivas recomiendas?
"""
        context = {"formation_data": formation_data}
        return self.analyze(problem, context)
    
    def identify_keyseat_risk(self, trajectory_data: Dict, lithology_log: Dict) -> Dict:
        """
        Identify keyseat formation risk
        
        Args:
            trajectory_data: Well trajectory information
            lithology_log: Lithology changes with depth
            
        Returns:
            Keyseat risk analysis
        """
        problem = f"""
Evalúa el riesgo de formación de keyseats:

TRAYECTORIA:
- DLS máximo: {trajectory_data.get('max_dls', 'N/A')}°/100ft
- Inclinación: {trajectory_data.get('inclination', 'N/A')}°
- Build rate: {trajectory_data.get('build_rate', 'N/A')}°/100ft

LITOLOGÍA:
{lithology_log}

Analiza:
1. ¿Dónde es más probable la formación de keyseats?
2. ¿Qué litologías son más propensas?
3. ¿Qué estrategias de mitigación recomiendas?
"""
        context = {
            "trajectory_data": trajectory_data,
            "lithology_log": lithology_log
        }
        return self.analyze(problem, context)
