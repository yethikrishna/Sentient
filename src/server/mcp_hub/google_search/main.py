import os
from typing import Dict, Any


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

# Local imports
from . import auth
from . import prompts
from . import utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

# --- Server Initialization ---
mcp = FastMCP(
    name="GoogleSearchServer",
    instructions="Provides a tool to perform a web search using the Google Custom Search API, enabling access to real-time information.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://google-search-agent-system")
def get_google_search_system_prompt() -> str:
    return prompts.google_search_agent_system_prompt

@mcp.prompt(name="google_search_user_prompt_builder")
def build_google_search_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.google_search_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Definition ---

@mcp.tool
async def google_search(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Performs a web search for a given `query` using the Google Custom Search API. Returns a list of search results including titles, links, and snippets.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        keys = await auth.get_google_api_keys(user_id)
        
        search_results = await utils.perform_google_search(
            keys["api_key"], keys["cse_id"], query
        )
        
        if not search_results.get("search_results"):
            return {"status": "success", "result": f"No results found for '{query}'."}
        
        return {"status": "success", "result": search_results}
    except Exception as e:
        return {"status": "failure", "error": str(e)}


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9005))
    
    print(f"Starting Google Search MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)