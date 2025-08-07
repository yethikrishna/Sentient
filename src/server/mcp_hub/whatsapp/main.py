import os
from typing import Dict, Any

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, utils

# Load environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="WhatsAppServer",
    instructions="Provides a tool to send a WhatsApp message to the user's connected phone number.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://whatsapp-agent-system")
def get_whatsapp_system_prompt() -> str:
    from . import prompts
    return prompts.whatsapp_agent_system_prompt

@mcp.prompt(name="whatsapp_user_prompt_builder")
def build_whatsapp_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    from . import prompts
    content = prompts.whatsapp_agent_user_prompt.format(query=query, username=username, previous_tool_response=previous_tool_response)
    return Message(role="user", content=content)

@mcp.tool()
async def send_message(ctx: Context, message: str) -> Dict[str, Any]:
    """
    Sends a text message to the user's primary WhatsApp number. Use this for notifications, alerts, or delivering results of a long-running task.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        chat_id = await auth.get_whatsapp_chat_id(user_id)
        
        result = await utils.send_whatsapp_message(chat_id, message)
        
        if result and result.get("id"):
            return {"status": "success", "result": f"Message sent successfully. Message ID: {result['id']}"}
        else:
            raise Exception("Failed to send message via WAHA service or received an unexpected response.")
    
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9024))
    
    print(f"Starting WhatsApp MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)


