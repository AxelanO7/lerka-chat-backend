from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from app.domain.entities.message import Message
from app.core.config import settings

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)
    model: Optional[str] = Field(settings.DEFAULT_MODEL, description="Model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    use_rag: bool = Field(False, description="Enable RAG context retrieval")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "hello dear!"
                    }
                ],
                "model": settings.DEFAULT_MODEL,
                "temperature": 0.7,
                "use_rag": False
            }
        }
    )

class ChatResponse(BaseModel):
    message: Message 