import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


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
    instructions="Provides a comprehensive suite of tools to manage Google Calendar, including creating, updating, deleting, and searching for events and calendars.",
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


# --- Helper for Tool Execution ---
async def _execute_tool(ctx: Context, func, *args, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        # Always fetch user info now, which includes timezone and privacy filters
        user_info = await auth.get_user_info(user_id)
        kwargs['user_info'] = user_info

        # Run the synchronous function in a separate thread
        result = await asyncio.to_thread(func, service, *args, **kwargs)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Definitions ---

@mcp.tool()
async def createEvent(ctx: Context, summary: str, start_time: str, end_time: str, calendar_id: str = "primary", location: Optional[str] = None, description: Optional[str] = None, attendees: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Creates a new event on a specified calendar. Requires a summary (title), start time, and end time in ISO 8601 format. Optionally accepts location, description, and a list of attendee emails.
    """
    def _create_event_sync(service, user_info: Dict, **kwargs):
        event = {
            "summary": kwargs.get('summary'),
            "location": kwargs.get('location'),
            "description": kwargs.get('description'),
            "start": {"dateTime": kwargs.get('start_time'), "timeZone": user_info['timezone']},
            "end": {"dateTime": kwargs.get('end_time'), "timeZone": user_info['timezone']},
        }
        attendees_list = kwargs.get('attendees')
        if attendees_list:
            event["attendees"] = [{"email": email} for email in attendees_list]
        
        created_event = service.events().insert(calendarId=kwargs.get('calendar_id', 'primary'), body=event, sendUpdates="all").execute()
        return f"Event created. View at: {created_event.get('htmlLink')}"

    return await _execute_tool(ctx, _create_event_sync, summary=summary, start_time=start_time, end_time=end_time, calendar_id=calendar_id, location=location, description=description, attendees=attendees)


@mcp.tool()
async def updateEvent(ctx: Context, event_id: str, calendar_id: str = "primary", new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None, new_location: Optional[str] = None, new_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates an existing calendar event. Requires the `event_id` and at least one new property to change, such as summary, start/end times, location, or description.
    """
    def _update_event_sync(service, user_info: Dict, **kwargs):
        event_to_update = service.events().get(calendarId=kwargs.get('calendar_id'), eventId=kwargs.get('event_id')).execute()

        new_summary, new_start_time, new_end_time, new_location, new_description = kwargs.get('new_summary'), kwargs.get('new_start_time'), kwargs.get('new_end_time'), kwargs.get('new_location'), kwargs.get('new_description')
        
        update_body = {}
        if new_summary: update_body["summary"] = new_summary
        if new_location: update_body["location"] = new_location
        if new_description: update_body["description"] = new_description
        if new_start_time: update_body["start"] = {"dateTime": new_start_time, "timeZone": user_info['timezone']}
        if new_end_time: update_body["end"] = {"dateTime": new_end_time, "timeZone": user_info['timezone']}

        if not update_body:
            raise Exception("No new information provided to update the event.")

        updated_event = service.events().patch(calendarId=kwargs.get('calendar_id'), eventId=kwargs.get('event_id'), body=update_body, sendUpdates="all").execute()
        return f"Event updated. View at: {updated_event.get('htmlLink')}"

    return await _execute_tool(ctx, _update_event_sync, event_id=event_id, calendar_id=calendar_id, new_summary=new_summary, new_start_time=new_start_time, new_end_time=new_end_time, new_location=new_location, new_description=new_description)

@mcp.tool()
async def getCalendars(ctx: Context) -> Dict[str, Any]:
    """
    Retrieves a list of all calendars the user has access to, returning their summary, ID, and access role.
    """
    def _get_calendars_sync(service, user_info: Dict):
        calendar_list = service.calendarList().list().execute()
        simplified = [utils._simplify_calendar_list_entry(c) for c in calendar_list.get("items", [])]
        return {"calendars": simplified}
    
    return await _execute_tool(ctx, _get_calendars_sync)

@mcp.tool()
async def createCalendar(ctx: Context, summary: str) -> Dict[str, Any]:
    """
    Creates a new secondary calendar with a given summary (title).
    """
    def _create_calendar_sync(service, user_info: Dict, summary: str):

        calendar_body = {'summary': summary}

        created_calendar = service.calendars().insert(body=calendar_body).execute()
        return {"calendar_id": created_calendar.get("id"), "summary": created_calendar.get("summary")}
    return await _execute_tool(ctx, _create_calendar_sync, summary=summary)

@mcp.tool()
async def deleteCalendar(ctx: Context, calendar_id: str) -> Dict[str, Any]:
    """
    Deletes a secondary calendar. Requires the `calendar_id`. The primary calendar cannot be deleted.
    """
    if calendar_id.lower() == "primary":
        return {"status": "failure", "error": "The primary calendar cannot be deleted."}
    def _delete_calendar_sync(service, user_info: Dict, calendar_id: str):
        service.calendars().delete(calendarId=calendar_id).execute()
        return f"Calendar with ID {calendar_id} has been deleted."

    return await _execute_tool(ctx, _delete_calendar_sync, calendar_id=calendar_id)

@mcp.tool()
async def getEvents(ctx: Context, calendar_id: str = "primary", time_min: Optional[str] = None, time_max: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """
    Searches for events on a specified calendar. Can be filtered by a time range (`time_min`, `time_max`) and a text query. Returns a list of simplified event objects.
    """
    def _get_events_sync(service, user_info: Dict, calendar_id: str, time_min: Optional[str], time_max: Optional[str], query: Optional[str]):
        start_time = time_min or datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            timeMin=start_time,
            timeMax=time_max,
            maxResults=50, # Fetch more to account for filtering
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        
        # Apply privacy filters
        filters = user_info.get("privacy_filters", {})
        keyword_filters = filters.get("keywords", [])
        email_filters = [e.lower() for e in filters.get("emails", [])]
        
        filtered_events = []
        for event in events:
            is_filtered = False
            
            content_to_check = (event.get("summary", "") + " " + event.get("description", "")).lower()
            if any(kw.lower() in content_to_check for kw in keyword_filters):
                is_filtered = True

            if not is_filtered and email_filters:
                attendees = event.get("attendees", [])
                if attendees:
                    attendee_emails = {a.get("email", "").lower() for a in attendees if a.get("email")}
                    if any(blocked_email in attendee_emails for blocked_email in email_filters):
                        is_filtered = True
            
            if not is_filtered:
                filtered_events.append(utils._simplify_event(event))
        return filtered_events

    result = await _execute_tool(ctx, _get_events_sync, calendar_id=calendar_id, time_min=time_min, time_max=time_max, query=query)
    
    if result["status"] == "success":
        if not result["result"]:
            result["result"] = "No events found matching the criteria."
        else:
            result["result"] = {"events": result["result"]}
            
    return result

@mcp.tool()
async def deleteEvent(ctx: Context, event_id: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """
    Permanently deletes an event from a calendar. Requires the `event_id`.
    """
    def _delete_event_sync(service, user_info: Dict, event_id: str, calendar_id: str):
        service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
        return f"Event {event_id} deleted successfully."
    
    return await _execute_tool(ctx, _delete_event_sync, event_id=event_id, calendar_id=calendar_id)

@mcp.tool()
async def getCalendar(ctx: Context, calendar_id: str = "primary") -> Dict[str, Any]:
    """
    Retrieves detailed information for a single calendar by its `calendar_id`.
    """
    def _get_calendar_sync(service, user_info: Dict, calendar_id: str):
        return service.calendars().get(calendarId=calendar_id).execute()
    
    return await _execute_tool(ctx, _get_calendar_sync, calendar_id=calendar_id)

@mcp.tool()
async def updateCalendar(ctx: Context, calendar_id: str, new_summary: Optional[str] = None, new_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates the summary or description of a secondary calendar. Requires the `calendar_id`.
    """
    if calendar_id.lower() == "primary":
        return {"status": "failure", "error": "The primary calendar's properties cannot be updated this way."}
    def _update_calendar_sync(service, user_info: Dict, calendar_id: str, new_summary: Optional[str], new_description: Optional[str]):
        calendar_to_update = service.calendars().get(calendarId=calendar_id).execute()

        update_body = {}
        if new_summary:
            update_body["summary"] = new_summary
        if new_description:
            update_body["description"] = new_description

        if not update_body:
            raise Exception("No new properties provided to update.")

        updated_calendar = service.calendars().patch(calendarId=calendar_id, body=update_body).execute()
        return utils._simplify_calendar_list_entry(updated_calendar)
    
    return await _execute_tool(ctx, _update_calendar_sync, calendar_id=calendar_id, new_summary=new_summary, new_description=new_description)

@mcp.tool()
async def respondToEvent(ctx: Context, event_id: str, response_status: str, calendar_id: str = "primary") -> Dict[str, Any]:
    """
    Sets the user's attendance status for an event they are invited to. Requires the `event_id` and a `response_status` ('accepted', 'declined', 'tentative').
    """
    def _respond_to_event_sync(service, user_info: Dict, event_id: str, response_status: str, calendar_id: str):
        valid_statuses = ["accepted", "declined", "tentative"]
        if response_status not in valid_statuses:
            raise Exception(f"Invalid response status. Must be one of: {', '.join(valid_statuses)}")

        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        attendees = event.get('attendees', [])
        user_email = user_info.get("email")

        if not user_email:
            raise Exception("Could not determine user's email to update attendance.")

        attendee_found = False
        for attendee in attendees:
            if attendee.get('email') == user_email:
                attendee['responseStatus'] = response_status
                attendee_found = True
                break

        if not attendee_found:
            raise Exception("You are not listed as an attendee for this event.")

        updated_event = service.events().patch(calendarId=calendar_id, eventId=event_id, body={'attendees': attendees}, sendUpdates="all").execute()
        return f"Your response for '{updated_event.get('summary')}' has been updated to '{response_status}'."
    
    return await _execute_tool(ctx, _respond_to_event_sync, event_id=event_id, response_status=response_status, calendar_id=calendar_id)

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9002))
    
    print(f"Starting GCal MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)