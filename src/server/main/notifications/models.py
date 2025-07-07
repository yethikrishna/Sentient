from pydantic import BaseModel, Field
from typing import Optional

class CreateNotificationRequest(BaseModel):
    user_id: str
    message: str
    task_id: Optional[str] = None # Link notification to a task if applicable

class DeleteNotificationRequest(BaseModel):
    notification_id: str