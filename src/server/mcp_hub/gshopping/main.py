import os
from typing import Dict, Any


from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils



mcp = FastMCP(
    name="GShoppingServer",
    instructions="This server provides a tool to search for products using the Google Shopping Search API.",
)

@mcp.resource("prompt://gshopping-agent-system")
def get_gshopping_system_prompt() -> str:
    return prompts.gshopping_agent_system_prompt

@mcp.prompt(name="gshopping_user_prompt_builder")
def build_gshopping_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gshopping_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

@mcp.tool
async def search_products(ctx: Context, query: str) -> Dict[str, Any]:
    """
    Searches for products online based on a query.
    Returns a list of products with titles, links, prices, and snippets.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        keys = await auth.get_google_api_keys(user_id)
        
        search_results = await utils.perform_shopping_search(
            keys["api_key"], keys["cse_id"], query
        )
        
        if not search_results.get("products"):
            return {"status": "success", "result": f"No products found for '{query}'."}
        
        return {"status": "success", "result": search_results}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9017))
    
    print(f"Starting Google Shopping MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)