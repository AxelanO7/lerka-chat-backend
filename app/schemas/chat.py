from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model_id: str = Field(..., description="e.g., 'openai/gpt-4o-mini' or 'llama3.1'")
    temperature: float = 0.7

class CompareRequest(BaseModel):
    prompt: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    temperature: float = 0.7
    is_curated: bool = False