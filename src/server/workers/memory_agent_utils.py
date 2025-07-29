import logging
from qwen_agent.agents import Assistant
from workers.planner.db import PlannerMongoManager
from workers.planner.config import OPENAI_API_BASE_URL, OPENAI_MODEL_NAME, OPENAI_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MEMORY_CELERY = """
You are a thoughtful memory processing agent. Your task is to analyze the given text, which is a fact about the user, and determine the best way to store it.

**Your primary goal is to use the `memory_mcp-cud_memory` tool.**
The user's identity is managed by the system configuration of the tool. You only need to pass the fact itself as the `information` parameter.
"""

def get_db_manager() -> PlannerMongoManager:
    """Returns an instance of the PlannerMongoManager for database access."""
    return PlannerMongoManager()

def get_memory_qwen_agent(memory_mcp_url: str):
    """Initializes a Qwen agent configured to use a specific Memory MCP URL."""
    llm_cfg = {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
        'api_key': OPENAI_API_KEY,
    }

    tools_config = [{
        "mcpServers": {
            "memory_mcp": {
                "url": memory_mcp_url,
                "transport": "sse"
            }
        }
    }]

    agent = Assistant(llm=llm_cfg, system_message=SYSTEM_PROMPT_MEMORY_CELERY, function_list=tools_config)
    logger.info(f"Memory Qwen Agent initialized successfully for MCP: {memory_mcp_url}")
    return agent