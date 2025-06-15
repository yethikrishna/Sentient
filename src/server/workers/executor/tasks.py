import os
import json
import datetime
import asyncio
import motor.motor_asyncio
import logging # Add logging
from typing import Dict, Any, List

from qwen_agent.agents import Assistant
from server.celery_app import celery_app
from server.workers.utils.api_client import notify_user

# Load environment variables for the worker
from server.main.config import (
    MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG,
    OLLAMA_BASE_URL, OLLAMA_MODEL_NAME
)

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- LLM Config for Executor ---
llm_cfg = {
    'model': OLLAMA_MODEL_NAME,
    'model_server': f"{OLLAMA_BASE_URL.rstrip('/')}/v1/",
    'api_key': 'ollama', # Ollama doesn't require a key
}

# --- Database Connection within Celery Task ---
# Celery tasks run in a separate process, so they need their own DB connection.
def get_db_client():
    return motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)[MONGO_DB_NAME]

async def update_task_status(db, task_id: str, status: str, user_id: str, details: Dict = None):
    update_doc = {"status": status, "updated_at": datetime.datetime.now(datetime.timezone.utc)}
    task_description = ""
    if details:
        if "result" in details:
            update_doc["result"] = details["result"]
        if "error" in details:
            update_doc["error"] = details["error"]
    
    # Fetch task description for notification message
    task_doc = await db.tasks.find_one({"task_id": task_id}, {"description": 1})
    if task_doc:
        task_description = task_doc.get("description", "Unnamed Task")

    logger.info(f"Updating task {task_id} status to '{status}' with details: {details}")
    # This might fail if the task document was deleted, but that's an edge case.
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$set": update_doc}
    )

    if status in ["completed", "error"]:
        final_message = "Task finished successfully." if status == "completed" else "Task failed."
        notification_message = f"Task '{task_description}' has finished with status: {status}."
        await notify_user(user_id, notification_message, task_id)

async def add_progress_update(db, task_id: str, user_id: str, message: str):
    logger.info(f"Adding progress update to task {task_id}: '{message}'")
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$push": {"progress_updates": {"message": message, "timestamp": datetime.datetime.now(datetime.timezone.utc)}}}
    )

@celery_app.task(name="execute_task_plan")
def execute_task_plan(task_id: str, user_id: str):
    """
    Celery task to execute a plan for a given task ID and user ID.
    """
    logger.info(f"Celery worker received task 'execute_task_plan' for task_id: {task_id}, user_id: {user_id}")
    # Celery runs in a sync context, so we need to create/get an event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'There is no current event loop...'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(async_execute_task_plan(task_id, user_id))


async def async_execute_task_plan(task_id: str, user_id: str):
    db = get_db_client()
    task = await db.tasks.find_one({"task_id": task_id, "user_id": user_id})

    if not task:
        logger.error(f"Executor: Task {task_id} not found for user {user_id}.")
        return {"status": "error", "message": "Task not found."}

    logger.info(f"Executor started processing task {task_id} for user {user_id}.")
    # Set status to processing
    await update_task_status(db, task_id, "processing", user_id)
    await add_progress_update(db, task_id, user_id, "Executor has picked up the task and is starting execution.")

    # 1. Determine available tools for the user
    user_profile = await db.user_profiles.find_one({"user_id": user_id})
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}
    google_auth_mode = user_profile.get("userData", {}).get("googleAuth", {}).get("mode", "default")
    
    active_mcp_servers = {}
    for service_name, config in INTEGRATIONS_CONFIG.items():
        if "mcp_server_config" not in config: continue
        
        mcp_config = config["mcp_server_config"]
        # Include progress updater tool for all executors
        if service_name == "progress_updater":
             active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
             continue
        
        is_google_service = service_name.startswith('g')
        is_available_via_custom = is_google_service and google_auth_mode == 'custom'
        
        is_builtin = config.get("auth_type") == "builtin"
        is_connected_via_oauth = user_integrations.get(service_name, {}).get("connected", False)

        if is_builtin or is_connected_via_oauth or is_available_via_custom:
            active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}

    tools_config = [{"mcpServers": active_mcp_servers}]
    logger.info(f"Task {task_id}: Executor configured with tools: {list(active_mcp_servers.keys())}")

    # 2. Prepare the plan for execution
    plan_description = task.get("description", "Unnamed plan")
    plan_steps_str = "\n".join([f"{i+1}. Use the '{step['tool']}' tool to '{step['description']}'" for i, step in enumerate(task.get("plan", []))])
    original_context_data = task.get("original_context", {})
    original_context_str = json.dumps(original_context_data, indent=2, default=str) if original_context_data else "No original context provided."

    full_plan_prompt = (
        f"You are executing a task with ID: '{task_id}'. "
        f"Use this ID *exactly* as the 'task_id' parameter when you call the 'update_progress' tool. "
        f"The original context that triggered this plan is:\n---BEGIN CONTEXT---\n{original_context_str}\n---END CONTEXT---\n\n"
        f"Your main goal is: '{plan_description}'.\n"
        f"The plan has the following steps:\n{plan_steps_str}\n\n"
        "Review the original context if needed to successfully complete the steps. You don't have to follow the plan exactly as it is. Feel free to change any of the steps on the fly, as new information becomes apparent. Feel free to retry any failed steps, but only once. Remember to call the 'update_progress' tool to report your status to the user after each major step. Do not call it with the plan title, use the provided task ID."
    )
    # 3. Initialize and run the executor agent
    try:
        await add_progress_update(db, task_id, user_id, f"Initializing executor agent with tools: {list(active_mcp_servers.keys())}")
        
        executor_agent = Assistant(
            llm=llm_cfg, 
            function_list=tools_config,
            system_message="You are an autonomous executor agent. Your sole purpose is to execute the given plan step-by-step using the available tools. You MUST call the 'update_progress' tool after each step to report on your progress."
        )
        
        messages = [{'role': 'user', 'content': full_plan_prompt}]
        
        logger.info(f"Task {task_id}: Starting agent run.")
        # The agent's run is iterative. We let it run to completion.
        final_history = None
        for responses in executor_agent.run(messages=messages):
            final_history = responses

        logger.info(f"Task {task_id}: Agent run finished.")
        final_content = "Plan execution finished with no specific output."
        if final_history and final_history[-1]['role'] == 'assistant':
            content = final_history[-1].get('content')
            if isinstance(content, str):
                # Clean up the <think> tags if they exist from the agent's output
                if content.strip().startswith('<think>'):
                    content = content.replace('<think>', '').replace('</think>', '').strip()
                final_content = content

        logger.info(f"Task {task_id}: Final result: {final_content}")
        await add_progress_update(db, task_id, user_id, "Execution script finished.")
        await update_task_status(db, task_id, "completed", user_id, details={"result": final_content})

        return {"status": "success", "result": final_content}

    except Exception as e:
        error_message = f"Executor agent failed: {str(e)}"
        logger.error(f"Task {task_id}: {error_message}", exc_info=True)
        await add_progress_update(db, task_id, user_id, f"An error occurred during execution: {error_message}")
        await update_task_status(db, task_id, "error", user_id, details={"error": error_message})
        return {"status": "error", "message": error_message}