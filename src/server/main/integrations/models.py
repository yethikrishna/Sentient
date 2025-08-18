# src/server/main/integrations/models.py
from pydantic import BaseModel
from typing import Dict, Any, Optional

class ManualConnectRequest(BaseModel):
    service_name: str
    credentials: Dict[str, Any]

class OAuthConnectRequest(BaseModel):
    service_name: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None

class DisconnectRequest(BaseModel):
    service_name: str

class OAuth1StartRequest(BaseModel):
    service_name: str
    redirect_uri: str

class OAuth1FinishRequest(BaseModel):
    service_name: str
    oauth_token: str
    oauth_verifier: str

class ComposioInitiateRequest(BaseModel):
    service_name: str

class ComposioFinalizeRequest(BaseModel):
    service_name: str
    connectedAccountId: str