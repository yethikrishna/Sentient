# src/server/workers/extractor/llm.py
import logging
from qwen_agent.agents import Assistant

from workers.extractor import config
from workers.extractor import prompts

logger = logging.getLogger(__name__)

def get_extractor_agent(user_name: str, user_location: str, user_timezone: str):
    """
    Initializes and returns a Qwen Assistant agent configured for extraction.
    """
    llm_cfg = {}

    system_prompt = prompts.SYSTEM_PROMPT.format(
        user_name=user_name,
        user_location=user_location,
        user_timezone=user_timezone
    )

    llm_cfg = {
        'model': config.OPENAI_MODEL_NAME,
        'model_server': config.OPENAI_API_BASE_URL,
        'api_key': config.OPENAI_API_KEY,
    }
    logger.info(f"Extractor agent configured for model='{config.OPENAI_MODEL_NAME}' and server='{llm_cfg['model_server']}'")
    try:
        agent = Assistant(
            llm=llm_cfg,
            system_message=system_prompt,
            function_list=[] # No tools, just structured output
        )
        logger.info("Qwen Extractor Agent initialized successfully.")
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Extractor Agent: {e}", exc_info=True)
        raise