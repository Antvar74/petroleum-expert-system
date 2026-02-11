import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai
from utils.llm_gateway import LLMGateway

# Load environment variables from .env file
load_dotenv()

async def verify_gemini():
    print(f"Checking API Key: {'FOUND' if os.getenv('GEMINI_API_KEY') else 'MISSING'}")
    
    gateway = LLMGateway()
    
    print("\n--- Testing Gemini (Fast Mode -> 2.5 Flash) ---")
    try:
        fast_response = await gateway.generate_analysis(
            prompt="Explain difference between porosity and permeability in 10 words.",
            mode="fast"
        )
        print(f"Response:\n{fast_response}")
    except Exception as e:
        print(f"Fast Mode Failed: {e}")

    print("\n--- Testing Gemini (Reasoning Mode -> 2.5 Flash) ---")
    try:
        reasoning_response = await gateway.generate_analysis(
            prompt="Analyze risks of high pressure zone drilling. List 1 main risk.",
            mode="reasoning"
        )
        print(f"Response:\n{reasoning_response}")
    except Exception as e:
        print(f"Reasoning Mode Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_gemini())
