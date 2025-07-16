import asyncio
import datetime
from datetime import timezone
import traceback
import logging

from workers.poller.gcalendar.config import POLLING_INTERVALS_WORKER as POLL_CFG
from workers.poller.gcalendar.db import PollerMongoManager
from workers.poller.gcalendar.utils import get_gcalendar_credentials, fetch_events
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

    async def _run_single_user_poll_cycle(self, user_id: str, polling_state: dict):
        logger.info(f"Starting GCalendar poll cycle for user {user_id}")
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
            calendar_filters = all_privacy_filters.get("gcalendar", {})
            keyword_filters = calendar_filters.get("keywords", [])
            
            creds = await get_gcalendar_credentials(user_id, self.db_manager)
            if not creds:
                logger.error(f"No valid GCalendar credentials for user {user_id}. Disabling polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled due to auth failure."
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return

            last_updated_iso = polling_state.get("last_successful_poll_timestamp_iso")
            events, new_last_updated_iso = await fetch_events(creds, last_updated_iso, max_results=50)
            
            processed_count = 0
            for event in events:
                event_id = event["id"]

                content_to_check = (event.get("summary", "") + " " + event.get("description", "")).lower()
                if any(word.lower() in content_to_check for word in keyword_filters):
                    logger.info(f"Skipping event {event_id} for user {user_id} due to privacy filter match.")
                    # Log as processed to avoid re-checking
                    continue

                if not await self.db_manager.is_item_processed(user_id, self.service_name, event_id):
                    # Dispatch a Celery task for each new event
                    from workers.tasks import extract_from_context
                    extract_from_context.delay(user_id, self.service_name, event_id, event)
                    await self.db_manager.log_processed_item(user_id, self.service_name, event_id)
                    processed_count += 1

            if processed_count > 0:
                logger.info(f"Processed and sent {processed_count} new GCalendar events to Kafka for user {user_id}.")
            
            updated_state["last_successful_poll_timestamp_iso"] = new_last_updated_iso
            updated_state["last_successful_poll_status_message"] = f"Successfully polled. Found {len(events)} updated events, processed {processed_count} new."
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
            await self.db_manager.update_polling_state(user_id, self.service_name, updated_state)
            logger.info(f"GCalendar poll cycle finished for user {user_id}. Next poll at {updated_state['next_scheduled_poll_time']}.")

    async def run_scheduler_loop(self):
        logger.info(f"GCalendar scheduler starting loop (interval: {POLL_CFG['SCHEDULER_TICK_SECONDS']}s)")
        await self.db_manager.initialize_indices_if_needed()
        await self.db_manager.reset_stale_polling_locks(self.service_name)

        while True:
            try:
                due_tasks_states = await self.db_manager.get_due_polling_tasks_for_service(self.service_name)
                
                if due_tasks_states:
                    logger.info(f"Scheduler: Found {len(due_tasks_states)} due GCalendar polling tasks.")
                    for task_state in due_tasks_states:
                        user_id = task_state["user_id"]
                        locked_task_state = await self.db_manager.set_polling_status_and_get(user_id, self.service_name)
                        if locked_task_state:
                            logger.info(f"Scheduler: Acquired lock for {user_id} (GCal). Triggering poll cycle.")
                            asyncio.create_task(self._run_single_user_poll_cycle(user_id, locked_task_state))
            except Exception as e:
                logger.error(f"Error in GCalendar scheduler loop: {e}", exc_info=True)
            
            await asyncio.sleep(POLL_CFG["SCHEDULER_TICK_SECONDS"])