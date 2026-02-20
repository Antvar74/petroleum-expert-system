from agents.base_agent import BaseAgent
from typing import Dict, Optional
import json


class RCAClassifierAgent(BaseAgent):
    """
    RCA Classifier Agent — Step 1 of the Investigation Pipeline.

    Classifies the incident level (1-3) based on API RP 585 criteria and
    recommends the investigation approach, team composition, and methodology.
    This is the FIRST agent in the standard workflow, setting the scope before
    technical specialists begin their analyses.
    """

    SYSTEM_PROMPT = """\
You are the RCA Incident Classifier, an expert in API RP 585 methodology.

Your SOLE responsibility is to perform the initial assessment of an operational
event and classify it according to the API RP 585 three-level investigation
framework:

**Level 1 (Low Consequence)**
- Minor equipment issues, no loss of containment, small easily-contained leaks
- Team: 1-2 persons | Methods: 5 Whys, "What If" | Duration: Hours to 1-2 days

**Level 2 (Medium Consequence)**
- Equipment failure requiring shutdown, repetitive Level 1 events, moderate NPT
- Team: 3-5 persons | Methods: Causal factor analysis, logic trees, Fishbone
- Duration: Several days to weeks

**Level 3 (High Consequence)**
- Major incidents (blowouts, fatalities, major environmental releases)
- Team: 6-10+ persons | Methods: Full API RP 585 + TRIPOD Beta + HFACS-OGI + FTA
- Duration: Several weeks to months

**CRITICAL**: Classification is based on BOTH actual AND potential consequences.
A near-miss with high potential severity = Level 3 investigation.

For every event you receive, provide:
1. Classification Level (1, 2, or 3) with justification
2. Recommended investigation methodology
3. Recommended team composition (which specialist disciplines)
4. Recommended investigation duration
5. Immediate actions (evidence preservation, notifications)
6. Key evidence to collect

Respond in the same language as the incident description (Spanish or English).
Always end your response with an explicit confidence level:
"Nivel de Confianza: HIGH/MEDIUM/LOW"
"""

    def __init__(self):
        super().__init__(
            name="rca_classifier",
            role="RCA Incident Classifier (API RP 585)",
            system_prompt=self.SYSTEM_PROMPT,
            knowledge_base_path="knowledge_base/rca/"
        )

    def classify_incident(self, incident_description: str, severity_data: Dict) -> Dict:
        """
        Classify the incident level (1-3) based on API RP 585 criteria.

        Args:
            incident_description: Brief narrative of what happened
            severity_data: Dictionary containing consequence data

        Returns:
            Dictionary with classification level and justification
        """
        problem = f"""\
Classify this incident according to API RP 585 (Level 1, 2, or 3):

DESCRIPTION:
{incident_description}

SEVERITY DATA:
{json.dumps(severity_data, indent=2)}

Provide:
1. Classification Level (1, 2, or 3)
2. Justification based on API RP 585 criteria (actual/potential consequence)
3. Recommended team composition and investigation duration
4. Recommended investigation methodology
5. Key evidence to collect immediately
"""
        return self.analyze_interactive(problem, context={"severity": severity_data})
