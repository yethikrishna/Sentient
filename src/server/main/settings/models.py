from pydantic import BaseModel
from typing import Optional

class WhatsAppNumberRequest(BaseModel):
    whatsapp_number: Optional[str] = ""