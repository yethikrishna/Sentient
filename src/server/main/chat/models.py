from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict

class ChatMessageInput(BaseModel):
    messages: List[Dict[str, Any]] # The full conversation history for context
    chatId: Optional[Any] = None
    pricing: Optional[str] = "free"
    credits: Optional[int] = 0

class ChatHistoryRequest(BaseModel):
    chatId: Any
