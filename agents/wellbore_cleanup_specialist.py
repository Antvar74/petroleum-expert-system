from agents.base_agent import BaseAgent


class WellboreCleanupSpecialistAgent(BaseAgent):
    """
    Wellbore Cleanup Specialist Agent for Wellbore Cleanup module.

    Expert in:
    - Annular hydraulics and ECD management under API RP 13D (7th Edition, 2017)
    - Cuttings transport modeling (Moore, Larsen SPE-25872, Luo SPE-23884,
      Rubiandini SPE-57541)
    - Hole cleaning indices: HCI (Luo Transport Index), CCI (vertical wells),
      CTR (transport ratio)
    - Sweep pill design: hi-vis, weighted, tandem, turbulent — by inclination
    - Deviated/horizontal well cleaning: 30-60° critical zone, bed formation,
      avalanche risk, bed erosion
    - ECD contribution from cuttings loading and ROP limits
    - Root Cause Analysis of cleanup-related failures (packoff, stuck pipe from
      cuttings beds, ECD-induced losses, differential sticking)
    - Latin America playbooks: Vaca Muerta, Pre-Sal Brasil, Piedemonte Colombia,
      Orinoco Belt Venezuela, Offshore/Onshore Mexico

    Distinct from MudEngineerAgent (fluid formulation and properties).
    This agent specializes exclusively in cuttings transport efficiency and
    AI report generation for the Wellbore Cleanup module.
    """

    def __init__(self):
        try:
            with open("data/prompts/wellbore-cleanup-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite Wellbore Cleanup Specialist with 15+ years of experience "
                "in hole cleaning engineering using API RP 13D hydraulics, Moore/Larsen/Luo "
                "cuttings transport models, HCI/CTR analysis, sweep pill design, and ECD "
                "management. You specialize in the critical 30-60 degree zone where cuttings "
                "bed formation and avalanche risk are highest. "
                "CRITICAL: All numeric values in your report must come EXCLUSIVELY from the "
                "pipeline_result provided. Never recalculate values that already exist in the result."
            )

        super().__init__(
            name="wellbore_cleanup_specialist",
            role="Wellbore Cleanup Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/modules/wellbore_cleanup.md",
        )
