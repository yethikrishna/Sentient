# src/server/main/llm.py
import os
import logging
from qwen_agent.agents import Assistant
from qwen_agent.llm import get_chat_model

from main.config import (OPENAI_API_BASE_URL, OPENAI_API_KEY,
                         OPENAI_MODEL_NAME)

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant called Sentient, developed by Existence. Your primary goal is to assist the user in managing their digital life by performing actions and providing responses that are deeply personalized to them."

def get_qwen_assistant(system_message: str = DEFAULT_SYSTEM_PROMPT, function_list: list = None):
    """
    Initializes and returns a Qwen Assistant agent configured for the current environment.
    """
    # Qwen-agent's `Assistant` uses an OpenAI-compatible interface.
    # We map our standard environment variables to its expected config format.
    # Note: `model_server` for qwen-agent is the `base_url`.
    llm_cfg = {
        'model': OPENAI_MODEL_NAME,
        'model_server': f"{OPENAI_API_BASE_URL.rstrip('/')}/v1",
        'api_key': OPENAI_API_KEY,
    }
    logger.info(f"Qwen Agent configured with model='{OPENAI_MODEL_NAME}' and server='{llm_cfg['model_server']}'")
    if not OPENAI_MODEL_NAME:
        logger.error("LLM model name is not configured. Qwen Agent cannot be initialized.")
        raise ValueError("LLM model configuration error.")

    try:
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