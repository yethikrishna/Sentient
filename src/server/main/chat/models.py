from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict

class ChatMessageInput(BaseModel):
    messages: List[Dict[str, Any]]  # The full conversation history for context
    pricing: Optional[str] = "free"
    credits: Optional[int] = 0

class DeleteMessageRequest(BaseModel):
    message_id: Optional[str] = None
    clear_all: Optional[bool] = False
