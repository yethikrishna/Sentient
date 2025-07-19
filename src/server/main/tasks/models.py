from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TaskStep(BaseModel):
    tool: str
    description: str

class Answer(BaseModel):
    question_id: str
    answer_text: str

class AddTaskRequest(BaseModel):
    prompt: str
    assignee: str # "ai" or "user"

class AnswerClarificationsRequest(BaseModel):
    task_id: str
    answers: List[Answer]

class UpdateTaskRequest(BaseModel):
    taskId: str
    description: Optional[str] = None
    priority: Optional[int] = None
    plan: Optional[List[TaskStep]] = None
    schedule: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    assignee: Optional[str] = None

class TaskIdRequest(BaseModel):
    taskId: str
class TaskActionRequest(BaseModel):
    taskId: str
    action: str

class TaskChatRequest(BaseModel):
    taskId: str
    message: str
