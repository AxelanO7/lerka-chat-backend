from pydantic import BaseModel, Field
from typing import List, Optional
from app.domain.entities.message import Message

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)
    model: Optional[str] = Field(None, description="Model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    use_rag: bool = Field(False, description="Enable RAG context retrieval")

class ChatResponse(BaseModel):
    message: Message 