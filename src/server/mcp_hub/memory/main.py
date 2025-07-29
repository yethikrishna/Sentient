import os
import logging
import asyncio
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP, Context

from . import auth, utils, db

# --- Environment and Logging Setup ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MCP Server Initialization ---
@asynccontextmanager
async def lifespan(app):
    logger.info("Memory MCP starting up...")
    # Initialize and setup PostgreSQL
    await db.get_db_pool()
    await db.setup_database()
    # Initialize embedding model and agents
    utils.initialize_embedding_model()
    utils.initialize_agents()

    # Start the background task to purge expired facts
    async def purge_loop():
        while True:
            await asyncio.sleep(3600) # Sleep for 1 hour
            try:
                await utils.purge_expired_facts()
            except Exception as e:
                logger.error(f"Error in background memory purge task: {e}", exc_info=True)

    purge_task = asyncio.create_task(purge_loop())

    logger.info("Memory MCP startup complete.")
    yield
    logger.info("Memory MCP shutting down...")
    purge_task.cancel() # Cleanly stop the background task
    await db.close_db_pool()
    logger.info("Memory MCP shutdown complete.")

mcp = FastMCP(
    name="MemoryServer",
    instructions="This server provides tools to manage a user's long-term memory using a PostgreSQL database.",
    lifespan=lifespan
)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        result = await func(user_id=user_id, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error executing tool '{func.__name__}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---
@mcp.tool()
async def search_memory(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Searches the user's memory to answer a question or find information.
    Use this to recall facts, preferences, relationships, and other details about the user.
    """
    return await _execute_tool(ctx, utils.search_memory, query=query)

@mcp.tool()
async def cud_memory(ctx: Context, information: str, source: str = None) -> Dict[str, Any]:
    """
    Adds, updates, or deletes a fact in the user's memory based on the provided information.
    The system will determine if the information is new, an update, or a deletion.
    Use the optional 'source' parameter to track where the information came from (e.g., 'user_chat', 'document.txt').
    """
    return await _execute_tool(ctx, utils.cud_memory, information=information, source=source)

@mcp.tool()
async def search_memory_by_source(ctx: Context, query: str, source_name: str) -> Dict[str, Any]:
    """
    Searches for information within a specific source in the user's memory.
    Use this to recall facts related to a particular document, import, or conversation, by providing the `source_name`.
    """
    return await _execute_tool(ctx, utils.search_memory_by_source, query=query, source_name=source_name)

@mcp.tool()
async def build_initial_memory(ctx: Context, documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Builds the user's memory from a list of documents, replacing any existing memory.
    Each document in the list should be a dictionary with 'text' and 'source' keys.
    """
    return await _execute_tool(ctx, utils.build_initial_memory, documents=documents)

@mcp.tool()
async def delete_memory_by_source(ctx: Context, source_name: str) -> Dict[str, Any]:
    """
    Deletes all facts from the memory that originated from a specific source.
    The `source_name` should match the 'source' property of the data (e.g., 'profile_import.txt').
    """
    return await _execute_tool(ctx, utils.delete_memory_by_source, source_name=source_name)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 8001))

    print(f"Starting Memory MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)