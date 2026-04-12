from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Callable, Optional
from app.domain.entities.message import Message

class LLMProvider(ABC):
    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate(
        self, 
        messages: List[Message], 
        model: str, 
        temperature: float,
        budget_limit: Optional[int] = None,
        on_usage_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        pass 