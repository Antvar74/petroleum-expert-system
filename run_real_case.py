import asyncio
import os
from dotenv import load_dotenv
from orchestrator.api_coordinator import APICoordinator
from utils.pdf_loader import load_pdf_text

# Load environment variables
load_dotenv()

async def run_bakte9_simulation():
    print("--- 🚀 STARTING REAL DATA SIMULATION (BAKTE-9) ---")
    
    # 1. Load the PDF Context
    pdf_path = "data/BAKTE-9_ETAPA_18.5.pdf"
    print(f"Loading context from: {pdf_path}")
    
    context_text = load_pdf_text(pdf_path, max_pages=10)
    
    if "Error" in context_text and len(context_text) < 100:
        print(f"❌ Failed to load PDF: {context_text}")
        return

    print(f"✅ Context Loaded ({len(context_text)} chars). Sample:\n{context_text[:200]}...\n")

    # 2. Initialize Coordinator
    coordinator = APICoordinator()

    # 3. Define the Incident Context (Injected from Real Data)
    incident_context = {
        "well_data": {
            "well_name": "BAKTE-9",
            "field": "Bakte",
            "country": "Mexico" # Assuming based on context, can be updated
        },
        "extracted_report_text": context_text
    }

    # 4. Define the User's Initial Observation (The Trigger)
    # We ask the LLM to identify the main problem from the text, but for the RCA agent 
    # we need to simulate a user report. Based on "Etapa 18.5", it's likely a specific section analysis.
    # Let's frame it as a general "Analyze this report" task first.
    
    user_observation = [
        "Review of BAKTE-9 Stage 18.5 Report.",
        "Analyze operational risks and potential failures described in the document.",
        "Identify root causes of any NPT events mentioned."
    ]

    print("--- 🧠 Running AI Agent Analysis (Gemini 2.5) ---")
    
    # We use '5whys' as the methodology to trigger the Deep Analysis logic in RCA Lead
    # The 'user_data' here acts as the prompt for what to look for
    try:
        result = await coordinator.run_automated_audit(
            methodology="5whys", 
            user_data=user_observation, 
            context=incident_context
        )
        
        print("\n\n--- 🏁 FINAL RCA REPORT ---")
        print(result.get("analysis", "No analysis returned."))
        
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_bakte9_simulation())
