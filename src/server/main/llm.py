# src/server/main/qwen_agent_utils.py
import os
import logging
from qwen_agent.agents import Assistant
from qwen_agent.llm import get_chat_model

from .config import (
    IS_DEV_ENVIRONMENT,
    OLLAMA_MODEL_NAME, OLLAMA_BASE_URL,
    OPENROUTER_MODEL_NAME, OPENROUTER_API_KEY
)

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."

def get_qwen_assistant(system_message: str = DEFAULT_SYSTEM_PROMPT, function_list: list = None):
    """
    Initializes and returns a Qwen Assistant agent configured for the current environment.
    """
    llm_cfg = {}
    if IS_DEV_ENVIRONMENT:
        # Ollama configuration for Qwen Agent (expects OpenAI-compatible v1 endpoint)
        # Ensure OLLAMA_BASE_URL is like "http://localhost:11434"
        ollama_v1_url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1"
        llm_cfg = {
            'model': OLLAMA_MODEL_NAME,  # e.g., "llama3.2:3b"
            'model_server': ollama_v1_url,
            'api_key': 'ollama',  # Placeholder, Ollama doesn't typically require a key via API
            'generate_cfg': {
                'temperature': 0.7, # Example generation parameter
            }
        }
        logger.info(f"Qwen Agent configured for Development (Ollama): model={OLLAMA_MODEL_NAME}, server={ollama_v1_url}")
    else:
        # OpenRouter configuration for Qwen Agent
        openrouter_v1_url = "https://openrouter.ai/api/v1" # Standard OpenRouter API base
        llm_cfg = {
            'model': OPENROUTER_MODEL_NAME,  # e.g., "meta-llama/llama-3.1-8b-instruct" or your "llama3.2:3b" if mapped
            'model_server': openrouter_v1_url,
            'api_key': OPENROUTER_API_KEY,
            'generate_cfg': {
                'temperature': 0.7, # Example generation parameter
            }
        }
        # For OpenRouter, some models might need specific routing prefixes if not handled by model_server directly
        # e.g. 'model': 'openrouter/meta-llama/llama-3.1-8b-instruct'
        # However, Qwen's OpenAI client usually takes the model name as passed.
        # The 'model_server' determines the endpoint.
        logger.info(f"Qwen Agent configured for Production (OpenRouter): model={OPENROUTER_MODEL_NAME}, server={openrouter_v1_url}")

    if not llm_cfg.get('model'):
        logger.error("LLM model name is not configured. Qwen Agent cannot be initialized.")
        raise ValueError("LLM model configuration error.")

    try:
        # Initialize the LLM part of the agent
        # llm_instance = get_chat_model(llm_cfg) # Can also pass llm_cfg directly to Assistant

        # Initialize the Assistant agent
        bot = Assistant(
            llm=llm_cfg,
            system_message=system_message,
            function_list=function_list or [] # Ensure function_list is a list
        )
        logger.info(f"Qwen Assistant initialized successfully with system message: '{system_message[:50]}...'")
        return bot
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Assistant: {e}", exc_info=True)
        raise RuntimeError(f"Qwen Assistant initialization failed: {e}")