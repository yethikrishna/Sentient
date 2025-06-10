from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TaskStep(BaseModel):
    tool: str
    description: str

class AddTaskRequest(BaseModel):
    description: str
    priority: int = 1
    plan: List[TaskStep]

class UpdateTaskRequest(BaseModel):
    taskId: str
    description: Optional[str] = None
    priority: Optional[int] = None
    plan: Optional[List[TaskStep]] = None

class TaskIdRequest(BaseModel):
    taskId: str