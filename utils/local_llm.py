import httpx
import json
import os
from typing import Dict, Any, Optional

class LocalLLMConnector:
    """
    Connects to a local LLM server (compatible with Ollama) 
    to provide automated analysis for v3.0.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "deepseek-r1:14b"):
        self.base_url = base_url
        self.model = model
        self.timeout = 120.0 # LLMs can take time

    async def generate_analysis(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Sends a request to Ollama to generate a response based on the prompt.
        """
        url = f"{self.base_url}/api/chat"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2048
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "Error: No response from model.")
        except Exception as e:
            return f"Error connecting to Local LLM (Ollama): {str(e)}"

    async def get_available_models(self) -> list:
        """Fetch list of models installed in Ollama"""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
                return []
        except:
            return []
