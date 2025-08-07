# src/server/main/llm.py
import os
import logging
import time
import httpx
from qwen_agent.agents import Assistant
from qwen_agent.llm import get_chat_model

from main.config import (OPENAI_API_KEYS, OPENAI_API_BASE_URL,
                         OPENAI_MODEL_NAME)

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant called Sentient, developed by Existence. Your primary goal is to assist the user in managing their digital life by performing actions and providing responses that are deeply personalized to them."

def get_qwen_assistant(system_message: str = DEFAULT_SYSTEM_PROMPT, function_list: list = None):
    """
    DEPRECATED: Use run_agent_with_fallback instead.
    This function is kept for non-streaming, simple use cases if any exist, but will only use the primary key.
    """
    llm_cfg = {
        'model': OPENAI_MODEL_NAME,
        'model_server': OPENAI_API_BASE_URL,
        'api_key': OPENAI_API_KEYS[0] if OPENAI_API_KEYS else None,
    }
    logger.info(f"Qwen Agent configured with model='{OPENAI_MODEL_NAME}' and server='{llm_cfg['model_server']}'")
    if not OPENAI_MODEL_NAME:
        logger.error("LLM model name is not configured. Qwen Agent cannot be initialized.")
        raise ValueError("LLM model configuration error.")

    try:
        bot = Assistant(
            llm=llm_cfg,
            system_message=system_message,
            function_list=function_list or [] # Ensure function_list is a list
        )
        return bot
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Assistant: {e}", exc_info=True)
        raise RuntimeError(f"Qwen Assistant initialization failed: {e}")
def run_agent_with_fallback(system_message: str, function_list: list, messages: list):
    """
    Initializes and runs a Qwen Assistant, trying a list of API keys in sequence if failures occur.
    Each key is tried up to 3 times with a delay to accommodate for transient network issues.
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

        # Retry logic
        max_retries = 3
        retry_delay = 2  # seconds
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to run agent with API key #{i+1} (Attempt {attempt + 1}/{max_retries})")
                bot = Assistant(llm=llm_cfg, system_message=system_message, function_list=function_list or [])

                yield from bot.run(messages=messages)
                return  # If the stream completes successfully, exit the generator.

            except Exception as e:
                error_message = f"Agent run with API key #{i+1}, attempt #{attempt + 1} failed: {e}"
                logger.warning(error_message, exc_info=True)

                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    # Last attempt failed, append error and move to next key
                    errors.append(error_message)
                    break  # Break from retry loop to go to next key

    # If the loop completes, all keys have failed
    raise Exception(f"All OpenAI API keys failed after retries. Errors: {errors}")
