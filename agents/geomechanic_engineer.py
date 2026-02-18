from agents.base_agent import BaseAgent

class GeomechanicsEngineerAgent(BaseAgent):
    """
    Geomechanics Specialist Agent
    
    Expert in:
    - Wellbore Stability Analysis
    - Pore Pressure & Fracture Gradient Prediction
    - Mud Weight Window Optimization
    - Casing & Cement Integrity Assessment
    - Sand Production Prediction
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/geomechanics-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Geomechanics Specialist."
            
        super().__init__(
            name="geomechanic_engineer",
            role="Geomechanics Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/geomechanics/"
        )
