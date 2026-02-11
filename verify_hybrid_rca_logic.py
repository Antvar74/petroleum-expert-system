import asyncio
import os
from dotenv import load_dotenv
import json
load_dotenv()
from orchestrator.api_coordinator import APICoordinator
from models import OperationalProblem
import json

async def verify_logic():
    print("Initializing API Coordinator...")
    coordinator = APICoordinator()
    
    # Mock Context
    context = {
        "well_data": {"well_name": "Test-Well-01"},
        "previous_analyses": [
            {"agent": "mud_engineer", "role": "Mud Engineer", "analysis": "Mud weight was 1.5 sg, below pore pressure of 1.6 sg."}
        ]
    }
    
    # Mock User Data (5-Whys)
    methodology = "5whys"
    user_data = [
        "Pipe stuck while tripping out.",
        "Swab effect reduced bottom hole pressure.",
        "Tripping speed was too fast.",
        "Driller wanted to save time.",
        "No procedure for tripping speed limit in this section."
    ]
    
    print("\n--- Running Automated Audit (5-Whys) ---")
    result = await coordinator.run_automated_audit(methodology, user_data, context)
    
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    if "agent" in result and result["agent"] == "rca_lead":
        print("\nSUCCESS: Audit completed successfully.")
    else:
        print("\nFAILURE: Audit did not return expected structure.")

if __name__ == "__main__":
    asyncio.run(verify_logic())
