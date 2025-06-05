# src/server/main/chat/models.py
# src/server/main/chat/models.py
from pydantic import BaseModel, Field
from typing import Optional

class ChatMessageInput(BaseModel):
    input: str
    pricing: Optional[str] = "free" 
    credits: Optional[int] = 0