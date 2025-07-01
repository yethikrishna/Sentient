import os
import uuid
import json
from typing import Dict, Any

from celery import Celery

from fastmcp import FastMCP, Context
from . import auth, config, db



mcp = FastMCP(
    name="ChatToolsServer",
    instructions="A server providing tools for the main chat agent to hand off tasks and query task status."
)

task_db_manager = db.TaskDBManager() # This is fine to instantiate globally as it's used within async functions

celery_app = Celery(
    'chat_tools_client',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

@mcp.tool
async def create_task_from_description(ctx: Context, task_description: str) -> Dict[str, Any]:
    """
    Hands off a task to the proactive planning and execution pipeline.
    Use this when the user asks for an action to be performed that isn't a simple memory update.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        
        # These are the arguments required by the `process_action_item` Celery task
        source_event_id = f"chat_handoff_{uuid.uuid4()}"
        original_context = {
                "source": "chat",
                "description": task_description,
            }
        task_args = (user_id, [task_description], source_event_id, original_context)
        
        # Send the task directly to the Celery queue (Redis)
        # The task name 'process_action_item' is defined in `src/server/workers/tasks.py`
        celery_app.send_task('process_action_item', args=task_args)
        
        return {"status": "success", "result": "Task has been handed off for planning. The user can check the Tasks page for progress."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def get_task_status(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Checks the status of a previously created task by searching for its description.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        task = await task_db_manager.find_task(user_id, query)
        if not task:
            return {"status": "success", "result": "No task found matching that description."}
        return {"status": "success", "result": task}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9013))
    
    print(f"Starting Chat Tools MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)