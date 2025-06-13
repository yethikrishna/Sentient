import asyncio
import logging
import json
import re

from server.workers.utils.api_client import notify_user
from server.celery_app import celery_app
from server.main.config import INTEGRATIONS_CONFIG
from .memory.llm import get_memory_qwen_agent
from .planner.llm import get_planner_agent
from .planner.db import PlannerMongoManager

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

# --- Memory Processing Task ---
@celery_app.task(name="process_memory_item")
def process_memory_item(user_id: str, fact_text: str):
    """
    Celery task to process a single memory item using the memory agent.
    """
    logger.info(f"Celery worker received memory task for user {user_id}: '{fact_text[:80]}...'")
    agent = get_memory_qwen_agent(user_id)
    messages = [{'role': 'user', 'content': fact_text}]
    
    final_agent_response = None
    try:
        for response_chunk in agent.run(messages=messages):
            final_agent_response = response_chunk
        
        logger.info(f"Memory agent finished for user {user_id}. Response: {final_agent_response}")

        # Improved success check
        if final_agent_response and isinstance(final_agent_response, list):
            tool_call_successful = any(
                msg.get('role') == 'function' and 
                isinstance(json.loads(msg.get('content', '{}')), dict) and
                json.loads(msg.get('content', '{}')).get('status') == 'success'
                for msg in final_agent_response
            )

            if tool_call_successful:
                logger.info(f"Successfully processed and stored memory for user {user_id}.")
                # Optionally log to DB here if needed, but for now, logging to console is enough.
                return {"status": "success", "fact": fact_text}
            else:
                logger.error(f"Memory agent tool call failed or did not report success for user {user_id}. Fact: '{fact_text}'.")
                return {"status": "failure", "fact": fact_text, "reason": "Tool call failed"}
        else:
            logger.error(f"Memory agent did not produce a valid list response for user {user_id}. Fact: '{fact_text}'")
            return {"status": "failure", "fact": fact_text, "reason": "Invalid agent response"}
    except Exception as e:
        logger.error(f"Critical error in process_memory_item for user {user_id}: {e}", exc_info=True)
        # Re-raise to let Celery handle the task failure
        raise

# --- Planning Task ---
@celery_app.task(name="process_action_item")
def process_action_item(user_id: str, action_items: list, source_event_id: str, original_context: dict):
    """
    Celery task to process action items and generate a plan.
    """
    logger.info(f"Celery worker received planner task for user {user_id} with {len(action_items)} actions.")
    db_manager = PlannerMongoManager()

    async def async_main():
        # The agent should know about ALL possible tools to make the best plan.
        all_possible_tools = list(INTEGRATIONS_CONFIG.keys())
        
        if not all_possible_tools:
            logger.warning(f"No tools defined in INTEGRATIONS_CONFIG. Planner cannot create plans.")
            return {"status": "aborted", "reason": "No tools defined in server configuration"}

        logger.info(f"Planner task for user {user_id} prompted with all possible tools: {all_possible_tools}")
        agent = get_planner_agent(all_possible_tools)
        
        user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
        messages = [{'role': 'user', 'content': user_prompt_content}]

        final_response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk: # type: ignore
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    content = last_message.get("content")
                    # Clean up markdown fences that LLMs sometimes add
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

            # --- Plan Validation Step ---
            # Check if the tools generated by the LLM are valid tools that *exist* in our system.
            if plan_steps:
                for step in plan_steps:
                    tool_used = step.get("tool")
                    if tool_used not in all_possible_tools: # Validate against master list
                        error_msg = f"Plan for user {user_id} contains a completely invalid tool: '{tool_used}'. Valid tools are: {all_possible_tools}"
                        logger.error(error_msg)
                        return {"status": "failure", "reason": error_msg}

            if not plan_steps:
                logger.warning(f"Planner agent for user {user_id} generated an empty plan.")
                return {"status": "success", "message": "No plan generated."}

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