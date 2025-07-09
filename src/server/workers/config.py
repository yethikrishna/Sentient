import os
from dotenv import load_dotenv


# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
SUPERMEMORY_MCP_BASE_URL = os.getenv("SUPERMEMORY_MCP_BASE_URL", "https://mcp.supermemory.ai/")
SUPERMEMORY_MCP_ENDPOINT_SUFFIX = os.getenv("SUPERMEMORY_MCP_ENDPOINT_SUFFIX", "/sse")
SUPPORTED_POLLING_SERVICES = ["gmail", "gcalendar"]
