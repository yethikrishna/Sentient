import os
import json
from typing import Dict, Optional

import motor.motor_asyncio
from dotenv import load_dotenv
from fastmcp import Context
from fastmcp.exceptions import ToolError

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_collection = db["user_profiles"]

def get_user_id_from_context(ctx: Context) -> str:
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")
    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")
    return user_id

async def get_whatsapp_chat_id(user_id: str) -> str:
    """Fetches the user's WhatsApp chat ID from their profile."""
    user_doc = await users_collection.find_one({"user_id": user_id})

    if not user_doc or not user_doc.get("userData"):
        raise ToolError(f"User profile not found for user_id: {user_id}.")

    # Correctly look for the agent's connection details under integrations
    wa_integration = user_doc.get("userData", {}).get("integrations", {}).get("whatsapp", {})

    if not wa_integration.get("connected"):
        raise ToolError("WhatsApp Agent is not connected. Please connect it in the Integrations page.")

    chat_id = wa_integration.get("credentials", {}).get("chatId")

    if not chat_id:
        raise ToolError("WhatsApp Agent is connected but the Chat ID is missing. Please try reconnecting.")

    return chat_id