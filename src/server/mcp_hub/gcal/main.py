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

# Conditionally load .env for local development
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
# Each tool uses asyncio.to_thread to run synchronous Google API calls without blocking.

@mcp.tool()
async def list_upcoming_events(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Lists the next upcoming events from the user's primary calendar."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)
        
        def _execute_sync_list():
            now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            events_result = service.events().list(
                calendarId="primary", timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            
            event_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list.append(f"- {event['summary']} (at {start})")
            return "\n".join(event_list) if event_list else "No upcoming events found."

        result_text = await asyncio.to_thread(_execute_sync_list)
        return {"status": "success", "result": result_text}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def add_event(ctx: Context, summary: str, start_time: str, end_time: str, location: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Adds a new event to the primary calendar."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        user_timezone = await auth.get_user_timezone(user_id) # Fetch timezone
        service = auth.authenticate_gcal(creds)
        
        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": user_timezone},
            "end": {"dateTime": end_time, "timeZone": user_timezone},
        }

        def _execute_sync_insert():
            return service.events().insert(calendarId="primary", body=event).execute()

        created_event = await asyncio.to_thread(_execute_sync_insert)
        return {"status": "success", "result": f"Event created successfully. View at: {created_event.get('htmlLink')}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def search_events(ctx: Context, query: str, time_min: Optional[str] = None, time_max: Optional[str] = None) -> Dict[str, Any]:
    """Searches for events matching a query within an optional time range."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)

        def _execute_sync_search():
            start_time = time_min or datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId="primary", q=query, timeMin=start_time, timeMax=time_max,
                singleEvents=True, orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            
            event_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list.append({"summary": event['summary'], "id": event['id'], "start_time": start})
            return event_list

        search_result = await asyncio.to_thread(_execute_sync_search)
        if not search_result:
            return {"status": "success", "result": f"No events found matching '{query}'."}
            
        return {"status": "success", "result": {"events_found": search_result}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def delete_event(ctx: Context, query: str) -> Dict[str, Any]:
    """Finds an event by query and deletes it."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gcal(creds)
        
        match = await utils.find_event_by_query(service, query)
        if match["status"] != "success":
            return match
        
        event_id = match["event"]["id"]
        
        def _execute_sync_delete():
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            
        await asyncio.to_thread(_execute_sync_delete)
        return {"status": "success", "result": f"Event '{match['event']['summary']}' deleted successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def update_event(ctx: Context, query: str, new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None, new_location: Optional[str] = None) -> Dict[str, Any]:
    """Finds an event by query and updates its details."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        user_timezone = await auth.get_user_timezone(user_id) # Fetch timezone
        service = auth.authenticate_gcal(creds)

        match = await utils.find_event_by_query(service, query)
        if match["status"] != "success":
            return match
        
        event_to_update = match["event"]
        event_id = event_to_update["id"]

        # Update fields if new values are provided
        if new_summary: event_to_update["summary"] = new_summary
        if new_location: event_to_update["location"] = new_location
        if new_start_time: event_to_update["start"] = {"dateTime": new_start_time, "timeZone": user_timezone}
        if new_end_time: event_to_update["end"] = {"dateTime": new_end_time, "timeZone": user_timezone}
        
        def _execute_sync_update():
            return service.events().update(calendarId="primary", eventId=event_id, body=event_to_update).execute()

        updated_event = await asyncio.to_thread(_execute_sync_update)
        return {"status": "success", "result": f"Event updated. View at: {updated_event.get('htmlLink')}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9002))
    
    print(f"Starting GCal MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)