from typing import AsyncGenerator, List, Callable, Optional
import logging
import httpx
import json

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.entities.message import Message
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        
    async def generate_stream(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        if budget_limit is not None:
            # We enforce that num_predict limit is maxed at budget_limit
            # Ollama uses num_predict for Max Tokens
            payload["options"]["num_predict"] = budget_limit
        
        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                            
                        if data.get("done") is True and on_usage_callback:
                            prompt_eval = data.get("prompt_eval_count", 0)
                            eval_count = data.get("eval_count", 0)
                            on_usage_callback(prompt_eval, eval_count)
                            
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    async def generate(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        url = f"{self.base_url}/api/chat"
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if budget_limit is not None:
            payload["options"]["num_predict"] = budget_limit
        
        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if data.get("done") is True and on_usage_callback:
                    prompt_eval = data.get("prompt_eval_count", 0)
                    eval_count = data.get("eval_count", 0)
                    on_usage_callback(prompt_eval, eval_count)
                    
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise 