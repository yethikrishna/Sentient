# server/mcp-hub/gmail/auth.py

import os
import motor.motor_asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from fastmcp import Context
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

# Establish a single, reusable connection to MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_collection = db["users"]


def get_user_id_from_context(ctx: Context) -> str:
    """
    Extracts the User ID from the 'X-User-ID' header in the HTTP request.

    Args:
        ctx (Context): The MCP context object.

    Returns:
        str: The user ID.

    Raises:
        ToolError: If the 'X-User-ID' header is not found.
    """
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")

    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")

    return user_id


async def get_google_creds(user_id: str) -> Credentials:
    """
    Fetches Google OAuth token from MongoDB for a given user_id.

    Args:
        user_id (str): The ID of the user.

    Returns:
        Credentials: A Google OAuth Credentials object.

    Raises:
        ToolError: If the user or their token is not found in the database.
    """
    user_doc = await users_collection.find_one({"_id": user_id})

    if not user_doc or "google_token" not in user_doc:
        raise ToolError(f"Google token not found for user_id: {user_id}. Please authenticate with Google.")

    token_info = user_doc["google_token"]

    # Ensure all required fields for Credentials object are present
    required_keys = ["token", "refresh_token", "token_uri", "client_id", "client_secret", "scopes"]
    if not all(key in token_info for key in required_keys):
        raise ToolError("Invalid token data in database. Re-authentication is required.")

    return Credentials.from_authorized_user_info(token_info)


def authenticate_gmail(creds: Credentials) -> Resource:
    """
    Authenticates and returns the Gmail API service using provided credentials.

    Args:
        creds (Credentials): The Google OAuth credentials.

    Returns:
        googleapiclient.discovery.Resource: The authenticated Gmail API service resource.
    """
    return build("gmail", "v1", credentials=creds)