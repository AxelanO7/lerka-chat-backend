import logging
import httpx
import json
from typing import AsyncGenerator, List

from app.domain.interfaces.llm_provider import LLMProvider
from app.schemas.chat import ChatMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        
    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        model_id: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        payload = {
            "model": model_id,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:
                                yield content
                        
                        if data.get("done") is True:
                            prompt_tokens = data.get("prompt_eval_count", 0)
                            completion_tokens = data.get("eval_count", 0)
                            
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise
        finally:
            yield f"__USAGE__ {{\"prompt_tokens\": {prompt_tokens}, \"completion_tokens\": {completion_tokens}}}"