import asyncio
import logging
import uuid
import json
import re
import datetime
import os
import httpx
from dateutil import rrule
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict, Any, Optional, List, Tuple
from bson import ObjectId
from main.analytics import capture_event

from workers.config import SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX, SUPPORTED_POLLING_SERVICES
from json_extractor import JsonExtractor
from workers.utils.api_client import notify_user, push_task_list_update
from main.config import INTEGRATIONS_CONFIG
from main.tasks.prompts import TASK_CREATION_PROMPT
from main.llm import get_qwen_assistant
from workers.celery_app import celery_app
from workers.planner.llm import get_planner_agent, get_question_generator_agent
from workers.planner.db import PlannerMongoManager, get_all_mcp_descriptions
from workers.supermemory_agent_utils import get_supermemory_qwen_agent, get_db_manager as get_memory_db_manager
from workers.executor.tasks import execute_task_plan
from main.vector_db import get_conversation_summaries_collection
from workers.planner.prompts import TOOL_SELECTOR_SYSTEM_PROMPT

# Imports for extractor logic
from workers.extractor.llm import get_extractor_agent
from workers.extractor.db import ExtractorMongoManager

# Imports for poller logic
from workers.poller.gmail.service import GmailPollingService
from workers.poller.gcalendar.service import GCalendarPollingService
from workers.poller.gmail.db import PollerMongoManager as GmailPollerDB
from workers.poller.gcalendar.db import PollerMongoManager as GCalPollerDB

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_date_from_text(text: str) -> str:
    """Extracts YYYY-MM-DD from text, defaults to today."""
    match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if match:
        return match.group(1)
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')

def clean_llm_output(text: str) -> str:
    """
    Removes reasoning tags (e.g., <think>...</think>) and trims whitespace from LLM output.
    """
    if not isinstance(text, str):
        return ""
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned_text.strip()

# --- Tool Selection Logic (adapted from chat utils) ---
def _get_tool_lists(user_integrations: Dict) -> Tuple[Dict, Dict]:
    """
    Separates tools into connected/available and disconnected lists.
    Includes built-in tools in the connected list.
    """
    connected_tools = {}
    disconnected_tools = {}
    for tool_name, config in INTEGRATIONS_CONFIG.items():
        is_connectable = config.get("auth_type") in ["oauth", "manual"]
        is_builtin = config.get("auth_type") == "builtin"

        if is_builtin:
            connected_tools[tool_name] = config.get("description", "")
            continue

        if is_connectable:
            if user_integrations.get(tool_name, {}).get("connected", False):
                connected_tools[tool_name] = config.get("description", "")
            else:
                disconnected_tools[tool_name] = config.get("description", "")
    return connected_tools, disconnected_tools

async def _select_relevant_tools(query: str, available_tools_map: Dict[str, str]) -> List[str]:
    """
    Uses a lightweight LLM call to select relevant tools for a given query.
    """
    if not available_tools_map:
        return []

    try:
        tools_description = "\n".join(f"- `{name}`: {desc}" for name, desc in available_tools_map.items())
        prompt = f"User Query: \"{query}\"\n\nAvailable Tools:\n{tools_description}"

        selector_agent = get_qwen_assistant(system_message=TOOL_SELECTOR_SYSTEM_PROMPT, function_list=[])
        messages = [{'role': 'user', 'content': prompt}]

        def _run_selector_sync():
            final_content_str = ""
            for chunk in selector_agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content_str = last_message["content"]
            return final_content_str

        final_content_str = await asyncio.to_thread(_run_selector_sync)
        selected_tools = JsonExtractor.extract_valid_json(final_content_str)
        if isinstance(selected_tools, list):
            logger.info(f"Tool selector identified relevant tools for context search: {selected_tools}")
            return selected_tools
        return []
    except Exception as e:
        logger.error(f"Error during tool selection for context search: {e}", exc_info=True)
        return list(available_tools_map.keys())

# Helper to run async code in Celery's sync context
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Memory Processing Task (Modified for Supermemory) ---
@celery_app.task(name="process_memory_item")
def process_memory_item(user_id: str, fact_text: str, source_event_id: Optional[str] = None):
    """
    Celery task to process a single memory item by calling the Supermemory MCP
    via a dedicated Qwen agent.
    """
    log_prefix = f"Event {source_event_id}: " if source_event_id else ""
    logger.info(f"{log_prefix}Celery worker received Supermemory task for user {user_id}: '{fact_text[:80]}...'")

    async def async_process_memory():
        db_manager = get_memory_db_manager() # This is a PlannerMongoManager instance
        try:
            user_profile = await db_manager.user_profiles_collection.find_one({"user_id": user_id})
            if not user_profile:
                logger.error(f"User profile not found for {user_id}. Cannot process memory item.")
                return {"status": "failure", "reason": "User profile not found"}

            supermemory_user_id = user_profile.get("userData", {}).get("supermemory_user_id")
            if not supermemory_user_id:
                logger.warning(f"User {user_id} has no Supermemory User ID. Skipping memory item: '{fact_text[:50]}...'")
                return {"status": "skipped", "reason": "Supermemory MCP URL not configured"}

            supermemory_mcp_url = f"{SUPERMEMORY_MCP_BASE_URL.rstrip('/')}/{supermemory_user_id}{SUPERMEMORY_MCP_ENDPOINT_SUFFIX}"

            agent = get_supermemory_qwen_agent(supermemory_mcp_url)
            messages = [{'role': 'user', 'content': f"Remember this fact: {fact_text}"}]

            all_responses = list(agent.run(messages=messages))
            final_history = all_responses[-1] if all_responses else None

            if not final_history:
                logger.error(f"Supermemory agent produced no output for user {user_id}.")
                return {"status": "failure", "reason": "Agent produced no output"}

            function_call_succeeded = False
            tool_response_content = "No tool response received."

            for message in reversed(final_history):
                if message.get("role") == "function" and message.get("name") == "supermemory-addToSupermemory":
                    tool_response_content = message.get("content", "")
                    if isinstance(tool_response_content, str) and "success" in tool_response_content.lower():
                        function_call_succeeded = True
                    break

            if function_call_succeeded:
                logger.info(f"Successfully executed Supermemory store for user {user_id}. MCP Response: '{tool_response_content}'. Fact: '{fact_text[:50]}...'")
                return {"status": "success", "fact": fact_text, "mcp_response": tool_response_content}
            else:
                logger.error(f"Supermemory agent tool call failed for user {user_id}. Response: {tool_response_content}")
                return {"status": "failure", "reason": "Supermemory tool call did not succeed", "mcp_response": tool_response_content}
        finally:
            if 'db_manager' in locals() and db_manager:
                await db_manager.close()

    return run_async(async_process_memory())

@celery_app.task(name="refine_and_plan_ai_task")
def refine_and_plan_ai_task(task_id: str):
    """
    Asynchronously refines an AI-assigned task's details using an LLM,
    updates the task in the DB, and then triggers the planning process.
    """
    logger.info(f"Refining and planning for AI task_id: {task_id}")
    run_async(async_refine_and_plan_ai_task(task_id))

async def async_refine_and_plan_ai_task(task_id: str):
    """Async logic for refining an AI task and then kicking off the planner."""
    db_manager = PlannerMongoManager()
    try:
        task = await db_manager.get_task(task_id)
        if not task or task.get("assignee") != "ai":
            logger.warning(f"Skipping refine/plan for task {task_id}: not found or not assigned to AI.")
            return

        user_id = task["user_id"]
        user_profile = await db_manager.user_profiles_collection.find_one({"user_id": user_id})
        personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
        user_name = personal_info.get("name", "User")
        user_timezone_str = personal_info.get("timezone", "UTC")
        try:
            user_timezone = ZoneInfo(user_timezone_str)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")
        current_time_str = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        system_prompt = TASK_CREATION_PROMPT.format(
            user_name=user_name,
            user_timezone=user_timezone_str,
            current_time=current_time_str
        )
        agent = get_qwen_assistant(system_message=system_prompt)
        # Use the raw prompt from the task's description for parsing
        messages = [{'role': 'user', 'content': task["description"]}]

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                response_str = chunk[-1].get("content", "")

        parsed_data = JsonExtractor.extract_valid_json(clean_llm_output(response_str))
        if parsed_data:
            # Inject user's timezone into the schedule object if it exists
            if 'schedule' in parsed_data and parsed_data.get('schedule'):
                parsed_data['schedule']['timezone'] = user_timezone_str
            # Ensure description is not empty, fall back to original prompt if needed
            if not parsed_data.get("description"):
                parsed_data["description"] = task["description"]
            await db_manager.update_task_field(task_id, parsed_data)
            logger.info(f"Successfully refined and updated AI task {task_id} with new details.")
        else:
            logger.warning(f"Could not parse details for AI task {task_id}, proceeding with raw description.")

        # Now trigger the planning step, which is the main purpose of AI-assigned tasks
        generate_plan_from_context.delay(task_id)
        logger.info(f"Refinement complete for AI task {task_id}, dispatched to planner.")

    except Exception as e:
        logger.error(f"Error refining and planning AI task {task_id}: {e}", exc_info=True)
        await db_manager.update_task_field(task_id, {"status": "error", "error": "Failed during initial refinement."})
    finally:
        await db_manager.close()

@celery_app.task(name="process_task_change_request")
def process_task_change_request(task_id: str, user_id: str, user_message: str):
    """Processes a user's change request on a completed task via the in-task chat."""
    logger.info(f"Task Change Request: Received for task {task_id} from user {user_id}. Message: '{user_message}'")
    run_async(async_process_change_request(task_id, user_id, user_message))

async def async_process_change_request(task_id: str, user_id: str, user_message: str):
    """Async logic for handling task change requests."""
    db_manager = PlannerMongoManager()
    try:
        # 1. Fetch the task and its full history
        task = await db_manager.get_task(task_id)
        if not task:
            logger.error(f"Task Change Request: Task {task_id} not found.")
            return

        # 2. Append user message to the task's chat history
        chat_history = task.get("chat_history", [])
        chat_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        })

        # 3. Update task status and chat history in DB
        await db_manager.update_task_field(task_id, {
            "chat_history": chat_history,
            "status": "planning" # Revert to planning to re-evaluate
        })

        await notify_user(user_id, f"I've received your changes for '{task.get('description', 'the task')}' and will start working on them.", task_id)

        # 4. Create a consolidated context for the planner
        # This is similar to the initial context creation but includes much more history
        original_context = task.get("original_context", {})
        original_context["previous_plan"] = task.get("plan", [])
        original_context["previous_result"] = task.get("result", "")
        original_context["chat_history"] = chat_history

        # 5. Trigger the planner with this rich context
        # The planner will now see the change request and all prior history
        # The action_items can be just the user's new message.
        process_action_item.delay(user_id, [user_message], [], task_id, original_context)
        logger.info(f"Task Change Request: Dispatched task {task_id} back to planner with new context.")

    except Exception as e:
        logger.error(f"Error in async_process_change_request for task {task_id}: {e}", exc_info=True)
    finally:
        await db_manager.close()
# --- Extractor Task ---
@celery_app.task(name="extract_from_context")
def extract_from_context(user_id: str, source_text: str, source_type: str, event_id: Optional[str] = None, event_data: Optional[Dict[str, Any]] = None, current_time_iso: Optional[str] = None):
    """
    Celery task to replace the Extractor worker. It takes context data,
    runs it through an LLM to extract memories and action items,
    and then dispatches further Celery tasks.

    Args:
        user_id (str): The ID of the user.
        source_text (str): The raw text to be processed by the LLM.
        source_type (str): The origin of the text (e.g., 'gmail', 'gcalendar', 'chat_summary').
        event_id (Optional[str]): A unique ID for the event if it's from a poller.
        event_data (Optional[Dict]): The original structured data of the event.
        current_time_iso (Optional[str]): ISO timestamp for time-sensitive extractions.
    """
    log_id = event_id or "adhoc"
    logger.info(f"Extractor task running for event_id: {log_id} (source: {source_type}) for user {user_id}")

    async def async_extract():
        db_manager = ExtractorMongoManager()
        try:
            if event_id and await db_manager.is_event_processed(user_id, event_id):
                logger.info(f"Skipping event_id: {event_id} - already processed.")
                return

            # Fetch user context to provide to the extractor agent
            user_profile = await db_manager.get_user_profile(user_id)
            personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
            user_name = personal_info.get("name", "User")
            user_location_raw = personal_info.get("location", "Not specified")
            user_timezone = personal_info.get("timezone", "UTC")
            if isinstance(user_location_raw, dict) and 'latitude' in user_location_raw:
                user_location = f"latitude: {user_location_raw.get('latitude')}, longitude: {user_location_raw.get('longitude')}"
            else:
                user_location = user_location_raw

            current_time = datetime.datetime.fromisoformat(current_time_iso) if current_time_iso else datetime.datetime.now(datetime.timezone.utc)
            time_context_str = f"The current date and time is {current_time.strftime('%A, %Y-%m-%d %H:%M:%S %Z')}."

            # Add time context to the input for the LLM
            full_llm_input = f"{time_context_str}\n\nPlease analyze the following content from source '{source_type}':\n\n{source_text}"

            if not source_text or not source_text.strip():
                logger.warning(f"Skipping event_id: {log_id} due to empty content.")
                return

            agent = get_extractor_agent(user_name, user_location, user_timezone)
            messages = [{'role': 'user', 'content': full_llm_input}]

            final_content_str = ""
            for chunk in agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content_str = last_message["content"]

            if not final_content_str.strip():
                logger.error(f"Extractor LLM returned no response for event_id: {log_id}.")
                return


            cleaned_content = clean_llm_output(final_content_str)
            logger.info(f"Extractor LLM response for event_id: {log_id} - {cleaned_content}.")
            extracted_data = JsonExtractor.extract_valid_json(cleaned_content)
            if not extracted_data:
                logger.error(f"Could not extract valid JSON from LLM response for event_id: {log_id}. Response: '{cleaned_content}'")
                if event_id: await db_manager.log_extraction_result(event_id, user_id, 0, 0)
                return

            if isinstance(extracted_data, list):
                extracted_data = extracted_data[0] if extracted_data and isinstance(extracted_data[0], dict) else {}

            if not isinstance(extracted_data, dict):
                logger.error(f"Extracted JSON is not a dictionary for event_id: {log_id}. Extracted: '{extracted_data}'")
                if event_id: await db_manager.log_extraction_result(event_id, user_id, 0, 0)
                return

            memory_items = extracted_data.get("memory_items", [])
            action_items = extracted_data.get("action_items", [])
            topics = extracted_data.get("topics", [])

            if source_type in ["gmail", "gcalendar", "chat", "chat_summary"]:
                for item in action_items:
                    if not isinstance(item, str) or not item.strip():
                        continue

                    original_source_context = {
                        "source": source_type,
                        "event_id": event_id,
                        "content": event_data
                    }

                    # Dispatch directly to the planner/action item processor
                    process_action_item.delay(user_id, [item], topics, event_id, original_source_context)
                    logger.info(f"Dispatched action item from {source_type} for processing: '{item}'")

            for fact in memory_items:
                if isinstance(fact, str) and fact.strip():
                    process_memory_item.delay(user_id, fact, event_id)

            await db_manager.log_extraction_result(event_id, user_id, len(memory_items), len(action_items))

        except Exception as e:
            logger.error(f"Error in extractor task for event_id: {log_id}: {e}", exc_info=True)
        finally:
            await db_manager.close()

    run_async(async_extract())

@celery_app.task(name="process_action_item")
def process_action_item(user_id: str, action_items: list, topics: list, source_event_id: str, original_context: dict):
    """Orchestrates the pre-planning phase for a new proactive task."""
    run_async(async_process_action_item(user_id, action_items, topics, source_event_id, original_context))

async def get_clarifying_questions(user_id: str, task_description: str, topics: list, original_context: dict, db_manager: PlannerMongoManager) -> List[str]:
    """
    Uses a unified agent to search memory and relevant tools, then generates clarifying questions if needed.
    Returns a list of questions, which is empty if no clarification is required.
    """
    user_profile = await db_manager.user_profiles_collection.find_one({"user_id": user_id})
    if not user_profile:
        logger.error(f"User profile not found for {user_id}. Cannot verify context.")
        return [f"Can you tell me more about '{topic}'?" for topic in topics]

    user_integrations = user_profile.get("userData", {}).get("integrations", {})
    supermemory_user_id = user_profile.get("userData", {}).get("supermemory_user_id")
    
    if not supermemory_user_id:
        logger.warning(f"User {user_id} has no Supermemory ID. Cannot verify context with memory.")

    # 1. Get all available (connected + built-in) tools for the user
    connected_tools, _ = _get_tool_lists(user_integrations)

    # 2. Select tools relevant to the task description
    relevant_tool_names = await _select_relevant_tools(task_description, connected_tools)

    # 3. Always include supermemory for context verification
    final_tool_names = set(relevant_tool_names)
    final_tool_names.add("supermemory")
    
    logger.info("Selected tools for context verification: " + ", ".join(final_tool_names))

    # 4. Build the MCP server config and prompt info for the agent
    mcp_servers_for_agent = {}
    available_tools_for_prompt = {}

    for tool_name in final_tool_names:
        config = INTEGRATIONS_CONFIG.get(tool_name)
        if not config: continue

        available_tools_for_prompt[tool_name] = config.get("description", "")
        
        if tool_name == "supermemory":
            if supermemory_user_id:
                supermemory_mcp_url = f"{SUPERMEMORY_MCP_BASE_URL.rstrip('/')}/{supermemory_user_id}{SUPERMEMORY_MCP_ENDPOINT_SUFFIX}"
                mcp_servers_for_agent["supermemory"] = {"url": supermemory_mcp_url, "transport": "sse"}
        else:
            mcp_config = config.get("mcp_server_config")
            if mcp_config and mcp_config.get("url"):
                 mcp_servers_for_agent[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}

    if not mcp_servers_for_agent:
        logger.warning(f"No MCP servers could be configured for context search for user {user_id}. Cannot verify context.")
        return []

    logger.info(f"Context Verifier for user {user_id} will use tools: {list(mcp_servers_for_agent.keys())}")
    
    agent = get_question_generator_agent(
        original_context=original_context,
        available_tools_for_prompt=available_tools_for_prompt,
        mcp_servers_for_agent=mcp_servers_for_agent
    )

    user_prompt = f"Based on the task '{task_description}' and the provided context, please use your tools to find relevant information and then determine if any clarifying questions are necessary."
    messages = [{'role': 'user', 'content': user_prompt}]

    final_response_str = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
            final_response_str = chunk[-1].get("content", "")

    response_data = JsonExtractor.extract_valid_json(clean_llm_output(final_response_str))
    if response_data and isinstance(response_data.get("clarifying_questions"), list):
        return response_data["clarifying_questions"]
    else:
        logger.error(f"Question generator agent returned invalid data: {response_data}. Cannot ask for clarification.")
        return [] # Default to no questions on failure

async def async_process_action_item(user_id: str, action_items: list, topics: list, source_event_id: str, original_context: dict):
    """Async logic for the proactive task orchestrator."""
    db_manager = PlannerMongoManager()
    task_id = None
    try:
        task_description = " ".join(map(str, action_items))
        # Per spec, create task with 'planning' status and immediately trigger planner.
        task = await db_manager.create_initial_task(user_id, task_description, action_items, topics, original_context, source_event_id) # noqa: E501
        task_id = task["task_id"]
        generate_plan_from_context.delay(task_id)
        logger.info(f"Task {task_id} created with status 'planning' and dispatched to planner worker.")

    except Exception as e:
        logger.error(f"Error in process_action_item: {e}", exc_info=True)
        if task_id:
            await db_manager.update_task_status(task_id, "error", {"error": str(e)})
    finally:
        await db_manager.close()

@celery_app.task(name="generate_plan_from_context")
def generate_plan_from_context(task_id: str):
    """Generates a plan for a task once all context is available."""
    run_async(async_generate_plan(task_id))

async def async_generate_plan(task_id: str):
    """Async logic for plan generation."""
    db_manager = PlannerMongoManager()
    try:
        task = await db_manager.get_task(task_id)
        if not task:
            logger.error(f"Cannot generate plan: Task {task_id} not found.")
            return

        if not task.get("runs"):
             logger.error(f"Cannot generate plan: Task {task_id} has no 'runs' array.")
             await db_manager.update_task_status(task_id, "error", {"error": "Task data is malformed: missing 'runs' array."})
             return

        # Determine if this is a change request before proceeding.
        is_change_request = bool(task.get("chat_history"))

        # Prevent re-planning if it's not in a plannable state
        plannable_statuses = ["planning", "clarification_answered"]
        if task.get("status") not in plannable_statuses:
             logger.warning(f"Task {task_id} is not in a plannable state (current: {task.get('status')}). Aborting plan generation.")
             return

        latest_run = task["runs"][-1]
        run_id = latest_run["run_id"]

        user_id = task["user_id"]
        topics = task.get("topics", [])
        original_context = task.get("original_context", {})

        # For re-planning, add previous results and chat history to the context
        if task.get("chat_history"):
            original_context["chat_history"] = task.get("chat_history")
            original_context["previous_plan"] = task.get("plan")
            original_context["previous_result"] = task.get("result")

        task_description = task.get("description", "")

        # If the task is in the 'planning' state, check if clarification is needed.
        if latest_run.get("status") == "planning":
            questions_list = await get_clarifying_questions(user_id, task_description, topics, original_context, db_manager)
            if questions_list and isinstance(questions_list, list) and len(questions_list) > 0:
                logger.info(f"Task {task_id}: Needs clarification. Questions: {questions_list}")
                questions_for_db = [{"question_id": str(uuid.uuid4()), "text": q.strip(), "answer": None} for q in questions_list]

                await db_manager.tasks_collection.update_one(
                    {"task_id": task_id},
                    {"$set": {
                        "status": "clarification_pending", "runs.$[run].status": "clarification_pending", "runs.$[run].clarifying_questions": questions_for_db
                    }},
                    array_filters=[{"run.run_id": run_id}])
                await notify_user(user_id, f"I have a few questions to help me plan: '{task_description[:50]}...'", task_id, notification_type="taskNeedsApproval")
                capture_event(user_id, "clarification_needed", {"task_id": task_id, "question_count": len(questions_list)})
                logger.info(f"Task {task_id} moved to 'clarification_pending'.")
                return # Stop here, wait for user input

        # --- Proceed with planning (Scenario A from spec) ---
        logger.info(f"Task {task_id}: No clarification needed or answers provided. Generating plan.")

        user_profile = await db_manager.user_profiles_collection.find_one(
            {"user_id": user_id},
            {"userData.personalInfo": 1} # Projection to get only necessary data
        )
        personal_info = user_profile.get("userData", {}).get("personalInfo", {})
        user_name = personal_info.get("name", "User")
        user_location_raw = personal_info.get("location", "Not specified")
        if isinstance(user_location_raw, dict):
            user_location = f"latitude: {user_location_raw.get('latitude')}, longitude: {user_location_raw.get('longitude')}"
        else:
            user_location = user_location_raw

        user_timezone_str = personal_info.get("timezone", "UTC")
        try:
            user_timezone = ZoneInfo(user_timezone_str)
        except ZoneInfoNotFoundError:
            logger.warning(f"Invalid timezone '{user_timezone_str}' for user {user_id}. Defaulting to UTC.")
            user_timezone = ZoneInfo("UTC")

        current_user_time = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        retrieved_context = latest_run.get("found_context", {}) # This field doesn't exist yet, but is good for future use
        action_items = task.get("action_items", [])
        if not action_items:
            # This is likely a manually created task. Use its description as the action item.
            logger.info(f"Task {task_id}: No 'action_items' field found. Using main description as the action.")
            action_items = [task.get("description", "")]
        # ** NEW ** Add answered questions to the context
        answered_questions = []
        if latest_run.get("clarifying_questions"):
            for q in latest_run["clarifying_questions"]:
                if q.get("answer"):
                    answered_questions.append(f"User Clarification: Q: {q['text']} A: {q['answer']}")

        if answered_questions:
            retrieved_context["user_clarifications"] = "\n".join(answered_questions)

        available_tools = get_all_mcp_descriptions()

        planner_agent = get_planner_agent(available_tools, current_user_time, user_name, user_location, retrieved_context)

        user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
        messages = [{'role': 'user', 'content': user_prompt_content}]

        final_response_str = ""
        for chunk in planner_agent.run(messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                final_response_str = chunk[-1].get("content", "")

        if not final_response_str:
            raise Exception("Planner agent returned no response.")

        plan_data = JsonExtractor.extract_valid_json(clean_llm_output(final_response_str))
        if not plan_data or "plan" not in plan_data:
            raise Exception(f"Planner agent returned invalid JSON: {final_response_str}")

        await db_manager.update_task_with_plan(task_id, run_id, plan_data, is_change_request=is_change_request)
        capture_event(user_id, "proactive_task_generated", {
            "task_id": task_id,
            "source": task.get("original_context", {}).get("source", "unknown"),
            "plan_steps": len(plan_data.get("plan", []))
        })

        # Notify user that a plan is ready for their approval
        await notify_user(
            user_id, f"I've created a new plan for you: '{plan_data.get('description', '...')[:50]}...'", task_id,
            notification_type="taskNeedsApproval"
        )

        # CRITICAL: Notify the frontend to refresh its task list
        await push_task_list_update(user_id, task_id, run_id)
        logger.info(f"Sent task_list_updated push notification for user {user_id}")


    except Exception as e:
        logger.error(f"Error generating plan for task {task_id}: {e}", exc_info=True)
        await db_manager.update_task_status(task_id, "error", {"error": str(e)})
    finally:
        await db_manager.close()

@celery_app.task(name="refine_task_details")
def refine_task_details(task_id: str):
    """
    Asynchronously refines a user-created task by using an LLM to parse
    the description, priority, and schedule from the initial prompt.
    """
    logger.info(f"Refining details for task_id: {task_id}")
    run_async(async_refine_task_details(task_id))

async def async_refine_task_details(task_id: str):
    db_manager = PlannerMongoManager()
    try:
        task = await db_manager.get_task(task_id)
        if not task or task.get("assignee") != "user":
            logger.warning(f"Skipping refinement for task {task_id}: not found or not assigned to user.")
            return

        user_id = task["user_id"]
        user_profile = await db_manager.user_profiles_collection.find_one({"user_id": user_id})
        personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
        user_name = personal_info.get("name", "User")
        user_timezone_str = personal_info.get("timezone", "UTC")
        user_timezone = ZoneInfo(user_timezone_str)
        current_time_str = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        system_prompt = TASK_CREATION_PROMPT.format(
            user_name=user_name,
            user_timezone=user_timezone_str,
            current_time=current_time_str
        )
        agent = get_qwen_assistant(system_message=system_prompt)
        messages = [{'role': 'user', 'content': task["description"]}] # Use the raw prompt for parsing

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                response_str = chunk[-1].get("content", "")

        parsed_data = JsonExtractor.extract_valid_json(clean_llm_output(response_str))
        if parsed_data:
            # Inject user's timezone into the schedule object if it exists
            if 'schedule' in parsed_data and parsed_data.get('schedule'):
                parsed_data['schedule']['timezone'] = user_timezone_str
            await db_manager.update_task_field(task_id, parsed_data)
            logger.info(f"Successfully refined and updated task {task_id} with new details.")

    except Exception as e:
        logger.error(f"Error refining task {task_id}: {e}", exc_info=True)
    finally:
        await db_manager.close()

# --- Polling Tasks ---
@celery_app.task(name="poll_gmail_for_user")
def poll_gmail_for_user(user_id: str, polling_state: dict):
    logger.info(f"Polling Gmail for user {user_id}")
    db_manager = GmailPollerDB()
    service = GmailPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state))

@celery_app.task(name="poll_gcalendar_for_user")
def poll_gcalendar_for_user(user_id: str, polling_state: dict):
    logger.info(f"Polling GCalendar for user {user_id}")
    db_manager = GCalPollerDB()
    service = GCalendarPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state))

# --- Scheduler Tasks ---
@celery_app.task(name="schedule_all_polling")
def schedule_all_polling():
    """Celery Beat task to check for and queue polling tasks for all services."""
    logger.info("Polling Scheduler: Checking for due polling tasks...")

    async def async_schedule():
        db_manager = GmailPollerDB()
        try:
            await db_manager.reset_stale_polling_locks("gmail")
            await db_manager.reset_stale_polling_locks("gcalendar")

            for service_name in SUPPORTED_POLLING_SERVICES:
                due_tasks_states = await db_manager.get_due_polling_tasks_for_service(service_name)
                logger.info(f"Found {len(due_tasks_states)} due tasks for {service_name}.")

                for task_state in due_tasks_states:
                    user_id = task_state["user_id"]
                    locked_task_state = await db_manager.set_polling_status_and_get(user_id, service_name)
                    if locked_task_state:
                        if service_name == "gmail":
                            poll_gmail_for_user.delay(user_id, locked_task_state)
                        elif service_name == "gcalendar":
                            poll_gcalendar_for_user.delay(user_id, locked_task_state)
                        logger.info(f"Dispatched polling task for {user_id} - service: {service_name}")
        finally:
            await db_manager.close()

    run_async(async_schedule())

def calculate_next_run(schedule: Dict[str, Any], last_run: Optional[datetime.datetime] = None) -> Tuple[Optional[datetime.datetime], Optional[str]]:
    """Calculates the next execution time for a scheduled task in UTC."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    user_timezone_str = schedule.get("timezone", "UTC")

    try:
        user_tz = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        logger.warning(f"Invalid timezone '{user_timezone_str}'. Defaulting to UTC.")
        user_timezone_str = "UTC"
        user_tz = ZoneInfo("UTC")

    # The reference time for 'after' should be in the user's timezone to handle day boundaries correctly
    start_time_user_tz = (last_run or now_utc).astimezone(user_tz)

    try:
        frequency = schedule.get("frequency")
        time_str = schedule.get("time", "09:00") # Default to 9 AM
        hour, minute = map(int, time_str.split(':'))

        # Create the start datetime in the user's timezone
        dtstart_user_tz = start_time_user_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)

        rule = None
        if frequency == 'daily':
            rule = rrule.rrule(rrule.DAILY, dtstart=dtstart_user_tz, until=start_time_user_tz + datetime.timedelta(days=365))
        elif frequency == 'weekly':
            days = schedule.get("days", [])
            if not days: return None, user_timezone_str
            weekday_map = {"Sunday": rrule.SU, "Monday": rrule.MO, "Tuesday": rrule.TU, "Wednesday": rrule.WE, "Thursday": rrule.TH, "Friday": rrule.FR, "Saturday": rrule.SA}
            byweekday = [weekday_map[day] for day in days if day in weekday_map]
            if not byweekday: return None, user_timezone_str
            rule = rrule.rrule(rrule.WEEKLY, dtstart=dtstart_user_tz, byweekday=byweekday, until=start_time_user_tz + datetime.timedelta(days=365))

        if rule:
            next_run_user_tz = rule.after(start_time_user_tz)
            if next_run_user_tz:
                # Convert the result back to UTC for storage
                return next_run_user_tz.astimezone(datetime.timezone.utc), user_timezone_str
    except Exception as e:
        logger.error(f"Error calculating next run time for schedule {schedule}: {e}")
    return None, user_timezone_str

@celery_app.task(name="run_due_tasks")
def run_due_tasks():
    """Celery Beat task to check for and queue user-defined tasks (recurring and scheduled-once)."""
    logger.info("Scheduler: Checking for due user-defined tasks...")
    run_async(async_run_due_tasks())


async def async_run_due_tasks():
    db_manager = PlannerMongoManager()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        # Fetch tasks that are due and are either 'active' (recurring) or 'pending' (scheduled-once)
        query = {
            "status": {"$in": ["active", "pending"]},
            "enabled": True,
            "next_execution_at": {"$lte": now}
        }
        due_tasks_cursor = db_manager.tasks_collection.find(query)
        due_tasks = await due_tasks_cursor.to_list(length=None)

        if not due_tasks:
            logger.info("Scheduler: No user-defined tasks are due.")
            return

        logger.info(f"Scheduler: Found {len(due_tasks)} due user-defined tasks.")
        for task in due_tasks:
            logger.info(f"Scheduler: Queuing user-defined task {task['task_id']} for execution.")
            execute_task_plan.delay(task['task_id'], task['user_id'])

            # For recurring tasks, calculate the next run time.
            # For one-off tasks, this will effectively be cleared.
            next_run_time = None
            if task.get('schedule', {}).get('type') == 'recurring':
                next_run_time, _ = calculate_next_run(task['schedule'], last_run=now)

            update_fields = {
                "last_execution_at": now,
                "next_execution_at": next_run_time
            }
            # One-off tasks have their next_execution_at set to None, so they won't run again.
            # Their status will be updated to 'processing' -> 'completed'/'error' by the executor.

            await db_manager.tasks_collection.update_one(
                {"_id": task["_id"]},
                {"$set": update_fields}
            )
            if next_run_time:
                 logger.info(f"Scheduler: Rescheduled user-defined task {task['task_id']} for {next_run_time}.")

    except Exception as e:
        logger.error(f"Scheduler: An error occurred checking user-defined tasks: {e}", exc_info=True)
    finally:
        await db_manager.close()


# --- Chat History Summarization Task ---
@celery_app.task(name="summarize_old_conversations")
def summarize_old_conversations():
    """
    Celery Beat task to find old, unsummarized messages, group them into chunks,
    summarize them, and store the summaries and embeddings in ChromaDB.
    """
    logger.info("Summarization Task: Starting to look for old conversations to summarize.")
    run_async(async_summarize_conversations())

async def async_summarize_conversations():
    db_manager = PlannerMongoManager()  # Re-using for its mongo access
    try:
        # 1. Find users with recent, unsummarized messages
        # We process one user at a time to keep the task manageable.
        # This aggregation finds the first user with unsummarized messages older than 1 day.
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        pipeline = [
            {"$match": {"is_summarized": False, "timestamp": {"$lt": one_day_ago}}},
            {"$group": {"_id": "$user_id"}},
            {"$limit": 1} # Process one user per run
        ]
        user_to_process = await db_manager.messages_collection.aggregate(pipeline).to_list(length=1)

        if not user_to_process:
            logger.info("Summarization Task: No users with old, unsummarized messages found.")
            return

        user_id = user_to_process[0]['_id']
        logger.info(f"Summarization Task: Found user {user_id} with messages to summarize.")

        # 2. Fetch all unsummarized messages for this user
        messages_cursor = db_manager.messages_collection.find({
            "user_id": user_id,
            "is_summarized": False
        }).sort("timestamp", 1) # Get them in chronological order
        
        messages_to_process = await messages_cursor.to_list(length=None)
        
        if not messages_to_process:
            logger.info(f"Summarization Task: No unsummarized messages to process for user {user_id}.")
            return

        # 3. Group messages into chunks (e.g., of 30 messages)
        chunk_size = 30
        message_chunks = [messages_to_process[i:i + chunk_size] for i in range(0, len(messages_to_process), chunk_size)]
        
        # 4. Process each chunk
        system_prompt = "You are a summarization expert. Summarize the key points, decisions, facts, and topics from the following conversation chunk into a dense, third-person paragraph. Focus on information that would be useful for future context. Do not add any preamble or sign-off."
        summarizer_agent = get_qwen_assistant(system_message=system_prompt)
        
        for chunk in message_chunks:
            if len(chunk) < 5: # Don't summarize very small chunks
                continue

            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chunk])
            
            # 4a. Summarize with LLM
            messages = [{'role': 'user', 'content': conversation_text}]
            summary_text = ""
            for response_chunk in summarizer_agent.run(messages=messages):
                 if isinstance(response_chunk, list) and response_chunk and response_chunk[-1].get("role") == "assistant":
                    summary_text = response_chunk[-1].get("content", "")

            summary_text = clean_llm_output(summary_text)
            if not summary_text:
                logger.warning(f"Summarization for user {user_id} produced an empty result. Skipping chunk.")
                continue

            # 4b. Store summary and embedding in ChromaDB
            summary_id = str(uuid.uuid4())
            message_ids = [msg['message_id'] for msg in chunk]
            
            collection = get_conversation_summaries_collection()
            collection.add(
                ids=[summary_id],
                documents=[summary_text],
                metadatas=[{
                    "user_id": user_id,
                    "start_timestamp": chunk[0]['timestamp'].isoformat(),
                    "end_timestamp": chunk[-1]['timestamp'].isoformat(),
                    "message_ids_json": json.dumps(message_ids)
                }]
            )
            logger.info(f"Summarization Task: Stored summary {summary_id} in ChromaDB for user {user_id}.")
            
            # 4c. Update original messages in MongoDB
            message_object_ids = [msg['_id'] for msg in chunk]
            await db_manager.messages_collection.update_many(
                {"_id": {"$in": message_object_ids}},
                {"$set": {"is_summarized": True, "summary_id": summary_id}}
            )

            # 4d. Extract memories from the summary
            extract_from_context.delay(user_id=user_id, source_text=summary_text, source_type="chat_summary")

    except Exception as e:
        logger.error(f"Error during conversation summarization: {e}", exc_info=True)
    finally:
        await db_manager.close()