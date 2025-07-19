from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class NoteBase(BaseModel):
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)

class NoteCreate(NoteBase):
    note_date: str

class NoteUpdate(NoteBase):
    note_date: Optional[str] = None
    tags: Optional[List[str]] = None

class NoteInDB(BaseModel):
    note_id: str
    user_id: str
    title: str
    content: str
    note_date: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime
    linked_task_ids: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True