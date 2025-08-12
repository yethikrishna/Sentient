import os
import logging
import time
import httpx
from qwen_agent.agents import Assistant
from qwen_agent.llm import get_chat_model

from main.config import (OPENAI_API_KEYS, OPENAI_API_BASE_URL,
                         OPENAI_MODEL_NAME)

logger = logging.getLogger(__name__)

class LLMProviderDownError(Exception):
    """Custom exception for when all LLM providers are down."""
    pass

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant called Sentient, developed by Existence. Your primary goal is to assist the user in managing their digital life by performing actions and providing responses that are deeply personalized to them."

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
    raise LLMProviderDownError(f"All OpenAI API keys failed after retries. Errors: {errors}")