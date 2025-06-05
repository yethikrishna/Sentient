# src/server/main/models.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import datetime

# --- User Profile Models ---
class UserProfileData(BaseModel):
    onboardingAnswers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    onboardingComplete: Optional[bool] = False
    personalInfo: Optional[Dict[str, Any]] = Field(default_factory=dict)
    active_chat_id: Optional[str] = None
    last_active_timestamp: Optional[datetime.datetime] = None
    data_sources_config: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict) # e.g. {"gmail": {"enabled": True}}
    # Store encrypted refresh tokens here if main server manages them
    encrypted_refresh_token: Optional[str] = None
    encrypted_google_refresh_token: Optional[str] = None # For Gmail API

class UserProfile(BaseModel):
    user_id: str = Field(..., description="The Auth0 user ID (sub claim)")
    userData: UserProfileData = Field(default_factory=UserProfileData)
    createdAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_updated: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @validator('createdAt', 'last_updated', pre=True, always=True)
    def ensure_datetime_objects(cls, v):
        if isinstance(v, str):
            try:
                # Handle ISO format with or without 'Z'
                return datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                # Fallback for other string formats if necessary, or raise error
                raise ValueError(f"Invalid datetime string format: {v}")
        if isinstance(v, datetime.datetime):
            return v
        return datetime.datetime.now(datetime.timezone.utc)

# --- API Request/Response Models ---
class ChatMessageInput(BaseModel):
    input: str
    pricing: Optional[str] = "free" # Client might send this
    credits: Optional[int] = 0      # Client might send this

class OnboardingRequest(BaseModel):
    data: Dict[str, Any] # Expects a dictionary of answers

class DataSourceToggleRequest(BaseModel):
    source: str # e.g., "gmail"
    enabled: bool

class EncryptionRequest(BaseModel):
    data: str

class DecryptionRequest(BaseModel):
    encrypted_data: str

class AuthTokenStoreRequest(BaseModel):
    refresh_token: str
    # Optional: id_token, access_token if client wants server to have them initially
    # id_token: Optional[str] = None
    # access_token: Optional[str] = None

class VoiceOfferRequest(BaseModel):
    sdp: str
    type: str
    # webrtc_id: Optional[str] = None # If client generates and sends this

class VoiceAnswerResponse(BaseModel):
    sdp: str
    type: str