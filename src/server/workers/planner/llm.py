import logging
import json
from qwen_agent.agents import Assistant
from typing import List, Any
from main.config import OPENAI_API_KEY, OPENAI_API_BASE_URL, OPENAI_MODEL_NAME
from workers.planner import config
from workers.planner import prompts
from workers.planner.db import get_all_mcp_descriptions

logger = logging.getLogger(__name__)

def get_planner_agent(available_tools: dict, current_time_str: str, user_name: str, user_location: str):
    """Initializes and returns a Qwen Assistant agent for planning."""
    
    # Format the MCP descriptions for the prompt
    # The keys are now the simple names (e.g., 'gmail')
        
    # Add current time to the prompt for better contextual planning
    system_prompt = prompts.SYSTEM_PROMPT.format(
        user_name=user_name,
        user_location=user_location,
        current_time=current_time_str,
    )

    # This function now returns the necessary components to run the agent with fallback
    return {
        "system_message": system_prompt,
        "function_list": []
    }