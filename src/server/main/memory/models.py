from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CustomizeMemoryRequest(BaseModel):
    information: str

class ShortTermMemoryRequest(BaseModel):
    category: Optional[str] = None
    limit: Optional[int] = 10

class ResetMemoryRequest(BaseModel):
    clear_graph: bool

class AddShortTermMemoryRequest(BaseModel):
    text: str
    category: str
    retention_days: int

class UpdateShortTermMemoryRequest(BaseModel):
    id: str
    text: str
    retention_days: int

class DeleteShortTermMemoryRequest(BaseModel):
    memory_id: str