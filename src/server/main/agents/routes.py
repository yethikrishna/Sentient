import datetime
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from .models import AddTaskRequest, UpdateTaskRequest, TaskIdRequest
from ..db import MongoManager
from ..dependencies import mongo_manager
from ..auth.utils import PermissionChecker
from ...celery_app import celery_app
from ...workers.executor.tasks import execute_task_plan

router = APIRouter(
    prefix="/agents",
    tags=["Agents & Tasks"]
)

@router.post("/add-task", status_code=status.HTTP_201_CREATED)
async def add_task(
    request: AddTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    task_id = str(uuid.uuid4())
    task_doc = {
        "task_id": task_id,
        "user_id": user_id,
        "description": request.description,
        "status": "approval_pending",  # New tasks start as plans needing approval
        "priority": request.priority,
        "plan": [step.dict() for step in request.plan],
        "progress_updates": [],
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        "result": None,
        "error": None,
        "agent_id": None
    }
    await mongo_manager.task_collection.insert_one(task_doc)
    return {"message": "Task created successfully", "task_id": task_id}

@router.post("/fetch-tasks")
async def fetch_tasks(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    tasks_cursor = mongo_manager.task_collection.find({"user_id": user_id})
    tasks = await tasks_cursor.to_list(length=None)
    for task in tasks:
        # Pydantic models in FastAPI handle ObjectId serialization, but it's good practice
        # to ensure it's a string if we are manually constructing the response.
        if "_id" in task:
            task["_id"] = str(task["_id"])
    return {"tasks": tasks}

@router.post("/update-task")
async def update_task(
    request: UpdateTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    update_data = {}
    if request.description is not None:
        update_data["description"] = request.description
    if request.priority is not None:
        update_data["priority"] = request.priority
    if request.plan is not None:
        update_data["plan"] = [step.dict() for step in request.plan]

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
    
    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)

    result = await mongo_manager.task_collection.update_one(
        {"task_id": request.taskId, "user_id": user_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    
    return {"message": "Task updated successfully."}

@router.post("/delete-task")
async def delete_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    result = await mongo_manager.task_collection.delete_one(
        {"task_id": request.taskId, "user_id": user_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return {"message": "Task deleted successfully."}

@router.post("/approve-task")
async def approve_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    # Ensure the task exists and is pending approval before proceeding
    task = await mongo_manager.task_collection.find_one({"task_id": request.taskId, "user_id": user_id, "status": "approval_pending"})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not pending approval.")

    # Enqueue the task for execution by the celery worker
    execute_task_plan.delay(request.taskId, user_id)

    # Update the status to 'pending' to indicate it's in the queue
    result = await mongo_manager.task_collection.update_one(
        {"task_id": request.taskId, "user_id": user_id, "status": "approval_pending"},
        {"$set": {"status": "pending", "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
    )
    return {"message": "Task approved and has been queued for execution."}

@router.post("/get-task-approval-data")
async def get_task_approval_data(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    task = await mongo_manager.task_collection.find_one(
        {"task_id": request.taskId, "user_id": user_id}
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    approval_data = task.get("approval_data", {"info": "This is a placeholder for dynamic approval data. The current plan seems reasonable."})
    
    return {"approval_data": approval_data}