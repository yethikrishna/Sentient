from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class WhatsAppNumberRequest(BaseModel):
    whatsapp_number: Optional[str] = ""
class ProfileUpdateRequest(BaseModel):
    onboardingAnswers: Dict[str, Any]
    personalInfo: Dict[str, Any]
    preferences: Dict[str, Any]

class LinkedInUrlRequest(BaseModel):
    linkedin_url: Optional[str] = ""
class AIPersonalitySettingsRequest(BaseModel):
    agentName: str
    humorLevel: str
    useEmojis: bool
    quietHours: Dict[str, Any]
    notificationControls: Dict[str, bool]