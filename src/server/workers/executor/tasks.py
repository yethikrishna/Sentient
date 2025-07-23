import os
import json
import datetime
import asyncio
import motor.motor_asyncio
import logging
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

from main.analytics import capture_event
from qwen_agent.agents import Assistant
from workers.celery_app import celery_app
from workers.utils.api_client import notify_user, push_progress_update

# Load environment variables for the worker from its own config
from workers.executor.config import (MONGO_URI, MONGO_DB_NAME,
                                     INTEGRATIONS_CONFIG, OPENAI_API_BASE_URL,
                                     OPENAI_API_KEY, OPENAI_MODEL_NAME, SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX)

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- LLM Config for Executor ---
llm_cfg = {
    'model': OPENAI_MODEL_NAME,
    'model_server': OPENAI_API_BASE_URL,
    'api_key': OPENAI_API_KEY,
}


# --- Database Connection within Celery Task ---
def get_db_client():
    return motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)[MONGO_DB_NAME]

async def update_task_run_status(db, task_id: str, run_id: str, status: str, user_id: str, details: Dict = None, block_id: Optional[str] = None):
    # Update the status of the specific run and the top-level task status
    update_doc = {
        "status": status, # Top-level status
        "runs.$[run].status": status,
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    task_description = ""
    
    if details:
        if "result" in details:
            update_doc["runs.$[run].result"] = details["result"]
        if "error" in details:
            update_doc["runs.$[run].error"] = details["error"]
    
    # Also update the block's status field even if there are no details
    if block_id:
        tasks_update = {"task_status": status}
        await db.tasks_blocks_collection.update_one(
            {"block_id": block_id, "user_id": user_id},
            {"$set": tasks_update}
        )

    task_doc = await db.tasks.find_one({"task_id": task_id}, {"description": 1})
    if task_doc:
        task_description = task_doc.get("description", "Unnamed Task")

    logger.info(f"Updating task {task_id} status to '{status}' with details: {details}")
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$set": update_doc},
        array_filters=[{"run.run_id": run_id}]
    )

    if status in ["completed", "error"]:
        notification_message = f"Task '{task_description}' has finished with status: {status}."
        notification_type = "taskCompleted" if status == "completed" else "taskFailed"
        await notify_user(user_id, notification_message, task_id, notification_type=notification_type)

async def add_progress_update(db, task_id: str, run_id: str, user_id: str, message: Any, block_id: Optional[str] = None):
    logger.info(f"Adding progress update to task {task_id}: '{message}'")
    # The 'message' is now the structured JSON object for the update
    progress_update = {"message": message, "timestamp": datetime.datetime.now(datetime.timezone.utc)}
    
    # 1. Push to frontend via WebSocket in real-time
    await push_progress_update(user_id, task_id, run_id, message)

    # 2. Save to DB for persistence
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id, "runs.run_id": run_id},
        {"$push": {"runs.$.progress_updates": progress_update}}
    )
    if block_id:
        await db.tasks_blocks_collection.update_one(
            {"block_id": block_id, "user_id": user_id},
            {"$push": {"task_progress": progress_update}}
        )

def parse_agent_string_to_updates(content: str) -> List[Dict[str, Any]]:
    """
    Parses a string containing agent's XML-like tags into a list of structured update objects.
    This logic is inspired by the frontend's ChatBubble.js parser.
    """
    if not content or not isinstance(content, str):
        return []

    updates = []
    regex = re.compile(r'(<(think|tool_code|tool_result|answer)[\s\S]*?>[\s\S]*?<\/\2>)', re.DOTALL)
    
    last_index = 0
    for match in regex.finditer(content):
        preceding_text = content[last_index:match.start()].strip()
        if preceding_text:
            updates.append({"type": "thought", "content": preceding_text})

        tag_content = match.group(1)
        
        think_match = re.search(r'<think>([\s\S]*?)</think>', tag_content, re.DOTALL)
        if think_match:
            updates.append({"type": "thought", "content": think_match.group(1).strip()})
            continue

        tool_code_match = re.search(r'<tool_code name="([^"]+)">([\s\S]*?)</tool_code>', tag_content, re.DOTALL)
        if tool_code_match:
            tool_name = tool_code_match.group(1)
            params_str = tool_code_match.group(2).strip()
            try:
                params = json.loads(params_str)
            except json.JSONDecodeError:
                params = {"raw_arguments": params_str}
            updates.append({"type": "tool_call", "tool_name": tool_name, "parameters": params})
            continue

        tool_result_match = re.search(r'<tool_result tool_name="([^"]+)">([\s\S]*?)</tool_result>', tag_content, re.DOTALL)
        if tool_result_match:
            tool_name = tool_result_match.group(1)
            result_str = tool_result_match.group(2).strip()
            try:
                result_content = json.loads(result_str)
            except (json.JSONDecodeError, TypeError):
                result_content = {"raw_result": result_str}
            is_error = isinstance(result_content, dict) and result_content.get("status") == "failure"
            updates.append({
                "type": "tool_result",
                "tool_name": tool_name,
                "result": result_content.get("result", result_content.get("error", result_content)),
                "is_error": is_error
            })
            continue

        answer_match = re.search(r'<answer>([\s\S]*?)</answer>', tag_content, re.DOTALL)
        if answer_match:
            updates.append({"type": "final_answer", "content": answer_match.group(1).strip()})
            continue
        
        last_index = match.end()

    trailing_text = content[last_index:].strip()
    if trailing_text:
        updates.append({"type": "thought", "content": trailing_text})
        
    return updates

@celery_app.task(name="execute_task_plan")
def execute_task_plan(task_id: str, user_id: str):
    logger.info(f"Celery worker received task 'execute_task_plan' for task_id: {task_id}, user_id: {user_id}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(async_execute_task_plan(task_id, user_id))


async def async_execute_task_plan(task_id: str, user_id: str):
    db = get_db_client()
    task = await db.tasks.find_one({"task_id": task_id, "user_id": user_id})

    if not task:
        logger.error(f"Executor: Task {task_id} not found for user {user_id}.")
        return {"status": "error", "message": "Task not found."}

    if not task.get("runs"):
        logger.error(f"Executor: Task {task_id} has no runs. Aborting.")
        return {"status": "error", "message": "Task has no execution runs."}

    latest_run = task["runs"][-1]
    run_id = latest_run["run_id"]

    original_context_data = task.get("original_context", {})
    block_id = None
    if original_context_data.get("source") == "tasks_block":
        block_id = original_context_data.get("block_id")

    logger.info(f"Executor started processing task {task_id} (block_id: {block_id}) for user {user_id}.")
    await update_task_run_status(db, task_id, run_id, "processing", user_id, block_id=block_id)
    await add_progress_update(db, task_id, run_id, user_id, {"type": "info", "content": "Executor has picked up the task and is starting execution."}, block_id=block_id)

    user_profile = await db.user_profiles.find_one({"user_id": user_id})
    personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
    preferences = user_profile.get("userData", {}).get("preferences", {}) if user_profile else {}
    user_name = personal_info.get("name", "User")
    user_location_raw = personal_info.get("location", "Not specified")
    if isinstance(user_location_raw, dict):
        user_location = f"latitude: {user_location_raw.get('latitude')}, longitude: {user_location_raw.get('longitude')}"
    else:
        user_location = user_location_raw

    required_tools_from_plan = {step['tool'] for step in latest_run.get('plan', [])}
    logger.info(f"Task {task_id}: Plan requires tools: {required_tools_from_plan}")
    
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}
    supermemory_user_id = user_profile.get("userData", {}).get("supermemory_user_id") if user_profile else None
    
    active_mcp_servers = {}
    progress_updater_config = INTEGRATIONS_CONFIG.get("progress_updater", {}).get("mcp_server_config")
    if progress_updater_config:
        active_mcp_servers[progress_updater_config["name"]] = {"url": progress_updater_config["url"], "headers": {"X-User-ID": user_id}}
    if supermemory_user_id:
        active_mcp_servers["supermemory"] = {
            "transport": "sse",
            "url": f"{SUPERMEMORY_MCP_BASE_URL.rstrip('/')}/{supermemory_user_id}{SUPERMEMORY_MCP_ENDPOINT_SUFFIX}"
        }

    for tool_name in required_tools_from_plan:
        if tool_name not in INTEGRATIONS_CONFIG:
            logger.warning(f"Task {task_id}: Plan requires tool '{tool_name}' which is not in server config.")
            continue
        config = INTEGRATIONS_CONFIG[tool_name]
        mcp_config = config.get("mcp_server_config")
        if not mcp_config or tool_name in ["progress_updater", "supermemory"]:
            continue
        is_builtin = config.get("auth_type") == "builtin"
        is_connected_via_oauth = user_integrations.get(tool_name, {}).get("connected", False)
        if is_builtin or is_connected_via_oauth:
            active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
        else:
            logger.warning(f"Task {task_id}: Plan requires tool '{tool_name}' but it is not available/connected for user {user_id}.")
    tools_config = [{"mcpServers": active_mcp_servers}]
    logger.info(f"Task {task_id}: Executor configured with tools: {list(active_mcp_servers.keys())}")

    user_timezone_str = personal_info.get("timezone", "UTC")
    try:
        user_timezone = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        logger.warning(f"Invalid timezone '{user_timezone_str}' for user {user_id}. Defaulting to UTC.")
        user_timezone = ZoneInfo("UTC")
    current_user_time = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

    plan_description = task.get("description", "Unnamed plan")
    original_context_str = json.dumps(original_context_data, indent=2, default=str) if original_context_data else "No original context provided."
    block_id_prompt = f"The block_id for this task is '{block_id}'. You MUST pass this ID to the 'update_progress' tool in the 'block_id' parameter." if block_id else "This task did not originate from a tasks block."
    agent_name = preferences.get('agentName', 'Sentient')
    verbosity = preferences.get('responseVerbosity', 'Balanced')
    humor_level = preferences.get('humorLevel', 'Balanced')
    emoji_usage = "You can use emojis in your final answer." if preferences.get('useEmojis', True) else "You should not use emojis."

    full_plan_prompt = (
        f"You are {agent_name}, a resourceful and autonomous executor agent. Your goal is to complete the user's request by intelligently following the provided plan. Your tone should be **{humor_level}** and your final answer should be **{verbosity}**. {emoji_usage}\n\n"
        f"**User Context:**\n- **User's Name:** {user_name}\n- **User's Location:** {user_location}\n- **Current Date & Time:** {current_user_time}\n\n"
        f"Your task ID is '{task_id}'. {block_id_prompt}\n\n"
        f"The original context that triggered this plan is:\n---BEGIN CONTEXT---\n{original_context_str}\n---END CONTEXT---\n\n"
        f"**Primary Objective:** '{plan_description}'\n\n"
        f"**The Plan to Execute:**\n" + "\n".join([f"- Step {i+1}: Use the '{step['tool']}' tool to '{step['description']}'" for i, step in enumerate(latest_run.get("plan", []))]) + "\n\n"
        "**EXECUTION STRATEGY:**\n"
        "1.  **Map Plan to Tools:** The plan provides a high-level tool name (e.g., 'gmail', 'gdrive'). You must map this to the specific functions available to you (e.g., `gmail-send_email`, `gdrive-gdrive_search`).\n"
        "2.  **Be Resourceful & Fill Gaps:** The plan is a guideline. If a step is missing information (e.g., an email address for a manager, a document name), your first action for that step MUST be to use the `supermemory-search` tool to find the missing information. Do not proceed with incomplete information.\n"
        "3.  **Remember New Information:** If you discover a new, permanent fact about the user during your execution (e.g., you find their manager's email is 'boss@example.com'), you MUST use `supermemory-addToSupermemory` to save it.\n"
        "4.  **Report Progress & Failures:** You MUST call the `progress_updater-update_progress` tool to report your status after each major step or when you encounter an error. If a tool fails, analyze the error, report it, and try an alternative approach to achieve the objective. Do not give up easily.\n"
        "5.  **Provide a Final, Detailed Answer:** Once all steps are completed, you MUST provide a final, comprehensive answer to the user. This is not a tool call. Your final response MUST be wrapped in `<answer>` tags. For example: `<answer>I have successfully scheduled the meeting and sent an invitation to John Doe.</answer>`.\n"
        "6.  **Contact Information:** To find contact details like phone numbers or emails, use the `gpeople` tool before attempting to send an email or make a call.\n"
        "\nNow, begin your work. Think step-by-step and start executing the plan."
    )
    
    try:
        executor_agent = Assistant(llm=llm_cfg, function_list=tools_config, system_message="You are an autonomous executor agent...")
        messages = [{'role': 'user', 'content': full_plan_prompt}]
        
        logger.info(f"Task {task_id}: Starting agent run.")
        last_assistant_content = ""
        
        for current_history in executor_agent.run(messages=messages):
            if not current_history or not isinstance(current_history, list): continue

            assistant_turn_content = ""
            assistant_turn_start_index = next((i for i, msg in reversed(list(enumerate(current_history))) if msg.get("role") == "user"), -1) + 1
            for msg in current_history[assistant_turn_start_index:]:
                if msg.get('role') == 'assistant' and msg.get('function_call'):
                    assistant_turn_content += f'<tool_code name="{msg["function_call"].get("name")}">{msg["function_call"].get("arguments", "{}")}</tool_code>'
                elif msg.get('role') == 'function':
                    assistant_turn_content += f'<tool_result tool_name="{msg.get("name")}">{msg.get("content", "")}</tool_result>'
                elif msg.get('role') == 'assistant' and isinstance(msg.get('content'), str):
                    assistant_turn_content += msg.get('content', '')

            if len(assistant_turn_content) > len(last_assistant_content):
                new_content_chunk = assistant_turn_content[len(last_assistant_content):]
                new_updates = parse_agent_string_to_updates(new_content_chunk)
                for update in new_updates:
                    await add_progress_update(db, task_id, run_id, user_id, update, block_id)
                last_assistant_content = assistant_turn_content

        logger.info(f"Task {task_id}: Agent run finished.")
        final_answer_match = re.search(r'<answer>([\s\S]*?)</answer>', last_assistant_content, re.DOTALL)
        final_content = final_answer_match.group(1).strip() if final_answer_match else "Task completed. Check the execution log for details."

        logger.info(f"Task {task_id}: Final result: {final_content}")
        await add_progress_update(db, task_id, run_id, user_id, {"type": "info", "content": "Execution script finished."}, block_id=block_id)
        capture_event(user_id, "task_execution_succeeded", {"task_id": task_id})
        await update_task_run_status(db, task_id, run_id, "completed", user_id, details={"result": final_content}, block_id=block_id)

        return {"status": "success", "result": final_content}

    except Exception as e:
        error_message = f"Executor agent failed: {str(e)}"
        logger.error(f"Task {task_id}: {error_message}", exc_info=True)
        await add_progress_update(db, task_id, run_id, user_id, {"type": "error", "content": f"An error occurred during execution: {error_message}"}, block_id=block_id)
        await update_task_run_status(db, task_id, run_id, "error", user_id, details={"error": error_message}, block_id=block_id)
        return {"status": "error", "message": error_message}