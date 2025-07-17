from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

class NoteBase(BaseModel):
    title: str
    content: str

class NoteCreate(NoteBase):
    note_date: str

class NoteUpdate(NoteBase):
    note_date: Optional[str] = None

class NoteInDB(BaseModel):
    note_id: str
    user_id: str
    title: str
    content: str
    note_date: str
    linked_task_ids: List[str] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True