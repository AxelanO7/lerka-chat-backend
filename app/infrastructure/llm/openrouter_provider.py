import logging
import httpx
import json
from typing import AsyncGenerator, List, Callable, Optional

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.entities.message import Message
from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = settings.OPENROUTER_API_KEY

    async def generate_stream(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "temperature": temperature
        }
        
        if budget_limit is not None:
            payload["max_tokens"] = budget_limit
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                            
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                            
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                                    
                            # Optional usage tracking if openrouter sends it (often not sent during stream without specific stream_options)
                            usage = data.get("usage")
                            if usage and on_usage_callback:
                                prompt_eval = usage.get("prompt_tokens", 0)
                                eval_count = usage.get("completion_tokens", 0)
                                on_usage_callback(prompt_eval, eval_count)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode JSON from stream: {data_str}")
                            continue
                            
        except Exception as e:
            logger.error(f"OpenRouter stream error: {e}")
            raise

    async def generate(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
            "temperature": temperature
        }
        
        if budget_limit is not None:
            payload["max_tokens"] = budget_limit
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                usage = data.get("usage")
                if usage and on_usage_callback:
                    prompt_eval = usage.get("prompt_tokens", 0)
                    eval_count = usage.get("completion_tokens", 0)
                    on_usage_callback(prompt_eval, eval_count)
                    
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise
