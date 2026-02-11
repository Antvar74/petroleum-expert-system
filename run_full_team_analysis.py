import asyncio
import os
from dotenv import load_dotenv
from orchestrator.api_coordinator import APICoordinator
from utils.pdf_loader import load_pdf_text

# Load environment variables
load_dotenv()

async def run_full_team_bakte9():
    print("--- 🚀 STARTING FULL TEAM ANALYSIS (BAKTE-9) ---")
    
    # 1. Load Context
    pdf_path = "data/BAKTE-9_ETAPA_18.5.pdf"
    print(f"Loading context from: {pdf_path}")
    context_text = load_pdf_text(pdf_path, max_pages=15)
    
    if "Error" in context_text and len(context_text) < 100:
        print(f"❌ Failed to load PDF: {context_text}")
        return

    # 2. Initialize Coordinator
    coordinator = APICoordinator()
    
    incident_context = {
        "well_data": {"well_name": "BAKTE-9"},
        "extracted_report_text": context_text
    }
    
    # 3. Define the Expert Team
    agents_to_consult = [
        "geologist",          # Formations / Instability
        "mud_engineer",       # Fluid properties / Cleaning
        "well_engineer",      # Trajectory / T&D
        "cementing_engineer", # Casing / Integrity
        "hse_engineer",       # Safety / Human Factors
    ]
    
    analyses = []
    
    print(f"Consulting {len(agents_to_consult)} specialists + RCA Lead...")
    
    # 4. Run Analysis for Each Specialist
    for agent_id in agents_to_consult:
        print(f"\n--- 🕵️‍♂️ Agent: {agent_id.upper()} ---")
        try:
            # We use a specific prompt asking them to analyze the PDF content for their domain
            problem_description = f"Analyze the attached well report text for BAKTE-9. Identify any risks, failures, or anomalies relevant to your discipline ({agent_id}). Focus on the stuck pipe event and operations around April 22, 2025."
            
            # Run the agent (Fast Mode via Gemini)
            # Note: We pass the *entire* context text in the context dict, and a specific prompt
            result = await coordinator.run_automated_step(
                agent_id=agent_id, 
                problem_description=problem_description,
                context=incident_context
            )
            
            analysis_text = result.get('analysis', 'No response')
            print(f"✅ Findings ({len(analysis_text)} chars):\n{analysis_text[:200]}...")
            
            analyses.append(result)
            
        except Exception as e:
            print(f"❌ Failed: {e}")

    # 5. Final Synthesis (RCA Lead)
    print("\n\n--- 🏁 FINAL SYNTHESIS (RCA LEAD) ---")
    try:
        # We use run_automated_audit or run_automated_synthesis. 
        # Here, we'll ask RCA Lead to synthesize purely based on the other agents' findings + context.
        
        # Construct a meta-prompt for the RCA Lead
        synthesis_prompt = "Synthesize these expert findings into a final Incident Report for BAKTE-9."
        
        # We can pass the previous analyses in the context
        full_context = incident_context.copy()
        full_context["previous_analyses"] = analyses
        
        final_result = await coordinator.run_automated_audit(
            methodology="5whys", # Uses 5-Whys logic for root cause
            user_data=["Stuck pipe", "Pipe parted", "Fishing operations"], # High level events
            context=full_context
        )
        
        print(final_result.get("analysis", "No final report."))
        
    except Exception as e:
        print(f"❌ Synthesis Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_full_team_bakte9())
