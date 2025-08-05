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
from json_extractor import JsonExtractor
from workers.utils.api_client import notify_user, push_task_list_update
from main.config import INTEGRATIONS_CONFIG
from main.tasks.prompts import TASK_CREATION_PROMPT
from main.llm import run_agent_with_fallback as run_main_agent_with_fallback
from main.db import MongoManager
from workers.celery_app import celery_app
from workers.planner.llm import get_planner_agent, get_question_generator_agent # noqa: E501
from workers.proactive.main import run_proactive_pipeline_logic
from workers.planner.db import PlannerMongoManager, get_all_mcp_descriptions # noqa: E501
from workers.memory_agent_utils import get_memory_qwen_agent, get_db_manager as get_memory_db_manager # noqa: E501
from workers.executor.tasks import execute_task_plan
from main.vector_db import get_conversation_summaries_collection
from main.chat.prompts import STAGE_1_SYSTEM_PROMPT
from workers.planner.llm import run_agent_with_fallback as run_worker_agent_with_fallback
from mcp_hub.memory.utils import cud_memory, initialize_embedding_model, initialize_agents
from workers.utils.text_utils import clean_llm_output

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
        prompt = f"User Query: \"{query}\"\n\nAvailable External Tools (for selection):\n{tools_description}"

        messages = [{'role': 'user', 'content': prompt}]

        def _run_selector_sync():
            final_content_str = ""
            for chunk in run_main_agent_with_fallback(system_message=STAGE_1_SYSTEM_PROMPT, function_list=[], messages=messages):
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

@celery_app.task(name="proactive_reasoning_pipeline")
def proactive_reasoning_pipeline(user_id: str, event_type: str, event_data: Dict[str, Any]):
    """
    Celery task entry point for the new proactive reasoning pipeline.
    """
    logger.info(f"Celery worker received task 'proactive_reasoning_pipeline' for user_id: {user_id}, event_type: {event_type}")
    run_async(run_proactive_pipeline_logic(user_id, event_type, event_data))

@celery_app.task(name="cud_memory_task")
def cud_memory_task(user_id: str, information: str, source: Optional[str] = None):
    """
    Celery task wrapper for the CUD (Create, Update, Delete) memory operation.
    This runs the core memory management logic asynchronously.
    """
    logger.info(f"Celery worker received cud_memory_task for user_id: {user_id}")

    # --- NEW: Fetch user's name before calling cud_memory ---
    db_manager = MongoManager()
    username = user_id # Default fallback
    try:
        user_profile = run_async(db_manager.get_user_profile(user_id))
        if user_profile:
            username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
    except Exception as e:
        logger.error(f"Failed to fetch user profile for {user_id} in cud_memory_task: {e}")
    finally:
        run_async(db_manager.close())
    # --- END NEW ---

    initialize_embedding_model()
    initialize_agents()
    # Pass the fetched username to the cud_memory function
    run_async(cud_memory(user_id, information, source, username))

@celery_app.task(name="create_task_from_suggestion")
def create_task_from_suggestion(user_id: str, suggestion_payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    """
    Takes an approved suggestion payload and creates a new task.
    """
    logger.info(f"Creating task from approved suggestion for user '{user_id}'. Type: {suggestion_payload.get('suggestion_type')}")
    
    action_details = suggestion_payload.get("action_details", {})
    action_type = action_details.get("action_type")

    # Define the task name from the suggestion description and the description from all available context.
    name = suggestion_payload.get('suggestion_description', f"Proactive Task: {action_type}")
    description_parts = [
        f"Action Details: {json.dumps(action_details, indent=2)}",
        f"Reasoning: {suggestion_payload.get('reasoning', 'N/A')}",
        f"Full Context: {json.dumps(context, indent=2, default=str)}"
    ]
    description = "\n\n---\n\n".join(description_parts)

    worker_mongo_manager = None
    try:
        worker_mongo_manager = MongoManager()
        task_data = {
            "name": name,
            "description": description,
            "original_context": {
                "source": "proactive_suggestion",
                "suggestion_type": suggestion_payload.get("suggestion_type"),
                "trigger_event": context.get("trigger_event")
            }
        }
        task_id = run_async(worker_mongo_manager.add_task(user_id, task_data))

        # For proactive tasks, we have enough context to go straight to planning.
        generate_plan_from_context.delay(task_id, user_id)
        logger.info(f"Successfully created and dispatched new task '{task_id}' from suggestion for planning.")
    finally:
        if worker_mongo_manager:
            run_async(worker_mongo_manager.close())


@celery_app.task(name="refine_and_plan_ai_task")
def refine_and_plan_ai_task(task_id: str, user_id: str):
    """
    Asynchronously refines an AI-assigned task's details using an LLM,
    updates the task in the DB, and then triggers the planning process.
    """
    logger.info(f"Refining and planning for AI task_id: {task_id}")
    run_async(async_refine_and_plan_ai_task(task_id, user_id))

async def async_refine_and_plan_ai_task(task_id: str, user_id: str):
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

        system_prompt = TASK_CREATION_PROMPT.format( # noqa
            user_name=user_name,
            user_timezone=user_timezone_str,
            current_time=current_time_str
        )
        # Use the raw prompt from the task's description for parsing
        messages = [{'role': 'user', 'content': task["description"]}]

        response_str = ""
        for chunk in run_main_agent_with_fallback(system_message=system_prompt, function_list=[], messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                response_str = chunk[-1].get("content", "")

        parsed_data = JsonExtractor.extract_valid_json(clean_llm_output(response_str))
        if parsed_data:
            # Safeguard: never allow the refiner to nullify or change the user_id
            if "user_id" in parsed_data:
                del parsed_data["user_id"]

            # Safeguard: never allow the refiner to nullify or change the user_id
            if "user_id" in parsed_data:
                del parsed_data["user_id"]

            # Inject user's timezone into the schedule object if it exists
            if 'schedule' in parsed_data and parsed_data.get('schedule'):
                parsed_data['schedule']['timezone'] = user_timezone_str
            # Ensure description is not empty, fall back to original prompt if needed
            if not parsed_data.get("name"):
                parsed_data["name"] = task["description"] or task["name"]
            await db_manager.update_task_field(task_id, parsed_data)
            logger.info(f"Successfully refined and updated AI task {task_id} with new details.")
        else:
            logger.warning(f"Could not parse details for AI task {task_id}, proceeding with raw description.")

        # Now trigger the planning step, which is the main purpose of AI-assigned tasks
        generate_plan_from_context.delay(task_id, user_id)
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

    # 1. Get all available (connected + built-in) tools for the user
    connected_tools, _ = _get_tool_lists(user_integrations)

    # 2. Select tools relevant to the task description
    relevant_tool_names = await _select_relevant_tools(task_description, connected_tools)

    # 3. Always include memory for context verification
    final_tool_names = set(relevant_tool_names)
    final_tool_names.add("memory")
    
    logger.info("Selected tools for context verification: " + ", ".join(final_tool_names))

    # 4. Build the MCP server config and prompt info for the agent
    mcp_servers_for_agent = {}
    available_tools_for_prompt = {}

    for tool_name in final_tool_names:
        config = INTEGRATIONS_CONFIG.get(tool_name)
        if not config: continue

        available_tools_for_prompt[tool_name] = config.get("description", "")
        
        mcp_config = config.get("mcp_server_config")
        if mcp_config and mcp_config.get("url"):
             mcp_servers_for_agent[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}

    if not mcp_servers_for_agent:
        logger.warning(f"No MCP servers could be configured for context search for user {user_id}. Cannot verify context.")
        return []

    logger.info(f"Context Verifier for user {user_id} will use tools: {list(mcp_servers_for_agent.keys())}")
    
    agent_config = get_question_generator_agent(
        original_context=original_context,
        available_tools_for_prompt=available_tools_for_prompt,
        mcp_servers_for_agent=mcp_servers_for_agent
    )

    user_prompt = f"Based on the task '{task_description}' and the provided context, please use your tools to find relevant information and then determine if any clarifying questions are necessary."
    messages = [{'role': 'user', 'content': user_prompt}]

    final_response_str = ""
    for chunk in run_worker_agent_with_fallback(system_message=agent_config["system_message"], function_list=agent_config["function_list"], messages=messages):
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
        # For proactive tasks, the initial name is the description, and the description is the context.
        # The planner will generate a better name and description later.
        full_description = json.dumps(original_context, indent=2, default=str)
        # Per spec, create task with 'planning' status and immediately trigger planner.
        task = await db_manager.create_initial_task(user_id, task_description, full_description, action_items, topics, original_context, source_event_id)
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
def generate_plan_from_context(task_id: str, user_id: str):
    """Generates a plan for a task once all context is available."""
    run_async(async_generate_plan(task_id, user_id))

async def async_generate_plan(task_id: str, user_id: str):
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

        # Trust the user_id passed to the Celery task.
        # If the document is missing it for some reason, log a warning and proceed.
        if not task.get("user_id"):
            logger.warning(f"Task {task_id} document is missing user_id. Proceeding with passed user_id '{user_id}'.")
            # Attempt to heal the document
            await db_manager.update_task_field(task_id, {"user_id": user_id})

        original_context = task.get("original_context", {})

        # For re-planning, add previous results and chat history to the context
        if task.get("chat_history"):
            original_context["chat_history"] = task.get("chat_history")
            original_context["previous_plan"] = task.get("plan")
            original_context["previous_result"] = task.get("result")

        task_description = task.get("description", "")

        # If the task is in the 'planning' state, check if clarification is needed.
        if latest_run.get("status") == "planning":
            questions_list = await get_clarifying_questions(user_id, task_description, task.get("topics", []), original_context, db_manager) # noqa
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
        if not user_profile:
            logger.error(f"User profile not found for user_id '{user_id}' associated with task {task_id}. Cannot generate plan.")
            await db_manager.update_task_status(task_id, "error", {"error": f"User profile not found for user_id '{user_id}'."})
            return

        if not user_profile:
            logger.error(f"User profile not found for user_id '{user_id}' associated with task {task_id}. Cannot generate plan.")
            await db_manager.update_task_status(task_id, "error", {"error": f"User profile not found for user_id '{user_id}'."})
            return

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

        agent_config = get_planner_agent(available_tools, current_user_time, user_name, user_location, retrieved_context)

        user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
        messages = [{'role': 'user', 'content': user_prompt_content}]

        final_response_str = ""
        for chunk in run_worker_agent_with_fallback(system_message=agent_config["system_message"], function_list=agent_config["function_list"], messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                final_response_str = chunk[-1].get("content", "")

        if not final_response_str:
            raise Exception("Planner agent returned no response.")

        plan_data = JsonExtractor.extract_valid_json(clean_llm_output(final_response_str))
        if not plan_data or "plan" not in plan_data:
            raise Exception(f"Planner agent returned invalid JSON: {final_response_str}")

        await db_manager.update_task_with_plan(task_id, run_id, plan_data, is_change_request)
        capture_event(user_id, "proactive_task_generated", {
            "task_id": task_id,
            "source": task.get("original_context", {}).get("source", "unknown"),
            "plan_steps": len(plan_data.get("plan", []))
        })

        # Notify user that a plan is ready for their approval
        await notify_user(
            user_id, f"I've created a new plan for you: '{plan_data.get('name', '...')[:50]}...'", task_id,
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

        system_prompt = TASK_CREATION_PROMPT.format( # noqa
            user_name=user_name,
            user_timezone=user_timezone_str,
            current_time=current_time_str
        )
        messages = [{'role': 'user', 'content': task["description"]}] # Use the raw prompt for parsing

        response_str = ""
        for chunk in run_main_agent_with_fallback(system_message=system_prompt, function_list=[], messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                response_str = chunk[-1].get("content", "")

        parsed_data = JsonExtractor.extract_valid_json(clean_llm_output(response_str))
        if parsed_data:
            # Inject user's timezone into the schedule object if it exists
            if 'schedule' in parsed_data and parsed_data.get('schedule'):
                parsed_data['schedule']['timezone'] = user_timezone_str
            await db_manager.update_task_field(task_id, parsed_data)
            logger.info(f"Successfully refined and updated user task {task_id} with new details.")

    except Exception as e:
        logger.error(f"Error refining task {task_id}: {e}", exc_info=True)
    finally:
        await db_manager.close()

def _event_matches_filter(event_data: Dict[str, Any], task_filter: Dict[str, Any], source: str) -> bool:
    """
    Checks if an event's data matches the conditions defined in a task's filter.
    """
    if not task_filter:
        return True # No filter means it matches all events of this type

    for key, value in task_filter.items():
        if source == 'gmail':
            # Special handling for gmail 'from' field which can be "Name <email@example.com>"
            if key == 'from':
                from_header = event_data.get('from', '').lower()
                if value.lower() not in from_header:
                    return False
            # Special handling for subject contains
            elif key == 'subject_contains':
                subject = event_data.get('subject', '').lower()
                if value.lower() not in subject:
                    return False
            else:
                # Generic key-value check for other fields
                event_value = event_data.get(key)
                if isinstance(event_value, str) and value.lower() not in event_value.lower():
                    return False
                elif isinstance(event_value, list) and value not in event_value:
                    return False
                elif event_value != value:
                    return False
        # Add logic for other sources like 'slack' here
        # elif source == 'slack':
        #     if key == 'channel' and event_data.get('channel_name') != value:
        #         return False
        else:
            # Default simple matching
            if event_data.get(key) != value:
                return False

    return True

async def async_execute_triggered_task(user_id: str, source: str, event_type: str, event_data: Dict[str, Any]):
    db_manager = MongoManager()
    try:
        # Find all active tasks for this user that are triggered by this source and event
        query = {
            "user_id": user_id,
            "status": "active",
            "enabled": True,
            "schedule.type": "triggered",
            "schedule.source": source,
            "schedule.event": event_type
        }
        triggered_tasks_cursor = db_manager.task_collection.find(query)
        tasks_to_check = await triggered_tasks_cursor.to_list(length=None)

        if not tasks_to_check:
            logger.info(f"No triggered tasks found for user '{user_id}' matching this event.")
            return

        logger.info(f"Found {len(tasks_to_check)} potential triggered tasks for user '{user_id}'.")

        for task in tasks_to_check:
            task_id = task['task_id']
            schedule = task.get('schedule', {})
            task_filter = schedule.get('filter', {})

            if _event_matches_filter(event_data, task_filter, source):
                logger.info(f"Event matches filter for triggered task {task_id}. Queuing for execution.")

                # The event data becomes the context for this execution run.
                # We need to create a new "run" for this triggered execution.
                new_run = {
                    "run_id": str(uuid.uuid4()),
                    "status": "processing", # Start execution immediately
                    "plan": task.get("plan", []), # Use the main plan
                    "trigger_event_data": event_data,
                    "created_at": datetime.datetime.now(datetime.timezone.utc)
                }

                await db_manager.task_collection.update_one(
                    {"task_id": task_id},
                    {"$push": {"runs": new_run}}
                )

                # Queue the executor with the new run_id
                execute_task_plan.delay(task_id, user_id)
            else:
                logger.debug(f"Event did not match filter for triggered task {task_id}.")

    except Exception as e:
        logger.error(f"Error during async_execute_triggered_task for user {user_id}: {e}", exc_info=True)
    finally:
        await db_manager.close()

@celery_app.task(name="execute_triggered_task")
def execute_triggered_task(user_id: str, source: str, event_type: str, event_data: Dict[str, Any]):
    """
    Checks for and executes any tasks triggered by a new event.
    """
    logger.info(f"Checking for triggered tasks for user '{user_id}' from source '{source}' event '{event_type}'.")
    run_async(async_execute_triggered_task(user_id, source, event_type, event_data))

# --- Polling Tasks ---
@celery_app.task(name="poll_gmail_for_proactivity")
def poll_gmail_for_proactivity(user_id: str, polling_state: dict):
    logger.info(f"Polling Gmail for proactivity for user {user_id}")
    db_manager = GmailPollerDB()
    service = GmailPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state, mode='proactivity'))

@celery_app.task(name="poll_gmail_for_triggers")
def poll_gmail_for_triggers(user_id: str, polling_state: dict):
    logger.info(f"Polling Gmail for triggers for user {user_id}")
    db_manager = GmailPollerDB()
    service = GmailPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state, mode='triggers'))

@celery_app.task(name="poll_gcalendar_for_proactivity")
def poll_gcalendar_for_proactivity(user_id: str, polling_state: dict):
    logger.info(f"Polling GCalendar for proactivity for user {user_id}")
    db_manager = GCalPollerDB()
    service = GCalendarPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state, mode='proactivity'))

@celery_app.task(name="poll_gcalendar_for_triggers")
def poll_gcalendar_for_triggers(user_id: str, polling_state: dict):
    logger.info(f"Polling GCalendar for triggers for user {user_id}")
    db_manager = GCalPollerDB()
    service = GCalendarPollingService(db_manager)
    run_async(service._run_single_user_poll_cycle(user_id, polling_state, mode='triggers'))

# --- Scheduler Tasks ---
@celery_app.task(name="schedule_proactivity_polling")
def schedule_proactivity_polling():
    """Celery Beat task for the less frequent proactivity polling."""
    logger.info("Proactivity Polling Scheduler: Checking for due tasks...")
    run_async(async_schedule_polling('proactivity'))

@celery_app.task(name="schedule_trigger_polling")
def schedule_trigger_polling():
    """Celery Beat task for the frequent triggered workflow polling."""
    logger.info("Trigger Polling Scheduler: Checking for due tasks...")
    run_async(async_schedule_polling('triggers'))

async def async_schedule_polling(mode: str):
    """Generic scheduler logic for both proactivity and triggers."""
    db_manager = GmailPollerDB() # Can use either DB manager as they are identical
    try:
        supported_polling_services = ["gmail", "gcalendar"]
        await db_manager.reset_stale_polling_locks("gmail", mode)
        await db_manager.reset_stale_polling_locks("gcalendar", mode)

        for service_name in supported_polling_services:
            due_tasks_states = await db_manager.get_due_polling_tasks_for_service(service_name, mode)
            logger.info(f"Found {len(due_tasks_states)} due '{mode}' tasks for {service_name}.")

            for task_state in due_tasks_states:
                user_id = task_state["user_id"]
                locked_task_state = await db_manager.set_polling_status_and_get(user_id, service_name, mode)

                if locked_task_state and '_id' in locked_task_state and isinstance(locked_task_state['_id'], ObjectId):
                    locked_task_state['_id'] = str(locked_task_state['_id'])

                if locked_task_state:
                    if service_name == "gmail":
                        if mode == 'proactivity':
                            poll_gmail_for_proactivity.delay(user_id, locked_task_state)
                        else: # triggers
                            poll_gmail_for_triggers.delay(user_id, locked_task_state)
                    elif service_name == "gcalendar":
                        if mode == 'proactivity':
                            poll_gcalendar_for_proactivity.delay(user_id, locked_task_state)
                        else: # triggers
                            poll_gcalendar_for_triggers.delay(user_id, locked_task_state)
                    logger.info(f"Dispatched '{mode}' polling task for {user_id} - service: {service_name}")
    finally:
        await db_manager.close()

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
            
            # --- NEW LOGIC: Create a new run for recurring tasks ---
            if task.get('schedule', {}).get('type') == 'recurring':
                # The plan is copied from the latest existing run, which is the approved template.
                latest_run_plan = task.get("runs", [{}])[-1].get("plan", [])
                new_run = {
                    "run_id": str(uuid.uuid4()),
                    "status": "processing", # Start execution immediately
                    "plan": latest_run_plan, # Use the approved plan
                    "created_at": datetime.datetime.now(datetime.timezone.utc)
                }
                
                # Atomically push the new run and update the top-level task status
                await db_manager.task_collection.update_one(
                    {"_id": task["_id"]},
                    {
                        "$push": {"runs": new_run},
                        "$set": {"status": "processing"}
                    }
                )
                logger.info(f"Created new run {new_run['run_id']} for recurring task {task['task_id']}.")
            # --- END NEW LOGIC ---

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

# src/server/workers/tasks.py

async def async_summarize_conversations():
    db_manager = PlannerMongoManager()  # Re-using for its mongo access
    try:
        # 1. Find users with recent, unsummarized messages
        # We process one user at a time to keep the task manageable.
        # This aggregation finds the first user with unsummarized messages older than 1 day.
        # Temporarily changed for testing
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)
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
        
        for chunk in message_chunks:
            if len(chunk) < 2: # Don't summarize single messages
                continue

            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chunk])
            
            # 4a. Summarize with LLM using the new, narrative-style prompt
            messages = [{'role': 'user', 'content': conversation_text}]
            summary_text = ""
            
            # --- MODIFIED PROMPT ---
            system_prompt = """
You are the AI assistant in the provided conversation log. Your task is to write a summary of the conversation from your own perspective, as if you are recalling the memory of the interaction.

Core Instructions:
1.  Adopt a First-Person Narrative: Use "I", "me", and "my" to refer to your own actions and thoughts. Refer to the other party as "the user".
2.  Describe the Flow: Recount the conversation as a sequence of events. For example: "The user told me about their project...", "I then asked for clarification on...", "We then discussed...".
3.  CRITICAL INSTRUCTION FOR FILE UPLOADS: If a user message involves uploading a file (e.g., "user: (Attached file for context: report.pdf) Can you summarize this?"), your summary must NOT state that you cannot process it. Instead, you MUST describe the user's action factually. For example: "The user uploaded a file named 'report.pdf' and asked for a summary."
4.  Goal: The goal is to create a dense, narrative paragraph that captures the key information, decisions, and flow of the conversation from your point of view. Focus on information that would be useful for future context.
5.  Format: Do not add any preamble or sign-off. Respond only with the summary paragraph.
"""
            # --- END MODIFIED PROMPT ---

            for response_chunk in run_main_agent_with_fallback(system_message=system_prompt, function_list=[], messages=messages):
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

    except Exception as e:
        logger.error(f"Error during conversation summarization: {e}", exc_info=True)
    finally:
        await db_manager.close()