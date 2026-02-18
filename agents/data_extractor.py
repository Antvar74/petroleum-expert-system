from typing import Dict, Any, Optional
import json
import re
from utils.llm_gateway import LLMGateway

class DataExtractionAgent:
    """
    Specialized agent for extracting structured engineering parameters 
    from unstructured text (Daily Reports, PDF dumps, etc.)
    """
    
    def __init__(self):
        self.gateway = LLMGateway()
        
    async def extract_parameters(self, text: str, context: str = "drilling") -> Dict[str, Any]:
        """
        Extracts 'Non-Negotiable' minimum data set from text.
        Returns a dictionary matching ParameterSet schema.
        """
        
        system_prompt = """You are an Expert Petroleum Data Analyst.
Your job is to extract specific technical parameters from drilling/workover reports.
Return ONLY a valid JSON object. Do not include markdown formatting like ```json.
If a value is not found, use null.
Convert all units to standard oilfield units:
- Depth: ft
- Weight: klb
- Pressure: psi
- Density: ppg
- Volume: bbl
- Flow: gpm
- Torque: ft-lb
"""

        user_prompt = f"""
EXTRACT the following parameters from the text below.
Return a JSON object with exactly these keys:

{{
    "depth_md": float or null,
    "depth_tvd": float or null,
    "inclination": float or null,
    "azimuth": float or null,
    "mud_weight": float or null,
    "viscosity_pv": float or null,
    "viscosity_yp": float or null,
    "flow_rate": float or null,
    "spp": float or null,
    "rpm": float or null,
    "rop": float or null,
    "wob": float or null,
    "torque": float or null,
    "hook_load": float or null,
    "pit_gain": float or null,
    "sidpp": float or null,
    "sicp": float or null,
    "operation_summary": "Brief 1-sentence summary of current operation"
}}

REPORT TEXT:
{text[:15000]}  # Limit text to avoid context window issues
"""

        try:
            # fast mode (Flash) is usually sufficient for extraction
            response_text = await self.gateway.generate_analysis(
                prompt=user_prompt,
                system_prompt=system_prompt,
                mode="fast"
            )
            
            # Clean response (remove markdown if model ignores instruction)
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(clean_text)
            return data
            
        except json.JSONDecodeError:
            print(f"❌ Extraction Failed: Invalid JSON reponse. Falling back to Safe Mode.")
            return self._get_fallback_data("AI Extraction failed (Invalid JSON). Please enter data manually.")
            
        except Exception as e:
            print(f"❌ Extraction Error: {str(e)}")
            return self._get_fallback_data(f"AI Extraction error: {str(e)}")

    def _get_fallback_data(self, reason: str) -> Dict[str, Any]:
        """Returns empty structure to prevent 500 errors"""
        return {
            "depth_md": None,
            "depth_tvd": None,
            "inclination": None,
            "azimuth": None,
            "mud_weight": None,
            "viscosity_pv": None,
            "viscosity_yp": None,
            "flow_rate": None,
            "spp": None,
            "rpm": None,
            "rop": None,
            "wob": None,
            "torque": None,
            "hook_load": None,
            "pit_gain": None,
            "sidpp": None,
            "sicp": None,
            "operation_summary": f"⚠️ {reason}"
        }
