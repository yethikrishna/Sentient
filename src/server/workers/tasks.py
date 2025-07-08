import asyncio
import logging
import json
import re
import datetime
from json_extractor import JsonExtractor
import os
import httpx
from dateutil import rrule
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict, Any, Optional

from workers.config import SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX, SUPPORTED_POLLING_SERVICES
from workers.utils.api_client import notify_user
from workers.celery_app import celery_app
from workers.planner.llm import get_planner_agent
from workers.planner.db import PlannerMongoManager, get_all_mcp_descriptions
from workers.supermemory_agent_utils import get_supermemory_qwen_agent, get_db_manager as get_memory_db_manager
from workers.executor.tasks import execute_task_plan

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
def process_memory_item(user_id: str, fact_text: str):
    """
    Celery task to process a single memory item by calling the Supermemory MCP
    via a dedicated Qwen agent.
    """
    logger.info(f"Celery worker received Supermemory task for user {user_id}: '{fact_text[:80]}...'")

    async def async_process_memory():
        db_manager = get_memory_db_manager()
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

# --- Extractor Task ---
@celery_app.task(name="extract_from_context")
def extract_from_context(user_id: str, service_name: str, event_id: str, event_data: Dict[str, Any]):
    """
    Celery task to replace the Extractor worker. It takes context data,
    runs it through an LLM to extract memories and action items,
    and then dispatches further Celery tasks.
    """
    logger.info(f"Extractor task running for event {event_id} ({service_name}) for user {user_id}")
    
    async def async_extract():
        db_manager = ExtractorMongoManager()
        try:
            if await db_manager.is_event_processed(user_id, event_id):
                logger.info(f"Skipping event {event_id} - already processed.")
                return

            llm_input_content = ""
            if service_name == "journal_block":
                page_date = event_data.get('page_date')
                if page_date:
                    llm_input_content = f"Source: Journal Entry on {page_date}\n\nContent:\n{event_data.get('content', '')}"
                else:
                    llm_input_content = f"Source: Journal Entry\n\nContent:\n{event_data.get('content', '')}"
            elif service_name == "gmail":
                llm_input_content = f"Source: Email\nSubject: {event_data.get('subject', '')}\n\nBody:\n{event_data.get('body', '')}"
            elif service_name == "gcalendar":
                llm_input_content = f"Source: Calendar Event\nSummary: {event_data.get('summary', '')}\n\nDescription:\n{event_data.get('description', '')}"

            if not llm_input_content.strip():
                logger.warning(f"Skipping event {event_id} due to empty content.")
                return

            agent = get_extractor_agent()
            messages = [{'role': 'user', 'content': llm_input_content}]
            
            final_content_str = ""
            for chunk in agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content_str = last_message["content"]

            if not final_content_str:
                logger.error(f"Extractor LLM returned no response for event {event_id}.")
                return

            extracted_data = JsonExtractor.extract_valid_json(final_content_str)
            if not extracted_data:
                logger.error(f"Could not extract valid JSON from LLM response for event {event_id}. Response: '{final_content_str}'")
                await db_manager.log_extraction_result(event_id, user_id, 0, 0) # Log to prevent re-processing
                return

            memory_items = extracted_data.get("memory_items", [])
            action_items = extracted_data.get("action_items", [])
            short_term_notes = extracted_data.get("short_term_notes", [])

            for fact in memory_items:
                if isinstance(fact, str) and fact.strip():
                    process_memory_item.delay(user_id, fact)

            if action_items:
                # Add block_id to context if it came from a journal
                if service_name == "journal_block":
                    original_context_with_block = {
                        "source": "journal_block",
                        "block_id": event_id,
            "original_content": event_data.get('content', ''),
            "page_date": event_data.get('page_date')
                    }
                    process_action_item.delay(user_id, action_items, event_id, original_context_with_block)
                else:
                    process_action_item.delay(user_id, action_items, event_id, event_data)

            for note in short_term_notes:
                if isinstance(note, str) and note.strip():
                    add_journal_entry_task.delay(user_id, note)

            await db_manager.log_extraction_result(event_id, user_id, len(memory_items), len(action_items))
        
        except Exception as e:
            logger.error(f"Error in extractor task for event {event_id}: {e}", exc_info=True)
        finally:
            await db_manager.close()

    run_async(async_extract())

@celery_app.task(name="add_journal_entry_task")
def add_journal_entry_task(user_id: str, content: str, date: Optional[str] = None):
    """
    Celery task to add a new entry to the user's journal via the Journal MCP.
    """
    logger.info(f"Journal task running for user {user_id}: '{content[:50]}...'")

    async def async_add_entry():
        mcp_url = os.getenv("JOURNAL_MCP_SERVER_URL", "http://localhost:9018/sse")
        payload = {
            "tool": "add_journal_entry",
            "parameters": {
                "content": content,
                "date": date # Will be None if not provided, tool handles default
            }
        }
        headers = {"Content-Type": "application/json", "X-User-ID": user_id}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(mcp_url, json=payload, headers=headers, timeout=20)
                response.raise_for_status()
                logger.info(f"Successfully called journal MCP for user {user_id}. Response: {response.text}")
                return {"status": "success", "response": response.text}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling journal MCP for user {user_id}: {e.response.status_code} - {e.response.text}")
            return {"status": "failure", "reason": "HTTP error"}
        except Exception as e:
            logger.error(f"Error in journal task for user {user_id}: {e}", exc_info=True)
            return {"status": "failure", "reason": str(e)}

    return run_async(async_add_entry())

# --- Planner Task ---
@celery_app.task(name="process_action_item")
def process_action_item(user_id: str, action_items: list, source_event_id: str, original_context: dict):
    """Celery task to process action items and generate a plan."""
    logger.info(f"Planner task running for user {user_id} with {len(action_items)} actions.")

    async def async_main():
        db_manager = PlannerMongoManager()
        try:
            # Fetch user's info to provide context to the planner
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

            available_tools = get_all_mcp_descriptions()
            if not available_tools:
                logger.warning(f"No tools available for planner task for user {user_id}.")
                return

            agent = get_planner_agent(available_tools, current_user_time, user_name, user_location)
            user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
            messages = [{'role': 'user', 'content': user_prompt_content}]


            final_response_str = ""
            for chunk in agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        content = last_message["content"]
                        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                        final_response_str = match.group(1) if match else content
            
            if not final_response_str:
                logger.error(f"Planner agent for user {user_id} returned no response.")
                return

            plan_data = json.loads(final_response_str)
            description = plan_data.get("description", "Proactively generated plan")
            plan_steps = plan_data.get("plan", [])

            if plan_steps and all(step.get("tool") in available_tools for step in plan_steps):
                task_id = await db_manager.save_plan_as_task(user_id, description, plan_steps, original_context, source_event_id)
                notification_message = f"I've created a new plan to '{description}'. It's ready for your approval."
                await notify_user(user_id, notification_message, task_id)
                logger.info(f"Saved plan as task {task_id} for user {user_id}.")
            else:
                 logger.warning(f"Planner for user {user_id} generated an empty or invalid plan.")

        except Exception as e:
            logger.error(f"Failed to process/save plan for user {user_id}: {e}", exc_info=True)
        finally:
            await db_manager.close()

    run_async(async_main())

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

def calculate_next_run(schedule: Dict[str, Any], last_run: Optional[datetime.datetime] = None) -> Optional[datetime.datetime]:
    """Calculates the next execution time for a scheduled task."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_time = last_run or now

    try:
        frequency = schedule.get("frequency")
        time_str = schedule.get("time", "00:00")
        hour, minute = map(int, time_str.split(':'))
        dtstart = start_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        rule = None
        if frequency == 'daily':
            rule = rrule.rrule(rrule.DAILY, dtstart=dtstart)
        elif frequency == 'weekly':
            days = schedule.get("days", [])
            if not days: return None
            weekday_map = {"Sunday": rrule.SU, "Monday": rrule.MO, "Tuesday": rrule.TU, "Wednesday": rrule.WE, "Thursday": rrule.TH, "Friday": rrule.FR, "Saturday": rrule.SA}
            byweekday = [weekday_map[day] for day in days if day in weekday_map]
            if not byweekday: return None
            rule = rrule.rrule(rrule.WEEKLY, dtstart=dtstart, byweekday=byweekday)

        if rule:
            next_run = rule.after(start_time)
            if next_run and next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=datetime.timezone.utc)
            return next_run
    except Exception as e:
        logger.error(f"Error calculating next run time for schedule {schedule}: {e}")
    return None

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
                next_run_time = calculate_next_run(task['schedule'], last_run=now)

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