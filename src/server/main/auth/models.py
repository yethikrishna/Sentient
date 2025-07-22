# src/server/main/auth/models.py
# src/server/main/auth/models.py
from pydantic import BaseModel
from typing import Dict, Any

class AuthTokenStoreRequest(BaseModel): # For Auth0 refresh token
    refresh_token: str

class EncryptionRequest(BaseModel):
    data: str

class DecryptionRequest(BaseModel):
    encrypted_data: str