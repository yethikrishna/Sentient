import logging
import json
from qwen_agent.agents import Assistant
from typing import List, Any
from main.config import OPENAI_API_KEYS, OPENAI_API_BASE_URL, OPENAI_MODEL_NAME
from workers.planner import config
from workers.planner import prompts
from workers.planner.db import get_all_mcp_descriptions

logger = logging.getLogger(__name__)

def run_agent_with_fallback(system_message: str, function_list: list, messages: list):
    """
    Initializes and runs a Qwen Assistant, trying a list of API keys in sequence if failures occur.
    This function is a generator that yields the results from the successful agent run.
    """
    if not OPENAI_API_KEYS:
        raise ValueError("No OpenAI API keys configured.")

    errors = []
    for i, key in enumerate(OPENAI_API_KEYS):
        llm_cfg = {
            'model': OPENAI_MODEL_NAME,
            'model_server': OPENAI_API_BASE_URL,
            'api_key': key,
        }

        try:
            logger.info(f"Attempting to run agent with API key #{i+1}")
            bot = Assistant(llm=llm_cfg, system_message=system_message, function_list=function_list or [])

            yield from bot.run(messages=messages)
            return # If the stream completes successfully, exit the generator.

        except Exception as e:
            error_message = f"Agent run with API key #{i+1} failed: {e}"
            logger.warning(error_message, exc_info=True)
            errors.append(error_message)
            continue # Try the next key

    # If the loop completes, all keys have failed
    raise Exception(f"All OpenAI API keys failed. Errors: {errors}")

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
