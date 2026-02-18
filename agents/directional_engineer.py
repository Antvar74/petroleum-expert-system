from agents.base_agent import BaseAgent

class DirectionalEngineerAgent(BaseAgent):
    """
    Directional Engineer Specialist Agent
    
    Expert in:
    - Trajectory Design & Optimization
    - BHA Design & Performance
    - Anti-Collision Analysis (ISCWSA)
    - Real-Time Geosteering
    - Survey Management
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/directional-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Directional Engineer Specialist."
            
        super().__init__(
            name="directional_engineer",
            role="Directional Engineer Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/directional/"
        )
