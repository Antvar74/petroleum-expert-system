"""
Drilling Engineer / Company Man Agent
Elite expert system for drilling operations, RCA, and well delivery
"""

# System prompt for the Drilling Engineer / Company Man agent
# System prompt for the Drilling Engineer / Company Man agent
# Now loaded from data/prompts/drilling-engineer-specialist.md
DRILLING_ENGINEER_PROMPT = "You are an elite Drilling Engineer / Company Man."


from agents.base_agent import BaseAgent

class DrillingEngineerAgent(BaseAgent):
    """
    Drilling Engineer / Company Man Agent
    Elite expert system for drilling operations, RCA, and well delivery
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/drilling-engineer-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Drilling Engineer / Company Man."

        super().__init__(
            name="drilling_engineer",
            role="Drilling Engineer / Company Man",
            system_prompt=system_prompt,
            knowledge_base_path="./knowledge/drilling"
        )
    def analyze_problem(self, problem_description: str) -> dict:
        """
        Analyze a drilling problem using the expert system prompt.
        
        Args:
            problem_description: Description of the drilling problem
            
        Returns:
            dict: Analysis results with formatted query for LLM
        """
        return self.analyze_interactive(problem_description)

# Keep the original prompt variable available for other modules if needed
# DRILLING_ENGINEER_PROMPT is defined above

