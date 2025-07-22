from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import datetime

class IntegrationData(BaseModel):
    encrypted_token: Optional[str] = None
    connected_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    credentials: Optional[str] = None
    connected: bool = False
    auth_type: Optional[str] = None

class UserPreferences(BaseModel):
    communicationStyle: Optional[str] = "Casual & Friendly"
    corePriorities: List[str] = Field(default_factory=list)
    # New Persona & Interaction Settings
    agentName: Optional[str] = Field(default="Sentient")
    responseVerbosity: Optional[str] = Field(default="Balanced")  # Concise, Balanced, Detailed
    humorLevel: Optional[str] = Field(default="Balanced")  # Strictly Formal, Balanced, Witty & Humorous
    useEmojis: Optional[bool] = Field(default=True)
    # New Proactivity & Boundary Settings
    quietHours: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"enabled": False, "start": "22:00", "end": "08:00"})
    notificationControls: Optional[Dict[str, bool]] = Field(default_factory=lambda: {
        "taskNeedsApproval": True,
        "taskCompleted": True,
        "taskFailed": False,
        "proactiveSummary": False,
        "importantInsights": False,
    })

class UserProfileData(BaseModel):
    onboardingAnswers: Dict[str, Any] = Field(default_factory=dict)
    onboardingComplete: bool = False
    personalInfo: Dict[str, Any] = Field(default_factory=dict)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    last_active_timestamp: Optional[datetime.datetime] = None
    integrations: Dict[str, IntegrationData] = Field(default_factory=dict)
    encrypted_refresh_token: Optional[str] = None
    supermemory_user_id: Optional[str] = None
    privacyFilters: List[str] = Field(default_factory=list)

class UserProfile(BaseModel):
    user_id: str = Field(..., description="The Auth0 user ID (sub claim)")
    userData: UserProfileData = Field(default_factory=UserProfileData)
    createdAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_updated: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class OnboardingRequest(BaseModel):
    data: Dict[str, Any]