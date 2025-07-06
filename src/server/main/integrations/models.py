# src/server/main/integrations/models.py
from pydantic import BaseModel, Field
from typing import Dict, Any

class ManualConnectRequest(BaseModel):
    service_name: str
    credentials: Dict[str, Any]

class OAuthConnectRequest(BaseModel):
    service_name: str
    code: str
    redirect_uri: str

class DisconnectRequest(BaseModel):
    service_name: str

