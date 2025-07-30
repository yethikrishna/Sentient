import os
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from qwen_agent.agents import Assistant
from json_extractor import JsonExtractor

from . import auth
from main.tasks.prompts import TASK_CREATION_PROMPT # Reusing the main server's prompt
from main.llm import get_qwen_assistant
from main.dependencies import mongo_manager # We can import from main as it's in the python path

logger = logging.getLogger(__name__)

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="TasksServer",
    instructions="This server provides tools to create and manage user tasks.",
)

@mcp.tool()
async def create_task_from_prompt(ctx: Context, prompt: str) -> Dict[str, Any]:
    """
    Creates a new task from a natural language prompt.
    Parses the prompt to determine the description, priority, and schedule,
    then creates a task for the AI to plan and execute.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        user_profile = await mongo_manager.get_user_profile(user_id)
        personal_info = user_profile.get("userData", {}).get("personalInfo", {}) if user_profile else {}
        user_name = personal_info.get("name", "User")
        user_timezone_str = personal_info.get("timezone", "UTC")
        
        try:
            user_timezone = ZoneInfo(user_timezone_str)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")

        current_time_str = datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        system_prompt = TASK_CREATION_PROMPT.format(
            user_name=user_name,
            user_timezone=user_timezone_str,
            current_time=current_time_str
        )
        
        agent = get_qwen_assistant(system_message=system_prompt)
        messages = [{'role': 'user', 'content': prompt}]

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    response_str = last_message["content"]

        if not response_str:
            raise Exception("LLM returned an empty response for task creation.")

        task_data = JsonExtractor.extract_valid_json(response_str)
        if not task_data or "description" not in task_data:
             raise Exception(f"Failed to parse task details from LLM response: {response_str}")

        task_id = await mongo_manager.add_task(user_id, task_data)

        if not task_id:
            raise Exception("Failed to save the task to the database.")
        
        from workers.tasks import refine_and_plan_ai_task
        refine_and_plan_ai_task.delay(task_id)

        return {"status": "success", "result": f"Task '{task_data['description']}' has been created and is being planned."}
    except Exception as e:
        logger.error(f"Error in create_task_from_prompt: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def search_tasks(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Searches for tasks based on a keyword query.
    Returns a list of tasks matching the query.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)

        search_query = {
            "user_id": user_id,
            "$text": {"$search": query}
        }

        projection = {
            "task_id": 1,
            "description": 1,
            "status": 1,
            "created_at": 1,
            "_id": 0
        }

        cursor = mongo_manager.task_collection.find(search_query, projection).sort([("created_at", -1)]).limit(10)
        tasks = await cursor.to_list(length=10)

        for task in tasks:
            if 'created_at' in task and isinstance(task['created_at'], datetime):
                task['created_at'] = task['created_at'].isoformat()

        return {"status": "success", "result": {"tasks": tasks}}
    except Exception as e:
        logger.error(f"Error in search_tasks: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9018))
    
    print(f"Starting Tasks MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)