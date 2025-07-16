from pydantic import BaseModel, Field
from typing import Optional, List

class BlockModel(BaseModel):
    block_id: str
    content: str
    order: int

class CreateBlockRequest(BaseModel):
    content: str
    page_date: str # YYYY-MM-DD
    order: int
    processWithAI: bool = False
    linked_task_id: Optional[str] = None
    task_status: Optional[str] = None
    
class UpdateBlockRequest(BaseModel):
    content: str