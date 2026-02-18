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
from utils.interactive_helper import (
    print_header, print_separator, print_query_box,
    get_multiline_input, show_progress, format_agent_name,
    print_success, print_warning, print_error
)
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
        self.standard_workflow = [
            "rca_lead",           # 1. Incident Classification (Level 1-3)
            "drilling_engineer",  # 2. General evaluation and leadership
            "hydrologist",        # 3. Pressures (input for mud engineer)
            "geologist",          # 4. Formations (input for all)
            "mud_engineer",       # 5. Fluids (with pressure and geo context)
            "well_engineer",      # 6. Trajectory and design (final synthesis)
            "rca_lead"            # 7. Final Report Synthesis (API RP 585)
        ]
    
    def analyze_stuck_pipe_interactive(self, problem: OperationalProblem) -> AnalysisResult:
        """
        Orchestrate complete analysis with all specialists (interactive mode)
        
        Args:
            problem: The operational problem to analyze
            
        Returns:
            AnalysisResult with all analyses and final synthesis
        """
        print(f"\n{'='*80}")
        print(f"INICIANDO ANÁLISIS MULTI-AGENTE")
        print(f"Pozo: {problem.well_name} | Profundidad: {problem.depth_md} ft")
        print(f"{'='*80}\n")
        
        analyses = []
        context = {
            "well_data": problem.to_dict(),
            "previous_analyses": []
        }
        
        # Execute sequential workflow
        for i, agent_name in enumerate(self.standard_workflow, 1):
            agent = self.agents[agent_name]
            
            print_header(f"PASO {i}/5: {format_agent_name(agent_name)}", "🔍")
            show_progress(i-1, 5, "Progreso general")
            
            # Generate analysis (query)
            analysis = agent.analyze_interactive(problem.description, context)
            
            # Display query to user
            print_query_box(
                f"CONSULTA PARA {agent.role.upper()}",
                analysis["query"]
            )
            
            print_separator()
            print("📋 INSTRUCCIONES:")
            print("1. COPIA la consulta de arriba (incluyendo SYSTEM PROMPT)")
            print("2. PÉGALA en Claude (Code, chat, o app)")
            print("3. COPIA la respuesta completa de Claude")
            print("4. PÉGALA aquí abajo")
            print_separator()
            
            # Get response from user
            response_text = get_multiline_input(
                f"Pega aquí la respuesta de Claude para {agent.role}:"
            )
            
            if not response_text or response_text.strip() == "":
                print_error("Respuesta vacía. Análisis cancelado.")
                return None
            
            # Set the response
            agent.set_response(analysis, response_text)
            
            analyses.append(analysis)
            context["previous_analyses"].append(analysis)
            
            print_success(f"✓ Análisis de {agent.role} completado")
            show_progress(i, 5, "Progreso general")
            print("\n")
        
        # Final synthesis by Drilling Engineer
        print_header("GENERANDO SÍNTESIS FINAL", "📊")
        print("El Drilling Engineer integrará todos los hallazgos...\n")
        
        synthesis_query = self._generate_synthesis_query(problem, analyses)
        
        print_query_box("CONSULTA DE SÍNTESIS FINAL", synthesis_query)
        
        print_separator()
        print("📋 Última consulta - Síntesis ejecutiva:")
        print_separator()
        
        synthesis_text = get_multiline_input(
            "Pega la síntesis final de Claude:"
        )
        
        final_synthesis = {
            "agent": "drilling_engineer",
            "role": "Drilling Engineer / Company Man (Synthesis)",
            "timestamp": analyses[0]["timestamp"],
            "analysis": synthesis_text,
            "confidence": self.agents["drilling_engineer"]._extract_confidence(synthesis_text)
        }
        
        # Create result
        result = AnalysisResult(
            problem=problem,
            individual_analyses=analyses,
            final_synthesis=final_synthesis,
            workflow_used=self.standard_workflow
        )
        
        return result
    
    def quick_analysis_interactive(self, problem_description: str, agents_to_consult: List[str]) -> Dict:
        """
        Quick analysis consulting only specific agents (interactive mode)
        
        Args:
            problem_description: Description of the problem
            agents_to_consult: List of agent IDs to consult
            
        Returns:
            Dictionary with analyses from selected agents
        """
        if not all(agent in self.agents for agent in agents_to_consult):
            raise ValueError(f"Invalid agents. Available: {list(self.agents.keys())}")
        
        print(f"\n{'='*80}")
        print(f"ANÁLISIS RÁPIDO")
        print(f"Consultando {len(agents_to_consult)} especialistas")
        print(f"{'='*80}\n")
        
        analyses = []
        context = {"previous_analyses": []}
        
        for i, agent_name in enumerate(agents_to_consult, 1):
            agent = self.agents[agent_name]
            
            print_header(f"ESPECIALISTA {i}/{len(agents_to_consult)}: {format_agent_name(agent_name)}", "🔍")
            
            # Generate analysis (query)
            analysis = agent.analyze_interactive(problem_description, context)
            
            # Display query
            print_query_box(
                f"CONSULTA PARA {agent.role.upper()}",
                analysis["query"]
            )
            
            print_separator()
            
            # Get response
            response_text = get_multiline_input(
                f"Pega la respuesta de Claude para {agent.role}:"
            )
            
            if response_text and response_text.strip():
                agent.set_response(analysis, response_text)
                analyses.append(analysis)
                context["previous_analyses"].append(analysis)
                print_success(f"✓ Análisis completado")
            else:
                print_warning("Respuesta vacía, saltando...")
            
            print("\n")
        
        return {
            "analyses": analyses,
            "agents_consulted": agents_to_consult
        }
    
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