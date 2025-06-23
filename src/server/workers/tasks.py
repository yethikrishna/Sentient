import asyncio
import logging
import json
import re
import datetime
from dateutil import rrule
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict, Any, Optional

from server.main.config import SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX
from server.workers.utils.api_client import notify_user
from server.celery_app import celery_app
from .planner.llm import get_planner_agent
from .planner.db import PlannerMongoManager, get_all_mcp_descriptions
from ..workers.supermemory_agent_utils import get_supermemory_qwen_agent, get_db_manager as get_memory_db_manager
from .executor.tasks import execute_task_plan

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
            messages = [{'role': 'user', 'content': f"Remember this fact: {fact_text}"}] # Give clear instruction to agent

            # The agent.run is a generator. We must exhaust it to ensure all steps
            # (including tool calls and their results) are completed.
            all_responses = list(agent.run(messages=messages))
            final_history = all_responses[-1] if all_responses else None
            logger.info(f"Supermemory agent final history for user {user_id}: {json.dumps(final_history, indent=2)}")

            if not final_history:
                logger.error(f"Supermemory agent produced no output for user {user_id}.")
                return {"status": "failure", "reason": "Agent produced no output"}

            # Check the final history for a successful function call result.
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
                logger.error(f"Supermemory agent tool call failed or did not return success for user {user_id}. Last Tool Response: {tool_response_content}")
                return {"status": "failure", "reason": "Supermemory tool call did not succeed", "mcp_response": tool_response_content}
        except Exception as e:
            logger.error(f"Critical error in process_memory_item for user {user_id}: {e}", exc_info=True)
            raise # Re-raise to let Celery handle the task failure (retry, etc.)
        finally:
            if 'db_manager' in locals() and db_manager: # Ensure db_manager is defined
                await db_manager.close()

    return run_async(async_process_memory())

# --- Planning Task ---
@celery_app.task(name="process_action_item")
def process_action_item(user_id: str, action_items: list, source_event_id: str, original_context: dict):
    """
    Celery task to process action items and generate a plan.
    """
    logger.info(f"Celery worker received planner task for user {user_id} with {len(action_items)} actions.")
    db_manager = PlannerMongoManager()

    async def async_main():
        # Step 1: Get the static list of all available service descriptions
        available_tools = get_all_mcp_descriptions()
        
        if not available_tools:
            logger.warning(f"No available MCP descriptions found. Aborting task for user {user_id}.")
            return {"status": "aborted", "reason": "No available tools configured."}

        logger.info(f"Planner task for user {user_id} will be prompted with {len(available_tools)} available services.")

        # Step 2: Initialize the planner agent with the list of available services
        agent = get_planner_agent(available_tools)
        
        user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
        messages = [{'role': 'user', 'content': user_prompt_content}]

        final_response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    content = last_message.get("content")
                    if "```json" in content:
                        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                        if match:
                            content = match.group(1)
                    final_response_str = content
        
        if not final_response_str:
            logger.error(f"Planner agent for user {user_id} returned no response.")
            return {"status": "failure", "reason": "Planner agent returned empty response"}
            
        logger.info(f"Planner agent response for user {user_id}: {final_response_str}")

        try:
            plan_data = json.loads(final_response_str)
            description = plan_data.get("description", "Proactively generated plan")
            plan_steps = plan_data.get("plan", [])

            # Step 3: Validate the generated plan against the master service list
            if plan_steps:
                valid_service_names = available_tools.keys()
                for step in plan_steps:
                    tool_used = step.get("tool")
                    if tool_used not in valid_service_names:
                        error_msg = f"Plan for user {user_id} hallucinated an unavailable service: '{tool_used}'. Available services: {list(valid_service_names)}"
                        logger.error(error_msg)
                        return {"status": "failure", "reason": error_msg}

            if not plan_steps:
                logger.warning(f"Planner agent for user {user_id} generated an empty plan.")
                return {"status": "success", "message": "No plan generated."}

            # Step 4: If valid, save the plan as a task for approval
            task_id = await db_manager.save_plan_as_task(user_id, description, plan_steps, original_context, source_event_id)
            logger.info(f"Successfully saved plan as task {task_id} for user {user_id}.")

            notification_message = f"I've created a new plan to '{description}'. It's ready for your approval."
            await notify_user(user_id, notification_message, task_id)

            return {"status": "success", "task_id": task_id}
        except Exception as e:
            logger.error(f"Failed to parse or save plan for user {user_id}: {e}", exc_info=True)
            return {"status": "failure", "reason": str(e)}
        finally:
            await db_manager.close()

    return run_async(async_main())

# --- Scheduler Task ---

def calculate_next_run(schedule: Dict[str, Any], last_run: Optional[datetime.datetime] = None) -> Optional[datetime.datetime]:
    """Calculates the next execution time for a scheduled task."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_time = last_run or now

    try:
        frequency = schedule.get("frequency")
        time_str = schedule.get("time", "00:00")
        hour, minute = map(int, time_str.split(':'))

        # We need the user's timezone to correctly calculate "today" or "next Monday"
        # For simplicity, we'll work in UTC here. A more robust solution would fetch user's timezone.
        # This means "daily at 9am" is 9am UTC.
        dtstart = start_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        rule = None
        if frequency == 'daily':
            rule = rrule.rrule(rrule.DAILY, dtstart=dtstart)
        elif frequency == 'weekly':
            days = schedule.get("days", [])
            if not days: return None
            # Map weekday names to rrule constants
            weekday_map = {"Sunday": rrule.SU, "Monday": rrule.MO, "Tuesday": rrule.TU, "Wednesday": rrule.WE, "Thursday": rrule.TH, "Friday": rrule.FR, "Saturday": rrule.SA}
            byweekday = [weekday_map[day] for day in days if day in weekday_map]
            if not byweekday: return None
            rule = rrule.rrule(rrule.WEEKLY, dtstart=dtstart, byweekday=byweekday)

        if rule:
            next_run = rule.after(start_time)
            # Ensure next_run is timezone-aware
            if next_run and next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=datetime.timezone.utc)
            return next_run

    except Exception as e:
        logger.error(f"Error calculating next run time for schedule {schedule}: {e}")

    return None

@celery_app.task(name="check_scheduled_tasks")
def check_scheduled_tasks():
    """
    Celery Beat task to check for and queue scheduled tasks.
    """
    logger.info("Scheduler: Checking for due tasks...")
    run_async(async_check_scheduled_tasks())

async def async_check_scheduled_tasks():
    db_manager = PlannerMongoManager()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        query = {
            "status": "active",
            "enabled": True,
            "schedule.type": "recurring",
            "next_execution_at": {"$lte": now}
        }
        due_tasks_cursor = db_manager.tasks_collection.find(query)
        due_tasks = await due_tasks_cursor.to_list(length=None)

        if not due_tasks:
            logger.info("Scheduler: No tasks are due.")
            return

        logger.info(f"Scheduler: Found {len(due_tasks)} due tasks.")
        for task in due_tasks:
            logger.info(f"Scheduler: Queuing task {task['task_id']} for execution.")
            execute_task_plan.delay(task['task_id'], task['user_id'])
            
            next_run_time = calculate_next_run(task['schedule'], last_run=now)
            await db_manager.tasks_collection.update_one(
                {"_id": task["_id"]},
                {"$set": {"last_execution_at": now, "next_execution_at": next_run_time}}
            )
            logger.info(f"Scheduler: Rescheduled task {task['task_id']} for {next_run_time}.")
    except Exception as e:
        logger.error(f"Scheduler: An error occurred: {e}", exc_info=True)
    finally:
        await db_manager.close()