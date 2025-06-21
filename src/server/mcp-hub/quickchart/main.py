# server/mcp-hub/quickchart/main.py

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="QuickChartServer",
    instructions="A server for generating data visualizations using QuickChart.io.",
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
    Generates a URL for a chart image based on a Chart.js configuration.
    
    Args:
        chart_config: A dictionary representing the Chart.js configuration.
    """
    try:
        auth.get_user_id_from_context(ctx)
        chart_url = utils.generate_chart_url(chart_config)
        return {"status": "success", "result": {"chart_url": chart_url}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def download_chart(ctx: Context, chart_config: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a chart and saves it as a PNG image to a local file.
    
    Args:
        chart_config: A dictionary representing the Chart.js configuration.
        output_path: Optional local file path to save the image.
    """
    try:
        auth.get_user_id_from_context(ctx)
        chart_url = utils.generate_chart_url(chart_config)
        saved_path = await utils.download_chart_image(chart_url, output_path)
        return {"status": "success", "result": f"Chart saved successfully to: {saved_path}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9008))
    
    print(f"Starting QuickChart MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)