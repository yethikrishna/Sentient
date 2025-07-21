import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker, AuthHelper
from workers.tasks import generate_plan_from_context, execute_task_plan, calculate_next_run, process_task_change_request, refine_task_details
from .models import AddTaskRequest, UpdateTaskRequest, TaskIdRequest, AnswerClarificationsRequest, TaskActionRequest, TaskChatRequest
from main.llm import get_qwen_assistant
from json_extractor import JsonExtractor
from .prompts import TASK_CREATION_PROMPT

class GeneratePlanRequest(BaseModel):
    prompt: str

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
    # --- Fast Path for User-Assigned Tasks ---
    if request.assignee == "user":
        task_data = {
            "description": request.prompt,
            "priority": 1, # Default priority
            "schedule": None,
            "assignee": "user"
        }
        task_id = await mongo_manager.add_task(user_id, task_data)
        if not task_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task.")

        # Asynchronously refine the task details in the background
        refine_task_details.delay(task_id)
        return {"message": "Task added to your list.", "task_id": task_id}

    # --- Full Path for AI-Assigned Tasks (requires sync LLM call) ---
    else:
        user_profile = await mongo_manager.get_user_profile(user_id)
        personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
        user_name = personal_info.get("name", "User")
        user_timezone_str = personal_info.get("timezone", "UTC")
        user_timezone = ZoneInfo(user_timezone_str)
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
                if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                    response_str = chunk[-1].get("content", "")
            parsed_data = JsonExtractor.extract_valid_json(response_str) or {}
        except Exception as e:
            logger.error(f"LLM parsing failed for AI task: {e}", exc_info=True)
            parsed_data = {}

    # Create task data dict
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

    # Trigger planning since it's an AI task
    generate_plan_from_context.delay(task_id)
    message = "Task created! I'll start planning it out."
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
            generate_plan_from_context.delay(request.taskId)
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
    task = await mongo_manager.get_task(request.taskId, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    is_modification = len(task.get("runs", [])) > 1

    if is_modification:
        # This is a "cancel change request" action.
        success = await mongo_manager.cancel_latest_run(request.taskId)
        # Also delete any notifications related to the cancelled modification attempt.
        await mongo_manager.delete_notifications_for_task(user_id, request.taskId)
        if success:
            return {"message": "Change request cancelled and original task restored."}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel change request.")
    else:
        # This is a normal task with only one run, so delete it entirely.
        message = await mongo_manager.delete_task(request.taskId, user_id)
        if not message:
            raise HTTPException(status_code=404, detail="Task not found or not deleted.")
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
    generate_plan_from_context.delay(request.task_id)
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

    # Trigger the planner for the new task
    generate_plan_from_context.delay(new_task_id)
    logger.info(f"Rerunning task {request.taskId}. New task {new_task_id} created and sent to planner.")
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
    schedule_data = task_doc.get("schedule") or {}

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

@router.post("/task-chat", status_code=status.HTTP_200_OK)
async def task_chat(
    request: TaskChatRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    """
    Handles a user's chat message for a task. If the task was completed,
    this will trigger a re-planning of the same task by adding a new 'run'.
    """
    task_id = request.taskId
    task = await mongo_manager.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    # --- Migration logic for older tasks ---
    if "runs" not in task:
        # First change request on an old task, migrate top-level fields to the first run
        first_run = {
            "run_id": str(uuid.uuid4()),
            "status": "completed",
            "plan": task.get("plan", []),
            "clarifying_questions": task.get("clarifying_questions", []),
            "progress_updates": task.get("progress_updates", []),
            "result": task.get("result"),
            "error": task.get("error")
        }
        await mongo_manager.update_task(task_id, {"runs": [first_run]})

    # Append user message to top-level chat history
    new_message = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc)
    }
    
    # Create a new run for the change request
    new_run = {
        "run_id": str(uuid.uuid4()),
        "status": "planning",
        "prompt": request.message # Store the prompt that initiated this run
    }

    await mongo_manager.task_collection.update_one(
        {"task_id": task_id},
        {"$set": {"status": "planning"}, "$push": {"chat_history": new_message, "runs": new_run}}
    )

    # Re-trigger the planner for the same task
    generate_plan_from_context.delay(task_id)
    return JSONResponse(content={"message": "Change request received. The task is now being re-planned."})