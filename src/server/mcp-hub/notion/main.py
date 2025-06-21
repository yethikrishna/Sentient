import os
import json
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message
from notion_client.helpers import is_full_page_or_database

from . import auth, prompts, utils
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="NotionServer",
    instructions="This server provides tools to interact with the Notion API.",
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
async def _execute_tool(ctx: Context, func, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_notion_creds(user_id)
        notion = auth.authenticate_notion(creds)
        
        result = await func(notion, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Implementations ---
async def _search(notion, query: str):
    response = await notion.search(query=query)
    # The Notion search response is complex, we need to simplify it for the LLM.
    simplified_results = []
    for item in response.get("results", []):
        if is_full_page_or_database(item):
            obj_type = item.get("object")
            title_text = "Untitled"
            if obj_type == "page" and item.get("properties"):
                # Find the title property
                for prop_name, prop_value in item["properties"].items():
                    if prop_value.get("type") == "title":
                        title_text = utils._simplify_rich_text(prop_value["title"])
                        break
            elif obj_type == "database" and item.get("title"):
                 title_text = utils._simplify_rich_text(item["title"])
            
            simplified_results.append({
                "id": item.get("id"),
                "type": obj_type,
                "title": title_text,
                "last_edited": item.get("last_edited_time"),
            })
    return {"search_results": simplified_results}

async def _get_page_content(notion, page_id: str):
    response = await notion.blocks.children.list(block_id=page_id)
    content = utils.simplify_block_children(response)
    return {"page_id": page_id, "content": content}

async def _create_page(notion, parent_page_id: Optional[str] = None, parent_database_id: Optional[str] = None, title: str = "Untitled", content: Optional[List[Dict]] = None):
    if not parent_page_id and not parent_database_id:
        raise ValueError("Either parent_page_id or parent_database_id must be provided.")

    parent_key = "page_id" if parent_page_id else "database_id"
    parent_value = parent_page_id or parent_database_id
    parent = {parent_key: parent_value}

    # Default properties for database pages
    properties = {"title": {"title": [{"text": {"content": title}}]}}
    if parent_database_id:
        # This is a simplified property structure. The LLM would need to know the target DB's schema
        # for more complex properties. For now, we only set the title.
        pass

    children_blocks = content or [] # content should be Notion block objects
    
    response = await notion.pages.create(parent=parent, properties=properties, children=children_blocks)
    return {"page_id": response.get("id"), "url": response.get("url")}

async def _query_database(notion, database_id: str, filter_json: Optional[str] = None):
    filter_obj = json.loads(filter_json) if filter_json else None
    response = await notion.databases.query(database_id=database_id, filter=filter_obj)
    simplified_pages = utils.simplify_database_pages(response)
    return {"pages": simplified_pages}

async def _append_to_page(notion, page_id: str, content_blocks: List[Dict]):
    """Appends content blocks to a page."""
    response = await notion.blocks.children.append(block_id=page_id, children=content_blocks)
    return {"status": "ok", "appended_block_count": len(response.get("results", []))}


# --- Tool Definitions ---
@mcp.tool
async def search_notion(ctx: Context, query: str) -> Dict:
    """Searches for pages and databases in Notion matching a query."""
    return await _execute_tool(ctx, _search, query=query)

@mcp.tool
async def get_notion_page_content(ctx: Context, page_id: str) -> Dict:
    """Retrieves the content (blocks) of a specific Notion page by its ID."""
    return await _execute_tool(ctx, _get_page_content, page_id=page_id)

@mcp.tool
async def create_notion_page(ctx: Context, title: str, parent_page_id: Optional[str] = None, parent_database_id: Optional[str] = None, content_blocks_json: Optional[str] = None) -> Dict:
    """
    Creates a new page in Notion, either inside another page or in a database.
    `content_blocks_json` should be a JSON string representing a list of Notion block objects.
    Example: '[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello World"}}]}}]'
    """
    content_blocks = json.loads(content_blocks_json) if content_blocks_json else []
    return await _execute_tool(ctx, _create_page, title=title, parent_page_id=parent_page_id, parent_database_id=parent_database_id, content=content_blocks)

@mcp.tool
async def append_to_notion_page(ctx: Context, page_id: str, content_blocks_json: str) -> Dict:
    """
    Appends new content blocks to an existing Notion page.
    `content_blocks_json` MUST be a JSON string of a list of Notion block objects.
    Example: '[{"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "New Section"}}]}}]'
    """
    content_blocks = json.loads(content_blocks_json)
    return await _execute_tool(ctx, _append_to_page, page_id=page_id, content_blocks=content_blocks)


@mcp.tool
async def query_notion_database(ctx: Context, database_id: str, filter_json: Optional[str] = None) -> Dict:
    """
    Queries a Notion database with an optional filter.
    `filter_json` should be a JSON string representing a valid Notion API filter object.
    Example for filtering by a 'Status' property: '{"property": "Status", "select": {"equals": "Done"}}'
    """
    return await _execute_tool(ctx, _query_database, database_id=database_id, filter_json=filter_json)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9009))
    
    print(f"Starting Notion MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)