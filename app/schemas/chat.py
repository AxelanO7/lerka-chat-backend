from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model_id: str = Field(..., description="e.g., 'openai/gpt-4o-mini' or 'llama3.1'")
    temperature: float = 0.7
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    use_rag: bool = True

class CompareRequest(BaseModel):
    prompt: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    models: Optional[List[str]] = None  # Frontend-selected model IDs
    temperature: float = 0.7
    is_curated: bool = False
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    use_rag: bool = True