import os
import asyncio
import json
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.prompt import Message
from notion_client.helpers import is_full_page_or_database

from . import auth, prompts, utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
mcp = FastMCP(
    name="NotionServer",
    instructions="Provides a comprehensive set of tools to interact with the Notion API, allowing for the creation and management of pages, databases, and blocks.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://notion-agent-system")
def get_notion_system_prompt() -> str:
    return prompts.notion_agent_system_prompt

@mcp.prompt(name="notion_user_prompt_builder")
def build_notion_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.notion_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Helper ---
async def _execute_tool(ctx: Context, async_func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_notion_creds(user_id)
        notion_client = auth.authenticate_notion(creds)
        
        # The function is async, so we await it directly
        result = await async_func(notion_client, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Synchronous Implementations for Tools ---

async def _create_page_async(client, parent_page_id: Optional[str], title: str, content: Optional[List[Dict]]):
    if not parent_page_id:
        raise ToolError("parent_page_id must be provided.")
    parent = {"page_id": parent_page_id}
    properties = {"title": {"title": [{"text": {"content": title}}]}}
    children_blocks = content or []
    response = await client.pages.create(parent=parent, properties=properties, children=children_blocks)
    return {"page_id": response.get("id"), "url": response.get("url")}

async def _search_pages_async(client, query: str):
    response = await client.search(query=query, filter={"value": "page", "property": "object"})
    return utils.simplify_search_results(response)

async def _read_page_content_async(client, page_id: str):
    response = await client.blocks.children.list(block_id=page_id)
    return utils.simplify_block_children(response)

async def _query_database_async(client, database_id: str, filter_json: Optional[str]):
    filter_obj = json.loads(filter_json) if filter_json else None
    response = await client.databases.query(database_id=database_id, filter=filter_obj)
    return utils.simplify_database_pages(response)

async def _update_block_async(client, block_id: str, content: Dict):
    response = await client.blocks.update(block_id=block_id, **content)
    return {"block_id": response.get("id"), "last_edited_time": response.get("last_edited_time")}

async def _get_block_children_async(client, block_id: str):
    response = await client.blocks.children.list(block_id=block_id)
    return utils.simplify_block_children(response)

async def _get_comments_async(client, block_id: str):
    response = await client.comments.list(block_id=block_id) # type: ignore
    return [utils._simplify_comment(c) for c in response.get("results", [])] # type: ignore

async def _get_workspace_async(client):
    response = await client.users.me()
    return response.get("bot", {}).get("owner", {})

async def _update_page_async(client, page_id: str, properties_json: str):
    properties = json.loads(properties_json)
    response = await client.pages.update(page_id=page_id, properties=properties)
    return {"page_id": response.get("id"), "url": response.get("url")}

async def _get_databases_async(client, query: Optional[str]):
    response = await client.search(query=query, filter={"value": "database", "property": "object"})
    # This function was incorrectly trying to parse database objects as page objects.
    # This is the corrected, simplified implementation.
    simplified_dbs = []
    for db in response.get("results", []):
        title_list = db.get("title", [])
        title = utils._simplify_rich_text(title_list) if title_list else "Untitled Database"
        simplified_dbs.append({
            "database_id": db.get("id"),
            "title": title
        })
    return simplified_dbs

async def _create_block_async(client, parent_block_id: str, content_blocks: List[Dict]):
    response = await client.blocks.children.append(block_id=parent_block_id, children=content_blocks)
    return {"status": "ok", "appended_block_count": len(response.get("results", []))}

async def _delete_block_async(client, block_id: str):
    response = await client.blocks.delete(block_id=block_id)
    return {"block_id": response.get("id"), "archived": response.get("archived")}

async def _create_comment_async(client, page_id: str, comment_text: str):
    comment_obj = {"rich_text": [{"text": {"content": comment_text}}]}
    response = await client.comments.create(parent={"page_id": page_id}, rich_text=comment_obj['rich_text'])
    return utils._simplify_comment(response)

async def _list_users_async(client):
    response = await client.users.list()
    return [utils._simplify_user(u) for u in response.get("results", [])]


# --- Tool Definitions ---
@mcp.tool
async def createPage(ctx: Context, title: str, parent_page_id: str, content_blocks_json: Optional[str] = None) -> Dict:
    """
    Creates a new page in Notion. Requires a `title` and a parent (`parent_page_id`). If parent page ID is not provided, ask the user to provide the title of the parent page, then use the `search_pages` tool to find its ID.
    Optionally, you can add body content by providing a `content_blocks_json` string, which is a list of Notion block objects.
    """
    try:
        content_blocks = json.loads(content_blocks_json) if content_blocks_json else []
    except (json.JSONDecodeError, TypeError):
        raise ToolError("Invalid `content_blocks_json`. It must be a valid JSON string representing a list of block objects.")
    return await _execute_tool(ctx, _create_page_async, parent_page_id=parent_page_id, title=title, content=content_blocks)

@mcp.tool
async def search_pages(ctx: Context, query: str) -> Dict:
    """
    Searches for pages across the Notion workspace using a text `query`.
    Returns a list of pages with their ID, title, and URL. This does NOT return page content.
    """
    return await _execute_tool(ctx, _search_pages_async, query=query)

@mcp.tool
async def read_page_content(ctx: Context, page_id: str) -> Dict:
    """
    Retrieves the full content of a specific page, formatted as markdown-like text.
    Requires the `page_id`, which can be found using the `search_pages` tool.
    """
    return await _execute_tool(ctx, _read_page_content_async, page_id=page_id)

@mcp.tool
async def queryDatabase(ctx: Context, database_id: str, filter_json: Optional[str] = None) -> Dict:
    """
    Retrieves pages from a specific database. Requires the `database_id` and can be filtered using a Notion API `filter_json` string.
    """
    return await _execute_tool(ctx, _query_database_async, database_id=database_id, filter_json=filter_json)

@mcp.tool
async def updateBlock(ctx: Context, block_id: str, content_json: str) -> Dict:
    """
    Updates the content of an existing block. Requires the `block_id` and a `content_json` string representing the new block content (e.g., '{"paragraph":...}').
    """
    content = json.loads(content_json)
    return await _execute_tool(ctx, _update_block_async, block_id=block_id, content=content)

@mcp.tool
async def getBlockChildren(ctx: Context, block_id: str) -> Dict:
    """
    Retrieves all the content blocks nested inside a parent block (such as a page, toggle, or column).
    """
    return await _execute_tool(ctx, _get_block_children_async, block_id=block_id)

@mcp.tool
async def getComments(ctx: Context, block_id: str) -> Dict:
    """Get comments for a page or block."""
    return await _execute_tool(ctx, _get_comments_async, block_id=block_id)

@mcp.tool
async def getWorkspace(ctx: Context) -> Dict:
    """Get information about the current Notion workspace (organization)."""
    return await _execute_tool(ctx, _get_workspace_async)

@mcp.tool
async def updatePage(ctx: Context, page_id: str, properties_json: str) -> Dict:
    """Update an existing Notion page by modifying its properties."""
    return await _execute_tool(ctx, _update_page_async, page_id=page_id, properties_json=properties_json)

@mcp.tool
async def getDatabases(ctx: Context, query: Optional[str] = None) -> Dict:
    """List available Notion databases that the integration has access to, with an optional query."""
    return await _execute_tool(ctx, _get_databases_async, query=query)

@mcp.tool
async def createBlock(ctx: Context, parent_block_id: str, content_blocks_json: str) -> Dict:
    """Add content blocks to an existing page or block."""
    content_blocks = json.loads(content_blocks_json)
    return await _execute_tool(ctx, _create_block_async, parent_block_id=parent_block_id, content_blocks=content_blocks)

@mcp.tool
async def deleteBlock(ctx: Context, block_id: str) -> Dict:
    """Delete a content block."""
    return await _execute_tool(ctx, _delete_block_async, block_id=block_id)

@mcp.tool
async def createComment(ctx: Context, page_id: str, comment_text: str) -> Dict:
    """Add a comment to a page or block."""
    return await _execute_tool(ctx, _create_comment_async, page_id=page_id, comment_text=comment_text)

@mcp.tool
async def listUsers(ctx: Context) -> Dict:
    """List all users who have access to the workspace."""
    return await _execute_tool(ctx, _list_users_async)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9009))
    
    print(f"Starting Notion MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)