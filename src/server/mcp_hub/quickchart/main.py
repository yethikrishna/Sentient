# server/mcp_hub/quickchart/main.py

import os
from typing import Dict, Any, Optional


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message
from fastmcp.utilities.logging import configure_logging, get_logger

from . import auth, prompts, utils

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
mcp = FastMCP(
    name="QuickChartServer",
    instructions="Provides tools to generate chart images from data using the QuickChart.io service, which is based on the Chart.js library.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://quickchart-agent-system")
def get_quickchart_system_prompt() -> str:
    return prompts.quickchart_agent_system_prompt

@mcp.prompt(name="quickchart_user_prompt_builder")
def build_quickchart_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.quickchart_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Definitions ---

@mcp.tool
async def generate_chart(ctx: Context, chart_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a public URL for a chart image.
    Requires a `chart_config` dictionary that follows the Chart.js configuration format.
    """
    logger.info(f"Executing tool: generate_chart")
    try:
        auth.get_user_id_from_context(ctx)
        chart_url = utils.generate_chart_url(chart_config)
        return {"status": "success", "result": {"chart_url": chart_url}}
    except Exception as e:
        logger.error(f"Tool generate_chart failed: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def download_chart(ctx: Context, chart_config: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a chart and downloads it as a PNG image to a local file path.
    Requires a `chart_config` dictionary. If `output_path` is not specified, it saves to the user's Desktop or home directory.
    """
    logger.info(f"Executing tool: download_chart")
    try:
        auth.get_user_id_from_context(ctx)
        chart_url = utils.generate_chart_url(chart_config)
        saved_path = await utils.download_chart_image(chart_url, output_path)
        return {"status": "success", "result": f"Chart saved successfully to: {saved_path}"}
    except Exception as e:
        logger.error(f"Tool download_chart failed: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9008))
    
    print(f"Starting QuickChart MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)