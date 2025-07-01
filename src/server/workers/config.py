import os


dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')

SUPERMEMORY_MCP_BASE_URL = os.getenv("SUPERMEMORY_MCP_BASE_URL", "https://mcp.supermemory.ai/")
SUPERMEMORY_MCP_ENDPOINT_SUFFIX = os.getenv("SUPERMEMORY_MCP_ENDPOINT_SUFFIX", "/sse")
SUPPORTED_POLLING_SERVICES = ["gmail", "gcalendar"]
