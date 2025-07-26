import os
from typing import Dict, Any

from dotenv import load_dotenv
from fastmcp import FastMCP, Context

from . import auth, utils

# Load environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="WhatsAppServer",
    instructions="This server provides tools to send messages via WhatsApp.",
)

@mcp.tool()
async def send_message(ctx: Context, message: str) -> Dict[str, Any]:
    """
    Sends a message to the user on WhatsApp. Use this to communicate directly with the user for follow-ups, results, or when you need to send information proactively.
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
