from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class WhatsAppNumberRequest(BaseModel):
    whatsapp_number: Optional[str] = ""
class ProfileUpdateRequest(BaseModel):
    onboardingAnswers: Dict[str, Any]
    personalInfo: Dict[str, Any]
    preferences: Dict[str, Any]
