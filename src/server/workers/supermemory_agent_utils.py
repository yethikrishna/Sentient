import logging
from qwen_agent.agents import Assistant
from workers.planner.db import PlannerMongoManager # Re-use for DB access
from workers.planner.config import LLM_PROVIDER, OLLAMA_MODEL_NAME, OLLAMA_BASE_URL, NOVITA_MODEL_NAME, NOVITA_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_SUPERMEMORY_CELERY = """
You are a thoughtful memory processing agent. Your task is to analyze the given text, which is a fact about the user, and determine the best way to store it.

**Your primary goal is to use the `supermemory-addToSupermemory` tool.**
The user's identity is managed by the system configuration of the tool. You only need to pass the fact itself as the `thingToRemember` parameter.
"""

def get_db_manager() -> PlannerMongoManager:
    """Returns an instance of the PlannerMongoManager for database access."""
    # PlannerMongoManager can fetch user_profiles, which is what we need.
    return PlannerMongoManager()

def get_supermemory_qwen_agent(supermemory_mcp_url: str):
    """
    Initializes a Qwen agent configured to use a specific Supermemory MCP URL.
    """
    llm_cfg = {}
    if LLM_PROVIDER == "OLLAMA":
        ollama_v1_url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1"
        llm_cfg = {
            'model': OLLAMA_MODEL_NAME,
            'model_server': ollama_v1_url,
            'api_key': 'ollama',
            'generate_cfg': {
                'temperature': 0.1, # Low temperature for deterministic tool use
            }
        }
    elif LLM_PROVIDER == "NOVITA":
        novita_v1_url = "https://api.novita.ai/v3/openai"
        llm_cfg = {
            'model': NOVITA_MODEL_NAME,
            'model_server': novita_v1_url,
            'api_key': NOVITA_API_KEY,
            'generate_cfg': {
                'temperature': 0.1,
            }
        }
    else:
        logger.error(f"Invalid LLM_PROVIDER for Supermemory agent: '{LLM_PROVIDER}'.")
        raise ValueError(f"Invalid LLM_PROVIDER configured: {LLM_PROVIDER}. Must be 'OLLAMA' or 'NOVITA'")

    if not llm_cfg.get('model'):
        logger.error("LLM model name is not configured. Supermemory Qwen Agent cannot be initialized.")
        raise ValueError("LLM model configuration error for Supermemory agent.")

    tools_config = [{
        "mcpServers": {
            "supermemory": { # The key "supermemory" should match tool names like "supermemory-addToSupermemory"
                "url": supermemory_mcp_url,
                "transport": "sse" # Ensure transport is specified if needed by Qwen Agent
                # No "headers" like X-User-ID needed for Supermemory's public MCP URL
            }
        }
    }]

    try:
        agent = Assistant(
            llm=llm_cfg,
            system_message=SYSTEM_PROMPT_SUPERMEMORY_CELERY,
            function_list=tools_config,
            description="An agent that uses a remote MCP server to manage memories.",
        )
        logger.info(f"Supermemory Qwen Agent initialized successfully for MCP: {supermemory_mcp_url}")
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize Supermemory Qwen Assistant for MCP {supermemory_mcp_url}: {e}", exc_info=True)
        raise RuntimeError(f"Supermemory Qwen Assistant initialization failed: {e}")