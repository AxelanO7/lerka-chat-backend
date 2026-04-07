from typing import AsyncGenerator, List
import logging

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.entities.message import Message
from app.schemas.chat import ChatRequest
from app.core.config import settings
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, llm_provider: LLMProvider, rag_service: RAGService):
        self.provider = llm_provider
        self.rag_service = rag_service

    async def _prepare_messages(self, messages: List[Message], use_rag: bool) -> List[Message]:
        if not use_rag or not messages:
            return messages
            
        last_message = messages[-1]
        if last_message.role == "user":
            context = await self.rag_service.retrieve_context(last_message.content)
            if context:
                context_str = "  ".join(context)
                augmented_content = f"Context information: {context_str}  Based on the above context, please answer the question: {last_message.content}"
                augmented_messages = messages[:-1] + [Message(role="user", content=augmented_content)]
                return augmented_messages
                
        return messages

    async def process_chat_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        # Handle Swagger UI default "string" by using DEFAULT_MODEL instead
        if request.model is None or request.model == "string" or request.model.strip() == "":
            model_to_use = settings.DEFAULT_MODEL
        else:
            model_to_use = request.model
            
        temperature_to_use = request.temperature if request.temperature is not None else 0.7
        
        messages = await self._prepare_messages(request.messages, request.use_rag)
        
        try:
            async for chunk in self.provider.generate_stream(
                messages=messages,
                model=model_to_use,
                temperature=temperature_to_use
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Error in ChatService streaming: {e}")
            raise 