import asyncio
import datetime
from datetime import timezone
import traceback
import logging

from workers.poller.gcalendar.config import POLLING_INTERVALS_WORKER as POLL_CFG
from workers.poller.gcalendar.db import PollerMongoManager
from workers.poller.gcalendar.utils import get_gcalendar_credentials, fetch_events # noqa
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GCalendarPollingService:
    def __init__(self, db_manager: PollerMongoManager):
        self.db_manager = db_manager
        self.service_name = "gcalendar"
        logger.info("GCalendarPollingService Initialized.")

    def _calculate_next_poll_interval(self, user_profile: dict) -> int:
        """Calculates the polling interval based on user activity."""
        # Import these here to avoid circular dependency issues at module load time
        from workers.poller.gcalendar.config import (
            ACTIVE_THRESHOLD_MINUTES_WORKER,
            RECENTLY_ACTIVE_THRESHOLD_HOURS_WORKER,
            PEAK_HOURS_START_WORKER,
            PEAK_HOURS_END_WORKER
        )
        now = datetime.datetime.now(timezone.utc)
        last_active_ts = user_profile.get("userData", {}).get("last_active_timestamp")

        if last_active_ts:
            minutes_since_active = (now - last_active_ts).total_seconds() / 60
            if minutes_since_active <= ACTIVE_THRESHOLD_MINUTES_WORKER:
                return POLL_CFG["ACTIVE_USER_SECONDS"]
            if minutes_since_active <= RECENTLY_ACTIVE_THRESHOLD_HOURS_WORKER * 60:
                return POLL_CFG["RECENTLY_ACTIVE_SECONDS"]

        current_hour = now.hour
        if PEAK_HOURS_START_WORKER <= current_hour < PEAK_HOURS_END_WORKER:
            return POLL_CFG["PEAK_HOURS_SECONDS"]
        else:
            return POLL_CFG["OFF_PEAK_SECONDS"]

    async def _handle_poll_failure(self, user_id: str, polling_state: dict, error_message: str):
        """Handles logic for when a poll fails."""
        failures = polling_state.get("consecutive_failure_count", 0) + 1
        backoff_seconds = min(
            POLL_CFG["MIN_POLL_SECONDS"] * (POLL_CFG["FAILURE_BACKOFF_FACTOR"] ** failures),
            POLL_CFG["MAX_FAILURE_BACKOFF_SECONDS"]
        )
        polling_state["consecutive_failure_count"] = failures
        polling_state["last_successful_poll_status_message"] = error_message
        polling_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=backoff_seconds)
        logger.warning(f"GCalendar user {user_id} experiencing {failures} failures. Backing off for {backoff_seconds}s.")

    async def _run_single_user_poll_cycle(self, user_id: str, polling_state: dict, mode: str):
        logger.info(f"Starting GCalendar poll cycle for user {user_id} in mode '{mode}'")
        updated_state = polling_state.copy()

        try:
            user_profile = await self.db_manager.get_user_profile(user_id)
            if not user_profile:
                logger.error(f"Could not find profile for user {user_id}. Disabling GCalendar polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled, user profile not found."
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return

            all_privacy_filters = user_profile.get("userData", {}).get("privacyFilters", {})
            calendar_filters = {}
            if isinstance(all_privacy_filters, dict):
                calendar_filters = all_privacy_filters.get("gcalendar", {})
            elif isinstance(all_privacy_filters, list):
                # Backward compatibility: old format was a flat list of keywords
                calendar_filters = {"keywords": all_privacy_filters, "emails": []}

            keyword_filters = calendar_filters.get("keywords", [])
            email_filters = [email.lower() for email in calendar_filters.get("emails", [])]
            
            creds = await get_gcalendar_credentials(user_id, self.db_manager)
            if not creds:
                logger.error(f"No valid GCalendar credentials for user {user_id}. Disabling polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled due to auth failure."
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return

            fetched_events = await fetch_events(creds, max_results=10)
            
            processed_count = 0
            for event in fetched_events:
                event_id = event["id"]

                content_to_check = (event.get("summary", "") + " " + event.get("description", "")).lower()
                if any(word.lower() in content_to_check for word in keyword_filters):
                    logger.info(f"Skipping event {event_id} for user {user_id} due to privacy filter match.")
                    # Log as processed to avoid re-checking
                    continue

                if email_filters:
                    attendees = event.get("attendees", [])
                    if attendees:
                        attendee_emails = {attendee.get("email", "").lower() for attendee in attendees if attendee.get("email")}
                        if any(blocked_email in attendee_emails for blocked_email in email_filters):
                            logger.info(f"Skipping event {event_id} for user {user_id} due to attendee filter match.")
                    continue

                # Run the main pre-filter here, before dispatching any tasks
                from workers.proactive.utils import event_pre_filter
                if not event_pre_filter(event, self.service_name, user_profile.get("userData", {}).get("personalInfo", {}).get("email")):
                    logger.info(f"Event {event_id} for user {user_id} was discarded by the main pre-filter.")
                    continue

                if not await self.db_manager.is_item_processed(user_id, self.service_name, event_id):
                    from workers.tasks import cud_memory_task, proactive_reasoning_pipeline, execute_triggered_task

                    if mode == 'proactivity':
                        # Construct a representative text string from the event data
                        source_text = f"Event: {event.get('summary', '')}\nDescription: {event.get('description', '')}"
                        # 1. Send to memory
                        # cud_memory_task.delay(
                        #     user_id=user_id,
                        #     information=source_text,
                        #     source=self.service_name
                        # ) # NOT SENDING TO MEMORY FOR NOW
                        # 2. Send to proactive reasoning
                        proactive_reasoning_pipeline.delay(
                            user_id=user_id,
                            event_type=self.service_name,
                            event_data=event
                        )
                    elif mode == 'triggers':
                        # 3. Check for and execute triggered tasks
                        execute_triggered_task.delay(
                            user_id=user_id, source=self.service_name,
                            event_type="new_event", event_data=event
                        )
                    await self.db_manager.log_processed_item(user_id, self.service_name, event_id)
                    processed_count += 1

            if processed_count > 0:
                logger.info(f"Dispatched {processed_count} new GCalendar events to the processing pipeline for user {user_id}.") # noqa
            
            updated_state["last_successful_poll_status_message"] = f"Successfully polled. Found {len(fetched_events)} events, dispatched {processed_count} new." # noqa
            updated_state["consecutive_failure_count"] = 0
            updated_state["error_backoff_until_timestamp"] = None

        except HttpError as he:
            logger.error(f"GCalendar API Error for user {user_id}: {he}")
            await self._handle_poll_failure(user_id, updated_state, f"API Error: {str(he)}. Status: {he.resp.status if he.resp else 'N/A'}")
            if he.resp and (he.resp.status == 401 or he.resp.status == 403):
                updated_state["is_enabled"] = False
                logger.error(f"Disabling GCalendar polling for user {user_id} due to {he.resp.status} error.")
        except Exception as e:
            logger.error(f"General error during GCalendar poll for user {user_id}: {e}", exc_info=True)
        
        finally:
            failures = updated_state.get("consecutive_failure_count", 0)
            if failures > 0:
                if failures >= POLL_CFG["MAX_CONSECUTIVE_FAILURES"]:
                    logger.error(f"User {user_id} reached max failures for GCalendar. Disabling polling.")
                    updated_state["is_enabled"] = False
                    updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
            else:
                next_interval = self._calculate_next_poll_interval(user_profile or {})
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=next_interval)
            
            updated_state["is_currently_polling"] = False
            await self.db_manager.update_polling_state(user_id, self.service_name, mode, updated_state)
            logger.info(f"GCalendar poll cycle finished for user {user_id}. Next poll at {updated_state['next_scheduled_poll_time']}.")

    async def run_scheduler_loop(self):
        logger.info(f"GCalendar scheduler starting loop (interval: {POLL_CFG['SCHEDULER_TICK_SECONDS']}s)")
        # await self.db_manager.initialize_indices_if_needed()
        # await self.db_manager.reset_stale_polling_locks(self.service_name)

        while True:
            try:
                due_tasks_states = await self.db_manager.get_due_polling_tasks_for_service(self.service_name, 'proactivity')
                
                if due_tasks_states:
                    logger.info(f"Scheduler: Found {len(due_tasks_states)} due GCalendar polling tasks.")
                    for task_state in due_tasks_states:
                        user_id = task_state["user_id"]
                        locked_task_state = await self.db_manager.set_polling_status_and_get(user_id, self.service_name, 'proactivity')
                        if locked_task_state:
                            logger.info(f"Scheduler: Acquired lock for {user_id} (GCal). Triggering poll cycle.")
                            asyncio.create_task(self._run_single_user_poll_cycle(user_id, locked_task_state, 'proactivity'))
            except Exception as e:
                logger.error(f"Error in GCalendar scheduler loop: {e}", exc_info=True)
            
            await asyncio.sleep(POLL_CFG["SCHEDULER_TICK_SECONDS"])