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
    name="DiscordServer",
    instructions="Provides tools to interact with a user's Discord account, allowing the agent to list servers (guilds), list channels, and send messages.",
)

@mcp.resource("prompt://discord-agent-system")
def get_discord_system_prompt() -> str:
    return prompts.discord_agent_system_prompt

@mcp.prompt(name="discord_user_prompt_builder")
def build_discord_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.discord_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

async def _execute_tool(ctx: Context, method_name: str, *args, **kwargs) -> Dict[str, Any]:
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_discord_creds(user_id)
        client = utils.DiscordApiClient(bot_token=creds['bot_token'])
        
        method_to_call = getattr(client, method_name)
        result = await method_to_call(*args, **kwargs)
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def list_guilds(ctx: Context) -> Dict:
    """
    Lists the Discord servers (guilds) that the authenticated user's bot is a member of, returning their names and IDs.
    """
    return await _execute_tool(ctx, "list_guilds")

@mcp.tool
async def list_channels(ctx: Context, guild_id: str) -> Dict:
    """
    Retrieves a list of all text and voice channels within a specified Discord server (guild), returning their names and IDs.
    """
    return await _execute_tool(ctx, "list_channels", guild_id)

@mcp.tool
async def send_channel_message(ctx: Context, channel_id: str, content: str) -> Dict:
    """
    Sends a text message to a specific Discord channel, identified by its `channel_id`.
    """
    return await _execute_tool(ctx, "send_channel_message", channel_id, content)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9022))
    
    print(f"Starting Discord MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)