import httpx
import json
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from .context import Context, MessageRole


class LLMProvider(ABC):
    """Abstract base class for LLM providers following MCP."""
    
    @abstractmethod
    async def generate_response(self, context: Context) -> str:
        """Generate a response from the LLM using the provided context."""
        pass


class OllamaProvider(LLMProvider):
    """Provider for Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3:12b"):
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api/chat"
    
    async def generate_response(self, context: Context) -> str:
        """Generate a response from Ollama with streaming support."""
        payload = {
            "model": self.model,
            "messages": context.get_formatted_messages(),
            "temperature": context.temperature,
            "stream": True
        }
        
        full_response = ""
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self.api_url, json=payload, timeout=240.0) as response:
                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")
                
                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    
                    try:
                        chunk_data = json.loads(chunk)
                        content = chunk_data.get("message", {}).get("content", "")
                        print(content, end="", flush=True)
                        full_response += content
                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        continue
                    
                    # Check if this is the final chunk
                    if chunk_data.get("done", False):
                        break
        
        print()  # Add a newline at the end
        return full_response


class ProviderFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> LLMProvider:
        """Create a provider based on the specified type."""
        if provider_type.lower() == "ollama":
            return OllamaProvider(**kwargs)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")