import os
import logging
from qwen_agent.agents import Assistant
from typing import Dict, Any, List, Union
import json

from . import prompts
from . import formats

# Use the main server's LLM config
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1/")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3:4b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")

logger = logging.getLogger(__name__)

def _get_base_llm_config() -> Dict[str, Any]:
    return {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
        'api_key': OPENAI_API_KEY
    }

def get_text_dissection_agent() -> Assistant:
    """Initializes a Qwen agent for dissecting text into categories."""
    system_prompt = prompts.text_dissection_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_info_extraction_agent() -> Assistant:
    """Initializes a Qwen agent for extracting entities and relationships."""
    system_prompt = prompts.information_extraction_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_query_classification_agent() -> Assistant:
    """Initializes a Qwen agent for classifying queries into categories."""
    system_prompt = prompts.query_classification_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_text_conversion_agent() -> Assistant:
    """Initializes a Qwen agent for converting graph data to text."""
    system_prompt = prompts.text_conversion_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_fact_extraction_agent() -> Assistant:
    """Initializes a Qwen agent for extracting single-sentence facts from text."""
    system_prompt = prompts.fact_extraction_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_crud_decision_agent() -> Assistant:
    """Initializes a Qwen agent for deciding CRUD operations on the graph."""
    system_prompt = prompts.graph_decision_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def run_agent_with_prompt(agent: Assistant, user_prompt: str) -> Union[Dict, List, str]:
    """Helper function to run an agent and extract the final content."""
    messages = [{'role': 'user', 'content': user_prompt}]
    final_content = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk:
            last_message = chunk[-1]
            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                final_content = last_message["content"]

    # Attempt to parse as JSON if it looks like it, otherwise return raw string
    if final_content.strip().startswith(("{", "[")):
        try:
            return json.loads(final_content)
        except json.JSONDecodeError:
            logger.warning(f"Agent output looked like JSON but failed to parse: {final_content}")
    return final_content