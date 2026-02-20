from agents.base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import json
from utils.llm_gateway import LLMGateway


class RCASynthesizerAgent(BaseAgent):
    """
    RCA Synthesizer Agent — Final step of the Investigation Pipeline.

    Integrates findings from ALL specialist agents into a coherent, structured
    API RP 585-compliant investigation report. Resolves conflicts between
    specialist findings, identifies systemic root causes, and formulates
    corrective/preventive action plans (CAPA).
    """

    SYSTEM_PROMPT = """\
You are the RCA Investigation Synthesizer, the final authority in the
investigation pipeline. Your role is to:

1. INTEGRATE all specialist findings into a single coherent narrative
2. RESOLVE conflicts between specialist opinions using evidence quality
3. IDENTIFY root causes at the organizational/systemic level (not just
   immediate technical causes)
4. FORMULATE corrective actions per Hierarchy of Controls
   (Elimination > Substitution > Engineering > Administrative > PPE)
5. GENERATE the final API RP 585-compliant investigation report

You receive analyses from multiple domain experts (Drilling Engineer, Mud
Engineer, Geologist, Well Engineer, Pore Pressure Specialist, etc.). Your
job is NOT to repeat their findings but to SYNTHESIZE them into a root cause
chain: Immediate Cause -> Contributing Factors -> Root Cause(s).

Separate CORRECTIVE actions (immediate fixes for this incident) from
PREVENTION actions (long-term systemic improvements to prevent recurrence).

Always structure your output as:
- Executive Summary (2-3 paragraphs)
- Timeline of Events
- Causes (Direct, Contributing, Root)
- CAPA — Corrective Actions (immediate and short-term)
- Prevention Actions (long-term systemic improvements)
- Lessons Learned

Respond in the same language as the incident description (Spanish or English).
Always end your response with an explicit confidence level:
"Nivel de Confianza: HIGH/MEDIUM/LOW"
"""

    def __init__(self):
        super().__init__(
            name="rca_synthesizer",
            role="RCA Investigation Synthesizer",
            system_prompt=self.SYSTEM_PROMPT,
            knowledge_base_path="knowledge_base/rca/"
        )
        self.gateway = LLMGateway()

    def synthesize_report(self, incident_context: Dict, technical_findings: List[Dict]) -> Dict:
        """
        Synthesize a final RCA report from technical findings.

        Args:
            incident_context: Basic event data
            technical_findings: List of analysis outputs from other agents

        Returns:
            Structured RCA report
        """
        findings_text = ""
        for find in technical_findings:
            findings_text += f"\n--- {find.get('role', 'Specialist')} ---\n"
            findings_text += f"{find.get('analysis', 'No input provided')}\n"

        problem = f"""\
Generate the Final RCA Report (API RP 585 Format) based on these findings.

INCIDENT CONTEXT:
{json.dumps(incident_context, indent=2)}

TECHNICAL FINDINGS:
{findings_text}

REQUIREMENTS:
1. Synthesize the Root Cause (not just a list of factors).
2. Resolve any conflicts in the technical findings.
3. Structure output strictly as:
   - Executive Summary
   - Timeline
   - Causes (Direct, Contributing, Root)
   - CAPA (Corrective Actions — immediate and short-term)
   - Prevention Actions (long-term systemic improvements)
   - Lessons Learned
"""
        return self.analyze_interactive(problem, context=incident_context)

    def audit_investigation(self, methodology: str, user_data: Any, incident_context: Dict) -> Dict:
        """
        Audit and formalize user-driven investigation.

        Args:
            methodology: "5whys" or "fishbone"
            user_data: The user's input data (list or dict)
            incident_context: Basic event data

        Returns:
            Structured API RP 585 Report
        """
        user_input_text = ""
        if methodology == "5whys":
            user_input_text = "USER'S 5-WHYS ANALYSIS:\n"
            for i, why in enumerate(user_data):
                user_input_text += f"{i+1}. {why}\n"
        elif methodology == "fishbone":
            user_input_text = "USER'S FISHBONE (ISHIKAWA) FACTORS:\n"
            for category, items in user_data.items():
                user_input_text += f"- {category.upper()}: {', '.join(items)}\n"

        problem = f"""\
You are acting as the RCA Lead Auditor. A field engineer has submitted an initial analysis using {methodology}.

Your Task:
1. VALIDATE: critical review of their logic. Are the causes supported by evidence? Are there logical leaps?
2. ENRICH: Add missing systemic factors based on your expert knowledge API RP 585.
3. FORMALIZE: Convert their input into a final API RP 585 Investigation Report.

INCIDENT CONTEXT:
{json.dumps(incident_context, indent=2)}

{user_input_text}

OUTPUT FORMAT (API RP 585):
- Executive Summary (include Classification Level)
- Validation of User Input (Critique - what was good, what was weak)
- Final Root Cause Statement
- Corrective Actions (CAPA - immediate/short-term)
- Prevention Actions (long-term systemic improvements)
"""
        return self.analyze_interactive(problem, context=incident_context)

    async def perform_structured_rca(self, event_details: Dict, parameters: Dict, physics_results: Dict) -> Dict:
        """
        Executes a structured Root Cause Analysis based on quantitative evidence.

        Args:
            event_details: Phase, Family, Description
            parameters: Extracted technical parameters (MD, MW, etc.)
            physics_results: Calculated physics indicators (ECD, CCI, Risk)

        Returns:
            JSON Dict matching RCAReport schema (5 Whys, Fishbone, etc.)
        """
        system_prompt = """You are the Lead RCA Investigator.
Your goal is to determine the ROOT CAUSE of a drilling event using the API RP 585 methodology.
You must rely on the provided EVIDENCE (Parameters & Physics) to justify your conclusions.

OUTPUT FORMAT (Strict JSON):
{
  "root_cause_category": "Equipment | Procedures | Personnel | Design | External",
  "root_cause_description": "Concise technical explanation of the failure.",
  "five_whys": [
    "1. Why did the event occur? ...",
    "2. Why did that happen? ...",
    "3. ...",
    "4. ...",
    "5. Root Cause ..."
  ],
  "fishbone_factors": {
    "Equipment": ["item1", "item2"],
    "People": ["item1"],
    "Methods": ["item1"],
    "Materials": ["item1"],
    "Environment": ["item1"]
  },
  "corrective_actions": [
    "Immediate: ...",
    "Short-term: ..."
  ],
  "prevention_actions": [
    "Long-term systemic improvement 1",
    "Long-term systemic improvement 2"
  ],
  "confidence_score": 0.0 to 1.0 (float)
}
"""

        user_prompt = f"""
ANALYZE THIS EVENT:

1. CONTEXT
- Phase: {event_details.get('phase')}
- Family: {event_details.get('family')}
- Type: {event_details.get('event_type')}
- Description: {event_details.get('description')}

2. TECHNICAL EVIDENCE (MEASURED)
{json.dumps(parameters, indent=2)}

3. PHYSICS ANALYSIS (CALCULATED)
{json.dumps(physics_results, indent=2)}

INSTRUCTIONS:
- If ECD is High, consider hole cleaning or geometry issues.
- If CCI is Poor, consider flow rate or rheology.
- If Mechanical Risk is High, consider tortuosity or BHA design.
- Connect the 'Physics' findings to the 'Parameters' to form the logical chain.
- Separate CORRECTIVE (immediate fixes) from PREVENTION (long-term systemic improvements).
- Generate the JSON output.
"""

        try:
            response_text = await self.gateway.generate_analysis(
                prompt=user_prompt,
                system_prompt=system_prompt,
                mode="reasoning"
            )

            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)

        except Exception as e:
            print(f"RCA Generation Error: {e}")
            return {
                "root_cause_category": "Unclassified",
                "root_cause_description": f"Analysis failed: {str(e)}",
                "five_whys": ["Analysis Error"],
                "fishbone_factors": {},
                "corrective_actions": [],
                "prevention_actions": [],
                "confidence_score": 0.0
            }
