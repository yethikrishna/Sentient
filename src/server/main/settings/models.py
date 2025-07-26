from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class WhatsAppMcpRequest(BaseModel):
    whatsapp_mcp_number: Optional[str] = ""

class WhatsAppNotificationNumberRequest(BaseModel):
    whatsapp_notifications_number: Optional[str] = ""

class WhatsAppNotificationRequest(BaseModel):
    enabled: bool

class ProfileUpdateRequest(BaseModel):
    onboardingAnswers: Dict[str, Any]
    personalInfo: Dict[str, Any]
    preferences: Dict[str, Any]

class LinkedInUrlRequest(BaseModel):
    linkedin_url: Optional[str] = ""
class AIPersonalitySettingsRequest(BaseModel):
    agentName: str
    responseVerbosity: str
    humorLevel: str
    useEmojis: bool
    quietHours: Dict[str, Any]
    notificationControls: Dict[str, bool]
