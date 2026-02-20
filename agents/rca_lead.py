from agents.base_agent import BaseAgent
from typing import Dict, List, Optional, Any
import json
from utils.llm_gateway import LLMGateway

class RCALeadAgent(BaseAgent):
    """
    RCA & Investigation Lead Agent
    
    Orchestrates the investigation process based on API RP 585 methodology.
    Responsible for:
    - Incident Classification (Level 1-3)
    - Evidence Strategy
    - Synthesis of technical findings
    - Corrective Action Plan (CAPA) formulation
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/rca-investigation-lead.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback if file not found (should be there in prod)
            system_prompt = "You are the RCA Lead Investigator utilizing API RP 585 methodology. Organize the investigation."
            
        super().__init__(
            name="rca_lead",
            role="RCA & Investigation Lead",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/rca/"
        )
        self.gateway = LLMGateway()

    def classify_incident(self, incident_description: str, severity_data: Dict) -> Dict:
        """
        Classify the incident level (1-3) based on API RP 585 criteria.
        
        Args:
            incident_description: Brief narrative of what happened
            severity_data: Dictionary containing consequence data (cost, NPT, safety impact)
            
        Returns:
            Dictionary with classification level and justification
        """
        problem = f"""
        Classify this incident according to API RP 585 (Level 1, 2, or 3):
        
        DESCRIPTION:
        {incident_description}
        
        SEVERITY DATA:
        {json.dumps(severity_data, indent=2)}
        
        Provide:
        1. Classification Level (1, 2, or 3)
        2. Justification based on API RP 585 criteria (actual/potential consequence)
        3. Recommended team composition and investigation duration
        """
        
        # Interactive mode: Return query for LLM
        return self.analyze_interactive(problem, context={"severity": severity_data})

    def synthesize_report(self, incident_context: Dict, technical_findings: List[Dict]) -> Dict:
        """
        Synthesize a final RCA report from technical findings.
        
        Args:
            incident_context: Basic event data
            technical_findings: List of analysis outputs from other agents
            
        Returns:
            Structured RCA report
        """
        # Format technical findings for validity
        findings_text = ""
        for find in technical_findings:
            findings_text += f"\n--- {find.get('role', 'Specialist')} ---\n"
            findings_text += f"{find.get('analysis', 'No input provided')}\n"
        
        problem = f"""
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
           - CAPA (Corrective Actions)
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
        
        problem = f"""
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
        - Corrective Actions (CAPA)
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
        
        # 1. Construct Evidence-Based Prompt
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
            # Call LLM
            response_text = await self.gateway.generate_analysis(
                prompt=user_prompt,
                system_prompt=system_prompt,
                mode="reasoning"  # Use smarter model for RCA
            )
            
            # Clean and Parse JSON
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except Exception as e:
            print(f"❌ RCA Generation Error: {e}")
            return {
                "root_cause_category": "Unclassified",
                "root_cause_description": f"Analysis failed: {str(e)}",
                "five_whys": ["Analysis Error"],
                "fishbone_factors": {},
                "corrective_actions": [],
                "confidence_score": 0.0
            }
