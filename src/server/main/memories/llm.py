import os
import logging
from qwen_agent.agents import Assistant
from typing import Dict, Any
import json

from . import prompts
from main.llm import run_agent

logger = logging.getLogger(__name__)

def get_fact_analysis_agent() -> Assistant:
    """Initializes an agent for performing a full analysis of a fact."""
    logger.debug("Initializing 'FactAnalysisAgent'.")
    return {"system_message": prompts.fact_analysis_system_prompt_template, "name": "FactAnalysisAgent"}

def run_agent_with_prompt(agent_config: Dict[str, Any], user_prompt: str) -> str:
    """Helper function to run an agent and extract the final content string."""
    agent_name = agent_config.get('name', 'UnknownAgent')
    system_message = agent_config.get('system_message', '')
    logger.info(f"Running agent '{agent_name}'...")
    logger.debug(f"Agent '{agent_name}' user prompt:\n---PROMPT START---\n{user_prompt}\n---PROMPT END---")
    messages = [{'role': 'user', 'content': user_prompt}]
    final_content = ""

    try:
        for chunk in run_agent(system_message=system_message, function_list=[], messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                final_content = chunk[-1].get("content", "")
    except Exception as e:
        logger.error(f"Agent '{agent_name}' failed after trying all keys: {e}")
        return "" # Return empty on failure

    logger.debug(f"Agent '{agent_name}' raw response:\n---RESPONSE START---\n{final_content}\n---RESPONSE END---")
    return final_content