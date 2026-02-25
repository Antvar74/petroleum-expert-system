from agents.base_agent import BaseAgent


class CompletionEngineerAgent(BaseAgent):
    """
    Completion Engineer / Petrophysics Specialist Agent

    Expert in:
    - Perforation Design & Karakas-Tariq Skin Analysis (SPE 18247)
    - Composite Interval Scoring & Net Pay Identification
    - Petrophysical Models (Archie, Simandoux, Indonesia)
    - IPR / Productivity Optimization
    - Shot Efficiency Analysis
    """

    def __init__(self):
        try:
            with open("data/prompts/completion-petrophysics-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite Completion Engineer and Petrophysics Specialist "
                "with 15+ years of experience in perforation design, skin analysis, "
                "Karakas-Tariq modeling, IPR optimization, and formation evaluation."
            )

        super().__init__(
            name="completion_engineer",
            role="Completion Engineer / Petrophysics Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/completion/"
        )
