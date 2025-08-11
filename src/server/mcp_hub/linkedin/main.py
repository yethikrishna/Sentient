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

# Load environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="LinkedInServer",
    instructions="Provides a tool to search for job listings on LinkedIn.",
)

@mcp.resource("prompt://linkedin-agent-system")
def get_linkedin_system_prompt() -> str:
    return prompts.linkedin_agent_system_prompt

@mcp.prompt(name="linkedin_user_prompt_builder")
def build_linkedin_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.linkedin_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

@mcp.tool()
async def job_search(ctx: Context, search_query: str, num_jobs: int = 10) -> Dict[str, Any]:
    """
    Searches for job listings on LinkedIn based on a search query and scrapes a specified number of jobs.
    It saves the results to a CSV file and returns the file path.
    """
    logger.info(f"Executing tool: job_search with query='{search_query}', num_jobs={num_jobs}")
    try:
        user_id = auth.get_user_id_from_context(ctx)
        await auth.check_linkedin_integration(user_id)
        
        # Sanitize user_id for directory creation
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '|', '_'))

        file_path = await utils.perform_job_search(safe_user_id, search_query, num_jobs)
        
        return {"status": "success", "result": f"Job search complete. Results saved to: {file_path}"}
    except Exception as e:
        logger.error(f"Tool job_search failed: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9027))
    
    print(f"Starting LinkedIn MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)