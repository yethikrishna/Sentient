# server/mcp-hub/google_search/auth.py

import os
from typing import Dict
from fastmcp import Context
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

def get_user_id_from_context(ctx: Context) -> str:
    """
    Extracts the User ID from the 'X-User-ID' header in the HTTP request.
    Maintained for structural consistency.
    """
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")

    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")

    return user_id

def get_google_api_keys() -> Dict[str, str]:
    """
    Retrieves the Google API Key and CSE ID from environment variables.

    Returns:
        Dict[str, str]: A dictionary containing the API key and CSE ID.

    Raises:
        ToolError: If the required keys are not set in the environment.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not all([api_key, cse_id]) or api_key == "your_google_api_key":
        raise ToolError(
            "Google Search API keys are not configured. "
            "Please set GOOGLE_API_KEY and GOOGLE_CSE_ID in your .env file."
        )
    return {"api_key": api_key, "cse_id": cse_id}