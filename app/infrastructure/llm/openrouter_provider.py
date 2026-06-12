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

    def get_fallback_chain(self, model_id: str) -> List[str]:
        """
        Determines the fallback order: primary -> alternative -> nano-class.
        Primary: model_id
        Alternative: google/gemma-4-26b-a4b-it
        Nano: google/gemma-4-26b-a4b-it
        """
        chain = [model_id]
        alternative = "google/gemma-4-26b-a4b-it"
        nano = "google/gemma-4-26b-a4b-it"
        
        if alternative not in chain:
            chain.append(alternative)
        if nano not in chain:
            chain.append(nano)
        return chain

    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        model_id: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lerka.ai",
            "X-Title": "Lerka Chat"
        }
        
        # 1. Filter and ensure a stable prompt prefix
        # We ensure the system prompt is present, stable, and comes first.
        system_msg = next((msg for msg in messages if msg.role == "system"), None)
        user_and_assistant_msgs = [msg for msg in messages if msg.role != "system" and msg.content.strip()]
        
        stable_messages = []
        if system_msg and system_msg.content.strip():
            stable_messages.append({"role": "system", "content": system_msg.content.strip()})
        else:
            # Add a default stable system prefix to optimize provider prompt caching
            stable_messages.append({"role": "system", "content": "You are Lerka AI, a helpful comparison assistant."})
            
        for msg in user_and_assistant_msgs:
            stable_messages.append({"role": msg.role, "content": msg.content})

        fallback_chain = self.get_fallback_chain(model_id)
        last_error = None
        yielded_any = False
        prompt_tokens = 0
        completion_tokens = 0

        for current_model in fallback_chain:
            payload = {
                "model": current_model,
                "messages": stable_messages,
                "stream": True,
                "temperature": temperature,
                "max_tokens": 1024,
                "provider": {
                    "allow_fallbacks": False
                }
            }
            
            logger.info(f"Attempting OpenRouter stream completion with model: {current_model}")
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_detail = await response.aread()
                            error_msg = error_detail.decode()
                            logger.error(f"OpenRouter error {response.status_code} for {current_model}: {error_msg}")
                            raise httpx.HTTPStatusError(
                                f"Status {response.status_code}: {error_msg}", 
                                request=response.request, 
                                response=response
                            )

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
                                        yielded_any = True
                                        
                                usage = data.get("usage")
                                if usage:
                                    prompt_tokens = usage.get("prompt_tokens", 0)
                                    completion_tokens = usage.get("completion_tokens", 0)
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON from stream: {data_str}")
                                continue
                # If we successfully completed the call (with or without tokens), we stop the fallback chain
                break
                
            except Exception as e:
                logger.error(f"Exception during stream with model {current_model}: {e}")
                last_error = e
                # If we have already yielded tokens, we cannot fall back to a different model mid-stream.
                if yielded_any:
                    yield f"\n[Stream interrupted: {str(e)}]"
                    break
                # Otherwise, continue to the next model in the fallback chain
                logger.info(f"Falling back from {current_model} due to error.")
                continue
        else:
            # If all models in the fallback chain failed and nothing was yielded
            if not yielded_any:
                logger.critical("All models in the OpenRouter fallback chain failed.")
                yield "Layanan sibuk, coba lagi nanti."
        
        # Always output the final structured usage line as contract requires
        yield f"__USAGE__ {{\"prompt_tokens\": {prompt_tokens}, \"completion_tokens\": {completion_tokens}}}"