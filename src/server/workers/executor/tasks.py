import os
import json
import datetime
import asyncio
import motor.motor_asyncio
from typing import Dict, Any, List

from qwen_agent.agents import Assistant
from server.celery_app import celery_app

# Load environment variables for the worker
from server.main.config import (
    MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG,
    OLLAMA_BASE_URL, OLLAMA_MODEL_NAME
)

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
    if details:
        if "result" in details:
            update_doc["result"] = details["result"]
        if "error" in details:
            update_doc["error"] = details["error"]
    
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$set": update_doc}
    )

async def add_progress_update(db, task_id: str, user_id: str, message: str):
     await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$push": {"progress_updates": {"message": message, "timestamp": datetime.datetime.now(datetime.timezone.utc)}}}
    )

@celery_app.task(name="execute_task_plan")
def execute_task_plan(task_id: str, user_id: str):
    """
    Celery task to execute a plan for a given task ID and user ID.
    """
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
        print(f"Executor: Task {task_id} not found for user {user_id}.")
        return {"status": "error", "message": "Task not found."}

    # Set status to processing
    await update_task_status(db, task_id, "processing", user_id)
    await add_progress_update(db, task_id, user_id, "Executor has picked up the task and is starting execution.")

    # 1. Determine available tools for the user
    user_profile = await db.user_profiles.find_one({"user_id": user_id})
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}
    
    active_mcp_servers = {}
    for service_name, config in INTEGRATIONS_CONFIG.items():
        if "mcp_server_config" not in config: continue
        
        mcp_config = config["mcp_server_config"]
        # Include progress updater tool for all executors
        if service_name == "progress_updater":
             active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
             continue
             
        if config["auth_type"] == "builtin":
            active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
        elif config["auth_type"] in ["oauth", "manual"] and user_integrations.get(service_name, {}).get("connected"):
            active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
    
    tools_config = [{"mcpServers": active_mcp_servers}]

    # 2. Prepare the plan for execution
    plan_description = task.get("description", "Unnamed plan")
    plan_steps_str = "\n".join([f"{i+1}. Use the '{step['tool']}' tool to '{step['description']}'" for i, step in enumerate(task.get("plan", []))])
    original_context_data = task.get("original_context", {})
    original_context_str = json.dumps(original_context_data, indent=2, default=str) if original_context_data else "No original context provided."

    full_plan_prompt = (
        f"You are executing a task with ID: '{task_id}'. "
        f"The original context that triggered this plan is:\n---BEGIN CONTEXT---\n{original_context_str}\n---END CONTEXT---\n\n"
        f"Your main goal is: '{plan_description}'.\n"
        f"Use this ID *exactly* as the 'task_id' parameter when you call the 'update_progress' tool. "
        f"The plan is titled '{plan_description}' and has the following steps:\n{plan_steps_str}\n\n"
        "Review the original context if needed to successfully complete the steps. Remember to call the 'update_progress' tool to report your status after each major step. Do not call it with the plan title, use the provided task ID."
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
        
        # The agent's run is iterative. We let it run to completion.
        final_history = None
        for responses in executor_agent.run(messages=messages):
            final_history = responses

        final_content = "Plan execution finished with no specific output."
        if final_history and final_history[-1]['role'] == 'assistant':
            content = final_history[-1].get('content')
            if isinstance(content, str):
                # Clean up the <think> tags if they exist from the agent's output
                if content.strip().startswith('<think>'):
                    content = content.replace('<think>', '').replace('</think>', '').strip()
                final_content = content

        await add_progress_update(db, task_id, user_id, "Execution script finished.")
        await update_task_status(db, task_id, "completed", user_id, details={"result": final_content})

        return {"status": "success", "result": final_content}

    except Exception as e:
        error_message = f"Executor agent failed: {str(e)}"
        print(error_message)
        await add_progress_update(db, task_id, user_id, f"An error occurred during execution: {error_message}")
        await update_task_status(db, task_id, "error", user_id, details={"error": error_message})
        return {"status": "error", "message": error_message}