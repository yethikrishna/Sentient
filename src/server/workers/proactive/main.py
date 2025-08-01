# src/server/workers/proactive/main.py
import logging
import json
import datetime
from typing import Dict, Any

from main.llm import get_qwen_assistant
from json_extractor import JsonExtractor
from workers.utils.api_client import notify_user
from workers.proactive.prompts import (
    PROACTIVE_REASONER_SYSTEM_PROMPT,
    SUGGESTION_TYPE_STANDARDIZER_SYSTEM_PROMPT,
    QUERY_FORMULATION_SYSTEM_PROMPT
)
from workers.proactive.utils import extract_query_text, get_universal_context
# Use PlannerMongoManager to get a DB connection in the worker
from workers.planner.db import PlannerMongoManager
from workers.utils.text_utils import clean_llm_output

logger = logging.getLogger(__name__)

async def formulate_search_queries(user_id: str, event_type: str, event_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Uses a dedicated LLM agent to decide what questions to ask universal search.
    """
    logger.info(f"Formulating dynamic search queries for user '{user_id}'.")
    agent = get_qwen_assistant(system_message=QUERY_FORMULATION_SYSTEM_PROMPT)

    prompt = json.dumps({"event_type": event_type, "event_data": event_data}, indent=2)
    messages = [{'role': 'user', 'content': prompt}]

    response_str = ""
    for chunk in agent.run(messages=messages):
        if isinstance(chunk, list) and chunk:
            last_message = chunk[-1]
            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                response_str = last_message["content"]

    queries = JsonExtractor.extract_valid_json(response_str)
    if not isinstance(queries, dict) or not queries:
        logger.warning(f"Query Formulation Agent failed to return a valid dictionary of queries. Response: {response_str}")
        # Fallback to a single, simple query
        return {"event_context": extract_query_text(event_data, event_type)}

    logger.info(f"Dynamically formulated queries: {queries}")
    return queries

async def standardize_suggestion_type(suggestion_type_description: str) -> str:
    """
    Uses an LLM call to map a free-form description to a canonical type from the DB,
    or generates a new snake_case type if no suitable match is found.
    """
    logger.info(f"Standardizing suggestion type for description: '{suggestion_type_description}'")
    db_manager = PlannerMongoManager()
    try:
        templates = await db_manager.get_all_proactive_suggestion_templates()
        
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
                    response_str = clean_llm_output(last_message["content"])

        # The LLM should return a single snake_case string.
        standardized_type = response_str.strip()
        logger.info(f"Standardizer LLM returned: '{standardized_type}'")

        if not standardized_type:
            logger.warning("Standardizer LLM returned an empty string. Defaulting to 'custom_proactive_action'.")
            return "custom_proactive_action"

        # Check if it's a new type or an existing one.
        is_existing_type = any(t['type_name'] == standardized_type for t in templates)
        if is_existing_type:
            logger.info(f"Matched to existing suggestion type: '{standardized_type}'")
        else:
            logger.info(f"LLM generated a new suggestion type: '{standardized_type}'")
        
        return standardized_type

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

    # 2. Formulate Dynamic Search Queries
    situational_queries = await formulate_search_queries(user_id, event_type, event_data)

    # 3. Get Universal Context (Cognitive Scratchpad)
    cognitive_scratchpad = await get_universal_context(user_id, situational_queries)

    # --- NEW: Fetch User Preferences ---
    db_manager = None
    try:
        db_manager = PlannerMongoManager()
        preferences = await db_manager.get_user_proactive_preferences(user_id)
        cognitive_scratchpad["user_preferences"] = preferences
        logger.info(f"Added user preferences to cognitive scratchpad for user '{user_id}'.")
    except Exception as e:
        logger.error(f"Failed to fetch user preferences for {user_id}: {e}", exc_info=True)
        cognitive_scratchpad["user_preferences"] = {} # Default to empty if error
    finally:
        if db_manager:
            await db_manager.close()
    # --- END NEW ---

    # 4. Add Trigger Event to Scratchpad
    cognitive_scratchpad["trigger_event"] = {
        "event_type": event_type,
        "event_data": event_data
    }
    cognitive_scratchpad["current_time_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 5. Pass to Proactive Reasoner
    reasoner_result = await run_proactive_reasoner(cognitive_scratchpad)

    # 6. Process Reasoner Output
    if reasoner_result and reasoner_result.get("actionable"):
        logger.info(f"Proactive action identified for user '{user_id}'. Suggestion: {reasoner_result.get('suggestion_description')}")
        
        suggestion_type_desc = reasoner_result.get("suggestion_type_description")
        if not suggestion_type_desc:
            logger.warning("Reasoner output is missing 'suggestion_type_description'. Cannot proceed.")
            return

        standardized_type = await standardize_suggestion_type(suggestion_type_desc)
        
        # --- NEW: Dynamic Thresholding Logic ---
        base_threshold = 0.70  # The default confidence score needed to show a suggestion.
        user_score = preferences.get(standardized_type, 0)
        
        # Adjust threshold based on score. Each point of score adjusts the threshold by 5%.
        # Positive score lowers the threshold (easier to show), negative score raises it (harder to show).
        threshold_adjustment = user_score * 0.05
        dynamic_threshold = base_threshold - threshold_adjustment
        
        # Clamp the threshold to a reasonable range (e.g., 40% to 95%) to avoid extreme behavior.
        dynamic_threshold = max(0.40, min(0.95, dynamic_threshold))

        llm_confidence = reasoner_result.get("confidence_score", 0.0)

        logger.info(f"Evaluating suggestion '{standardized_type}' for user '{user_id}'. LLM Confidence: {llm_confidence:.2f}, User Score: {user_score}, Dynamic Threshold: {dynamic_threshold:.2f}")

        if llm_confidence >= dynamic_threshold:
            logger.info("Suggestion passed dynamic threshold. Notifying user.")
            # --- END NEW ---

            notification_payload = {
                "suggestion_type": standardized_type,
                "action_details": reasoner_result.get("suggestion_action_details"),
                "gathered_context": cognitive_scratchpad,
                "reasoning": reasoner_result.get("reasoning")
            }
            
            user_facing_message = f"AI Suggestion: {reasoner_result.get('suggestion_description')}"

            await notify_user(
                user_id=user_id,
                message=user_facing_message,
                notification_type="proactive_suggestion",
                payload=notification_payload
            )
            logger.info(f"Sent proactive suggestion notification to user '{user_id}'.")
        
        # --- NEW ---
        else:
            logger.info(f"Suggestion for user '{user_id}' was suppressed. LLM confidence ({llm_confidence:.2f}) did not meet the dynamic threshold ({dynamic_threshold:.2f}) based on user feedback.")
        # --- END NEW ---
        
    else:
        logger.info(f"No proactive action deemed necessary for user '{user_id}'. Reasoner output: {reasoner_result}")