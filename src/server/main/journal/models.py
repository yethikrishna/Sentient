from pydantic import BaseModel, Field
from typing import Optional

class BlockModel(BaseModel):
    block_id: str
    content: str
    order: int

class CreateBlockRequest(BaseModel):
    content: str
    page_date: str # YYYY-MM-DD
    order: int
    
class UpdateBlockRequest(BaseModel):
    content: str