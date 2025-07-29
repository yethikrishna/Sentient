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
    return {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
        'api_key': OPENAI_API_KEY
    }

def get_topic_classification_agent() -> Assistant:
    """Initializes an agent for classifying text into one or more Topics."""
    system_prompt = prompts.topic_classification_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_subtopic_generation_agent() -> Assistant:
    """Initializes an agent for generating subtopics for a given fact."""
    system_prompt = prompts.subtopic_generation_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_fact_summarization_agent() -> Assistant:
    """Initializes an agent for summarizing a list of facts into a paragraph."""
    system_prompt = prompts.fact_summarization_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_fact_extraction_agent() -> Assistant:
    """Initializes an agent for extracting single-sentence facts from text."""
    system_prompt = prompts.fact_extraction_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_edit_decision_agent() -> Assistant:
    """Initializes an agent for deciding on CRUD operations for a fact."""
    system_prompt = prompts.edit_decision_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def get_memory_type_agent() -> Assistant:
    """Initializes an agent for deciding if a fact is long or short-term."""
    system_prompt = prompts.memory_type_decision_system_prompt_template
    llm_cfg = _get_base_llm_config()
    return Assistant(llm=llm_cfg, system_message=system_prompt)

def run_agent_with_prompt(agent: Assistant, user_prompt: str) -> str:
    """Helper function to run an agent and extract the final content string."""
    messages = [{'role': 'user', 'content': user_prompt}]
    final_content = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk:
            last_message = chunk[-1]
            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                final_content = last_message["content"]
    return final_content