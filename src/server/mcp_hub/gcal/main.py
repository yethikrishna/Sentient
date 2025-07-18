import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime


from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

# Local imports
from . import auth
from . import prompts
from . import utils
from . import utils

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

# --- Server Initialization ---
mcp = FastMCP(
    name="GCalServer",
    instructions="This server provides tools to interact with the Google Calendar API for managing calendar events.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://gcal-agent-system")
def get_gcal_system_prompt() -> str:
    """Provides the system prompt for the GCal agent."""
    return prompts.gcal_agent_system_prompt

@mcp.prompt(name="gcal_user_prompt_builder")
def build_gcal_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    """Builds a formatted user prompt for the GCal agent."""
    content = prompts.gcal_agent_user_prompt.format(
        query=query,
        username=username,
        previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Definitions ---

@mcp.tool()
async def createEvent(ctx: Context, summary: str, start_time: str, end_time: str, calendar_id: str = "primary", location: Optional[str] = None, description: Optional[str] = None, attendees: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a new calendar event with specified details, time, and attendees."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        user_info = await auth.get_user_info(user_id)
        service = auth.authenticate_gcal(creds)

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": user_info['timezone']},
            "end": {"dateTime": end_time, "timeZone": user_info['timezone']},
        }
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        def _execute_sync_insert():
            return service.events().insert(calendarId=calendar_id, body=event, sendUpdates="all").execute()

        created_event = await asyncio.to_thread(_execute_sync_insert)
        return {"status": "success", "result": f"Event created. View at: {created_event.get('htmlLink')}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def updateEvent(ctx: Context, event_id: str, calendar_id: str = "primary", new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None, new_location: Optional[str] = None, new_description: Optional[str] = None) -> Dict[str, Any]:
    """Modify an existing calendar event by changing any of its properties."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        user_info = await auth.get_user_info(user_id)
        service = auth.authenticate_gcal(creds)

        def _get_event_sync():
            return service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        event_to_update = await asyncio.to_thread(_get_event_sync)

        update_body = {}
        if new_summary: update_body["summary"] = new_summary
        if new_location: update_body["location"] = new_location
        if new_description: update_body["description"] = new_description
        if new_start_time: update_body["start"] = {"dateTime": new_start_time, "timeZone": user_info['timezone']}
        if new_end_time: update_body["end"] = {"dateTime": new_end_time, "timeZone": user_info['timezone']}

        if not update_body:
            return {"status": "failure", "error": "No new information provided to update the event."}

        def _execute_sync_patch():
            return service.events().patch(calendarId=calendar_id, eventId=event_id, body=update_body, sendUpdates="all").execute()

        updated_event = await asyncio.to_thread(_execute_sync_patch)
        return {"status": "success", "result": f"Event updated. View at: {updated_event.get('htmlLink')}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def getCalendars(ctx: Context) -> Dict[str, Any]:
    """List all calendars accessible to the authenticated user."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _execute_sync_list():
            calendar_list = service.calendarList().list().execute()
            return [gcal_utils._simplify_calendar_list_entry(c) for c in calendar_list.get("items", [])]

        simplified_calendars = await asyncio.to_thread(_execute_sync_list)
        return {"status": "success", "result": {"calendars": simplified_calendars}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def createCalendar(ctx: Context, summary: str) -> Dict[str, Any]:
    """Create a new secondary calendar."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        calendar_body = {'summary': summary}

        def _execute_sync_insert():
            return service.calendars().insert(body=calendar_body).execute()

        created_calendar = await asyncio.to_thread(_execute_sync_insert)
        return {"status": "success", "result": {"calendar_id": created_calendar.get("id"), "summary": created_calendar.get("summary")}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def deleteCalendar(ctx: Context, calendar_id: str) -> Dict[str, Any]:
    """Delete a secondary calendar (primary calendar cannot be deleted)."""
    if calendar_id.lower() == "primary":
        return {"status": "failure", "error": "The primary calendar cannot be deleted."}
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _execute_sync_delete():
            service.calendars().delete(calendarId=calendar_id).execute()

        await asyncio.to_thread(_execute_sync_delete)
        return {"status": "success", "result": f"Calendar with ID {calendar_id} has been deleted."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def getEvents(ctx: Context, calendar_id: str = "primary", time_min: Optional[str] = None, time_max: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve calendar events within a specified time range with optional filtering."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _execute_sync_list():
            start_time = time_min or datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId=calendar_id,
                q=query,
                timeMin=start_time,
                timeMax=time_max,
                maxResults=25,
                singleEvents=True, orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            return [gcal_utils._simplify_event(e) for e in events]

        event_list = await asyncio.to_thread(_execute_sync_list)

        if not event_list:
            return {"status": "success", "result": "No events found matching the criteria."}

        return {"status": "success", "result": {"events": event_list}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def deleteEvent(ctx: Context, event_id: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """Remove a calendar event permanently."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)
        
        def _execute_sync_delete():
            service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
            
        await asyncio.to_thread(_execute_sync_delete)
        return {"status": "success", "result": f"Event {event_id} deleted successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def getCalendar(ctx: Context, calendar_id: str = "primary") -> Dict[str, Any]:
    """Get detailed information about a specific calendar."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _execute_sync_get():
            return service.calendars().get(calendarId=calendar_id).execute()

        calendar_data = await asyncio.to_thread(_execute_sync_get)
        return {"status": "success", "result": calendar_data}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def updateCalendar(ctx: Context, calendar_id: str, new_summary: Optional[str] = None, new_description: Optional[str] = None) -> Dict[str, Any]:
    """Update the properties of an existing calendar."""
    if calendar_id.lower() == "primary":
        return {"status": "failure", "error": "The primary calendar's properties cannot be updated this way."}
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _get_calendar_sync():
            return service.calendars().get(calendarId=calendar_id).execute()

        calendar_to_update = await asyncio.to_thread(_get_calendar_sync)

        update_body = {}
        if new_summary:
            update_body["summary"] = new_summary
        if new_description:
            update_body["description"] = new_description

        if not update_body:
            return {"status": "failure", "error": "No new properties provided to update."}

        def _execute_sync_patch():
            return service.calendars().patch(calendarId=calendar_id, body=update_body).execute()

        updated_calendar = await asyncio.to_thread(_execute_sync_patch)
        return {"status": "success", "result": gcal_utils._simplify_calendar_list_entry(updated_calendar)}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def respondToEvent(ctx: Context, event_id: str, response_status: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """Update your response status for a calendar event (accepted, declined, tentative)."""
    valid_statuses = ["accepted", "declined", "tentative"]
    if response_status not in valid_statuses:
        return {"status": "failure", "error": f"Invalid response status. Must be one of: {', '.join(valid_statuses)}"}
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        user_info = await auth.get_user_info(user_id)
        service = auth.authenticate_gcal(creds)

        def _get_event_sync():
            return service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        event = await asyncio.to_thread(_get_event_sync)

        attendees = event.get('attendees', [])
        user_email = user_info.get("email")

        if not user_email:
             return {"status": "failure", "error": "Could not determine user's email to update attendance."}

        attendee_found = False
        for attendee in attendees:
            if attendee.get('email') == user_email:
                attendee['responseStatus'] = response_status
                attendee_found = True
                break

        if not attendee_found:
            return {"status": "failure", "error": "You are not listed as an attendee for this event."}

        def _execute_sync_patch():
            return service.events().patch(calendarId=calendar_id, eventId=event_id, body={'attendees': attendees}, sendUpdates="all").execute()

        updated_event = await asyncio.to_thread(_execute_sync_patch)
        return {"status": "success", "result": f"Your response for '{updated_event.get('summary')}' has been updated to '{response_status}'."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9002))
    
    print(f"Starting GCal MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)