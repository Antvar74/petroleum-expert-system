"""
Hydrologist Agent
Specialized agent for pore pressure analysis and wellbore stability
"""

from agents.base_agent import BaseAgent
from typing import Dict


class HydrologistAgent(BaseAgent):
    """
    Pore Pressure Specialist / Hydrologist agent
    Expert in pressure analysis and wellbore stability
    """
    
    def __init__(self):
        # Load system prompt from the documentation file
        try:
            with open("data/prompts/hydrologist-pore-pressure-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are an elite Hydrologist / Pore Pressure Specialist."
        super().__init__(
            name="hydrologist",
            role="Pore Pressure Specialist / Hydrologist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/pressure_analysis/"
        )

    def calculate_differential_force(self, pressure_data: Dict, geometry_data: Dict) -> Dict:
        """
        Calculate differential sticking force
        
        Args:
            pressure_data: Pressure parameters
            geometry_data: Pipe and hole geometry
            
        Returns:
            Force calculation analysis
        """
        problem = f"""
Calcula la fuerza de differential sticking:

DATOS DE PRESIÓN:
- Presión de poro: {pressure_data.get('pore_pressure_ppg', 'N/A')} ppg EMW
- Densidad del lodo: {pressure_data.get('mud_weight_ppg', 'N/A')} ppg
- Overbalance: {pressure_data.get('overbalance_psi', 'N/A')} psi
- Profundidad TVD: {pressure_data.get('tvd_ft', 'N/A')} ft

GEOMETRÍA:
- Longitud de contacto estimada: {geometry_data.get('contact_length_ft', 'N/A')} ft
- Diámetro exterior de tubería: {geometry_data.get('pipe_od_in', 'N/A')} in
- Diámetro del hoyo: {geometry_data.get('hole_size_in', 'N/A')} in
- Área de contacto estimada: {geometry_data.get('contact_area_in2', 'N/A')} in²

Calcula y proporciona:
1. Fuerza de sticking usando: F = ΔP × A × μ (donde μ = 0.15-0.25 típico)
2. Overpull requerido para liberar (con factor de seguridad)
3. Evaluación si es posible liberar con capacidad del rig
4. Alternativas si el overpull calculado excede capacidad

Muestra todos los cálculos paso a paso.
"""
        context = {
            "pressure_data": pressure_data,
            "geometry_data": geometry_data
        }
        return self.analyze(problem, context)
    
    def analyze_mud_weight_window(self, depth_range: Dict, formation_data: Dict) -> Dict:
        """
        Analyze mud weight window for a depth interval
        
        Args:
            depth_range: Start and end depths
            formation_data: Formation pressure and strength data
            
        Returns:
            Mud weight window analysis
        """
        problem = f"""
Analiza la ventana de peso de lodo:

INTERVALO DE PROFUNDIDAD:
- Profundidad inicial: {depth_range.get('start_depth_ft', 'N/A')} ft
- Profundidad final: {depth_range.get('end_depth_ft', 'N/A')} ft

DATOS DE FORMACIÓN:
- Gradiente de poro: {formation_data.get('pore_gradient_ppg', 'N/A')} ppg
- Gradiente de fractura: {formation_data.get('frac_gradient_ppg', 'N/A')} ppg
- LOT/FIT data: {formation_data.get('lot_fit_data', 'N/A')}

Proporciona:
1. Cálculo de la ventana operativa (MWW)
2. Densidad de lodo óptima recomendada
3. Margin to kick y margin to losses
4. Evaluación de si la ventana es suficiente
5. Recomendaciones si la ventana es estrecha
"""
        context = {
            "depth_range": depth_range,
            "formation_data": formation_data
        }
        return self.analyze(problem, context)
    
    def evaluate_depleted_zone_risk(self, production_data: Dict, current_depth: float) -> Dict:
        """
        Evaluate risk from depleted zones
        
        Args:
            production_data: Production history from offset wells
            current_depth: Current drilling depth
            
        Returns:
            Depleted zone risk analysis
        """
        problem = f"""
Evalúa el riesgo de zonas depletadas:

DATOS DE PRODUCCIÓN OFFSET:
{production_data}

PROFUNDIDAD ACTUAL:
{current_depth} ft MD

Analiza:
1. ¿Hay evidencia de depleción en la zona actual?
2. ¿Cuánto ha disminuido la presión de poro?
3. ¿Qué riesgos operacionales presenta?
4. ¿Qué ajustes de densidad recomiendas?
5. ¿Hay riesgo de pérdidas en formaciones superiores?
"""
        context = {"production_data": production_data}
        return self.analyze(problem, context)
