import asyncio
import logging
import json
import re
from server.main.config import SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX

from server.workers.utils.api_client import notify_user
from server.celery_app import celery_app
from .planner.llm import get_planner_agent
from .planner.db import PlannerMongoManager
from .supermemory_agent_utils import get_supermemory_qwen_agent, get_db_manager as get_memory_db_manager

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
    db_manager = PlannerMongoManager() # This is the correct DB manager for planner

    async def async_main():
        # Step 1: Determine the user's available tools
        available_tools = await db_manager.get_available_tools(user_id)
        
        if not available_tools:
            logger.warning(f"No available tools for user {user_id}. Planner cannot create a plan.")
            return {"status": "aborted", "reason": "No available tools for user."}

        logger.info(f"Planner task for user {user_id} prompted with available tools: {available_tools}")

        # Step 2: Initialize the planner agent with the list of available tools
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

            # Step 3: Validate the generated plan against the user's available tools
            if plan_steps:
                for step in plan_steps:
                    tool_used = step.get("tool")
                    if tool_used not in available_tools:
                        error_msg = f"Plan for user {user_id} hallucinated an unavailable tool: '{tool_used}'. Available tools: {available_tools}"
                        logger.error(error_msg)
                        # Do not save the task, as it's invalid.
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