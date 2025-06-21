import os
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

# Local imports
from . import auth
from . import prompts
from . import utils

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# --- Server Initialization ---
mcp = FastMCP(
    name="GDriveServer",
    instructions="This server provides tools to search for and read files from Google Drive.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://gdrive-agent-system")
def get_gdrive_system_prompt() -> str:
    return prompts.gdrive_agent_system_prompt

@mcp.prompt(name="gdrive_user_prompt_builder")
def build_gdrive_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gdrive_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Definitions ---

@mcp.tool()
async def gdrive_search(ctx: Context, query: str) -> Dict[str, Any]:
    """Searches for files in Google Drive matching a query."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gdrive(creds)
        # If the query from the LLM is a simple string without Drive operators,
        # wrap it in `fullText contains` for robustness.
        drive_operators = ['contains', ' in ', '=', '!=', '>', '<']
        if not any(op in query for op in drive_operators):
            # Escape single quotes within the query text itself
            safe_query_text = query.replace("'", "\\'")
            final_query = f"fullText contains '{safe_query_text}'"
        else:
            final_query = query

        def _execute_sync_search():
            results = service.files().list(
                q=final_query,
                pageSize=20,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)"
            ).execute()
            
            files = results.get("files", [])
            for file in files:
                if 'size' in file:
                    size = int(file['size'])
                    if size < 1024:
                        file['size'] = f"{size} B"
                    elif size < 1024**2:
                        file['size'] = f"{size/1024:.1f} KB"
                    else:
                        file['size'] = f"{size/1024**2:.1f} MB"
            return files

        search_results = await asyncio.to_thread(_execute_sync_search)
        if not search_results:
            return {"status": "success", "result": f"No files found matching the query: '{final_query}'"}
            
        return {"status": "success", "result": {"files_found": search_results}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def gdrive_read_file(ctx: Context, file_id: str) -> Dict[str, Any]:
    """Reads the content of a file from Google Drive by its ID."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gdrive(creds)
        
        file_content = await asyncio.to_thread(
            utils.download_and_convert_file_sync, service, file_id
        )
        
        return {"status": "success", "result": file_content}
    except Exception as e:
        return {"status": "failure", "error": f"Failed to read file: {e}"}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9003))
    
    print(f"Starting GDrive MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)