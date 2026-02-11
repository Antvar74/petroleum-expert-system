import os
import httpx
import google.generativeai as genai
from typing import Optional, Dict, Any

class LLMGateway:
    """
    Gateway to route LLM requests to the best available provider:
    - Gemini 2.0 Flash (Speed)
    - Gemini 1.5 Pro (Reasoning)
    - Ollama (Local Fallback)
    """
    
    def __init__(self):
        self._setup_gemini()
        self.ollama_base_url = "http://localhost:11434"
        self.ollama_model = "deepseek-r1:14b"
        self.timeout = 120.0

    def _setup_gemini(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            # Using gemini-2.5-flash for BOTH modes as it's the only one currently passing quota checks
            self.gemini_flash = genai.GenerativeModel('gemini-2.5-flash')
            self.gemini_pro = genai.GenerativeModel('gemini-2.5-flash') 
            print("✅ Gemini API Configured (Using Gemini 2.5 Flash)")
        else:
            print("⚠️ Gemini API Key not found. Using Local Fallback.")

    async def generate_analysis(self, prompt: str, system_prompt: Optional[str] = None, mode: str = "fast") -> str:
        """
        Generates analysis using the appropriate model based on 'mode'.
        mode: 'fast' (Flash), 'reasoning' (Pro), 'local' (Ollama)
        """
        
        # 1. Try Gemini if configured and mode is not forced local
        if self.gemini_key and mode != "local":
            try:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
                
                if mode == "reasoning":
                    response = await self.gemini_pro.generate_content_async(full_prompt)
                else:
                    response = await self.gemini_flash.generate_content_async(full_prompt)
                    
                return response.text
            except Exception as e:
                if "429" in str(e):
                    # Rate Limit Hit - Do NOT fallback to Ollama if user likely doesn't have it
                    print("🚦 Rate Limit Hit (429). Advise user to wait.")
                    return "⚠️ **API RATE LIMIT EXCEEDED** (Gemini Free Tier).\n\nPlease wait **30-60 seconds** and try again.\n(The system paused to prevent spamming the API).\n\nDetails: Quota exceeded for 'gemini-2.5-flash'."
                
                print(f"❌ Gemini Error: {e}. Falling back to Local LLM.")

        # 2. Fallback to Ollama (Only if not rate limited or explicit local mode)
        return await self._call_ollama(prompt, system_prompt)

    async def _call_ollama(self, prompt: str, system_prompt: Optional[str]) -> str:
        # Check if Ollama is even running first
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(self.ollama_base_url)
        except:
             return "⚠️ **Connection Error**: Could not connect to Gemini (Rate Limited?) and Local LLM (Ollama) is not running.\n\n**Solution**: update your API Key or wait 60 seconds."

        url = f"{self.ollama_base_url}/api/chat"
        # ... Rest of Ollama logic
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 2048}
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "Error: No response from model.")
        except Exception as e:
            return f"Error connecting to Local LLM (Ollama): {str(e)}"
