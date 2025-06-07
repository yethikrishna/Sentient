# server/mcp-hub/accuweather/auth.py

import os
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

load_dotenv()

def get_accuweather_api_key() -> str:
    """
    Retrieves the AccuWeather API key from environment variables.

    Raises:
        ToolError: If the ACCUWEATHER_API_KEY is not set.
    """
    api_key = os.getenv("ACCUWEATHER_API_KEY")
    if not api_key or api_key == "your_accuweather_api_key":
        raise ToolError(
            "AccuWeather API key is not configured. "
            "Please set ACCUWEATHER_API_KEY in your .env file."
        )
    return api_key