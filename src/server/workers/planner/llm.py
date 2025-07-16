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
    llm_cfg = {
        'model': config.OPENAI_MODEL_NAME,
        'model_server': config.OPENAI_API_BASE_URL,
        'api_key': config.OPENAI_API_KEY,
    }

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
    
def get_question_generator_agent(supermemory_mcp_url: str, original_context: dict, topics: list, available_tools: dict):
    """Initializes a unified Qwen agent to verify context and generate clarifying questions."""
    original_context_str = json.dumps(original_context, indent=2, default=str)
    tools_list_str = "\n".join([f"- {name}: {desc}" for name, desc in available_tools.items()])
    system_prompt = prompts.QUESTION_GENERATOR_SYSTEM_PROMPT.format(
        original_context=original_context_str,
        topics=", ".join(topics),
        available_tools=tools_list_str
    )
    llm_cfg = {
        'model': config.OPENAI_MODEL_NAME,
        'model_server': config.OPENAI_API_BASE_URL,
        'api_key': config.OPENAI_API_KEY,
    }
    
    tools_config = [{
        "mcpServers": {
            "supermemory": {
                "url": supermemory_mcp_url,
                "transport": "sse"
            }
        }
    }]
    
    agent = Assistant(
        llm=llm_cfg,
        system_message=system_prompt,
        function_list=tools_config
    )
    return agent