import logging
import json
from qwen_agent.agents import Assistant
from typing import List, Any

from workers.planner import config
from workers.planner import prompts
from workers.planner.db import get_all_mcp_descriptions

logger = logging.getLogger(__name__)

def run_agent_with_fallback(system_message: str, function_list: list, messages: list):
    """
    Worker-specific implementation to run a Qwen Assistant with API key fallback.
    """
    if not config.OPENAI_API_KEYS:
        raise ValueError("No OpenAI API keys configured for planner worker.")

    errors = []
    for i, key in enumerate(config.OPENAI_API_KEYS):
        llm_cfg = {
            'model': config.OPENAI_MODEL_NAME,
            'model_server': config.OPENAI_API_BASE_URL,
            'api_key': key,
        }

        try:
            logger.info(f"Attempting to run planner/question agent with API key #{i+1}")
            bot = Assistant(llm=llm_cfg, system_message=system_message, function_list=function_list or [])

            yield from bot.run(messages=messages)
            return # Success

        except Exception as e:
            error_message = f"Planner/Question agent run with API key #{i+1} failed: {e}"
            logger.warning(error_message)
            errors.append(error_message)
            continue # Try next key

    raise Exception(f"All OpenAI API keys failed for planner/question agent. Errors: {errors}")

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

    # This function now returns the necessary components to run the agent with fallback
    return {
        "system_message": system_prompt,
        "function_list": []
    }
    
def get_question_generator_agent(
    original_context: dict,
    available_tools_for_prompt: dict,
    mcp_servers_for_agent: dict
):
    """Initializes a unified Qwen agent to verify context and generate clarifying questions."""
    original_context_str = json.dumps(original_context, indent=2, default=str)

    system_prompt = prompts.QUESTION_GENERATOR_SYSTEM_PROMPT.format(
        original_context=original_context_str,
    )
    
    tools_config = [{"mcpServers": mcp_servers_for_agent}]
    
    return {
        "system_message": system_prompt,
        "function_list": tools_config
    }
