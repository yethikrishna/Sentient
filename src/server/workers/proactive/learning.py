# src/server/workers/proactive/learning.py
import logging
from main.dependencies import mongo_manager

logger = logging.getLogger(__name__)

async def record_user_feedback(user_id: str, suggestion_type: str, feedback: str):
    """
    Records user feedback to adjust preferences for proactive suggestions.
    'feedback' should be "positive" or "negative".
    """
    if not all([user_id, suggestion_type, feedback]):
        logger.warning("Missing arguments for record_user_feedback.")
        return

    increment_value = 1 if feedback == "positive" else -1
    await mongo_manager.update_proactive_preference_score(user_id, suggestion_type, increment_value)
    logger.info(f"Recorded '{feedback}' feedback for user '{user_id}' on suggestion type '{suggestion_type}'.")