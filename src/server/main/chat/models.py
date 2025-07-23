from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
import datetime

class ChatMessageInput(BaseModel):
    messages: List[Dict[str, Any]] # The full conversation history for context
    chatId: Optional[str] = None
    pricing: Optional[str] = "free"
    credits: Optional[int] = 0

class ChatHistoryRequest(BaseModel):
    chatId: str

class RenameChatRequest(BaseModel):
    title: str

class ChatSessionInfo(BaseModel):
    chat_id: str
    title: str
    updated_at: datetime.datetime
