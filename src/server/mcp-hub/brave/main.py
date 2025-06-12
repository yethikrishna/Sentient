# server/mcp-hub/brave/main.py

import os
from typing import Dict, Any
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

# Local imports
from . import auth
from . import prompts
from . import utils

load_dotenv()

# --- Server Initialization ---
mcp = FastMCP(
    name="BraveSearchServer",
    instructions="This server provides a tool to search the web using the Brave Search API.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://brave-agent-system")
def get_brave_system_prompt() -> str:
    return prompts.brave_agent_system_prompt

@mcp.prompt(name="brave_user_prompt_builder")
def build_brave_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.brave_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Definition ---

@mcp.tool
async def web_search(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Searches the web for information on a given query using the Brave Search API.
    """
    try:
        # User ID is maintained for consistency but not used for Brave API key
        auth.get_user_id_from_context(ctx) 
        api_key = auth.get_brave_api_key()
        
        search_results = await utils.perform_brave_search(api_key, query)
        
        if not search_results.get("search_results") and not search_results.get("faq"):
            return {"status": "success", "result": f"No results found for '{query}'."}
        
        return {"status": "success", "result": search_results}
    except Exception as e:
        return {"status": "failure", "error": str(e)}


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9004))
    
    print(f"Starting Brave Search MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)