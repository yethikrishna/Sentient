# Create new file: src/server/mcp_hub/history/main.py
# src/server/mcp_hub/history/main.py
import os
import asyncio
import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

from . import auth, prompts
from main.vector_db import get_conversation_summaries_collection
from main.db import MongoManager

# --- Environment and Server Initialization ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="ChatHistoryServer",
    instructions="Provides tools to search the user's long-term conversation history, using either semantic search for topics or time-based search for specific periods.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://history-agent-system")
def get_history_system_prompt() -> str:
    return prompts.history_agent_system_prompt

@mcp.prompt(name="history_user_prompt_builder")
def build_history_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> str:
    return prompts.history_agent_user_prompt.format(query=query, username=username, previous_tool_response=previous_tool_response)


# --- Tool Definitions ---

@mcp.tool()
async def semantic_search(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Performs a semantic (meaning-based) search of the user's long-term conversation summaries.
    Use this to find information about topics, concepts, or past decisions when the exact time is unknown (e.g., 'what did we decide about the marketing plan?').
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        collection = get_conversation_summaries_collection()
        
        results = await asyncio.to_thread(
            lambda: collection.query(
                query_texts=[query],
                n_results=5,
                where={"user_id": user_id}
            )
        )
        
        # Extract and format the documents (summaries)
        documents = results.get('documents', [[]])[0]
        if not documents:
            return {"status": "success", "result": "No relevant conversation summaries found in your memory."}
            
        return {"status": "success", "result": {"summaries": documents}}
    except Exception as e:
        return {"status": "failure", "error": f"An unexpected error occurred during semantic search: {str(e)}"}

@mcp.tool()
async def time_based_search(ctx: Context, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Retrieves a log of all messages within a specific date range. Use this when the user asks about a conversation on a specific day or period (e.g., 'what did we talk about yesterday afternoon?').
    Dates must be in ISO 8601 format (e.g., '2024-07-29T00:00:00Z').
    """
    db_manager = None
    try:
        user_id = auth.get_user_id_from_context(ctx)
        
        try:
            start_dt = datetime.datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise ToolError("Invalid date format. Please use ISO 8601 format.")

        db_manager = MongoManager()
        query = {
            "user_id": user_id,
            "timestamp": {"$gte": start_dt, "$lte": end_dt}
        }
        
        cursor = db_manager.messages_collection.find(query).sort("timestamp", 1)
        messages = await cursor.to_list(length=200) # Limit to 200 messages for a single time-based search
        
        if not messages:
            return {"status": "success", "result": "No messages found in that time period."}
            
        # Format for readability
        conversation_log = "\n".join([f"[{msg['timestamp'].strftime('%Y-%m-%d %H:%M')}] {msg['role']}: {msg['content']}" for msg in messages])
        
        return {"status": "success", "result": {"conversation": conversation_log}}
    except Exception as e:
        return {"status": "failure", "error": f"An unexpected error occurred during time-based search: {str(e)}"}
    finally:
        if db_manager:
            await db_manager.close()


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9020))
    
    print(f"Starting Chat History MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)