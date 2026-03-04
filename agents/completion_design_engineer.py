from agents.base_agent import BaseAgent


class CompletionDesignEngineerAgent(BaseAgent):
    """
    Completion Engineer Specialist Agent for Completion Design module.

    Expert in:
    - Production tubing design and material selection (API 5CT, CRA alloys)
    - Packer and barrier systems (SCSSV, TRSV/WRSV per API 14A/14B)
    - Sand control design (Gravel Pack, Frac-Pack, Standalone Screen)
    - Hydraulic fracturing design (DFIT, PKN/KGD/P3D models, plug & perf)
    - Matrix acidizing (wormholing theory, diversion techniques)
    - Artificial lift selection and diagnosis (ESP, GL, BRP, PCP)
    - Workover and intervention (CT, wireline, snubbing, fishing)
    - Completion RCA forensics (failure modes, scale, corrosion)
    - Latin America playbooks (Vaca Muerta, pre-sal, Piedemonte, Orinoco)

    Distinct from CompletionEngineerAgent (completion-petrophysics-specialist),
    which handles perforation design, Karakas-Tariq skin, and shot efficiency.
    This agent specializes in the mechanical completion design and AI report
    generation for the Completion Design module.
    """

    def __init__(self):
        try:
            with open("data/prompts/completion-engineer-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite Completion Engineer Specialist with 15+ years of experience "
                "in production tubing design, sand control, hydraulic fracturing, acidizing, "
                "artificial lift selection, workover interventions, and completion RCA forensics. "
                "You cover Latam operations: Vaca Muerta, pre-sal Brasil, Piedemonte, Orinoco. "
                "CRITICAL: All numeric values in your report must come EXCLUSIVELY from the "
                "pipeline_result provided. Never recalculate values that already exist in the result."
            )

        super().__init__(
            name="completion_design_engineer",
            role="Completion Engineer Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/completion/"
        )
