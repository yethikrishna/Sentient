# src/server/workers/pollers/gmail/service.py
import asyncio
import datetime
from datetime import timezone
import traceback
import time # For sleep
import logging # Import logging

from .config import POLLING_INTERVALS_WORKER as POLL_CFG, GMAIL_POLL_KAFKA_TOPIC, ACTIVE_THRESHOLD_MINUTES_WORKER, RECENTLY_ACTIVE_THRESHOLD_HOURS_WORKER, PEAK_HOURS_START_WORKER, PEAK_HOURS_END_WORKER
from .db import PollerMongoManager
from .utils import GmailKafkaProducer, get_gmail_credentials, fetch_emails # AES decryption is in get_gmail_credentials
from googleapiclient.errors import HttpError # Import HttpError

logger = logging.getLogger(__name__)

class GmailPollingService:
    def __init__(self, db_manager: PollerMongoManager):
        self.db_manager = db_manager
        self.service_name = "gmail"
        logger.info("GmailPollingService Initialized.")

    def _calculate_next_poll_interval(self, user_profile: dict) -> int:
        """Calculates the polling interval based on user activity."""
        now = datetime.datetime.now(timezone.utc)
        last_active_ts = user_profile.get("userData", {}).get("last_active_timestamp")

        if last_active_ts:
            minutes_since_active = (now - last_active_ts).total_seconds() / 60
            if minutes_since_active <= ACTIVE_THRESHOLD_MINUTES_WORKER:
                return POLL_CFG["ACTIVE_USER_SECONDS"]
            if minutes_since_active <= RECENTLY_ACTIVE_THRESHOLD_HOURS_WORKER * 60:
                return POLL_CFG["RECENTLY_ACTIVE_SECONDS"]

        # Peak hours logic
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
        logger.warning(f"User {user_id} experiencing {failures} failures. Backing off for {backoff_seconds}s.")

    async def _run_single_user_poll_cycle(self, user_id: str, polling_state: dict):
        logger.info(f"Starting poll cycle for user {user_id}")
        updated_state = polling_state.copy() # To modify and save later
        new_data_found = False

        try:
            user_profile = await self.db_manager.get_user_profile(user_id)
            if not user_profile:
                logger.error(f"Could not find profile for user {user_id}. Disabling polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled, user profile not found."
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return

            privacy_filters = user_profile.get("userData", {}).get("privacyFilters", [])
            creds = await get_gmail_credentials(user_id, self.db_manager)
            if not creds:
                logger.error(f"No valid Gmail credentials for user {user_id}. Disabling polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled due to auth failure."
                updated_state["consecutive_failure_count"] = (updated_state.get("consecutive_failure_count", 0) + 1) % (POLL_CFG["MAX_CONSECUTIVE_FAILURES"] +1) # to prevent infinite loop
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return

            last_ts_unix = polling_state.get("last_successful_poll_timestamp_unix")
            emails = await fetch_emails(creds, last_ts_unix, max_results=25) # Fetch up to 25 new emails
            
            highest_email_ts_ms = 0
            processed_count = 0

            batch_payloads = []
            for email in emails:
                email_item_id = email["id"]

                content_to_check = (email.get("subject", "") + " " + email.get("body", "")).lower()
                if any(word.lower() in content_to_check for word in privacy_filters):
                    logger.info(f"Skipping email {email['id']} for user {user_id} due to privacy filter match.")
                    await self.db_manager.log_processed_item(user_id, self.service_name, email_item_id)
                    continue

                if not await self.db_manager.is_item_processed(user_id, self.service_name, email_item_id):
                    # Send to Kafka
                    kafka_payload = {
                        "user_id": user_id,
                        "service_name": self.service_name,
                        "event_type": "new_email",
                        "event_id": email_item_id,
                        "data": email, # Full email data
                        "timestamp_utc": datetime.datetime.fromtimestamp(email["timestamp_ms"] / 1000, tz=timezone.utc)
                    }
                    batch_payloads.append(kafka_payload)
                
                if email["timestamp_ms"] > highest_email_ts_ms:
                    highest_email_ts_ms = email["timestamp_ms"]
            
            if batch_payloads:
                success = await GmailKafkaProducer.send_gmail_data(batch_payloads, user_id)
                if success:
                    for payload in batch_payloads:
                        await self.db_manager.log_processed_item(user_id, self.service_name, payload["event_id"])
                    processed_count = len(batch_payloads)
                    new_data_found = True

            if processed_count > 0:
                logger.info(f"Processed and sent {processed_count} new emails to Kafka for user {user_id}.")
            
            # Update last processed timestamp if new emails were found and processed
            if highest_email_ts_ms > 0 : # and new_data_found (implicit if highest_email_ts_ms is updated)
                 updated_state["last_successful_poll_timestamp_unix"] = highest_email_ts_ms // 1000 # Store as Unix seconds
            
            updated_state["last_successful_poll_status_message"] = f"Successfully polled. Found {len(emails)} messages, processed {processed_count} new."
            updated_state["consecutive_failure_count"] = 0
            updated_state["error_backoff_until_timestamp"] = None

        except HttpError as he: # Catch Google API specific errors
            logger.error(f"Google API Error for user {user_id}: {he}")
            await self._handle_poll_failure(user_id, updated_state, f"API Error: {str(he)}. Status: {he.resp.status if he.resp else 'N/A'}")
            if he.resp and (he.resp.status == 401 or he.resp.status == 403): # Auth error
                updated_state["is_enabled"] = False # Disable polling
                logger.error(f"Disabling Gmail polling for user {user_id} due to {he.resp.status} error.")
        except Exception as e:
            logger.error(f"General error during poll for user {user_id}: {e}", exc_info=True)
            traceback.print_exc()
            await self._handle_poll_failure(user_id, updated_state, f"Error: {str(e)}")
        
        finally:
            failures = updated_state.get("consecutive_failure_count", 0)
            if failures > 0 :
                if failures >= POLL_CFG["MAX_CONSECUTIVE_FAILURES"]:
                    logger.error(f"User {user_id} reached max failures. Disabling polling.")
                    updated_state["is_enabled"] = False # Disable after too many failures
                    updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1) # Check much later
            else:
                next_interval = self._calculate_next_poll_interval(user_profile or {})
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=next_interval)
            
            updated_state["is_currently_polling"] = False # Release lock
            await self.db_manager.update_polling_state(user_id, self.service_name, updated_state)
            logger.info(f"Poll cycle finished for user {user_id}. Next poll at {updated_state['next_scheduled_poll_time']}.")


    async def run_scheduler_loop(self):
        """
        Periodically checks MongoDB for users whose Gmail polling is due.
        """
        logger.info(f"Scheduler starting loop (interval: {POLL_CFG['SCHEDULER_TICK_SECONDS']}s)")
        await self.db_manager.initialize_indices_if_needed()
        await self.db_manager.reset_stale_polling_locks(self.service_name) # Reset locks for "gmail"

        while True:
            try:
                due_tasks_states = await self.db_manager.get_due_polling_tasks_for_service(self.service_name)
                
                if not due_tasks_states:
                    # logger.debug("Scheduler: No due Gmail polling tasks.")
                    pass
                else:
                    logger.info(f"Scheduler: Found {len(due_tasks_states)} due Gmail polling tasks.")

                for task_state in due_tasks_states:
                    user_id = task_state["user_id"]
                    
                    # Try to acquire a lock on the task
                    locked_task_state = await self.db_manager.set_polling_status_and_get(user_id, self.service_name)
                    
                    if locked_task_state:
                        logger.info(f"Scheduler: Acquired lock for {user_id}. Triggering poll cycle.")
                        # Run the poll cycle in a new task to not block the scheduler loop
                        asyncio.create_task(self._run_single_user_poll_cycle(user_id, locked_task_state))
                    else:
                        logger.debug(f"Scheduler: Could not acquire lock for {user_id} (already processing or no longer due).")

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                traceback.print_exc()
            
            await asyncio.sleep(POLL_CFG["SCHEDULER_TICK_SECONDS"])