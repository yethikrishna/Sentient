# server/mcp_hub/gcal/utils.py

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from googleapiclient.discovery import Resource

def _find_event_sync(service: Resource, query: str) -> Dict[str, Any]:
    """Synchronous part of finding an event."""
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            q=query,
            timeMin=now,
            maxResults=1,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        return {"status": "failure", "error": f"No upcoming event found matching query: '{query}'"}
    
    return {"status": "success", "event": events[0]}

async def find_event_by_query(service: Resource, query: str) -> Dict[str, Any]:
    """
    Finds the soonest upcoming event that matches a text query.

    Args:
        service (Resource): Authenticated Google Calendar API service.
        query (str): The search query for the event summary/description.

    Returns:
        Dict[str, Any]: A dictionary with the status and the found event object.
    """
    return await asyncio.to_thread(_find_event_sync, service, query)
def _simplify_calendar_list_entry(calendar: Dict) -> Dict:
    return {
        "id": calendar.get("id"),
        "summary": calendar.get("summary"),
        "accessRole": calendar.get("accessRole"),
        "primary": calendar.get("primary", False)
    }

def _simplify_event(event: Dict) -> Dict:
    return {
        "id": event.get("id"),
        "summary": event.get("summary"),
        "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
        "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
        "status": event.get("status"),
        "url": event.get("htmlLink"),
        "attendees": [a.get("email") for a in event.get("attendees", []) if a.get("email")]
    }
