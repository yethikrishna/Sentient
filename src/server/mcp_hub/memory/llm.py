import os
from qwen_agent.agents import Assistant
from typing import Dict, Any
import json

from . import prompts
import logging
from main.llm import run_agent

logger = logging.getLogger(__name__)

# Use the main server's LLM config
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1/") # Keep for consistency in config
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3:4b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")

def _get_base_llm_config() -> Dict[str, Any]:
    config = {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
    }
    logger.debug(f"Using LLM config: model={config['model']}, server={config['model_server']}")
    return config

def get_fact_relevance_agent() -> Assistant:
    """Initializes an agent for checking if a fact is relevant to a query."""
    logger.debug("Initializing 'FactRelevanceAgent'.")
    return {"system_message": prompts.fact_relevance_system_prompt_template, "name": "FactRelevanceAgent"}

def get_fact_summarization_agent() -> Assistant:
    """Initializes an agent for summarizing a list of facts into a paragraph."""
    logger.debug("Initializing 'FactSummarizationAgent'.")
    return {"system_message": prompts.fact_summarization_system_prompt_template, "name": "FactSummarizationAgent"}

def get_fact_extraction_agent() -> Assistant:
    """Initializes an agent for extracting single-sentence facts from text."""
    logger.debug("Initializing 'FactExtractionAgent'.")
    return {"system_message": prompts.fact_extraction_system_prompt_template, "name": "FactExtractionAgent"}

def get_fact_analysis_agent() -> Assistant:
    """Initializes an agent for performing a full analysis of a fact."""
    logger.debug("Initializing 'FactAnalysisAgent'.")
    return {"system_message": prompts.fact_analysis_system_prompt_template, "name": "FactAnalysisAgent"}

def get_cud_decision_agent() -> Assistant:
    """Initializes an agent for deciding on CUD operations and performing analysis."""
    logger.debug("Initializing 'CudDecisionAgent'.")
    return {"system_message": prompts.cud_decision_system_prompt_template, "name": "CudDecisionAgent"}

def run_agent_with_prompt(agent_config: Dict[str, Any], user_prompt: str) -> str:
    """Helper function to run an agent and extract the final content string."""
    agent_name = agent_config.get('name', 'UnknownAgent')
    system_message = agent_config.get('system_message', '')
    logger.info(f"Running agent '{agent_name}'...")
    logger.debug(f"Agent '{agent_name}' user prompt:\n---PROMPT START---\n{user_prompt}\n---PROMPT END---")
    messages = [{'role': 'user', 'content': user_prompt}]
    final_content = ""
    
    # Removed: # Import here to avoid circular dependency issues at module load time
    
    try:
        for chunk in run_agent(system_message=system_message, function_list=[], messages=messages):
            if isinstance(chunk, list) and chunk and chunk[-1].get("role") == "assistant":
                final_content = chunk[-1].get("content", "")
    except Exception as e:
        logger.error(f"Agent '{agent_name}' failed: {e}")
        return "" # Return empty on failure

    logger.debug(f"Agent '{agent_name}' raw response:\n---RESPONSE START---\n{final_content}\n---RESPONSE END---")
    return final_content