from agents.base_agent import BaseAgent


class CTInterventionSpecialistAgent(BaseAgent):
    """
    CT & Well Intervention Engineer Agent for Workover Hydraulics module.

    Expert in:
    - CT hydraulics (Bingham plastic pressure loss, ECD, solid transport)
    - CT mechanics: Lubinski/Hammerlindl 4-component elongation model
    - CT fatigue life: API RP 5C7 / Miner's rule, ICoTA reel standards
    - CT forces: buoyed weight, drag, snubbing, pipe-light/heavy conditions
    - Helical/sinusoidal buckling (Dawson-Paslay, Chen) and max reach calculation
    - Well control in CT/workover operations (IWCF Level 4): kill weight,
      bullheading, forward/reverse circulation, stripping, BOP stack
    - CT burst rating (API 5C7: 0.875 × 2 × Fy × wall / OD)
    - Specialized CT operations: milling, perforating, acidizing, N2 lift, fishing
    - Latin America playbooks: Vaca Muerta, pre-sal Brasil, Piedemonte, Orinoco,
      offshore Mexico (Ku-Maloob-Zaap, Cantarell)

    Distinct from WellEngineerAgent (casing design, trajectory, cementing).
    This agent specializes exclusively in CT/workover operations and AI report
    generation for the Workover Hydraulics module.
    """

    def __init__(self):
        try:
            with open("data/prompts/ct-intervention-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite CT & Well Intervention Engineer with 15+ years of experience "
                "in coiled tubing hydraulics, CT mechanics (Lubinski elongation), CT fatigue "
                "(API RP 5C7 / Miner's rule), helical buckling and max reach calculations, "
                "well control in CT/workover operations (IWCF Level 4), and CT burst rating. "
                "CRITICAL: All numeric values in your report must come EXCLUSIVELY from the "
                "pipeline_result provided. Never recalculate values that already exist in the result."
            )

        super().__init__(
            name="ct_intervention_specialist",
            role="CT & Well Intervention Engineer",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/modules/workover_hydraulics.md"
        )
