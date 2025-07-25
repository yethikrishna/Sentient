from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class MemberInviteRequest(BaseModel):
    user_id: str

class ContextItemCreateRequest(BaseModel):
    type: str # 'text' or 'gdrive'
    content: Any
