import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def add_fact_to_supermemory(user_id: str, mcp_url: str, fact: str) -> Dict[str, Any]:
    """
    Directly calls the Supermemory MCP server to add a memory.
    """
    if not mcp_url or not mcp_url.startswith("https://mcp.supermemory.ai/"):
        logger.warning(f"Invalid or missing Supermemory MCP URL for user {user_id}. Cannot add fact.")
        return {"status": "error", "message": "Invalid MCP URL"}

    payload = {
        "tool": "addToSupermemory",
        "parameters": {"memory": fact}
    }
    
    api_endpoint = mcp_url.replace("/sse", "")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_endpoint, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Successfully sent fact to Supermemory for user {user_id}: '{fact[:50]}...'")
            return {"status": "success", "response": response.json()}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling Supermemory for user {user_id}: {e.response.status_code} - {e.response.text}")
        return {"status": "error", "message": f"HTTP Error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error sending fact to Supermemory for user {user_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}