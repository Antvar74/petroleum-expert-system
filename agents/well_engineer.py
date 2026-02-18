"""
Well Engineer Agent
Specialized agent for well design, trajectory, and torque/drag modeling
"""

from agents.base_agent import BaseAgent
from typing import Dict


class WellEngineerAgent(BaseAgent):
    """
    Well Engineer / Trajectory Specialist agent
    Expert in well design and torque/drag analysis
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/well-engineer-trajectory-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Well Engineer / Trajectory Specialist."
        
        super().__init__(
            name="well_engineer",
            role="Well Engineer / Trajectory Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/well_design/"
        )
    def analyze_trajectory_quality(self, survey_data: Dict) -> Dict:
        """
        Analyze trajectory quality and smoothness
        
        Args:
            survey_data: Directional survey data
            
        Returns:
            Trajectory quality analysis
        """
        problem = f"""
Analiza la calidad de la trayectoria del pozo:

DATOS DE SURVEYS:
{survey_data}

Evalúa:
1. ¿La trayectoria ejecutada es suave o tiene problemas?
2. ¿Dónde están los DLS más altos y por qué?
3. ¿Hay evidencia de spiraling o tortuosidad?
4. ¿Qué impacto tiene en operaciones de perforación?
5. ¿Qué mejoras recomiendas para futuros pozos?
"""
        context = {"survey_data": survey_data}
        return self.analyze(problem, context)
    
    def compare_torque_drag_model(self, model_data: Dict, actual_data: Dict) -> Dict:
        """
        Compare torque/drag model predictions vs actual measurements
        
        Args:
            model_data: Predicted values from software
            actual_data: Actual measured values
            
        Returns:
            Comparison analysis
        """
        problem = f"""
Compara el modelo de torque/drag con datos reales:

MODELO PREDICTIVO:
- Hookload picking up: {model_data.get('hookload_pu', 'N/A')} lbs
- Hookload slacking off: {model_data.get('hookload_so', 'N/A')} lbs
- Torque rotando: {model_data.get('torque_rotating', 'N/A')} klb-ft
- Factores de fricción usados: {model_data.get('friction_factors', 'N/A')}

DATOS REALES:
- Hookload picking up: {actual_data.get('hookload_pu', 'N/A')} lbs
- Hookload slacking off: {actual_data.get('hookload_so', 'N/A')} lbs
- Torque rotando: {actual_data.get('torque_rotating', 'N/A')} klb-ft

Analiza:
1. ¿Qué tan precisas fueron las predicciones?
2. ¿Qué factores de fricción reales se observan?
3. ¿Hay zonas específicas con fricción excesiva?
4. ¿Qué ajustes recomiendas al modelo?
"""
        context = {
            "model_data": model_data,
            "actual_data": actual_data
        }
        return self.analyze(problem, context)
    
    def evaluate_sidetrack_options(self, problem_depth: float, well_data: Dict) -> Dict:
        """
        Evaluate sidetrack options
        
        Args:
            problem_depth: Depth where problem occurred
            well_data: Complete well data
            
        Returns:
            Sidetrack evaluation
        """
        problem = f"""
Evalúa opciones de sidetrack:

PROBLEMA:
- Profundidad del problema: {problem_depth} ft MD

DATOS DEL POZO:
{well_data}

Proporciona:
1. Profundidad óptima de kickoff para sidetrack
2. Trayectoria propuesta del nuevo pozo
3. Estrategia para evitar zona problemática
4. Análisis de viabilidad técnica
5. Estimado de tiempo adicional requerido
6. Consideraciones de costo
"""
        context = {"well_data": well_data}
        return self.analyze(problem, context)
