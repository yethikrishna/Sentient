import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker, AuthHelper
from workers.tasks import generate_plan_from_context, execute_task_plan, calculate_next_run, process_task_change_request
from .models import AddTaskRequest, UpdateTaskRequest, TaskIdRequest, AnswerClarificationsRequest, TaskActionRequest
from main.llm import get_qwen_assistant
from json_extractor import JsonExtractor
from .prompts import TASK_CREATION_PROMPT

class GeneratePlanRequest(BaseModel):
    prompt: str

class TaskChatRequest(BaseModel):
    taskId: str
    message: str

from json_extractor import JsonExtractor
from .prompts import TASK_CREATION_PROMPT
router = APIRouter(
    prefix="/tasks",
    tags=["Agents & Tasks"]
)

logger = logging.getLogger(__name__)

@router.post("/generate-plan", status_code=status.HTTP_200_OK)
async def generate_plan_from_prompt(
    request: GeneratePlanRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
    user_name = personal_info.get("name", "User")
    user_timezone_str = personal_info.get("timezone", "UTC")
    try:
        user_timezone = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")

    current_time_str = datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

    system_prompt = TASK_CREATION_PROMPT.format(
        user_name=user_name,
        user_timezone=user_timezone_str,
        current_time=current_time_str
    )

    try:
        agent = get_qwen_assistant(system_message=system_prompt)
        messages = [{'role': 'user', 'content': request.prompt}]

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    response_str = last_message["content"]

        if not response_str:
            raise HTTPException(status_code=500, detail="LLM returned an empty response.")

        task_data = JsonExtractor.extract_valid_json(response_str)

        return JSONResponse(content=task_data)

    except Exception as e:
        logger.error(f"Error generating plan from prompt for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_details(
    task_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    """Fetches the full details of a single task by its ID."""
    task = await mongo_manager.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return JSONResponse(content=task)

@router.post("/add-task", status_code=status.HTTP_201_CREATED)
async def add_task(
    request: AddTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"])),
):
    # 1. Get user info for context
    user_profile = await mongo_manager.get_user_profile(user_id)
    personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
    user_name = personal_info.get("name", "User")
    user_timezone_str = personal_info.get("timezone", "UTC")
    try:
        user_timezone = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")

    current_time_str = datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

    # 2. Call LLM to parse prompt
    system_prompt = TASK_CREATION_PROMPT.format(
        user_name=user_name,
        user_timezone=user_timezone_str,
        current_time=current_time_str
    )
    try:
        agent = get_qwen_assistant(system_message=system_prompt)
        messages = [{'role': 'user', 'content': request.prompt}]

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    response_str = last_message["content"]

        if not response_str:
            raise Exception("LLM returned an empty response.")

        parsed_data = JsonExtractor.extract_valid_json(response_str)
        if not parsed_data:
            # Fallback for simple prompts
            parsed_data = {"description": request.prompt, "priority": 1, "schedule": None}

    except Exception as e:
        logger.error(f"Error parsing task from prompt for user {user_id}: {e}", exc_info=True)
        # Fallback to just using the prompt as description
        parsed_data = {"description": request.prompt, "priority": 1, "schedule": None}

    # 3. Create task data dict
    task_data = {
        "description": parsed_data.get("description", request.prompt),
        "schedule": parsed_data.get("schedule"),
        "priority": parsed_data.get("priority", 1),
        "assignee": request.assignee
    }

    # 4. Save to DB
    task_id = await mongo_manager.add_task(user_id, task_data)
    if not task_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task.")

    # 5. Trigger planning if assigned to AI
    if request.assignee == "ai":
        generate_plan_from_context.delay(task_id, user_id)
        message = "Task created! I'll start planning it out."
    else:
        message = "Task created for you."

    return {"message": message, "task_id": task_id}

@router.post("/fetch-tasks")
async def fetch_tasks(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    tasks = await mongo_manager.get_all_tasks_for_user(user_id)
    return {"tasks": tasks}

@router.post("/update-task")
async def update_task(
    request: UpdateTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    task = await mongo_manager.get_task(request.taskId, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    update_data = request.dict(exclude_unset=True)
    update_data.pop("taskId", None)

    # If assignee is changed to 'ai' and task is in a non-planned state, trigger planning
    if 'assignee' in update_data and update_data['assignee'] == 'ai':
        if task.get('status') == 'pending': # Assuming 'pending' is the status for user-assigned tasks
            update_data['status'] = 'planning'
            generate_plan_from_context.delay(request.taskId, user_id)
            logger.info(f"Task {request.taskId} reassigned to AI. Triggering planning.")

    success = await mongo_manager.update_task(request.taskId, update_data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or no updates applied.")
    return {"message": "Task updated successfully."}

@router.post("/delete-task")
async def delete_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    message = await mongo_manager.delete_task(request.taskId, user_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not deleted.")
    return {"message": message}

@router.post("/task-action", status_code=status.HTTP_200_OK)
async def task_action(
    request: TaskActionRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    if request.action == "decline":
        message = await mongo_manager.decline_task(request.taskId, user_id)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to decline task.")
        return JSONResponse(content={"message": message})
    elif request.action == "execute":
        # This implies immediate execution, potentially bypassing approval if allowed
        message = await mongo_manager.execute_task_immediately(request.taskId, user_id)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to execute task immediately.")
        return JSONResponse(content={"message": message})
    else:
        raise HTTPException(status_code=400, detail="Invalid task action.")

@router.post("/answer-clarifications", status_code=status.HTTP_200_OK)
async def answer_clarifications(
    request: AnswerClarificationsRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    if not await mongo_manager.get_task(request.task_id, user_id):
        raise HTTPException(status_code=404, detail="Task not found or permission denied.")
    
    success = await mongo_manager.add_answers_to_task(request.task_id, [ans.dict() for ans in request.answers], user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save answers to the task.")
    
    # Set status to trigger re-planning and call the planner worker
    await mongo_manager.update_task(request.task_id, {"status": "clarification_answered"})
    # Re-trigger the planner
    generate_plan_from_context.delay(request.task_id, user_id)
    logger.info(f"Answers submitted for task {request.task_id}. Re-triggering planner.")
    
    return JSONResponse(content={"message": "Answers submitted. Task is being re-planned."})

@router.post("/rerun-task")
async def rerun_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    new_task_id = await mongo_manager.rerun_task(request.taskId, user_id)
    if not new_task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original task not found or failed to duplicate.")
    return {"message": "Task has been duplicated for re-run.", "new_task_id": new_task_id}

@router.post("/approve-task", status_code=status.HTTP_200_OK)
async def approve_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    """Approves a task, scheduling it for execution."""
    task_id = request.taskId
    task_doc = await mongo_manager.get_task(task_id, user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or user does not have permission.")

    update_data = {}
    schedule_data = task_doc.get("schedule", {})

    if schedule_data.get("type") == "recurring":
        next_run = calculate_next_run(schedule_data)
        if next_run:
            update_data["next_execution_at"] = next_run
            update_data["status"] = "active"
            update_data["enabled"] = True
        else:
            update_data["status"] = "error"
            update_data["error"] = "Could not calculate next run time for recurring task."
    elif schedule_data.get("type") == "once" and schedule_data.get("run_at"):
        run_at_time_str = schedule_data.get("run_at")
        run_at_time = datetime.fromisoformat(run_at_time_str).replace(tzinfo=timezone.utc)
        if run_at_time > datetime.now(timezone.utc):
            update_data["next_execution_at"] = run_at_time
            update_data["status"] = "pending"
        else:
            execute_task_plan.delay(task_id, user_id)
    else: # Default case: not scheduled, run immediately
        execute_task_plan.delay(task_id, user_id)
    
    if update_data:
        success = await mongo_manager.update_task(task_id, update_data)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve task.")
            
    return JSONResponse(content={"message": "Task approved and scheduled/executed."})
@router.post("/complete-task", status_code=status.HTTP_200_OK)
async def complete_task(
    request: TaskIdRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    """Marks a task as completed and archives it."""
    task_doc = await mongo_manager.get_task(request.taskId, user_id)
    if not task_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or user does not have permission.")

    # Here we are using 'archived' as the final state.
    success = await mongo_manager.update_task(request.taskId, {"status": "archived"})
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to archive task.")

    return JSONResponse(content={"message": "Task completed and archived."})

@router.post("/task-chat", status_code=status.HTTP_200_OK)
async def task_chat(
    request: TaskChatRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    """Handles a user's chat message for a task, typically for change requests."""
    # The logic of adding the message to history and triggering the worker is now in the worker itself.
    process_task_change_request.delay(request.taskId, user_id, request.message)
    return JSONResponse(content={"message": "Change request received. The AI will start working on it."})
