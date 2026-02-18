from typing import Dict, List, Optional, Any
from .coordinator import StuckPipeCoordinator
from models import OperationalProblem, AnalysisResult
from utils.llm_gateway import LLMGateway

class APICoordinator(StuckPipeCoordinator):
    """
    Coordinator variant for API usage.
    Avoids interactive CLI prints and inputs.
    """
    
    def __init__(self):
        super().__init__()
        self.gateway = LLMGateway()

    async def run_automated_step(self, agent_id: str, problem_description: str, context: Optional[Dict] = None, provider: str = "auto") -> Dict[str, Any]:
        """
        Run a single analysis step automatically using the LLM Gateway (Mode: Fast).
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        agent = self.agents[agent_id]
        # Generate the prompt
        analysis = agent.analyze_interactive(problem_description, context)

        # Call the LLM Gateway (Fast Mode for individual agents)
        response_text = await self.gateway.generate_analysis(
            prompt=analysis["query"],
            system_prompt=None,
            mode="fast",
            provider=provider
        )
        
        # Process and set response
        agent.set_response(analysis, response_text)
        return analysis

    async def run_automated_audit(self, methodology: str, user_data: Any, context: Dict) -> Dict[str, Any]:
        """
        Run the RCA audit automatically using the LLM Gateway (Mode: Reasoning).
        """
        agent = self.agents["rca_lead"]
        
        # Generate the prompt using the new audit method
        analysis = agent.audit_investigation(methodology, user_data, context)
        
        # Call the LLM Gateway (Reasoning Mode for deep logic check)
        response_text = await self.gateway.generate_analysis(
            prompt=analysis["query"],
            system_prompt=None,
            mode="reasoning"
        )
        
        # Process and set response
        agent.set_response(analysis, response_text)
        return analysis

    async def run_automated_synthesis(self, problem: OperationalProblem, analyses: List[Dict], leader_agent_id: str = "drilling_engineer") -> Dict[str, Any]:
        """
        Run the final synthesis automatically using the LLM Gateway.
        """
        query = self.get_synthesis_query(problem, analyses, leader_agent_id)
        
        # Reasoning mode for final synthesis
        response_text = await self.gateway.generate_analysis(prompt=query, mode="reasoning")
        
        leader_agent = self.agents.get(leader_agent_id, self.agents["drilling_engineer"])
        confidence = leader_agent._extract_confidence(response_text)
        
        return {
            "agent": leader_agent_id,
            "role": f"{leader_agent.role} (Synthesis Leader)",
            "analysis": response_text,
            "confidence": confidence
        }

    async def run_automated_program(self, program_type: str, well_name: str, additional_data: Optional[Dict] = None) -> str:
        """
        Generates a full technical program (DDP/CP/WO) automatically.
        """
        prompt = self.get_program_prompt(program_type, well_name, additional_data)
        
        # Reasoning mode for complex program generation
        response_text = await self.gateway.generate_analysis(
            prompt=prompt,
            system_prompt="Eres un Ingeniero de Perforación y Completación de nivel Élite con 30 años de experiencia.",
            mode="reasoning"
        )
        return response_text

    def get_program_prompt(self, program_type: str, well_name: str, additional_data: Optional[Dict] = None) -> str:
        """
        Constructs the detailed prompt for generating a technical program.
        """
        templates = {
            "drilling": f"Genera un Programa Digital de Perforación (DDP) detallado para el pozo {well_name}.",
            "completion": f"Genera un Programa de Completación (CP) detallado para el pozo {well_name}.",
            "workover": f"Genera un Programa de Intervención/Workover detallado para el pozo {well_name}."
        }
        
        base_prompt = templates.get(program_type, templates["drilling"])
        
        sections = """
        Incluye las siguientes secciones:
        1. Objetivos del Pozo y Resumen Ejecutivo.
        2. Diseño de Casing y Programa de Cementación.
        3. Programa de Fluidos de Perforación/Completación.
        4. Selección de Barrenas e Hidráulica.
        5. Sartas de Perforación/Completación y BHA.
        6. Evaluación de Formación (Registros, Cores).
        7. Consideraciones de Seguridad y Contingencias.
        """
        
        data_str = ""
        if additional_data:
            data_str = "\n# DATOS ADICIONALES SUMINISTRADOS:\n" + json.dumps(additional_data, indent=2)
            
        return f"{base_prompt}\n{sections}\n{data_str}\n\nResponde en formato Markdown profesional con lenguaje técnico de alto nivel."

    def get_agent_query(self, agent_id: str, problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate a query for a specific agent without interactive prompts"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        analysis = agent.analyze_interactive(problem_description, context)
        return analysis

    def process_agent_response(self, agent_id: str, analysis: Dict[str, Any], response_text: str) -> Dict[str, Any]:
        """Process an agent's response and update the analysis dict"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        agent.set_response(analysis, response_text)
        return analysis

    def get_synthesis_query(self, problem: OperationalProblem, analyses: List[Dict], leader_id: str = "drilling_engineer") -> str:
        """Expose the internal synthesis query generator"""
        return self._generate_synthesis_query(problem, analyses, leader_id)
        
    def get_workflow(self, workflow_type: str = "standard") -> List[str]:
        """Return the list of agent IDs for a workflow"""
        if workflow_type == "standard":
            return self.standard_workflow
        return list(self.agents.keys())
