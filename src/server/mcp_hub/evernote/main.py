import os
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="EvernoteServer",
    instructions="A server for interacting with an Evernote account.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://evernote-agent-system")
def get_evernote_system_prompt() -> str:
    return prompts.evernote_agent_system_prompt

@mcp.prompt(name="evernote_user_prompt_builder")
def build_evernote_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.evernote_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, method_name: str, *args, **kwargs) -> Dict[str, Any]:
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_evernote_creds(user_id)
        client = utils.EvernoteApiClient(token=creds['token'])

        method_to_call = getattr(client, method_name)
        result = await method_to_call(*args, **kwargs)

        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---

@mcp.tool
async def list_notebooks(ctx: Context) -> Dict:
    """Lists all notebooks in the user's Evernote account."""
    return await _execute_tool(ctx, "list_notebooks")

@mcp.tool
async def create_note(ctx: Context, notebook_id: str, title: str, content: str) -> Dict:
    """
    Creates a new note in a specified notebook.
    'content' should be plain text; it will be wrapped in ENML.
    """
    return await _execute_tool(ctx, "create_note", notebook_id, title, content)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9023))

    print(f"Starting Evernote MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
