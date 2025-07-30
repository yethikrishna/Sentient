# src/server/workers/proactive/utils.py
import logging
import json
from typing import Dict, Any, Optional

from main.search.utils import perform_unified_search

logger = logging.getLogger(__name__)

def event_pre_filter(event_data: Dict[str, Any], event_type: str) -> bool:
    """
    A simple pre-filter to discard obviously irrelevant events.
    Returns True if the event should be processed, False if it should be discarded.
    """
    if event_type == "gmail":
        # Check for common spam/newsletter keywords in subject or snippet
        content_to_check = (
            event_data.get("subject", "") + " " + event_data.get("snippet", "")
        ).lower()

        filter_keywords = [
            "unsubscribe", "promotional", "newsletter", "sale", "discount",
            "special offer", "limited time", "no-reply", "noreply"
        ]

        if any(keyword in content_to_check for keyword in filter_keywords):
            logger.info(f"Event pre-filter: Discarding email due to keyword match. Subject: {event_data.get('subject')}")
            return False

    elif event_type == "gcalendar":
        # Discard events that have been cancelled
        if event_data.get("status") == "cancelled":
            logger.info(f"Event pre-filter: Discarding cancelled calendar event. Summary: {event_data.get('summary')}")
            return False

    return True

def extract_query_text(event_data: Dict[str, Any], event_type: str) -> str:
    """
    Extracts a string from the event data to be used as a query for universal search.
    """
    if event_type == "gmail":
        subject = event_data.get("subject", "")
        # Use snippet as it's a concise summary of the body
        snippet = event_data.get("snippet", "")
        return f"{subject} {snippet}".strip()

    elif event_type == "gcalendar":
        summary = event_data.get("summary", "")
        description = event_data.get("description", "")
        return f"{summary} {description}".strip()

    # Fallback for other event types
    return json.dumps(event_data)

async def get_universal_context(user_id: str, query_text: str) -> Dict[str, Any]:
    """
    Calls the unified search agent to gather context for the cognitive scratchpad.
    """
    logger.info(f"Getting universal context for user '{user_id}' with query: '{query_text}'")
    final_report = "No context found."
    try:
        # perform_unified_search is an async generator
        async for chunk in perform_unified_search(query_text, user_id):
            event = json.loads(chunk)
