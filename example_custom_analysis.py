"""
Example: Custom Problem Analysis
Demonstrates how to create and analyze a custom operational problem
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from orchestrator.coordinator import StuckPipeCoordinator
from models.problem import OperationalProblem


def create_custom_problem():
    """
    Create a custom operational problem for analysis
    """
    problem = OperationalProblem(
        well_name="YOUR-WELL-NAME",
        depth_md=10000.0,  # Measured depth in feet
        depth_tvd=9500.0,   # True vertical depth in feet
        description="""
Describe your operational problem in detail here.

Include:
- What was happening when the problem occurred
- Symptoms observed (torque, drag, pressure, etc.)
- Formation information
- Any relevant history or context
        """,
        operation="drilling",  # or "tripping_in", "tripping_out", etc.
        
        # Optional fields
        formation="Formation Name",
        mud_weight=10.5,  # ppg
        inclination=35.0,  # degrees
        azimuth=120.0,     # degrees
        torque=20.0,       # klb-ft
        overpull=50000,    # lbs
        string_weight=150000,  # lbs
        
        # Additional data (completely flexible)
        additional_data={
            "mud_properties": {
                "type": "WBM",  # or "OBM", "SBM"
                "density_ppg": 10.5,
                "pv": 15,
                "yp": 10
            },
            "formation_data": {
                "lithology": "Sandstone",
                "permeability_md": 100
            },
            "pressure_data": {
                "pore_pressure_ppg": 9.0,
                "frac_gradient_ppg": 13.0
            }
        }
    )
    
    return problem


def main():
    """Run custom analysis"""
    
    # Create your problem
    problem = create_custom_problem()
    
    # Initialize coordinator
    coordinator = StuckPipeCoordinator()
    
    # Choose workflow
    # Options: "standard", "quick_differential", "quick_mechanical", 
    #          "lost_circulation", "wellbore_stability"
    workflow = "standard"
    
    # Or create custom workflow
    # custom_workflow = ["drilling_engineer", "mud_engineer", "hydrologist"]
    
    # Run analysis
    result = coordinator.analyze_problem(problem, workflow=workflow)
    
    # Print summary
    result.print_summary()
    
    # Save results
    timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
    result.to_json(f"analysis_results/{problem.well_name}_{timestamp}.json")
    result.generate_markdown_report(f"analysis_results/{problem.well_name}_{timestamp}.md")
    
    print(f"\n✅ Analysis complete!")
    print(f"📁 Results saved to analysis_results/")


if __name__ == "__main__":
    main()
