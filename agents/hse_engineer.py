from agents.base_agent import BaseAgent

class HSEEngineerAgent(BaseAgent):
    """
    HSE & Process Safety Specialist Agent
    
    Expert in:
    - Process Safety Management (PSM)
    - Barrier Analysis (Bow-Tie)
    - Human Factors Engineering
    - Compliance & Safety Culture
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("docs/hse-safety-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite HSE & Process Safety Specialist."
            
        super().__init__(
            name="hse_engineer",
            role="HSE & Process Safety Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/hse/"
        )
