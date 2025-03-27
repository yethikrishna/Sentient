from model.context.base import BaseContextEngine
from model.agents.functions import authenticate_gcalendar
from model.context.runnables import get_gcalendar_context_runnable
from datetime import datetime, timedelta
from dateutil import parser
import asyncio

class GCalendarContextEngine(BaseContextEngine):
    """Context Engine for processing Google Calendar data."""

    def __init__(self, *args, **kwargs):
        print("GCalendarContextEngine.__init__ started")
        super().__init__(*args, **kwargs)
        print("GCalendarContextEngine.__init__ - calling authenticate_gcalendar()")
        self.gcalendar_service = authenticate_gcalendar()
        print("GCalendarContextEngine.__init__ - gcalendar_service authenticated")
        self.category = "gcalendar"
        print(f"GCalendarContextEngine.__init__ - category set to: {self.category}")
        print("GCalendarContextEngine.__init__ finished")

    async def start(self):
        """Start the engine, running periodically every hour."""
        print("GCalendarContextEngine.start started")
        while True:
            print("GCalendarContextEngine.start - running engine iteration")
            await self.run_engine()
            print("GCalendarContextEngine.start - engine iteration finished, sleeping for 3600 seconds")
            await asyncio.sleep(3600)  # Check every hour

    async def fetch_new_data(self):
        """Fetch upcoming events from Google Calendar for the next 24 hours."""
        print("GCalendarContextEngine.fetch_new_data started")
        now = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        print(f"GCalendarContextEngine.fetch_new_data - fetching events from {now} to {time_max}")
        events_result = self.gcalendar_service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        print(f"GCalendarContextEngine.fetch_new_data - fetched {len(events)} events")
        
        # Update context with the last fetch time
        self.context["gcalendar"] = self.context.get("gcalendar", {})
        self.context["gcalendar"]["last_fetched"] = now
        print("GCalendarContextEngine.fetch_new_data - saving context")
        await self.save_context()
        print(f"GCalendarContextEngine.fetch_new_data - returning {len(events)} events")
        print("GCalendarContextEngine.fetch_new_data finished")
        return events

    async def process_new_data(self, new_events):
        """Process new calendar events into summaries."""
        print("GCalendarContextEngine.process_new_data started")
        print(f"GCalendarContextEngine.process_new_data - processing {len(new_events)} new events")
        summaries = []
        for event in new_events:
            event_summary = event.get("summary", "No title")
            start_time = parser.parse(event["start"].get("dateTime", event["start"].get("date")))
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M")
            summary = f"You have an event '{event_summary}' at {start_time_str}"
            summaries.append(summary)
            print(f"GCalendarContextEngine.process_new_data - generated summary: {summary}")
        joined_summaries = "\n".join(summaries)
        print(f"GCalendarContextEngine.process_new_data - joined summaries: {joined_summaries}")
        print("GCalendarContextEngine.process_new_data finished")
        return joined_summaries

    async def get_runnable(self):
        """Return the GCalendar-specific runnable."""
        print("GCalendarContextEngine.get_runnable started")
        runnable = get_gcalendar_context_runnable()
        print(f"GCalendarContextEngine.get_runnable - returning runnable: {runnable}")
        print("GCalendarContextEngine.get_runnable finished")
        return runnable

    async def get_category(self):
        """Return the memory category for GCalendar."""
        print("GCalendarContextEngine.get_category started")
        print(f"GCalendarContextEngine.get_category - returning category: {self.category}")
        print("GCalendarContextEngine.get_category finished")
        return self.category