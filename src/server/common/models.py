from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import datetime # Use the standard datetime

class UserProfileData(BaseModel):
    onboardingAnswers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    onboardingComplete: Optional[bool] = False
    personalInfo: Optional[Dict[str, Any]] = Field(default_factory=dict)
    active_chat_id: Optional[str] = None
    last_active_timestamp: Optional[datetime.datetime] = None
    # Storing data source enabled status in user profile
    data_sources_config: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)

class UserProfile(BaseModel):
    user_id: str = Field(..., description="The Auth0 user ID (sub claim)")
    userData: UserProfileData = Field(default_factory=UserProfileData)
    createdAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_updated: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @validator('createdAt', 'last_updated', pre=True, always=True)
    def ensure_datetime_objects(cls, v):
        if isinstance(v, str):
            return datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
        if isinstance(v, datetime.datetime):
            return v
        return datetime.datetime.now(datetime.timezone.utc)


class ChatMessageInput(BaseModel):
    input: str
    # Client sends these, main server might pass them to chat server if chat server uses them for rate limiting etc.
    pricing: Optional[str] = "free" 
    credits: Optional[int] = 0

class OnboardingRequest(BaseModel):
    data: Dict[str, Any]

class DataSourceToggleRequest(BaseModel):
    source: str
    enabled: bool

class NotificationData(BaseModel):
    user_id: str
    message: str
    type: str 
    details: Optional[Dict[str, Any]] = None

class PollingEvent(BaseModel):
    user_id: str
    service_name: str
    event_type: str
    event_id: str
    data: Dict[str, Any]
    timestamp_utc: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class EncryptionRequest(BaseModel):
    data: str

class DecryptionRequest(BaseModel):
    encrypted_data: str

class SetReferrerRequest(BaseModel):
    referral_code: str