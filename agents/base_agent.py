"""
Base Agent Class (Interactive Mode - No API)
Parent class for all specialized petroleum engineering agents
"""

from typing import Dict, List, Optional
import json
from datetime import datetime
import os


class BaseAgent:
    """
    Base class for all specialized agents in the petroleum expert system.
    INTERACTIVE MODE: Generates formatted queries for manual execution in Claude.
    """
    
    def __init__(self, name: str, role: str, system_prompt: str, knowledge_base_path: str):
        """
        Initialize a specialized agent
        
        Args:
            name: Agent identifier (e.g., 'drilling_engineer')
            role: Human-readable role description
            system_prompt: Detailed system prompt defining agent's expertise
            knowledge_base_path: Path to agent's knowledge base directory
        """
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.knowledge_base_path = knowledge_base_path
        self.conversation_history = []
    
    def analyze_interactive(self, problem_description: str, context: Optional[Dict] = None) -> Dict:
        """
        Generate formatted query for manual execution in Claude
        User will copy this query, paste in Claude, and return the response
        
        Args:
            problem_description: Description of the problem to analyze
            context: Additional context including well data and previous analyses
            
        Returns:
            Dictionary containing the formatted query and eventual response
        """
        # Generate the complete query with system prompt and context
        formatted_query = self._generate_formatted_query(problem_description, context)
        
        # This will be filled by the coordinator after user provides Claude's response
        analysis = {
            "agent": self.name,
            "role": self.role,
            "timestamp": datetime.now().isoformat(),
            "query": formatted_query,
            "analysis": None,  # To be filled with user input
            "confidence": None,  # To be extracted from response
            "mode": "interactive"
        }
        
        return analysis
    
    def set_response(self, analysis: Dict, response_text: str):
        """
        Set the response received from Claude for this analysis
        
        Args:
            analysis: The analysis dictionary to update
            response_text: The response text from Claude
        """
        analysis["analysis"] = response_text
        analysis["confidence"] = self._extract_confidence(response_text)
        
        self.conversation_history.append({
            "query": analysis["query"],
            "response": response_text,
            "confidence": analysis["confidence"],
            "timestamp": analysis["timestamp"]
        })
    
    def _generate_formatted_query(self, problem: str, context: Optional[Dict]) -> str:
        """
        Generate a complete, formatted query for manual execution in Claude
        
        Args:
            problem: Problem description
            context: Context dictionary with well data and previous analyses
            
        Returns:
            Complete formatted query string
        """
        query = f"""SYSTEM PROMPT:
{self.system_prompt}

---

USER REQUEST:

# Problema a Analizar:
{problem}
"""
        
        # Add previous analyses from other specialists
        if context and "previous_analyses" in context:
            query += "\n\n# Análisis de Otros Especialistas:\n"
            for prev_analysis in context["previous_analyses"]:
                if prev_analysis.get("analysis"):  # Only include if analysis was provided
                    query += f"\n## {prev_analysis['role']}:\n{prev_analysis['analysis']}\n"
                    query += f"**Nivel de Confianza:** {prev_analysis.get('confidence', 'N/A')}\n"
        
        # Add well data if available
        if context and "well_data" in context:
            query += f"\n\n# Datos del Pozo:\n```json\n{json.dumps(context['well_data'], indent=2, ensure_ascii=False)}\n```"
            
        # Add extracted report text if available (Crucial for PDF analysis)
        if context and "extracted_report_text" in context:
             query += f"\n\n# REPORTE/DOCUMENTO ADJUNTO:\n{context['extracted_report_text']}\n"
        
        return query
    
    def _extract_confidence(self, text: str) -> str:
        """
        Extract confidence level from analysis text
        
        Args:
            text: Analysis text
            
        Returns:
            Confidence level: HIGH, MEDIUM, or LOW
        """
        if not text:
            return "UNKNOWN"
        
        text_lower = text.lower()
        
        # Check for explicit confidence markers
        if "nivel de confianza: high" in text_lower or "confianza: high" in text_lower:
            return "HIGH"
        elif "nivel de confianza: medium" in text_lower or "confianza: medium" in text_lower:
            return "MEDIUM"
        elif "nivel de confianza: low" in text_lower or "confianza: low" in text_lower:
            return "LOW"
        
        # Check for implicit confidence indicators
        high_confidence_terms = ["definitivamente", "claramente", "sin duda", "alta confianza"]
        medium_confidence_terms = ["probablemente", "posiblemente", "parece que", "media confianza"]
        low_confidence_terms = ["quizás", "tal vez", "incierto", "baja confianza", "insuficiente"]
        
        if any(term in text_lower for term in high_confidence_terms):
            return "HIGH"
        elif any(term in text_lower for term in low_confidence_terms):
            return "LOW"
        elif any(term in text_lower for term in medium_confidence_terms):
            return "MEDIUM"
        
        # Default to medium if unclear
        return "MEDIUM"
    
    def save_response(self, response_text: str, filepath: str):
        """
        Save a response to a file for later use
        
        Args:
            response_text: The response to save
            filepath: Where to save it
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response_text)
    
    def load_response(self, filepath: str) -> str:
        """
        Load a previously saved response
        
        Args:
            filepath: Path to the saved response
            
        Returns:
            The loaded response text
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def get_history(self) -> List[Dict]:
        """
        Get conversation history for this agent
        
        Returns:
            List of historical interactions
        """
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []