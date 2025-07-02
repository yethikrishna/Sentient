import os
import asyncio
import json
from typing import Dict, Any


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

# Conditionally load .env for local development
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="GDocsServer",
    instructions="This server provides tools to create Google Docs.",
)

@mcp.resource("prompt://gdocs-agent-system")
def get_gdocs_system_prompt() -> str:
    return prompts.gdocs_agent_system_prompt

@mcp.prompt(name="gdocs_user_prompt_builder")
def build_gdocs_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gdocs_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

@mcp.tool()
async def create_google_document(ctx: Context, title: str, sections_json: str) -> Dict[str, Any]:
    """
    Creates a new Google Document with a title and structured content.
    'sections_json' must be a JSON string of a list of section objects.
    Each section object should contain 'heading', 'heading_level', 'paragraphs', 'bullet_points', and an optional 'image_description'.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        docs_service = auth.authenticate_gdocs(creds)
        drive_service = auth.authenticate_gdrive(creds)
        
        try:
            sections = json.loads(sections_json)
            if not isinstance(sections, list):
                raise ValueError("sections_json must be a list of section objects.")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid format for sections_json: {e}")

        # The core logic is synchronous, so run it in a thread
        document_result = await asyncio.to_thread(
            utils.create_google_document_sync, docs_service, drive_service, title, sections
        )
        
        return document_result
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9004))
    
    print(f"Starting GDocs MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)