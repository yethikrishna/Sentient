# src/server/main/models.py
# src/server/main/models.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import datetime

# --- User Profile Models ---
class GoogleServiceTokenData(BaseModel):
    encrypted_refresh_token: Optional[str] = None
    # access_token: Optional[str] = None # Not typically stored long-term
    # expiry_timestamp: Optional[datetime.datetime] = None # If access token is stored

class UserGoogleServicesData(BaseModel):
    gmail: Optional[GoogleServiceTokenData] = None
    calendar: Optional[GoogleServiceTokenData] = None
    # Add other services as needed

class UserProfileData(BaseModel):
    onboardingAnswers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    onboardingComplete: Optional[bool] = False
    personalInfo: Optional[Dict[str, Any]] = Field(default_factory=dict)
    active_chat_id: Optional[str] = None
    last_active_timestamp: Optional[datetime.datetime] = None
    data_sources_config: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict) # e.g. {"gmail": {"enabled": True}}
    encrypted_refresh_token: Optional[str] = None # Auth0 refresh token
    google_services: Optional[UserGoogleServicesData] = Field(default_factory=UserGoogleServicesData) # For Google service tokens

class UserProfile(BaseModel):
    user_id: str = Field(..., description="The Auth0 user ID (sub claim)")
    userData: UserProfileData = Field(default_factory=UserProfileData)
    createdAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_updated: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @validator('createdAt', 'last_updated', pre=True, always=True)
    def ensure_datetime_objects(cls, v):
        if isinstance(v, str):
            try:
                return datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid datetime string format: {v}")
        if isinstance(v, datetime.datetime):
            return v
        return datetime.datetime.now(datetime.timezone.utc)

# --- API Request/Response Models ---
class ChatMessageInput(BaseModel):
    input: str
    pricing: Optional[str] = "free" 
    credits: Optional[int] = 0      

class OnboardingRequest(BaseModel):
    data: Dict[str, Any] 

class DataSourceToggleRequest(BaseModel):
    source: str 
    enabled: bool

class EncryptionRequest(BaseModel):
    data: str

class DecryptionRequest(BaseModel):
    encrypted_data: str

class AuthTokenStoreRequest(BaseModel): # For Auth0 refresh token
    refresh_token: str

class GoogleTokenStoreRequest(BaseModel): # ADDED: For Google refresh token
    service_name: str # e.g., "gmail", "calendar"
    google_refresh_token: str

class VoiceOfferRequest(BaseModel):
    sdp: str
    type: str

class VoiceAnswerResponse(BaseModel):
    sdp: str
    type: str