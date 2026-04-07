from pydantic import BaseModel
from typing import Literal

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str 