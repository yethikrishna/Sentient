from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import datetime

# --- Integration Models ---
class GoogleAuthSettings(BaseModel):
    mode: str
    credentialsJson: Optional[str] = None
# ADDED: Model for Supermemory MCP settings
class SupermemorySettings(BaseModel):
    mcp_url: Optional[str] = None

class IntegrationData(BaseModel):
    encrypted_token: str
    connected_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class GoogleAuthData(BaseModel):
    mode: str = Field(default="default")
    encryptedCredentials: Optional[str] = None

# --- User Profile Models (Core) ---
class UserProfileData(BaseModel):
    onboardingAnswers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    onboardingComplete: Optional[bool] = False
    personalInfo: Optional[Dict[str, Any]] = Field(default_factory=dict)
    active_chat_id: Optional[str] = None
    last_active_timestamp: Optional[datetime.datetime] = None
    integrations: Optional[Dict[str, IntegrationData]] = Field(default_factory=dict)
    googleAuth: Optional[GoogleAuthData] = Field(default_factory=GoogleAuthData)
    encrypted_refresh_token: Optional[str] = None
    # Field for Supermemory MCP URL, will store the full URL.
    supermemory_mcp_url: Optional[str] = None

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

class OnboardingRequest(BaseModel):
    data: Dict[str, Any]