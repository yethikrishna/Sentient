import os
import logging
from qwen_agent.agents import Assistant
from typing import Dict, Any, List, Union
import json

from . import prompts

# Use the main server's LLM config
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1/")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3:4b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")

logger = logging.getLogger(__name__)

def _get_base_llm_config() -> Dict[str, Any]:
    config = {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
        'api_key': OPENAI_API_KEY
    }
    logger.debug(f"Using LLM config: model={config['model']}, server={config['model_server']}")
    return config

def get_fact_summarization_agent() -> Assistant:
    """Initializes an agent for summarizing a list of facts into a paragraph."""
    logger.debug("Initializing 'FactSummarizationAgent'.")
    system_prompt = prompts.fact_summarization_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, name="FactSummarizationAgent", system_message=system_prompt)

def get_fact_extraction_agent() -> Assistant:
    """Initializes an agent for extracting single-sentence facts from text."""
    logger.debug("Initializing 'FactExtractionAgent'.")
    system_prompt = prompts.fact_extraction_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, name="FactExtractionAgent", system_message=system_prompt)

def get_fact_analysis_agent() -> Assistant:
    """Initializes an agent for performing a full analysis of a fact."""
    logger.debug("Initializing 'FactAnalysisAgent'.")
    system_prompt = prompts.fact_analysis_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, name="FactAnalysisAgent", system_message=system_prompt)

def get_cud_decision_agent() -> Assistant:
    """Initializes an agent for deciding on CUD operations and performing analysis."""
    logger.debug("Initializing 'CudDecisionAgent'.")
    system_prompt = prompts.cud_decision_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, name="CudDecisionAgent", system_message=system_prompt)

def run_agent_with_prompt(agent: Assistant, user_prompt: str) -> str:
    """Helper function to run an agent and extract the final content string."""
    logger.info(f"Running agent '{getattr(agent, 'name', 'UnknownAgent')}'...")
    logger.debug(f"Agent '{getattr(agent, 'name', 'UnknownAgent')}' user prompt:\n---PROMPT START---\n{user_prompt}\n---PROMPT END---")
    messages = [{'role': 'user', 'content': user_prompt}]
    final_content = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk:
            last_message = chunk[-1]
            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                final_content = last_message["content"]
    logger.debug(f"Agent '{getattr(agent, 'name', 'UnknownAgent')}' raw response:\n---RESPONSE START---\n{final_content}\n---RESPONSE END---")
    return final_content