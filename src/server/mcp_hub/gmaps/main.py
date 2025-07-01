import os
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()  # Load from default .env if not found

mcp = FastMCP(
    name="GMapsServer",
    instructions="This server provides tools to get information from Google Maps, such as searching for places and getting directions.",
)

@mcp.resource("prompt://gmaps-agent-system")
def get_gmaps_system_prompt() -> str:
    return prompts.gmaps_agent_system_prompt

@mcp.prompt(name="gmaps_user_prompt_builder")
def build_gmaps_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gmaps_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        api_key = await auth.get_google_api_key(user_id)
        
        # Pass api_key to the utility function
        result = await func(api_key=api_key, **kwargs)
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def search_places(ctx: Context, query: str) -> Dict:
    """
    Searches for places like restaurants, landmarks, or addresses.
    Returns a list of matching places with their names, addresses, and IDs.
    """
    return await _execute_tool(ctx, utils.search_places_util, query=query)

@mcp.tool
async def get_directions(ctx: Context, origin: str, destination: str, mode: Optional[str] = "DRIVING") -> Dict:
    """
    Gets directions between an origin and a destination.
    The 'mode' can be 'DRIVING', 'WALKING', 'BICYCLING', or 'TRANSIT'.
    """
    return await _execute_tool(ctx, utils.get_directions_util, origin=origin, destination=destination, mode=mode)

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9016))
    
    print(f"Starting Google Maps MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)