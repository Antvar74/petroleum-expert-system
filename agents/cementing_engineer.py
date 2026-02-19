from agents.base_agent import BaseAgent


class CementingEngineerAgent(BaseAgent):
    """
    Cementing & Zonal Isolation Specialist Agent

    Expert in:
    - Slurry Design & Chemistry (Nelson & Guillot)
    - Displacement Mechanics & ECD Management
    - Barrier Evaluation (CBL/VDL)
    - Casing Design (API TR 5C3 / ISO 10400)
    - Zonal Isolation Forensics
    - Free-Fall & U-Tube Equilibrium
    """

    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/cementing-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Cementing & Zonal Isolation Specialist."

        super().__init__(
            name="cementing_engineer",
            role="Cementing & Zonal Isolation Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/cementing/"
        )
