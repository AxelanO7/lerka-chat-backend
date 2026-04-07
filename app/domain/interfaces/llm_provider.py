from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from app.domain.entities.message import Message

class LLMProvider(ABC):
    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float
    ) -> str:
        pass 