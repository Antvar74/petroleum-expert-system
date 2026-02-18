"""
Analysis Result Data Model
Contains results from multi-agent analysis
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import json
import os


@dataclass
class AnalysisResult:
    """
    Contains comprehensive analysis results from multiple specialist agents
    """
    
    problem: 'OperationalProblem'
    individual_analyses: List[Dict[str, Any]]
    final_synthesis: Dict[str, Any]
    workflow_used: List[str]
    leader_agent_id: str = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_confidence_summary(self) -> Dict[str, int]:
        """
        Get count of confidence levels across all analyses
        
        Returns:
            Dictionary with counts per confidence level
        """
        confidence_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "ERROR": 0}
        
        for analysis in self.individual_analyses:
            conf = analysis.get('confidence', 'MEDIUM')
            if conf in confidence_counts:
                confidence_counts[conf] += 1
        
        return confidence_counts
    
    def get_overall_confidence(self) -> str:
        """
        Determine overall confidence level
        
        Returns:
            Overall confidence: HIGH, MEDIUM, or LOW
        """
        counts = self.get_confidence_summary()
        total = sum(counts.values())
        
        if total == 0:
            return "LOW"
        
        # If majority is HIGH, return HIGH
        if counts["HIGH"] / total > 0.6:
            return "HIGH"
        # If any LOW or ERROR, return LOW
        elif counts["LOW"] > 0 or counts["ERROR"] > 0:
            return "LOW"
        else:
            return "MEDIUM"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "well": self.problem.well_name,
            "depth_md": self.problem.depth_md,
            "operation": self.problem.operation,
            "workflow": self.workflow_used,
            "confidence_summary": self.get_confidence_summary(),
            "overall_confidence": self.get_overall_confidence(),
            "individual_analyses": self.individual_analyses,
            "final_synthesis": self.final_synthesis
        }
    
    def to_json(self, filepath: str):
        """
        Export complete result to JSON file
        
        Args:
            filepath: Output file path
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = self.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON exportado: {filepath}")
    
    def generate_markdown_report(self, filepath: str):
        """
        Generate comprehensive markdown report
        
        Args:
            filepath: Output file path
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Petroleum Expert System - Análisis de Operaciones\n\n")
            f.write(f"**Pozo:** {self.problem.well_name}\n")
            f.write(f"**Profundidad:** {self.problem.depth_md} ft MD ({self.problem.depth_tvd} ft TVD)\n")
            f.write(f"**Operación:** {self.problem.operation}\n")
            if self.problem.formation:
                f.write(f"**Formación:** {self.problem.formation}\n")
            f.write(f"**Fecha de Análisis:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Workflow Utilizado:** {' → '.join(self.workflow_used)}\n")
            f.write(f"\n---\n\n")
            
            # Problem description
            f.write(f"## Descripción del Problema\n\n")
            f.write(f"{self.problem.description}\n\n")
            f.write(f"---\n\n")
            
            # Confidence summary
            conf_summary = self.get_confidence_summary()
            overall_conf = self.get_overall_confidence()
            f.write(f"## Resumen de Confianza\n\n")
            f.write(f"**Confianza Global:** {overall_conf}\n\n")
            f.write(f"**Distribución por Especialista:**\n")
            f.write(f"- Alta (HIGH): {conf_summary['HIGH']}\n")
            f.write(f"- Media (MEDIUM): {conf_summary['MEDIUM']}\n")
            f.write(f"- Baja (LOW): {conf_summary['LOW']}\n")
            if conf_summary['ERROR'] > 0:
                f.write(f"- Errores: {conf_summary['ERROR']}\n")
            f.write(f"\n---\n\n")
            
            # Executive synthesis
            f.write(f"## Síntesis Ejecutiva Integrada\n\n")
            f.write(f"{self.final_synthesis.get('analysis', 'No disponible')}\n\n")
            f.write(f"**Confianza de la Síntesis:** {self.final_synthesis.get('confidence', 'N/A')}\n")
            f.write(f"\n---\n\n")
            
            # Individual analyses
            f.write(f"## Análisis Detallados por Disciplina\n\n")
            
            for i, analysis in enumerate(self.individual_analyses, 1):
                role = analysis.get('role', 'Unknown')
                conf = analysis.get('confidence', 'N/A')
                content = analysis.get('analysis', 'No disponible')
                
                f.write(f"### {i}. {role}\n\n")
                f.write(f"**Nivel de Confianza:** {conf}\n\n")
                f.write(f"{content}\n\n")
                f.write(f"---\n\n")
            
            # Footer
            f.write(f"\n## Metadata\n\n")
            f.write(f"- **Archivo generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Sistema:** Petroleum Expert System v1.0\n")
            f.write(f"- **Modelo AI:** Claude Sonnet 4 (claude-sonnet-4-20250514)\n")
        
        print(f"✅ Reporte Markdown exportado: {filepath}")
    
    def print_summary(self):
        """Print a summary of the analysis to console"""
        print(f"\n{'='*80}")
        print(f"RESUMEN DEL ANÁLISIS")
        print(f"{'='*80}")
        print(f"Pozo: {self.problem.well_name}")
        print(f"Profundidad: {self.problem.depth_md} ft MD")
        print(f"Workflow: {' → '.join(self.workflow_used)}")
        print(f"\nConfianza Global: {self.get_overall_confidence()}")
        
        conf_summary = self.get_confidence_summary()
        print(f"\nDistribución de Confianza:")
        print(f"  HIGH: {conf_summary['HIGH']}")
        print(f"  MEDIUM: {conf_summary['MEDIUM']}")
        print(f"  LOW: {conf_summary['LOW']}")
        
        print(f"\nEspecialistas Consultados: {len(self.individual_analyses)}")
        for analysis in self.individual_analyses:
            print(f"  - {analysis['role']}: {analysis['confidence']}")
        
        print(f"\n{'='*80}\n")
