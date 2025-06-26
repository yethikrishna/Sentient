import os
import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from . import auth, utils

# Inherit from the main server .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="JournalServer",
    instructions="This server provides tools to read from and write to the user's daily journal."
)

db_manager = utils.JournalDBManager()

@mcp.tool
async def add_journal_entry(ctx: Context, content: str, date: Optional[str] = None) -> Dict[str, Any]:
    """Adds a new text block to the user's journal for a specific date. If no date is provided, today's date is used."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        date_str = date or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        # Simple order logic: just append to the end.
        last_block = await db_manager.blocks_collection.find_one(
            {"user_id": user_id, "page_date": date_str},
            sort=[("order", -1)]
        )
        new_order = (last_block["order"] + 1) if last_block else 0
        
        new_block = await db_manager.add_block(user_id, content, date_str, new_order)
        return {"status": "success", "result": f"New journal block added with ID: {new_block['block_id']}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def add_progress_update_to_block(ctx: Context, block_id: str, update_message: str) -> Dict[str, Any]:
    """Appends a progress update to a specific journal block, typically one that generated a task."""
    try:
        # No user_id needed as block_id is globally unique, but auth is still good practice.
        auth.get_user_id_from_context(ctx)
        success = await db_manager.add_progress_update(block_id, update_message)
        if not success:
            return {"status": "failure", "error": "Block not found or update failed."}
        return {"status": "success", "result": "Progress update added to block."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def search_journal(ctx: Context, query: str) -> Dict[str, Any]:
    """Searches the user's journal entries for a specific keyword or phrase."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        search_results = await db_manager.search_journal_content(user_id, query)
        if not search_results:
            return {"status": "success", "result": "No matching journal entries found."}
        
        simplified_results = [
            f"On {item['page_date']}: \"{item['content']}\""
            for item in search_results
        ]
        return {"status": "success", "result": "\n".join(simplified_results)}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def summarize_day(ctx: Context, date: str) -> Dict[str, Any]:
    """Retrieves all journal entries for a given date (format: YYYY-MM-DD) and returns their combined content."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        summary = await db_manager.get_day_summary(user_id, date)
        return {"status": "success", "result": summary}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9018))
    mcp.run(transport="sse", host=host, port=port)