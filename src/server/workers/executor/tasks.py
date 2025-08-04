
### `src\server\workers\executor\tasks.py`

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
from workers.utils.text_utils import clean_llm_output
from celery import chord, group

# Load environment variables for the worker from its own config
from workers.executor.config import (MONGO_URI, MONGO_DB_NAME,
                                     INTEGRATIONS_CONFIG, OPENAI_API_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL_NAME)

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
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
        # Always update the status of the specific run to use the array filter
        "runs.$[run].status": status
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

    task_doc = await db.tasks.find_one({"task_id": task_id}, {"name": 1})
    if task_doc:
        task_description = task_doc.get("name", "Unnamed Task")

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
    
    # 1. Push to frontend via WebSocket in real-time by calling the main server
    await push_progress_update(user_id, task_id, run_id, message)

    # 2. Save to DB for persistence, targeting the correct run in the array
    await db.tasks.update_one(
        {"task_id": task_id, "user_id": user_id},
        {"$push": {"runs.$[run].progress_updates": progress_update}},
        array_filters=[{"run.run_id": run_id}]
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
            updates.append({"type": "info", "content": preceding_text})

        tag_content = match.group(1)
        
        think_match = re.search(r'<think>([\s\S]*?)</think>', tag_content, re.DOTALL)
        if think_match:
            updates.append({"type": "thought", "content": think_match.group(1).strip()})
            continue

        tool_code_match = re.search(r'<tool_code name="([^"]+)">([\s\S]*?)</tool_code>', tag_content, re.DOTALL)
        if tool_code_match:
            tool_name = tool_code_match.group(1)
            updates.append({"type": "info", "content": f"Using tool: {tool_name}"})
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
        updates.append({"type": "info", "content": trailing_text})
        
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
    
    active_mcp_servers = {}
    progress_updater_config = INTEGRATIONS_CONFIG.get("progress_updater", {}).get("mcp_server_config")
    if progress_updater_config:
        active_mcp_servers[progress_updater_config["name"]] = {"url": progress_updater_config["url"], "headers": {"X-User-ID": user_id}}

    for tool_name in required_tools_from_plan:
        if tool_name not in INTEGRATIONS_CONFIG:
            logger.warning(f"Task {task_id}: Plan requires tool '{tool_name}' which is not in server config.")
            continue
        config = INTEGRATIONS_CONFIG[tool_name]
        mcp_config = config.get("mcp_server_config")
        if not mcp_config or tool_name in ["progress_updater"]:
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

    plan_description = task.get("name", "Unnamed plan")
    original_context_str = json.dumps(original_context_data, indent=2, default=str) if original_context_data else "No original context provided."
    block_id_prompt = f"The block_id for this task is '{block_id}'. You MUST pass this ID to the 'update_progress' tool in the 'block_id' parameter." if block_id else "This task did not originate from a tasks block."

    full_plan_prompt = (
        f"You are Sentient, a resourceful and autonomous executor agent. Your goal is to complete the user's request by intelligently following the provided plan.\n\n"
        f"**User Context:**\n- **User's Name:** {user_name}\n- **User's Location:** {user_location}\n- **Current Date & Time:** {current_user_time}\n\n"
        f"Your task ID is '{task_id}' and the current run ID is '{run_id}'.\n\n"
        f"The original context that triggered this plan is:\n---BEGIN CONTEXT---\n{original_context_str}\n---END CONTEXT---\n\n"
        f"**Primary Objective:** '{plan_description}'\n\n"
        f"**The Plan to Execute:**\n" + "\n".join([f"- Step {i+1}: Use the '{step['tool']}' tool to '{step['description']}'" for i, step in enumerate(latest_run.get("plan", []))]) + "\n\n" # noqa
        "**EXECUTION STRATEGY:**\n"
        "1.  **Execution Flow:** You MUST start by executing the first step of the plan. Do not summarize the plan or provide a final answer until you have executed all steps. Follow the plan sequentially.\n"
        "2.  **Map Plan to Tools:** The plan provides a high-level tool name (e.g., 'gmail', 'gdrive'). You must map this to the specific functions available to you (e.g., `gmail_server-sendEmail`, `gdrive_server-gdrive_search`).\n"
        "3.  **Be Resourceful & Fill Gaps:** The plan is a guideline. If a step is missing information (e.g., an email address for a manager, a document name), your first action for that step MUST be to use the `memory-search_memory` tool to find the missing information. Do not proceed with incomplete information.\n"
        "4.  **Remember New Information:** If you discover a new, permanent fact about the user during your execution (e.g., you find their manager's email is 'boss@example.com'), you MUST use `memory-cud_memory` to save it.\n"
        "5.  **Report Progress & Failures:** You MUST call the `progress_updater_server-update_progress` tool to report your status. You MUST provide the `task_id`, the `run_id`, and a descriptive `update_message` string. If a tool fails, analyze the error, report it, and try an alternative approach. Do not give up easily.\n"
        "6.  **Provide a Final, Detailed Answer:** ONLY after all steps are successfully completed, you MUST provide a final, comprehensive answer to the user. This is not a tool call. Your final response MUST be wrapped in `<answer>` tags. For example: `<answer>I have successfully scheduled the meeting and sent an invitation to John Doe.</answer>`.\n"
        "7.  **Contact Information:** To find contact details like phone numbers or emails, use the `gpeople` tool before attempting to send an email or make a call.\n"
        "\nNow, begin your work. Think step-by-step and start executing the plan, beginning with Step 1."
    )
    
    try:
        executor_agent = Assistant(llm=llm_cfg, function_list=tools_config, system_message=full_plan_prompt)
        initial_messages = [{'role': 'user', 'content': "Begin executing the plan. Follow your instructions meticulously."}]
        
        logger.info(f"Task {task_id}: Starting agent run.")

        last_processed_history_len = len(initial_messages)
        final_answer_content = ""

        for current_history in executor_agent.run(messages=initial_messages):
            # Process only the new messages that have been added since the last iteration
            new_messages_to_process = current_history[last_processed_history_len:]

            for msg in new_messages_to_process:
                update_to_push = None
                if msg.get('role') == 'assistant' and isinstance(msg.get('content'), str) and msg.get('content').strip():
                    # This is a thought process or final answer text
                    parsed_updates = parse_agent_string_to_updates(msg['content'])
                    for update in parsed_updates:
                        await add_progress_update(db, task_id, run_id, user_id, update, block_id)
                        if update.get("type") == "final_answer":
                            final_answer_content = update.get("content")
                elif msg.get('role') == 'assistant' and msg.get('function_call'):
                    # This is a tool call.
                    tool_name = msg['function_call']['name']
                    update_to_push = {"type": "info", "content": f"Using tool: {tool_name}"}
                elif msg.get('role') == 'function':
                    # This is a tool result
                    result_content = json.loads(msg.get('content', '{}'))
                    is_error = result_content.get("status") == "failure"
                    update_to_push = {"type": "tool_result", "tool_name": msg.get('name'), "result": result_content.get("result", result_content.get("error")), "is_error": is_error}

                if update_to_push:
                    await add_progress_update(db, task_id, run_id, user_id, update_to_push, block_id)

            last_processed_history_len = len(current_history)

        final_content = final_answer_content or "Task completed. Check the execution log for details."
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

@celery_app.task(name="aggregate_results_callback")
def aggregate_results_callback(results):
    """Celery callback task to aggregate results from a chord."""
    logger.info(f"Aggregating results from parallel workers. Results: {str(results)[:500]}")
    return results

@celery_app.task(name="run_single_item_worker")
def run_single_item_worker(user_id: str, item: Any, worker_prompt: str, worker_tools: List[str]):
    """
    A Celery worker that executes a sub-task for a single item from a collection.
    This worker runs a self-contained agent to fulfill the worker_prompt using a specific set of tools.
    """
    logger.info(f"Running single item worker for user {user_id} on item: {str(item)[:200]} with tools: {worker_tools}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(async_run_single_item_worker(user_id, item, worker_prompt, worker_tools))

async def async_run_single_item_worker(user_id: str, item: Any, worker_prompt: str, worker_tools: List[str]):
    """
    Async logic for the single item worker.
    """
    db = get_db_client()
    try:
        # 1. Get user context
        user_profile = await db.user_profiles.find_one({"user_id": user_id})
        user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

        # 2. Configure tools for the sub-agent based on the provided list
        active_mcp_servers = {}
        for tool_name in worker_tools:
            config = INTEGRATIONS_CONFIG.get(tool_name)
            if not config:
                logger.warning(f"Worker for user {user_id} requested unknown tool '{tool_name}'.")
                continue
            
            mcp_config = config.get("mcp_server_config")
            if not mcp_config: continue

            is_builtin = config.get("auth_type") == "builtin"
            is_connected = user_integrations.get(tool_name, {}).get("connected", False)

            if is_builtin or is_connected:
                active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
            else:
                logger.warning(f"Worker for user {user_id} needs tool '{tool_name}' but it is not connected/available.")

        tools_config = [{"mcpServers": active_mcp_servers}]

        # 3. Construct prompts for the sub-agent
        system_prompt = (
            "You are an autonomous sub-agent. Your goal is to complete a specific task given to you as part of a larger parallel operation. "
            "You have access to a specific, limited suite of tools. Follow the user's prompt precisely. "
            "Your final output should be a single, concise result (e.g., a string, a number, a JSON object, or null). Do not add conversational filler. "
            "If you generate a final answer, wrap it in <answer> tags."
        )
        
        item_context = json.dumps(item, indent=2, default=str)
        full_worker_prompt = f"**Task:**\n{worker_prompt}\n\n**Input Data for this Task:**\n```json\n{item_context}\n```"
        
        messages = [{'role': 'user', 'content': full_worker_prompt}]

        # 4. Run the agent
        agent = Assistant(llm=llm_cfg, function_list=tools_config, system_message=system_prompt)
        
        final_content = ""
        final_response_list = []
        for response in agent.run(messages=messages):
            if isinstance(response, list) and response and response[-1].get("role") == "assistant":
                final_content = response[-1].get("content", "")
            final_response_list = response

        # 5. Parse and return the result
        answer_match = re.search(r'<answer>([\s\S]*?)</answer>', final_content, re.DOTALL)
        if answer_match:
            result_str = answer_match.group(1).strip()
            try:
                return json.loads(result_str)
            except json.JSONDecodeError:
                if result_str.lower() == 'null':
                    return None
                return result_str
        
        last_message = final_response_list[-1] if final_response_list else {}
        if last_message.get("role") == "function":
            try:
                tool_result = json.loads(last_message.get("content", "{}"))
                return tool_result.get("result")
            except (json.JSONDecodeError, AttributeError):
                return last_message.get("content")

        cleaned_content = clean_llm_output(final_content)
        if cleaned_content.lower() == 'null':
            return None
        return cleaned_content

    except Exception as e:
        logger.error(f"Error in single item worker for user {user_id}: {e}", exc_info=True)
        return {"error": str(e)}