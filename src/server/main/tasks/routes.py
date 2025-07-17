import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker, AuthHelper
from agents.task_planner import generate_plan_from_context, execute_task_plan
from utils.time_utils import calculate_next_run

from .models import AddTaskRequest, UpdateTaskRequest, TaskActionRequest, AnswerClarificationsRequest, GeneratePlanRequest
from main.data.db import TaskDBManager # Assuming TaskDBManager is now in main.data.db

router = APIRouter(
    prefix="/tasks",
    tags=["Agents & Tasks"]
)

mongo_manager = TaskDBManager()
logger = logging.getLogger(__name__)


@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_details(
    task_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))
):
    """Fetches the full details of a single task by its ID."""
    task = await mongo_manager.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.post("/add-task", status_code=status.HTTP_201_CREATED)
async def add_task(
    request: AddTaskRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    task_data = request.dict()
    task_data.pop("taskId", None) # Remove if present
    
    # Per new spec, all manually created tasks start in 'planning' state to be reviewed.
    task_data["status"] = "planning"
    task_data.pop("next_execution_at", None) # Let the approval step set this

    task_id = await mongo_manager.add_task(user_id, task_data)
    if not task_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task.")

    # Trigger plan generation for the newly added task
    generate_plan_from_context.delay(task_id, user_id)
    return {"message": "Task created and planning initiated.", "task_id": task_id}

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
    # The logic for determining recurring tasks and updating multiple instances
    # is now encapsulated within TaskDBManager.
    success = await mongo_manager.update_task(request.taskId, user_id, request)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or no updates applied.")
    return {"message": "Task updated successfully."}

@router.post("/delete-task")
async def delete_task(
    request: TaskActionRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    # The logic for determining recurring tasks and deleting multiple instances
    # is now encapsulated within TaskDBManager.
    message = await mongo_manager.delete_task(request.taskId, user_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not deleted.")
    return {"message": message}

@router.post("/task-action", status_code=status.HTTP_200_OK)
async def task_action(
    request: TaskActionRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    if request.action == "approve":
        task_id = request.task_id
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
                update_data["enabled"] = True # Ensure recurring tasks are enabled on approval
            else: # Handle case where next run can't be calculated
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
        
        success = await mongo_manager.update_task(task_id, update_data)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve task.")
        return JSONResponse(content={"message": "Task approved and scheduled/executed."})

    elif request.action == "decline":
        message = await mongo_manager.decline_task(request.task_id, user_id)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to decline task.")
        return JSONResponse(content={"message": message})
    elif request.action == "execute":
        # This implies immediate execution, potentially bypassing approval if allowed
        message = await mongo_manager.execute_task_immediately(request.task_id, user_id)
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
    task = await mongo_manager.get_task(request.task_id)
    if not task or task.get("user_id") != user_id:
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
    request: TaskActionRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))
):
    new_task_id = await mongo_manager.rerun_task(request.task_id, user_id)
    if not new_task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original task not found or failed to duplicate.")
    return {"message": "Task has been duplicated for re-run.", "new_task_id": new_task_id}