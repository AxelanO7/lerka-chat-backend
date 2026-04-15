from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from app.schemas.chat import ChatMessage

class LLMProvider(ABC):
    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        model_id: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        pass