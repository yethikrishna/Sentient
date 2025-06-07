# server/mcp-hub/brave/auth.py

import os
from fastmcp import Context
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

def get_user_id_from_context(ctx: Context) -> str:
    """
    Extracts the User ID from the 'X-User-ID' header in the HTTP request.
    Maintained for structural consistency with other MCP servers.
    """
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")

    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")

    return user_id

def get_brave_api_key() -> str:
    """
    Retrieves the Brave Search API key from environment variables.

    Returns:
        str: The Brave Search API key.

    Raises:
        ToolError: If the BRAVE_SEARCH_API_KEY is not set.
    """
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ToolError(
            "Brave Search API key is not configured. "
            "Please set BRAVE_SEARCH_API_KEY in your .env file."
        )
    return api_key