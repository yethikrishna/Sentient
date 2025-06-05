# src/server/main/models.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import datetime

# --- User Profile Models (Core) ---
class GoogleServiceTokenData(BaseModel):
    encrypted_refresh_token: Optional[str] = None

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
    data_sources_config: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)
    encrypted_refresh_token: Optional[str] = None # Auth0 refresh token (auth module will handle specifics)
    google_services: Optional[UserGoogleServicesData] = Field(default_factory=UserGoogleServicesData)

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

# --- API Request/Response Models (General/Miscellaneous) ---
# Specific models will be moved to their respective modules (auth, chat, voice)

class OnboardingRequest(BaseModel):
    data: Dict[str, Any] 

class DataSourceToggleRequest(BaseModel):
    source: str 
    enabled: bool

# Models that were in the original main.models.py and are not moved yet:
# ChatMessageInput -> moved to chat/models.py
# EncryptionRequest -> moved to auth/models.py
# DecryptionRequest -> moved to auth/models.py
# AuthTokenStoreRequest -> moved to auth/models.py
# GoogleTokenStoreRequest -> moved to auth/models.py
# VoiceOfferRequest -> moved to voice/models.py
# VoiceAnswerResponse -> moved to voice/models.py