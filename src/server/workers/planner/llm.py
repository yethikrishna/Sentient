import logging
import json
from qwen_agent.agents import Assistant

from workers.planner import config
from workers.planner import prompts
from workers.planner.db import get_all_mcp_descriptions

logger = logging.getLogger(__name__)

def get_planner_agent(available_tools: dict, current_time_str: str, user_name: str, user_location: str, retrieved_context: dict = None):
    """Initializes and returns a Qwen Assistant agent for planning."""
    
    # Format the MCP descriptions for the prompt
    # The keys are now the simple names (e.g., 'gmail')
    tools_list_str = "\n".join([f"- {name}: {desc}" for name, desc in available_tools.items()])
    
    # Format the retrieved context for the prompt
    context_str = json.dumps(retrieved_context, indent=2) if retrieved_context else "No additional context was found in memory."

    # Add current time to the prompt for better contextual planning
    system_prompt = prompts.SYSTEM_PROMPT.format(
        user_name=user_name,
        user_location=user_location,
        current_time=current_time_str,
        available_tools=tools_list_str,
        retrieved_context=context_str
    )

    llm_cfg = {}
    if config.LLM_PROVIDER == "OLLAMA":
        ollama_v1_url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1"
        llm_cfg = {
            'model': config.OLLAMA_MODEL_NAME,
            'model_server': ollama_v1_url,
            'api_key': 'ollama',
        }
    elif config.LLM_PROVIDER == "NOVITA":
        llm_cfg = {
            'model': config.NOVITA_MODEL_NAME,
            'model_server': "https://api.novita.ai/v3/openai",
            'api_key': config.NOVITA_API_KEY,
        }
    else: # Add NOVITA provider
        raise ValueError(f"Unsupported LLM_PROVIDER for planner: {config.LLM_PROVIDER}. Must be 'OLLAMA' or 'NOVITA'")

    try:
        agent = Assistant(
            llm=llm_cfg,
            system_message=system_prompt,
            function_list=[]  # Planner doesn't call tools, just generates the plan
        )
        logger.info("Qwen Planner Agent initialized.")
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Planner Agent: {e}", exc_info=True)
        raise