import os
import asyncio
from typing import Dict, Any, Optional, List
import json

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from json_extractor import JsonExtractor
from celery import chord, group

from . import auth, prompts
from main.dependencies import mongo_manager
from main.llm import run_agent_with_fallback
from main.config import INTEGRATIONS_CONFIG
from main.tasks.utils import clean_llm_output
from workers.tasks import refine_and_plan_ai_task
from workers.executor.tasks import run_single_item_worker, aggregate_results_callback

from fastmcp.utilities.logging import configure_logging, get_logger

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="TasksServer",
    instructions="Provides tools for creating and searching user tasks that can be planned and executed by AI agents.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://tasks-agent-system")
def get_tasks_system_prompt() -> str:
    return prompts.tasks_agent_system_prompt

@mcp.prompt(name="tasks_user_prompt_builder")
def build_tasks_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> str:
    return prompts.tasks_agent_user_prompt.format(query=query, username=username, previous_tool_response=previous_tool_response)

@mcp.tool()
async def create_task_from_prompt(ctx: Context, prompt: str) -> Dict[str, Any]:
    """
    Creates a new task from a natural language `prompt`.
    An internal AI analyzes the prompt to extract the task description, priority, and schedule, then creates the task and queues it for planning and execution.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)

        # Create a placeholder task with the raw prompt
        task_data = {
            "name": prompt,
            "description": prompt, # The refiner will use this to generate a better name and description
            "priority": 1,  # Default priority
            "schedule": None,
            "assignee": "ai"
        }

        task_id = await mongo_manager.add_task(user_id, task_data)

        if not task_id:
            raise Exception("Failed to save the task to the database.")
        
        # Asynchronously trigger the refinement and planning process
        refine_and_plan_ai_task.delay(task_id, user_id)

        # Truncate prompt for a cleaner success message
        short_prompt = prompt[:50] + '...' if len(prompt) > 50 else prompt
        return {"status": "success", "result": f"Task '{short_prompt}' has been created and is being planned."}
    except Exception as e:
        logger.error(f"Error in create_task_from_prompt: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def search_tasks(
    ctx: Context, 
    query: Optional[str] = None,
    status_list: Optional[List[str]] = None,
    priority_list: Optional[List[int]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs an advanced search for tasks using various filters like a text `query`, `status_list` (e.g., 'pending', 'active'), `priority_list` (0=High, 1=Medium, 2=Low), or a date range.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)

        # Build the MongoDB query dynamically
        mongo_query: Dict[str, Any] = {"user_id": user_id}
        
        if query:
            mongo_query["$text"] = {"$search": query}
        if status_list:
            mongo_query["status"] = {"$in": status_list}
        if priority_list:
            mongo_query["priority"] = {"$in": priority_list}
        
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        if date_filter:
            # We search against `next_execution_at` for scheduled tasks and `created_at` for others as a fallback
            mongo_query["$or"] = [
                {"next_execution_at": date_filter},
                {"created_at": date_filter, "next_execution_at": None}
            ]

        cursor = mongo_manager.task_collection.find(mongo_query).sort([("priority", 1), ("created_at", -1)]).limit(20)
        tasks = await cursor.to_list(length=20)

        return {"status": "success", "result": {"tasks": tasks}}
    except Exception as e:
        logger.error(f"Error in search_tasks: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def process_collection_in_parallel(ctx: Context, items: List[Any], goal: str) -> Dict[str, Any]:
    """
    Orchestrates parallel processing of a collection of items based on a high-level goal.
    A resource manager agent analyzes the goal and items, then defines one or more sub-tasks. Each sub-task can have a different prompt and a different set of tools, which are then executed in parallel by worker agents.
    This is a blocking operation that waits for all sub-agents to complete.
    The aggregated results from all workers are returned as a list.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        
        if not isinstance(items, list):
            raise ToolError("The 'items' parameter must be a list.")
        
        if not items:
            return {"status": "success", "result": "The collection is empty, nothing to process."}

        # --- 1. Resource Manager Agent ---
        logger.info(f"Invoking Resource Manager for user {user_id} with goal: {goal}")
        
        user_profile = await mongo_manager.get_user_profile(user_id)
        user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}
        
        available_tools = {}
        for tool_name, config in INTEGRATIONS_CONFIG.items():
            if tool_name in ["tasks", "progress_updater"]: continue
            is_builtin = config.get("auth_type") == "builtin"
            is_connected = user_integrations.get(tool_name, {}).get("connected", False)
            if is_builtin or is_connected:
                available_tools[tool_name] = config.get("description", "")
        
        system_prompt = prompts.RESOURCE_MANAGER_SYSTEM_PROMPT.format(
            available_tools_json=json.dumps(list(available_tools.keys()))
        )
        
        items_sample = items[:5]
        user_prompt = f"Goal: \"{goal}\"\n\nItems (sample of {len(items)} total):\n{json.dumps(items_sample, indent=2, default=str)}"
        
        messages = [{'role': 'user', 'content': user_prompt}]
        
        manager_response_str = ""
        for chunk in run_agent_with_fallback(system_message=system_prompt, function_list=[], messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    manager_response_str = last_message["content"]

        manager_response_str = clean_llm_output(manager_response_str).strip()

        if not manager_response_str:
            raise ToolError("Resource Manager agent returned an empty response.")
        
        execution_plan = JsonExtractor.extract_valid_json(manager_response_str)
        
        if not isinstance(execution_plan, list) or not all(isinstance(item, dict) for item in execution_plan):
            raise ToolError(f"Resource Manager returned an invalid plan. Response: {manager_response_str}")

        logger.info(f"Resource Manager created execution plan with {len(execution_plan)} sub-task(s).")

        # --- 2. Dispatch Worker Tasks ---
        all_worker_groups = []
        for config in execution_plan:
            item_indices = config.get("item_indices", [])
            worker_prompt = config.get("worker_prompt")
            required_tools = config.get("required_tools", [])
            
            if not all([isinstance(item_indices, list), worker_prompt, isinstance(required_tools, list)]):
                logger.warning(f"Skipping invalid worker configuration: {config}")
                continue

            task_group = group(run_single_item_worker.s(user_id=user_id, item=items[i], worker_prompt=worker_prompt, worker_tools=required_tools) for i in item_indices if i < len(items))
            if task_group:
                all_worker_groups.append(task_group)

        if not all_worker_groups:
            raise ToolError("The execution plan resulted in no valid tasks to run.")
        
        header = group(all_worker_groups)
        callback = aggregate_results_callback.s()
        chord_task = chord(header, callback)
        
        logger.info(f"Dispatching a chord of {sum(len(g.tasks) for g in all_worker_groups)} parallel workers for user {user_id}.")
        
        loop = asyncio.get_running_loop()
        result_async = chord_task.apply_async()
        result = await loop.run_in_executor(
            None,
            lambda: result_async.get(timeout=1800)
        )

        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error in process_collection_in_parallel: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9018))
    
    print(f"Starting Tasks MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)