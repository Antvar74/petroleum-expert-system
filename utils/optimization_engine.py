import math
from typing import Dict, List, Optional

class OptimizationEngine:
    """
    Expert system for specialized drilling calculations.
    Provides hydraulics, torque & drag, and bit selection optimization.
    """
    
    @staticmethod
    def calculate_hydraulics(flow_rate_gpm: float, mud_weight_ppg: float, depth_ft: float, id_pipe_in: float) -> Dict:
        """
        Calculates basic annular velocity and pressure drop.
        Simple Bingham Plastic model approximation.
        """
        # Flow area (simplified for pipe ID)
        area_in2 = math.pi * (id_pipe_in/2)**2
        velocity_fps = (flow_rate_gpm * 0.408) / (id_pipe_in**2)
        
        # Simple pressure drop approximation (Fanning friction factor simplified)
        # DeltaP = (0.000076 * MW * L * V^1.8) / (D^1.2)
        pressure_drop_psi = (0.000076 * mud_weight_ppg * depth_ft * (velocity_fps**1.8)) / (id_pipe_in**1.2)
        
        return {
            "annular_velocity_fps": round(velocity_fps, 2),
            "pressure_drop_psi": round(pressure_drop_psi, 2),
            "ecd_ppg": round(mud_weight_ppg + (pressure_drop_psi / (0.052 * depth_ft)), 2) if depth_ft > 0 else mud_weight_ppg,
            "status": "Optimal" if velocity_fps > 2.0 else "Low Velocity"
        }

    @staticmethod
    def calculate_torque_drag(depth_ft: float, inclination_deg: float, mud_weight_ppg: float, pipe_weight_lb_ft: float, friction_factor: float = 0.25) -> Dict:
        """
        Calculates hook load and torque at surface (Soft String Model approximation).
        """
        inclination_rad = math.radians(inclination_deg)
        buoyancy_factor = 1 - (mud_weight_ppg / 65.5) # Approx buoyancy in steel
        
        # Buoyed weight
        total_weight_lb = depth_ft * pipe_weight_lb_ft * buoyancy_factor
        
        # Drag (simplified sin/cos component)
        hook_load_up_lb = total_weight_lb * (math.cos(inclination_rad) + friction_factor * math.sin(inclination_rad))
        hook_load_down_lb = total_weight_lb * (math.cos(inclination_rad) - friction_factor * math.sin(inclination_rad))
        
        return {
            "buoyed_weight_lb": round(total_weight_lb, 0),
            "hook_load_up_lb": round(hook_load_up_lb, 0),
            "hook_load_down_lb": round(hook_load_down_lb, 0),
            "margin_of_overpull_lb": round(hook_load_up_lb * 0.1, 0) # 10% safety margin
        }

    @staticmethod
    def optimize_bit_selection(formation_hardness: str, previous_rop: float) -> List[Dict]:
        """
        Recommends bits based on performance data.
        """
        recommendations = []
        if formation_hardness.lower() == "soft":
            recommendations.append({"type": "PDC", "cutters": "13mm", "justification": "High ROP in soft shales"})
        elif formation_hardness.lower() == "medium":
            recommendations.append({"type": "PDC", "cutters": "16mm", "justification": "Balance of durability and ROP"})
            recommendations.append({"type": "Roller Cone", "jets": "3x12n", "justification": "Stability in interbedded layers"})
        else:
            recommendations.append({"type": "Roller Cone", "inserts": "TCI", "justification": "Durability in hard/abrasive sands"})
            
        return recommendations
