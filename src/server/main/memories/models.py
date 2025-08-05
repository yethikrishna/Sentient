from pydantic import BaseModel
from typing import Optional

class CreateMemoryRequest(BaseModel):
    content: str
    source: Optional[str] = "manual"

class UpdateMemoryRequest(BaseModel):
    content: str