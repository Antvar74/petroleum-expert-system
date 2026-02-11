import asyncio
import os
from dotenv import load_dotenv
from orchestrator.api_coordinator import APICoordinator

# Load environment variables
load_dotenv()

async def verify_new_agents():
    print("--- 🚀 VERIFYING EXPANSION AGENTS ---")
    
    coordinator = APICoordinator()
    
    # Mock Problem for Cementing/HSE context
    problem_desc = "Primary cement job on 9-5/8 casing showed poor bonding in the top interval. Gas migration suspected. Field personnel felt pressured to pump fast."
    
    agents_to_test = ["cementing_engineer", "hse_engineer", "optimization_engineer"]
    
    for agent_id in agents_to_test:
        print(f"\n--- Testing Agent: {agent_id} ---")
        try:
            # 1. Generate Prompt
            analysis = coordinator.get_agent_query(agent_id, problem_desc)
            print(f"✅ Query Generated. Role: {analysis['role']}")
            
            # 2. Run Analysis (Fast Mode via Gemini)
            print(f"⏳ Calling Gemini (Fast Mode)...")
            result = await coordinator.run_automated_step(agent_id, problem_desc)
            
            response = result.get('analysis', '')
            print(f"✅ Response Received ({len(response)} chars)")
            print(f"Snippet: {response[:150]}...")
            
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_new_agents())
