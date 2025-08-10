import os
import motor.motor_asyncio
import datetime
from typing import Dict, Any


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import configure_logging, get_logger
from . import auth

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
# --- DB Setup ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
tasks_collection = db["tasks"]

# --- MCP Server ---
mcp = FastMCP(
    name="ProgressUpdaterServer",
    instructions="Provides a tool for executor agents to report progress updates on a long-running task."
)

@mcp.tool
async def update_progress(ctx: Context, task_id: str, run_id: str, update_message: Any) -> Dict[str, Any]:
    """
    Sends a progress update for a specific task run. This tool is intended to be called by executor agents to report their status, actions, or results back to the main server and user.
    The `update_message` can be a simple string or a structured dictionary.
    """
    logger.info(f"Executing tool: update_progress for task_id='{task_id}', run_id='{run_id}'")
    try:
        user_id = auth.get_user_id_from_context(ctx)

        # This MCP's job is to forward the update to the main server's WebSocket endpoint.
        # The main server will handle the DB update and the push to the client.
        # This avoids race conditions and keeps DB logic centralized.
        from workers.utils.api_client import push_progress_update
        await push_progress_update(user_id, task_id, run_id, update_message)

        return {"status": "success", "result": "Progress update pushed to main server."}
    except Exception as e:
        logger.error(f"Tool update_progress failed: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9011))
    mcp.run(transport="sse", host=host, port=port)