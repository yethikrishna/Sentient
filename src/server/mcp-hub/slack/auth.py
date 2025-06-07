# server/mcp-hub/slack/auth.py

import os
from typing import Dict
import motor.motor_asyncio
from fastmcp import Context
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_collection = db["users"]

def get_user_id_from_context(ctx: Context) -> str:
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")
    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")
    return user_id

async def get_slack_creds(user_id: str) -> Dict[str, str]:
    """
    Fetches Slack credentials (token and team_id) from MongoDB.
    """
    user_doc = await users_collection.find_one({"_id": user_id})

    if not user_doc or "slack_token" not in user_doc:
        raise ToolError(f"Slack token not found for user_id: {user_id}. Please run generate_slack_token.py.")

    token_info = user_doc["slack_token"]
    if not all(key in token_info for key in ["token", "team_id"]):
        raise ToolError("Invalid Slack token data in database. Re-authentication is required.")

    return token_info