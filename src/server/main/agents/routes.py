import datetime
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from .models import AddTaskRequest, UpdateTaskRequest, TaskIdRequest
from ..config import INTEGRATIONS_CONFIG
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
    task = await mongo_manager.task_collection.find_one(
        {"task_id": request.taskId, "user_id": user_id, "status": "approval_pending"}
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not pending approval.")

    # --- NEW: Check if all required tools are connected ---
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

    required_tools = {step['tool'] for step in task.get('plan', [])}
    missing_tools = []

    for tool_name in required_tools:
        tool_config = INTEGRATIONS_CONFIG.get(tool_name, {})
        is_builtin = tool_config.get("auth_type") == "builtin"
        is_connected = user_integrations.get(tool_name, {}).get("connected", False)

        if not (is_builtin or is_connected):
            missing_tools.append(tool_config.get("display_name", tool_name))

    if missing_tools:
        error_detail = f"Cannot approve task. Please connect the following tools first: {', '.join(missing_tools)}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_detail)

    # Enqueue the task for execution by the celery worker
    execute_task_plan.delay(request.taskId, user_id)

    # Update the status to 'pending' to indicate it's in the queue
    result = await mongo_manager.task_collection.update_one(
        {"task_id": request.taskId, "user_id": user_id, "status": "approval_pending"},
        {"$set": {"status": "pending", "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
    )
    return {"message": "Task approved and has been queued for execution."}

@router.post("/rerun-task")
async def rerun_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    original_task = await mongo_manager.task_collection.find_one({"task_id": request.taskId, "user_id": user_id})
    if not original_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original task not found.")

    new_task_id = str(uuid.uuid4())
    new_task_doc = original_task.copy()
    new_task_doc.pop("_id", None)
    new_task_doc["task_id"] = new_task_id
    new_task_doc["status"] = "approval_pending"
    new_task_doc["created_at"] = new_task_doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    new_task_doc["progress_updates"] = []
    new_task_doc["result"] = None
    new_task_doc["error"] = None

    await mongo_manager.task_collection.insert_one(new_task_doc)
    return {"message": "Task has been duplicated for re-run.", "new_task_id": new_task_id}

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