# src/server/workers/proactive/utils.py
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple

from main.search.utils import perform_unified_search

logger = logging.getLogger(__name__)

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def event_pre_filter(event_data: Dict[str, Any], event_type: str, user_email: Optional[str] = None) -> bool:
    """
    An enhanced pre-filter to discard obviously irrelevant or non-actionable events based on content and metadata.
    This runs AFTER user-defined privacy filters.
    Returns True if the event should be processed, False if it should be discarded.
    """
    if event_type == "gmail":
        headers = {h['name'].lower(): h['value'] for h in event_data.get('payload', {}).get('headers', [])}
        subject = event_data.get("subject", "")
        # Use the correct keys from the Composio payload
        snippet = event_data.get("preview", {}).get("body", "")
        body = event_data.get("message_text", "")
        content_to_check = f"{subject} {snippet}".lower()

        # Filter 1: Auto-replies (e.g., out-of-office)
        if headers.get("auto-submitted") == "auto-replied":
            logger.info(f"Gmail pre-filter: Discarding auto-reply email. Subject: {subject}")
            return False

        # Filter 2: Mailing lists and bulk mail
        if "list-unsubscribe" in headers or headers.get("precedence") in ["bulk", "junk"]:
            logger.info(f"Gmail pre-filter: Discarding mailing list/bulk email. Subject: {subject}")
            return False

        # Filter 3: Calendar invitations/updates via email (often redundant with calendar polling)
        if "text/calendar" in headers.get("content-type", "") or subject.startswith(("invitation:", "accepted:", "declined:", "updated invitation:")):
            logger.info(f"Gmail pre-filter: Discarding calendar-related email. Subject: {subject}")
            return False

        # Filter 4: Short, non-actionable "fluff" emails
        short_fluff_bodies = ["thanks", "thank you", "got it", "ok", "okay", "received", "sounds good"]
        if len(body.split()) < 5 and any(phrase in body for phrase in short_fluff_bodies):
            logger.info(f"Gmail pre-filter: Discarding short/fluff email. Body: '{body}'")
            return False

        # Filter 5: Common transactional/promotional keywords
        filter_keywords = [
            "unsubscribe", "promotional", "newsletter", "sale", "discount", "special offer",
            "limited time", "no-reply", "noreply", "order confirmation", "shipping update",
            "your receipt for", "verify your email"
        ]
        if any(keyword in content_to_check for keyword in filter_keywords):
            logger.info(f"Gmail pre-filter: Discarding email due to keyword match. Subject: {subject}")
            return False

    elif event_type == "gcalendar":
        summary = event_data.get("summary", "").lower()

        # Filter 1: Cancelled events
        if event_data.get("status") == "cancelled":
            logger.info(f"GCal pre-filter: Discarding cancelled event. Summary: {summary}")
            return False

        # Filter 2: Events created by the user themselves
        # Composio payload provides organizer_email. Compare it with the user's email.
        organizer_email = event_data.get("organizer_email", "").lower()
        if user_email and organizer_email == user_email.lower():
             logger.info(f"GCal pre-filter: Discarding event created by the user. Summary: {summary}")
             return False

        # Filter 3: Events the user has already declined
        if user_email:
            for attendee in event_data.get("attendees", []):
                if attendee.get("email", "").lower() == user_email.lower() and attendee.get("responseStatus") == "declined":
                    logger.info(f"GCal pre-filter: Discarding event user has declined. Summary: {summary}")
                    return False

        # Filter 4: Generic, non-actionable "blocking" events
        blocking_keywords = ["busy", "hold for", "blocked", "focus time", "ooo", "out of office"]
        if any(keyword in summary for keyword in blocking_keywords):
            logger.info(f"GCal pre-filter: Discarding generic blocking event. Summary: {summary}")
            return False

    # If no filter condition was met, the event is considered valid for processing.
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

async def get_universal_context(user_id: str, queries: Dict[str, str]) -> Dict[str, Any]:
    """
    Calls the unified search agent with multiple queries in parallel to gather context for the cognitive scratchpad.
    """
    logger.info(f"Getting universal context for user '{user_id}' with {len(queries)} queries.")
    
    async def run_search(query_key: str, query_text: str) -> Tuple[str, str]:
        """Wrapper to run a single search and return the result with its key."""
        final_report = "No context found."
        # perform_unified_search is an async generator
        async for chunk in perform_unified_search(query_text, user_id):
            event = json.loads(chunk)
            if event.get("type") == "done":
                final_report = event.get("final_report", "No context found.")
                break
        return query_key, final_report

    try:
        # Create and run search tasks concurrently
        search_tasks = [run_search(key, text) for key, text in queries.items()]
        search_results_list = await asyncio.gather(*search_tasks)

        # Convert the list of tuples back into a dictionary
        search_results_dict = dict(search_results_list)
        logger.info(f"Universal search completed for all {len(queries)} queries.")
        return {"universal_search_results": search_results_dict}
    except Exception as e:
        logger.error(f"Error during universal context search for user '{user_id}': {e}", exc_info=True)
        return {"universal_search_results": f"An error occurred during search: {e}"}