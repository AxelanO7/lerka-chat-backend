import logging
import httpx
import json
from typing import AsyncGenerator, List

from app.domain.interfaces.llm_provider import LLMProvider
from app.schemas.chat import ChatMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = settings.OPENROUTER_API_KEY

    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        model_id: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Filter out empty messages to avoid OpenRouter 400 errors
        valid_messages = [msg for msg in messages if msg.content.strip()]
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in valid_messages]
        
        payload = {
            "model": model_id,
            "messages": formatted_messages,
            "stream": True,
            "temperature": temperature
        }
        
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_detail = await response.aread()
                        logger.error(f"OpenRouter error {response.status_code}: {error_detail.decode()}")
                        yield f"Error from OpenRouter ({response.status_code}): {error_detail.decode()[:100]}"
                        return

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
                                    
                            usage = data.get("usage")
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                                
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode JSON from stream: {data_str}")
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e}")
            yield f"AI Service Error: {str(e)}"
        except Exception as e:
            logger.error(f"OpenRouter stream error: {e}")
            yield f"Connection Error: {str(e)}"
        finally:
            yield f"__USAGE__ {{\"prompt_tokens\": {prompt_tokens}, \"completion_tokens\": {completion_tokens}}}"