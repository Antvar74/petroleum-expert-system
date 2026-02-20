"""
Stuck Pipe Coordinator (Interactive Mode - No API)
Orchestrates multiple specialized agents to analyze operational problems
"""

from typing import Dict, List, Optional
from agents import (
    DrillingEngineerAgent,
    MudEngineerAgent,
    GeologistAgent,
    WellEngineerAgent,
    HydrologistAgent
)
from agents.rca_lead import RCALeadAgent
from agents.cementing_engineer import CementingEngineerAgent
from agents.optimization_engineer import OptimizationEngineerAgent
from agents.hse_engineer import HSEEngineerAgent
from agents.geomechanic_engineer import GeomechanicsEngineerAgent
from agents.directional_engineer import DirectionalEngineerAgent
from models import OperationalProblem, AnalysisResult
import json


class StuckPipeCoordinator:
    """Coordinates analysis across multiple specialized agents in interactive mode"""
    
    def __init__(self):
        """Initialize all specialized agents"""
        self.agents = {
            "drilling_engineer": DrillingEngineerAgent(),
            "mud_engineer": MudEngineerAgent(),
            "geologist": GeologistAgent(),
            "well_engineer": WellEngineerAgent(),
            "hydrologist": HydrologistAgent(),
            "rca_lead": RCALeadAgent(),
            "cementing_engineer": CementingEngineerAgent(),
            "optimization_engineer": OptimizationEngineerAgent(),
            "hse_engineer": HSEEngineerAgent(),
            "geomechanic_engineer": GeomechanicsEngineerAgent(),
            "directional_engineer": DirectionalEngineerAgent()
        }
        
        # Standard workflow for stuck pipe analysis
        # NOTE: rca_lead appears only once here. The final synthesis is handled
        # separately by the /synthesis/auto endpoint using the designated leader.
        self.standard_workflow = [
            "rca_lead",           # 1. Incident Classification (Level 1-3)
            "drilling_engineer",  # 2. General evaluation and leadership
            "hydrologist",        # 3. Pressures (input for mud engineer)
            "geologist",          # 4. Formations (input for all)
            "mud_engineer",       # 5. Fluids (with pressure and geo context)
            "well_engineer",      # 6. Trajectory and design (final synthesis)
        ]
    
    def _generate_synthesis_query(self, problem: OperationalProblem, analyses: List[Dict], leader_id: str = "drilling_engineer") -> str:
        """
        Generate query for final synthesis by the Leader Agent
        
        Args:
            problem: The operational problem
            analyses: List of all specialist analyses
            leader_id: The ID of the agent leading the investigation
            
        Returns:
            Formatted query string for synthesis
        """
        leader_agent = self.agents.get(leader_id, self.agents["drilling_engineer"])
        leader_role = leader_agent.role
        
        query = f"""Como {leader_role} y LÍDER OFICIAL del análisis, genera una síntesis ejecutiva integrando los hallazgos de todo el equipo.
Tu responsabilidad es dirigir la conclusión final y establecer el plan de acción definitivo.

# PROBLEMA ANALIZADO:
{problem.description}

# ANÁLISIS DE LOS ESPECIALISTAS:

"""
        
        for analysis in analyses:
            query += f"## {analysis['role']}:\n"
            query += f"{analysis.get('analysis', 'No disponible')}\n"
            query += f"**Confianza:** {analysis.get('confidence', 'N/A')}\n\n"
        
        query += """
# ESTRUCTURA DE LA SÍNTESIS:

1. **Executive Summary**: Diagnóstico principal en 2-3 líneas (Redactado como Líder)
2. **Root Cause Analysis**: Causa raíz identificada con confianza
3. **Contributing Factors**: Factores secundarios por disciplina
4. **Integrated Assessment**: Cómo interactúan los factores
5. **Immediate Action Plan**: Pasos de liberación priorizados
6. **Preventive Measures**: Recomendaciones por disciplina
7. **Lessons Learned**: Key takeaways para operaciones futuras
8. **Overall Confidence**: HIGH/MEDIUM/LOW con justificación

Sé específico, técnico y accionable. Resuelve contradicciones entre especialistas si existen.
"""
        
        return query