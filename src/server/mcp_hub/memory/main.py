import os
import logging
import asyncio
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from workers.tasks import cud_memory_task

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
                logger.info("Starting background task: purge expired facts.")
                await utils.purge_expired_facts()
                logger.info("Background task 'purge_expired_facts' completed successfully.")
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
    instructions="Provides tools to manage a user's long-term, structured memory, enabling the agent to learn, recall, and forget information about the user.",
    lifespan=lifespan
)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    tool_name = func.__name__
    # Sanitize large arguments for logging
    log_kwargs = {k: v if not isinstance(v, list) else f"list with {len(v)} items" for k, v in kwargs.items()}
    logger.info(f"Executing tool '{tool_name}' with args: {log_kwargs}")
    try:
        user_id = auth.get_user_id_from_context(ctx)
        result = await func(user_id=user_id, **kwargs)
        logger.info(f"Tool '{tool_name}' executed successfully.")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error executing tool '{func.__name__}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---
@mcp.tool()
async def search_memory(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Performs a semantic search on the user's memory to recall facts, preferences, or other stored information. Use this when you need to answer a question about the user (e.g., 'what is my favorite color?').
    """
    return await _execute_tool(ctx, utils.search_memory, query=query)

@mcp.tool()
async def cud_memory(ctx: Context, information: str, source: str = None) -> Dict[str, Any]:
    """
    Adds, updates, or deletes a single piece of information in the user's memory. The tool automatically determines if the information is new (ADD), a modification (UPDATE), or a removal (DELETE). This is the primary tool for learning from conversation. It is an asynchronous operation.
    """
    user_id = auth.get_user_id_from_context(ctx)
    cud_memory_task.delay(user_id=user_id, information=information, source=source)
    return {"status": "success", "result": "Memory update has been queued for processing."}

@mcp.tool()
async def search_memory_by_source(ctx: Context, query: str, source_name: str) -> Dict[str, Any]:
    """
    Performs a semantic search for facts that originated from a specific `source_name` (e.g., a document name like 'resume.pdf' or an import like 'profile_onboarding').
    """
    return await _execute_tool(ctx, utils.search_memory_by_source, query=query, source_name=source_name)

@mcp.tool()
async def build_initial_memory(ctx: Context, documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Ingests a list of documents to build the user's initial memory, replacing any existing facts. Each document must have 'text' and 'source' keys. This is useful for bulk imports.
    """
    return await _execute_tool(ctx, utils.build_initial_memory, documents=documents)

@mcp.tool()
async def delete_memory_by_source(ctx: Context, source_name: str) -> Dict[str, Any]:
    """
    Deletes all facts from the user's memory that are associated with a specific `source_name`.
    """
    return await _execute_tool(ctx, utils.delete_memory_by_source, source_name=source_name)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 8001))

    print(f"Starting Memory MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)