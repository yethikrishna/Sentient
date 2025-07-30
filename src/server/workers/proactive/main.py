# src/server/workers/proactive/main.py
import logging
import json
from typing import Dict, Any

from main.llm import get_qwen_assistant
from json_extractor import JsonExtractor
from workers.utils.api_client import notify_user
from workers.proactive.prompts import PROACTIVE_REASONER_SYSTEM_PROMPT, SUGGESTION_TYPE_STANDARDIZER_SYSTEM_PROMPT
from workers.proactive.utils import (
    event_pre_filter,
    extract_query_text,
    get_universal_context,
)
# Use PlannerMongoManager to get a DB connection in the worker
from workers.planner.db import PlannerMongoManager

logger = logging.getLogger(__name__)

async def standardize_suggestion_type(suggestion_type_description: str) -> str:
    """
    Uses an LLM call to map a free-form description to a canonical type.
    """
    logger.info(f"Standardizing suggestion type for description: '{suggestion_type_description}'")
    db_manager = PlannerMongoManager()
    try:
        templates = await db_manager.get_all_proactive_suggestion_templates()
        if not templates:
            logger.warning("No proactive suggestion templates found in DB. Defaulting to custom type.")
            return "custom_proactive_action"

        prompt = (
            f"Action Description:\n\"{suggestion_type_description}\"\n\n"
            f"Available Canonical Types:\n{json.dumps(templates, indent=2)}"
        )
        
        agent = get_qwen_assistant(system_message=SUGGESTION_TYPE_STANDARDIZER_SYSTEM_PROMPT)
        messages = [{'role': 'user', 'content': prompt}]

        response_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    response_str = last_message["content"]

        response_str = response_str.strip()
        logger.info(f"Standardizer LLM returned: '{response_str}'")

        if response_str == "create_new_type":
            logger.info(f"New suggestion type identified for description: '{suggestion_type_description}'")
            return "custom_proactive_action"
        
        if any(t['type_name'] == response_str for t in templates):
            return response_str
        else:
            logger.warning(f"Standardizer LLM returned an invalid type name: '{response_str}'. Defaulting to custom type.")
            return "custom_proactive_action"

    except Exception as e:
        logger.error(f"Error during suggestion type standardization: {e}", exc_info=True)
        return "custom_proactive_action"
    finally:
        await db_manager.close()

async def run_proactive_reasoner(scratchpad: Dict[str, Any]) -> Dict[str, Any]:
    """
    Makes the LLM call to the proactive reasoner.
    """
    logger.info("Running proactive reasoner LLM call...")

    agent = get_qwen_assistant(system_message=PROACTIVE_REASONER_SYSTEM_PROMPT)

    # The user prompt is the scratchpad itself
    user_prompt = json.dumps(scratchpad, indent=2)
    messages = [{'role': 'user', 'content': user_prompt}]

    response_str = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk:
            last_message = chunk[-1]
            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                response_str = last_message["content"]

    if not response_str:
        logger.error("Proactive reasoner LLM returned an empty response.")
        return {"actionable": False, "error": "Empty LLM response"}

    reasoner_output = JsonExtractor.extract_valid_json(response_str)
    if not reasoner_output:
        logger.error(f"Failed to parse JSON from reasoner LLM response: {response_str}")
        return {"actionable": False, "error": "Invalid JSON response from LLM"}

    return reasoner_output

async def run_proactive_pipeline_logic(user_id: str, event_type: str, event_data: Dict[str, Any]):
    """
    The main orchestration logic for the proactive pipeline.
    """
    logger.info(f"Starting proactive pipeline for user '{user_id}', event_type '{event_type}'.")

    # 1. Event Pre-Filter
    if not event_pre_filter(event_data, event_type):
        logger.info("Event discarded by pre-filter. Pipeline stopped.")
        return

    # 2. Extract Query Text
    query_text = extract_query_text(event_data, event_type)
    if not query_text:
        logger.warning("Could not extract query text from event. Pipeline stopped.")
        return

    logger.info(f"Extracted query text: '{query_text[:100]}...'")

    # 3. Get Universal Context (Cognitive Scratchpad)
    cognitive_scratchpad = await get_universal_context(user_id, query_text)

    # 4. Add Trigger Event to Scratchpad
    cognitive_scratchpad["trigger_event"] = {
        "event_type": event_type,
        "event_data": event_data
    }

    # 5. Pass to Proactive Reasoner
    reasoner_result = await run_proactive_reasoner(cognitive_scratchpad)

    # 6. Process Reasoner Output
    if reasoner_result and reasoner_result.get("actionable"):
        logger.info(f"Proactive action identified for user '{user_id}'. Suggestion: {reasoner_result.get('suggestion_description')}")
        
        # --- PHASE 2 LOGIC ---
        # 6a. Standardize the suggestion type
        suggestion_type_desc = reasoner_result.get("suggestion_type_description")
        if not suggestion_type_desc:
            logger.warning("Reasoner output is missing 'suggestion_type_description'. Cannot standardize.")
            return

        standardized_type = await standardize_suggestion_type(suggestion_type_desc)
        
        # 6b. Construct and send the notification
        notification_payload = {
            "suggestion_type": standardized_type,
            "action_details": reasoner_result.get("suggestion_action_details")
        }
        
        user_facing_message = f"AI Suggestion: {reasoner_result.get('suggestion_description')}"

        await notify_user(
            user_id=user_id,
            message=user_facing_message,
            notification_type="proactive_suggestion",
            payload=notification_payload
        )
        logger.info(f"Sent proactive suggestion notification to user '{user_id}'.")
        
    else:
        logger.info(f"No proactive action deemed necessary for user '{user_id}'. Reasoner output: {reasoner_result}")