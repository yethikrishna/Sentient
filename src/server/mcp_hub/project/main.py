# src/server/mcp_hub/project/main.py
import os
import asyncio
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import motor.motor_asyncio

from . import auth

# --- Environment & DB Setup ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
projects_collection = db["projects"]
project_members_collection = db["project_members"]
project_context_items_collection = db["project_context_items"]

# --- Server Initialization ---
mcp = FastMCP(
    name="ProjectServer",
    instructions="This server provides tools to interact with shared project context.",
)

# --- Tool Helper ---
async def _check_project_membership(user_id: str, project_id: str):
    """Verifies if a user is a member of the project."""
    count = await project_members_collection.count_documents(
        {"project_id": project_id, "user_id": user_id}
    )
    if count == 0:
        raise ToolError("Access denied: You are not a member of this project.")

# --- Tool Definitions ---
@mcp.tool
async def list_context_items(ctx: Context, project_id: str) -> Dict[str, Any]:
    """Lists all shared context items (text snippets, files) for a given project."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        await _check_project_membership(user_id, project_id)

        cursor = project_context_items_collection.find(
            {"project_id": project_id},
            {"_id": 0, "content": 0} # Exclude content for list view
        ).sort("created_at", 1)
        
        items = await cursor.to_list(length=None)
        return {"status": "success", "result": {"context_items": items}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def read_text_context_item(ctx: Context, item_id: str) -> Dict[str, Any]:
    """Reads the full content of a specific text-based context item by its ID."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        
        item = await project_context_items_collection.find_one(
            {"item_id": item_id, "type": "text"},
            {"_id": 0}
        )
        if not item:
            raise ToolError("Text context item not found.")

        await _check_project_membership(user_id, item["project_id"])
        
        return {"status": "success", "result": item}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9020))
    
    print(f"Starting Project MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)