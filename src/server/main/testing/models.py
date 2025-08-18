from pydantic import BaseModel
from typing import Dict, Any

class ContextInjectionRequest(BaseModel):
    service_name: str
    event_data: Dict[str, Any]

class WhatsAppTestRequest(BaseModel):
    phone_number: str
class TestNotificationRequest(BaseModel):
    type: str
