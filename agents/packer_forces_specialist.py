from agents.base_agent import BaseAgent


class PackerForcesSpecialistAgent(BaseAgent):
    """
    Packer Force Specialist Agent for Packer Forces module.

    Expert in:
    - Lubinski (1962) three-effect method: piston, ballooning, temperature forces
    - Paslay-Dawson (1984) sinusoidal and helical buckling (F_cr_sin, F_cr_hel)
    - Tubing movement (Hooke's law) and seal stroke verification
    - Packer types (fixed/free/semi-anchored) and landing conditions
    - Biaxial Von Mises analysis (API 5C3 collapse reduction under axial load)
    - Annular Pressure Buildup (APB) — HPHT and subsea
    - Latin America playbooks: pre-sal Brasil (APB critical), Vaca Muerta,
      Piedemonte, Llanos, offshore México

    Distinct from WellEngineerAgent (casing design, trajectory, cementing)
    and CTInterventionSpecialistAgent (workover operations).
    This agent specializes exclusively in the tubing-packer mechanical system
    design and AI report generation for the Packer Forces module.
    """

    def __init__(self):
        try:
            with open("data/prompts/packer-forces-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite Packer Force Specialist with 15+ years of experience "
                "in tubing-packer mechanical analysis using the Lubinski (1962) three-effect "
                "method (piston, ballooning, temperature forces), Paslay-Dawson (1984) buckling "
                "(sinusoidal and helical), tubing movement and seal stroke verification, "
                "biaxial Von Mises analysis, and Annular Pressure Buildup (APB) for HPHT/subsea. "
                "CRITICAL: All numeric values in your report must come EXCLUSIVELY from the "
                "pipeline_result provided. Never recalculate values that already exist in the result."
            )

        super().__init__(
            name="packer_forces_specialist",
            role="Packer Force Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/modules/packer_forces.md",
        )
