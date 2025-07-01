import os
import asyncio
import json
from typing import Dict, Any, List
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
    name="GSheetsServer",
    instructions="This server provides tools to create and manage Google Sheets.",
)

@mcp.resource("prompt://gsheets-agent-system")
def get_gsheets_system_prompt() -> str:
    return prompts.gsheets_agent_system_prompt

@mcp.prompt(name="gsheets_user_prompt_builder")
def build_gsheets_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gsheets_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

@mcp.tool()
async def create_google_sheet(ctx: Context, title: str, sheets_json: str) -> Dict[str, Any]:
    """
    Creates a new Google Spreadsheet with one or more sheets containing data.
    'sheets_json' must be a JSON string of a list of sheet objects.
    Each sheet object should contain 'title', 'table', with 'headers' and 'rows'.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gsheets(creds)
        
        try:
            sheets_data = json.loads(sheets_json)
            if not isinstance(sheets_data, list):
                raise ValueError("sheets_json must be a list of sheet objects.")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid format for sheets_json: {e}")

        spreadsheet_result = await asyncio.to_thread(
            utils.create_spreadsheet_with_data, service, title, sheets_data
        )
        
        return spreadsheet_result
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9015))
    
    print(f"Starting GSheets MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)