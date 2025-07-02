import os
import asyncio
import json
from typing import Dict, Any


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
    name="GSlidesServer",
    instructions="This server provides tools to create Google Slides presentations.",
)

@mcp.resource("prompt://gslides-agent-system")
def get_gslides_system_prompt() -> str:
    return prompts.gslides_agent_system_prompt

@mcp.prompt(name="gslides_user_prompt_builder")
def build_gslides_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.gslides_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

@mcp.tool()
async def create_google_presentation(ctx: Context, outline_json: str) -> Dict[str, Any]:
    """
    Creates a new Google Slides presentation based on a structured outline.
    'outline_json' must be a JSON string of an object containing 'topic', 'username', and a list of 'slides'.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        slides_service = auth.authenticate_gslides(creds)
        drive_service = auth.authenticate_gdrive(creds)
        
        try:
            outline = json.loads(outline_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for outline_json: {e}")

        # The core logic is synchronous, so run it in a thread
        presentation_result = await utils.create_presentation_from_outline(
            slides_service, drive_service, outline
        )
        
        return presentation_result
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9014))
    
    print(f"Starting GSlides MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)