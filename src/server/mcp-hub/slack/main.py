# server/mcp-hub/slack/main.py

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="SlackServer",
    instructions="A server for interacting with a Slack workspace using a user token.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://slack-agent-system")
def get_slack_system_prompt() -> str:
    return prompts.slack_agent_system_prompt

@mcp.prompt(name="slack_user_prompt_builder")
def build_slack_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.slack_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

# --- Tool Definitions ---
async def _execute_tool(ctx: Context, method_name: str, *args, **kwargs) -> Dict[str, Any]:
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_slack_creds(user_id)
        client = utils.SlackApiClient(token=creds['token'], team_id=creds['team_id'])
        
        method_to_call = getattr(client, method_name)
        result = await method_to_call(*args, **kwargs)
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def slack_list_channels(ctx: Context, limit: int = 100, cursor: Optional[str] = None) -> Dict:
    """Lists public channels in the workspace."""
    return await _execute_tool(ctx, "list_channels", limit, cursor)

@mcp.tool
async def slack_post_message(ctx: Context, channel_id: str, text: str) -> Dict:
    """Posts a new message to a Slack channel."""
    return await _execute_tool(ctx, "post_message", channel_id, text)

@mcp.tool
async def slack_reply_to_thread(ctx: Context, channel_id: str, thread_ts: str, text: str) -> Dict:
    """Replies to a specific message thread in a channel."""
    return await _execute_tool(ctx, "reply_to_thread", channel_id, thread_ts, text)

@mcp.tool
async def slack_add_reaction(ctx: Context, channel_id: str, timestamp: str, reaction: str) -> Dict:
    """Adds an emoji reaction to a message. The reaction is the emoji name without colons (e.g., 'thumbsup')."""
    return await _execute_tool(ctx, "add_reaction", channel_id, timestamp, reaction)

@mcp.tool
async def slack_get_channel_history(ctx: Context, channel_id: str, limit: int = 10) -> Dict:
    """Gets recent messages from a channel."""
    return await _execute_tool(ctx, "get_channel_history", channel_id, limit)

@mcp.tool
async def slack_get_thread_replies(ctx: Context, channel_id: str, thread_ts: str) -> Dict:
    """Gets all replies in a message thread."""
    return await _execute_tool(ctx, "get_thread_replies", channel_id, thread_ts)

@mcp.tool
async def slack_get_users(ctx: Context, limit: int = 100, cursor: Optional[str] = None) -> Dict:
    """Gets a list of all users in the workspace."""
    return await _execute_tool(ctx, "get_users", limit, cursor)

@mcp.tool
async def slack_get_user_profile(ctx: Context, user_id: str) -> Dict:
    """Gets detailed profile information for a specific user."""
    return await _execute_tool(ctx, "get_user_profile", user_id)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9006))
    
    print(f"Starting Slack MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)