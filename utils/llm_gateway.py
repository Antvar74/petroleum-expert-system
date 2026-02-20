import os
import httpx
import google.generativeai as genai
from typing import Optional, Dict, Any, List

class LLMGateway:
    """
    Gateway to route LLM requests to the best available provider:
    - Gemini 2.5 Flash (Primary)
    - Ollama (Local Fallback — only if running)
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
            # Model instances are created per-call now to support system_instruction
            print("✅ Gemini API Configured (Using Gemini 2.5 Flash)")
        else:
            print("⚠️ Gemini API Key not found.")

    async def get_available_providers(self) -> List[Dict[str, str]]:
        """Return list of available LLM providers. Ollama only shown if running."""
        providers = [{"id": "auto", "name": "Auto (Best Available)", "name_es": "Auto (Mejor Disponible)"}]
        if self.gemini_key:
            providers.append({"id": "gemini", "name": "Google Gemini", "name_es": "Google Gemini"})
        # Check if Ollama is actually running
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(self.ollama_base_url)
            providers.append({"id": "ollama", "name": "Ollama (Local)", "name_es": "Ollama (Local)"})
        except Exception:
            pass  # Ollama not running — don't show it
        return providers

    async def generate_analysis(self, prompt: str, system_prompt: Optional[str] = None, mode: str = "fast", provider: str = "auto") -> str:
        """
        Generates analysis using the specified or best available provider.
        provider: "auto" | "gemini" | "ollama"
        Priority (auto): Gemini → Ollama
        """

        # Helper to try Gemini
        async def try_gemini():
            if not self.gemini_key: return None, "Gemini Key Missing"
            try:
                # Use system_instruction parameter instead of concatenating to prompt
                model_kwargs = {}
                if system_prompt:
                    model_kwargs["system_instruction"] = system_prompt
                model = genai.GenerativeModel('gemini-2.5-flash', **model_kwargs)
                response = await model.generate_content_async(prompt)
                return response.text, None
            except Exception as e:
                return None, str(e)

        # Helper to try Ollama
        async def try_ollama():
            try:
                res = await self._call_ollama(prompt, system_prompt)
                if "Error" in res or "⚠️" in res: return None, res
                return res, None
            except Exception as e:
                return None, str(e)

        # --- EXPLICIT PROVIDER SELECTION ---
        if provider == "gemini":
            res, err = await try_gemini()
            if res: return res
            return f"❌ **Gemini Failed**: {err}"

        if provider == "ollama":
            return await self._call_ollama(prompt, system_prompt)

        # --- AUTO MODE (CASCADE): Gemini → Ollama ---
        errors = []

        # 1. Gemini (Primary)
        if self.gemini_key and mode != "local":
            res, err = await try_gemini()
            if res: return res
            errors.append(f"Gemini: {err}")

        # 2. Ollama (Fallback)
        res, err = await try_ollama()
        if res: return res
        errors.append(f"Ollama: {err}")

        return f"⚠️ **All Providers Failed**\n\nDetails:\n- " + "\n- ".join(errors)

    async def _call_ollama(self, prompt: str, system_prompt: Optional[str]) -> str:
        # Check if Ollama is even running first
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(self.ollama_base_url)
        except:
             return "⚠️ **Ollama Not Running**: Could not connect to local Ollama server.\n\n**Solution**: Start Ollama with `ollama serve` or select a different provider."

        url = f"{self.ollama_base_url}/api/chat"

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
