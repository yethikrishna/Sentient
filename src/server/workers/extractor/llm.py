# src/server/workers/extractor/llm.py
import logging
from qwen_agent.agents import Assistant

from . import config
from . import prompts

logger = logging.getLogger(__name__)

def get_extractor_agent():
    """
    Initializes and returns a Qwen Assistant agent configured for extraction.
    """
    llm_cfg = {}
    if config.LLM_PROVIDER == "OLLAMA":
        ollama_v1_url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1"
        llm_cfg = {
            'model': config.OLLAMA_MODEL_NAME,
            'model_server': ollama_v1_url,
            'api_key': 'ollama',
            'generate_cfg': {
                'temperature': 0.1,
                'response_format': {'type': 'json_object'},
            }
        }
        logger.info(f"Qwen Agent configured for OLLAMA: model={config.OLLAMA_MODEL_NAME}")
    elif config.LLM_PROVIDER == "OPENROUTER":
        openrouter_v1_url = "https://openrouter.ai/api/v1"
        llm_cfg = {
            'model': config.OPENROUTER_MODEL_NAME,
            'model_server': openrouter_v1_url,
            'api_key': config.OPENROUTER_API_KEY,
            'generate_cfg': {
                'temperature': 0.1,
                'response_format': {'type': 'json_object'},
            }
        }
        logger.info(f"Qwen Agent configured for OPENROUTER: model={config.OPENROUTER_MODEL_NAME}")
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {config.LLM_PROVIDER}")

    try:
        agent = Assistant(
            llm=llm_cfg,
            system_message=prompts.SYSTEM_PROMPT,
            function_list=[] # No tools, just structured output
        )
        logger.info("Qwen Extractor Agent initialized successfully.")
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Extractor Agent: {e}", exc_info=True)
        raise