import datetime
import uuid
import json
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from .models import AddTaskRequest, UpdateTaskRequest, TaskIdRequest, GeneratePlanRequest
from ..config import INTEGRATIONS_CONFIG
from ..db import MongoManager
from ..dependencies import mongo_manager
from ..auth.utils import PermissionChecker
from ...celery_app import celery_app
from ...workers.executor.tasks import execute_task_plan
from ...workers.planner.llm import get_planner_agent
from ...workers.planner.db import get_all_mcp_descriptions
from ...workers.tasks import calculate_next_run

router = APIRouter(
    prefix="/agents",
    tags=["Agents & Tasks"]
)


@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_details(
    task_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    """Fetches the full details of a single task by its ID."""
    task = await mongo_manager.task_collection.find_one(
        {"task_id": task_id, "user_id": user_id}
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    if "_id" in task:
        task["_id"] = str(task["_id"])
    return task

@router.post("/add-task", status_code=status.HTTP_201_CREATED)
async def add_task(
    request: AddTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    task_id = str(uuid.uuid4())
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    next_execution_time = None

    if request.schedule and request.schedule.get("type") == "once" and request.schedule.get("run_at"):
        try:
            # Frontend sends ISO 8601 format string (e.g., "2024-08-01T15:30")
            # We parse it and assume it's in the user's local time, so we need to convert it to UTC.
            # However, since datetime.fromisoformat() on a naive string is naive, we can just attach UTC.
            # A more robust solution would handle timezones properly if the user's timezone is known.
            next_execution_time = datetime.datetime.fromisoformat(request.schedule["run_at"]).replace(tzinfo=datetime.timezone.utc)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid 'run_at' datetime format. Please use ISO 8601 format.")

    task_doc = {
        "task_id": task_id,
        "user_id": user_id,
        "description": request.description,
        "status": "approval_pending",
        "priority": request.priority,
        "plan": [step.dict() for step in request.plan],
        "schedule": request.schedule,
        "enabled": True,
        "progress_updates": [],
        "created_at": now_utc,
        "updated_at": now_utc,
        "result": None,
        "error": None,
        "last_execution_status": None,
        "last_execution_at": None,
        "next_execution_at": next_execution_time
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
    if request.schedule is not None:
        update_data["schedule"] = request.schedule
        # Handle "run_at" for scheduled-once tasks during update
        if request.schedule.get("type") == "once" and request.schedule.get("run_at"):
             try:
                update_data["next_execution_at"] = datetime.datetime.fromisoformat(request.schedule["run_at"]).replace(tzinfo=datetime.timezone.utc)
             except (ValueError, TypeError):
                 raise HTTPException(status_code=400, detail="Invalid 'run_at' datetime format.")
        else:
             update_data["next_execution_at"] = None


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
    task = await mongo_manager.task_collection.find_one(
        {"task_id": request.taskId, "user_id": user_id, "status": "approval_pending"}
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not pending approval.")

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
        raise HTTPException(status_code=409, detail=f"Cannot approve task. Connect tools: {', '.join(missing_tools)}.")

    update_doc = {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
    
    if task.get("schedule") and task["schedule"].get("type") == "recurring":
        update_doc["status"] = "active"
        update_doc["enabled"] = True
        update_doc["next_execution_at"] = calculate_next_run(task["schedule"])
        await mongo_manager.task_collection.update_one({"task_id": request.taskId}, {"$set": update_doc})
        return {"message": "Recurring workflow approved and scheduled."}
    elif task.get("next_execution_at"):
        # This is a one-off task scheduled for a specific time.
        update_doc["status"] = "pending" # Set to pending to be picked up by scheduler
        await mongo_manager.task_collection.update_one({"task_id": request.taskId}, {"$set": update_doc})
        return {"message": "Task approved and scheduled for its specified time."}
    else:
        # This is a one-off task to be run immediately.
        update_doc["status"] = "pending" # Set to pending before sending to queue
        await mongo_manager.task_collection.update_one({"task_id": request.taskId}, {"$set": update_doc})
        execute_task_plan.delay(request.taskId, user_id)
        return {"message": "Task approved and has been queued for immediate execution."}


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
    new_task_doc["schedule"] = None # Reruns are always one-off immediate tasks
    new_task_doc["next_execution_at"] = None

    await mongo_manager.task_collection.insert_one(new_task_doc)
    return {"message": "Task has been duplicated for re-run.", "new_task_id": new_task_id}

@router.post("/generate-plan", summary="Generate a task plan from a prompt")
async def generate_plan(
    request: GeneratePlanRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    try:
        available_tools = get_all_mcp_descriptions()
        if not available_tools:
            raise HTTPException(status_code=503, detail="No tools available for planning.")
        
        current_time_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        agent = get_planner_agent(available_tools, current_time_str)

        user_prompt = f"Please create a plan for the following goal: {request.prompt}"
        messages = [{'role': 'user', 'content': user_prompt}]

        final_response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    content = last_message["content"]
                    match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                    final_response_str = match.group(1) if match else content

        if not final_response_str:
            raise HTTPException(status_code=500, detail="Planner agent returned an empty response.")

        plan_data = json.loads(final_response_str)
        return {"description": plan_data.get("description"), "plan": plan_data.get("plan", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")