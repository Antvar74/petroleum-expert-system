from agents.base_agent import BaseAgent

class OptimizationEngineerAgent(BaseAgent):
    """
    Drilling Optimization & Mechanics Specialist Agent
    
    Expert in:
    - ROP Maximization
    - Mechanical Specific Energy (MSE)
    - Vibration Analysis (Stick-slip, Whirl)
    - Bit Selection & Dismantling
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("docs/drilling-optimization-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Drilling Optimization Specialist."
            
        super().__init__(
            name="optimization_engineer",
            role="Drilling Optimization Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/optimization/"
        )
