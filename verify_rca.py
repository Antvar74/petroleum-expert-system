from agents.rca_lead import RCALeadAgent
import json

def verify_rca_lead():
    print("Initializing RCA Lead Agent...")
    agent = RCALeadAgent()
    
    # 1. Verify System Prompt Loading
    print("\n--- Verifying System Prompt ---")
    essential_phrases = [
        "API RP 585",
        "Level 1 (Minor / Precursor)",
        "Fishbone (Ishikawa)",
        "Executive Summary"
    ]
    
    missing = []
    for phrase in essential_phrases:
        if phrase not in agent.system_prompt:
            missing.append(phrase)
            
    if missing:
        print(f"FAILED: Missing phrases in system prompt: {missing}")
    else:
        print("SUCCESS: System prompt contains all API RP 585 elements.")

    # 2. Verify Incident Classification Query
    print("\n--- Verifying Classification Query ---")
    incident = "During tripping out at 12,500ft, observed tight spot. Worked pipe for 4 hours. Pump pressure increased. Eventually jarred free."
    severity = {"NPT": "4 hours", "Cost": "$50k", "Safety": "None"}
    
    analysis = agent.classify_incident(incident, severity)
    print(f"Query Generated:\n{analysis['query'][:500]}...")
    
    if "Classify this incident according to API RP 585" in analysis['query']:
        print("SUCCESS: Classification query structure correct.")
    else:
        print("FAILED: Classification query malformed.")

if __name__ == "__main__":
    verify_rca_lead()
