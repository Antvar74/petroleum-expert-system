"""
Operational Problem Data Model
Represents petroleum engineering operational problems for analysis
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class OperationalProblem:
    """
    Represents an operational problem in petroleum operations
    (stuck pipe, lost circulation, wellbore instability, etc.)
    """
    
    # Required fields
    well_name: str
    depth_md: float  # Measured depth in feet
    depth_tvd: float  # True vertical depth in feet
    description: str  # Detailed problem description
    operation: str  # Type of operation when problem occurred
    
    # Optional operational data
    formation: Optional[str] = None
    mud_weight: Optional[float] = None  # ppg
    inclination: Optional[float] = None  # degrees
    azimuth: Optional[float] = None  # degrees
    torque: Optional[float] = None  # klb-ft
    drag: Optional[float] = None  # lbs
    overpull: Optional[float] = None  # lbs
    string_weight: Optional[float] = None  # lbs
    
    # Timestamps
    incident_datetime: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Additional structured data
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert problem to dictionary for API calls and storage
        
        Returns:
            Dictionary representation of the problem
        """
        base_data = {
            "well_name": self.well_name,
            "depth_md": self.depth_md,
            "depth_tvd": self.depth_tvd,
            "description": self.description,
            "operation": self.operation,
            "formation": self.formation,
            "mud_weight_ppg": self.mud_weight,
            "inclination_deg": self.inclination,
            "azimuth_deg": self.azimuth,
            "torque_klbft": self.torque,
            "drag_lbs": self.drag,
            "overpull_lbs": self.overpull,
            "string_weight_lbs": self.string_weight,
        }
        
        # Add datetime if available
        if self.incident_datetime:
            base_data["incident_datetime"] = self.incident_datetime.isoformat()
        
        # Merge with additional data
        if self.additional_data:
            base_data.update(self.additional_data)
        
        # Remove None values for cleaner output
        return {k: v for k, v in base_data.items() if v is not None}
    
    def summary(self) -> str:
        """
        Generate a one-line summary of the problem
        
        Returns:
            Summary string
        """
        return (
            f"{self.well_name} @ {self.depth_md}' MD - "
            f"{self.operation} - {self.formation or 'Unknown formation'}"
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationalProblem':
        """
        Create OperationalProblem instance from dictionary
        
        Args:
            data: Dictionary with problem data
            
        Returns:
            OperationalProblem instance
        """
        # Extract known fields
        known_fields = {
            'well_name', 'depth_md', 'depth_tvd', 'description', 'operation',
            'formation', 'mud_weight', 'inclination', 'azimuth', 'torque',
            'drag', 'overpull', 'string_weight', 'incident_datetime'
        }
        
        problem_data = {}
        additional = {}
        
        for key, value in data.items():
            if key in known_fields:
                problem_data[key] = value
            else:
                additional[key] = value
        
        if additional:
            problem_data['additional_data'] = additional
        
        return cls(**problem_data)


# Common operation types
OPERATION_TYPES = [
    "drilling",
    "tripping_in",
    "tripping_out", 
    "running_casing",
    "cementing",
    "logging",
    "reaming",
    "circulating",
    "making_connection",
    "slide_drilling",
    "rotary_drilling"
]

# Common problem types
PROBLEM_TYPES = [
    "stuck_pipe_differential",
    "stuck_pipe_mechanical",
    "stuck_pipe_packoff",
    "lost_circulation",
    "wellbore_instability",
    "well_control",
    "equipment_failure",
    "formation_damage"
]
