# src/server/mcp_hub/todoist/main.py
import os
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="TodoistServer",
    instructions="A server for interacting with a Todoist account.",
)

async def _execute_tool(ctx: Context, method_name: str, *args, **kwargs) -> Dict[str, Any]:
    try:
        user_id = auth.get_user_id_from_context(ctx)
        token = await auth.get_todoist_token(user_id)
        client = utils.TodoistApiClient(token=token)
        
        method_to_call = getattr(client, method_name)
        result = await method_to_call(*args, **kwargs)
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def get_projects(ctx: Context) -> Dict:
    """Lists all of a user's projects."""
    return await _execute_tool(ctx, "get_projects")

@mcp.tool
async def get_tasks(ctx: Context, project_id: Optional[str] = None, filter_str: Optional[str] = None) -> Dict:
    """
    Gets a list of active tasks. Can be filtered by project_id or a filter string (e.g., 'today', 'p1 & #Work').
    See Todoist filter documentation for syntax.
    """
    return await _execute_tool(ctx, "get_tasks", project_id, filter_str)

@mcp.tool
async def create_task(ctx: Context, content: str, project_id: Optional[str] = None, due_string: Optional[str] = None) -> Dict:
    """
    Creates a new task.
    'due_string' is a human-readable date/time like 'tomorrow at 4pm' or 'every weekday'.
    """
    return await _execute_tool(ctx, "create_task", content, project_id, due_string)

@mcp.tool
async def close_task(ctx: Context, task_id: str) -> Dict:
    """Marks a task as complete."""
    return await _execute_tool(ctx, "close_task", task_id)

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9021))
    
    print(f"Starting Todoist MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)