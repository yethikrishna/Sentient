import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from . import auth, utils, db
from .llm import (
    get_text_dissection_agent, get_info_extraction_agent,
    get_query_classification_agent, get_text_conversion_agent,
    get_fact_extraction_agent, get_crud_decision_agent
)

# --- Environment and Logging Setup ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MCP Server Initialization ---
# Use a lifespan context manager to handle resource initialization and cleanup
@asynccontextmanager
async def lifespan(app):
    logger.info("Memory MCP starting up...")
    # Initialize and setup Neo4j
    db.get_neo4j_driver()
    db.setup_neo4j_constraints_and_indexes()
    # Initialize embedding model and agents
    utils.initialize_embedding_model()
    utils.initialize_agents()
    logger.info("Memory MCP startup complete.")
    yield
    logger.info("Memory MCP shutting down...")
    db.close_neo4j_driver()
    logger.info("Memory MCP shutdown complete.")

mcp = FastMCP(
    name="MemoryServer",
    instructions="This server provides tools to manage a user's long-term memory using a knowledge graph.",
    lifespan=lifespan
)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        # Pass user_id to the underlying utility function
        result = await func(user_id=user_id, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error executing tool '{func.__name__}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---
@mcp.tool()
async def search_memory(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Searches the user's memory (knowledge graph) to answer a question or find information.
    Use this to recall facts, preferences, relationships, and other details about the user.
    """
    return await _execute_tool(ctx, utils.query_user_profile, query=query)

@mcp.tool()
async def update_memory(ctx: Context, information: str) -> Dict[str, Any]:
    """
    Updates the user's memory with new information. Use this to add or modify facts.
    The information should be a descriptive sentence or paragraph.
    """
    return await _execute_tool(ctx, utils.crud_graph_operations, information=information)

@mcp.tool()
async def add_fact_to_memory(ctx: Context, fact: str) -> Dict[str, Any]:
    """
    Adds a single, simple fact to the user's memory. This is a lightweight version of update_memory.
    The fact should be a complete sentence.
    """
    # This tool is specifically for the Celery worker `process_memory_item`
    return await _execute_tool(ctx, utils.crud_graph_operations, information=fact)

@mcp.tool()
async def build_initial_graph(ctx: Context, documents: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Builds the initial knowledge graph from a list of documents.
    Each document in the list should be a dictionary with 'text' and 'source' keys.
    This will clear any existing graph for the user before building.
    """
    return await _execute_tool(ctx, utils.build_initial_knowledge_graph, extracted_texts=documents)

@mcp.tool()
async def delete_memory_source(ctx: Context, source_name: str) -> Dict[str, Any]:
    """
    Deletes all information (nodes and relationships) from the memory that originated from a specific source.
    The `source_name` should match the 'source' property of the data (e.g., 'linkedin_profile.txt').
    """
    return await _execute_tool(ctx, utils.delete_source_subgraph, file_name=source_name)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 8001))

    print(f"Starting Memory MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)