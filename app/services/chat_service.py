from typing import AsyncGenerator, List
import logging

from app.infrastructure.llm.factory import get_llm_provider
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        pass

    async def stream_chat(
        self, 
        messages: List[ChatMessage], 
        model_id: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        provider = get_llm_provider(model_id)
        
        async for chunk in provider.generate_stream(
            messages=messages,
            model_id=model_id,
            temperature=temperature
        ):
            yield chunk