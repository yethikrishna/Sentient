from pydantic import BaseModel, Field
from typing import Optional, Any

class ChatMessageInput(BaseModel):
    input: str
    chatId: Optional[Any] = None
    pricing: Optional[str] = "free" 
    credits: Optional[int] = 0
    enable_internet: Optional[bool] = False
    enable_weather: Optional[bool] = False
    enable_news: Optional[bool] = False
    enable_maps: Optional[bool] = False

class ChatHistoryRequest(BaseModel):
    chatId: Any

class RenameChatRequest(BaseModel):
    chatId: str
    newTitle: str

class DeleteChatRequest(BaseModel):
    chatId: str