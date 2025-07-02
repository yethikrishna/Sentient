import os
from typing import Dict, Any, Optional


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
if ENVIRONMENT == 'dev':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
mcp = FastMCP(
    name="NewsServer",
    instructions="A server for fetching news articles from NewsAPI.org.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://news-agent-system")
def get_news_system_prompt() -> str:
    return prompts.news_agent_system_prompt

@mcp.prompt(name="news_user_prompt_builder")
def build_news_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.news_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        # Auth check for consistency, even if key is not user-specific
        auth.get_user_id_from_context(ctx)
        api_key = auth.get_news_api_key()
        result = await func(api_key=api_key, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---
@mcp.tool
async def get_top_headlines(ctx: Context, query: Optional[str] = None, category: Optional[str] = None, country: str = 'us') -> Dict:
    """
    Fetches top headlines. Can be filtered by a query, category, or country.
    Valid categories: business, entertainment, general, health, science, sports, technology.
    """
    return await _execute_tool(ctx, utils.fetch_top_headlines, query=query, category=category, country=country)

@mcp.tool
async def search_everything(ctx: Context, query: str, language: str = 'en', sort_by: str = 'relevancy') -> Dict:
    """
    Searches for articles across all sources for a specific query.
    `sort_by` can be 'relevancy', 'popularity', or 'publishedAt'.
    """
    return await _execute_tool(ctx, utils.search_everything, query=query, language=language, sort_by=sort_by)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9012))
    
    print(f"Starting News MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)