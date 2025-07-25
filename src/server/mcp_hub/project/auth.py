# src/server/mcp_hub/project/auth.py
import os
from fastmcp import Context
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True)

def get_user_id_from_context(ctx: Context) -> str:
    """
    Extracts the User ID from the 'X-User-ID' header in the HTTP request.
    """
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")
    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")
    return user_id