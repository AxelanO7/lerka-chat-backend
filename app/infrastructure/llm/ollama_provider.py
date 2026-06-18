import asyncio
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
        # Force IPv4 loopback: "localhost" can resolve to IPv6 (::1) first, but Ollama
        # listens only on 127.0.0.1, producing spurious "All connection attempts failed".
        base = settings.OLLAMA_BASE_URL.rstrip("/")
        self.base_url = base.replace("//localhost:", "//127.0.0.1:")
        
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

        # Retry the connect phase only. On a cold start Ollama loads the model into RAM
        # and can briefly refuse parallel connections (compare fires models concurrently),
        # which surfaced as a first-message "All connection attempts failed".
        max_attempts = 4
        started = False
        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        async with client.stream("POST", url, json=payload) as response:
                            if response.status_code != 200:
                                error_detail = await response.aread()
                                logger.error(f"Ollama error {response.status_code}: {error_detail.decode()}")
                                yield f"Error from Ollama ({response.status_code}): {error_detail.decode()[:100]}"
                                return

                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                started = True
                                data = json.loads(line)

                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    if content:
                                        yield content

                                if data.get("done") is True:
                                    prompt_tokens = data.get("prompt_eval_count", 0)
                                    completion_tokens = data.get("eval_count", 0)
                    return
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as conn_err:
                    # Only safe to retry if we haven't streamed any tokens yet.
                    if started or attempt == max_attempts:
                        raise
                    logger.warning(f"Ollama connect failed ({model_id}) attempt {attempt}/{max_attempts}: {conn_err}. Retrying...")
                    await asyncio.sleep(1.5 * attempt)
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"Ollama Connection Error: {str(e)}"
        finally:
            yield f"__USAGE__ {{\"prompt_tokens\": {prompt_tokens}, \"completion_tokens\": {completion_tokens}}}"