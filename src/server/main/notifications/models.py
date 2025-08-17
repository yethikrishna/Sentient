from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateNotificationRequest(BaseModel):
    user_id: str
    message: str
    task_id: Optional[str] = None # Link notification to a task if applicable
    notification_type: Optional[str] = "general"
    payload: Optional[Dict[str, Any]] = None

class DeleteNotificationRequest(BaseModel):
    notification_id: Optional[str] = None
    delete_all: Optional[bool] = False
