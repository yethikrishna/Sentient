# src/server/main/proactivity/models.py
from pydantic import BaseModel

class SuggestionActionRequest(BaseModel):
    notification_id: str
    user_action: str # "approved" or "dismissed"
