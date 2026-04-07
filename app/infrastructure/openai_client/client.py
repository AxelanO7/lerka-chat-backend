import openai
from openai import AsyncOpenAI
from typing import AsyncGenerator, List
import logging
import asyncio

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.entities.message import Message
from app.core.config import settings
from app.core.exceptions import ChatServiceException

logger = logging.getLogger(__name__)

class OpenAIClient(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.max_retries = 3

    async def stream_chat(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    temperature=temperature,
                    stream=True
                )
                
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return
            except openai.APIError as e:
                logger.error(f"OpenAI API Error (attempt {attempt+1}): {e}")
                if attempt == self.max_retries - 1:
                    raise ChatServiceException(f"LLM Provider API Error: {str(e)}", status_code=502)
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected Error in OpenAI Client: {e}")
                raise ChatServiceException("Internal Server Error communicating with LLM", status_code=500)

    async def chat(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float
    ) -> str:
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                stream=False
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Unexpected Error in OpenAI Client: {e}")
            raise ChatServiceException("Internal Server Error", status_code=500)
