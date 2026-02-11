from agents.geologist import GeologistAgent
from agents.hydrologist import HydrologistAgent
from agents.mud_engineer import MudEngineerAgent
from agents.well_engineer import WellEngineerAgent

def verify_agent_prompt(agent, expected_phrases):
    print(f"\nVerifying {agent.name}...")
    
    # Generate a dummy analysis query
    analysis = agent.analyze_interactive("Test Problem")
    query = analysis["query"]
    
    # Check if system prompt is in the query
    missing = []
    for phrase in expected_phrases:
        if phrase not in query:
            missing.append(phrase)
            
    if missing:
        print(f"FAILED: {agent.name} is missing phrases:")
        for m in missing:
            print(f"  - {m}")
        return False
    else:
        print(f"SUCCESS: {agent.name} contains all expected high-fidelity prompt elements.")
        return True

def main():
    # Instantiate agents
    geo = GeologistAgent()
    hydro = HydrologistAgent()
    mud = MudEngineerAgent()
    well = WellEngineerAgent()
    
    # Define expected phrases from the new docs
    
    # Geologist: from geologist-petrophysicist.md
    geo_phrases = [
        "Geologist / Petrophysicist - Senior Expert System",
        "Root Cause Analysis (RCA) of geology-related well failures",
        "Clay smear continuity"
    ]
    
    # Hydrologist: from hydrologist-pore-pressure-specialist.md
    hydro_phrases = [
        "Hydrologist / Pore Pressure Specialist - Senior Expert System",
        "Root Cause Analysis (RCA) of pressure-related well failures"
    ]
    
    # Mud Engineer: from mud-engineer-fluids-specialist.md
    mud_phrases = [
        "Mud Engineer / Drilling Fluids Specialist - Senior Expert System",
        "Root Cause Analysis (RCA) of fluid-related well failures"
    ]
    
    # Well Engineer: from well-engineer-trajectory-specialist.md
    well_phrases = [
        "Well Engineer / Trajectory Specialist - Senior Expert System",
        "Root Cause Analysis (RCA) of trajectory and mechanical failures"
    ]
    
    results = [
        verify_agent_prompt(geo, geo_phrases),
        verify_agent_prompt(hydro, hydro_phrases),
        verify_agent_prompt(mud, mud_phrases),
        verify_agent_prompt(well, well_phrases)
    ]
    
    if all(results):
        print("\nALL AGENTS VERIFIED SUCCESSFULLY.")
    else:
        print("\nSOME AGENTS FAILED VERIFICATION.")

if __name__ == "__main__":
    main()
