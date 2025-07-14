from pydantic import BaseModel
from typing import Dict, Any

class ContextInjectionRequest(BaseModel):
    service_name: str
    event_data: Dict[str, Any]
