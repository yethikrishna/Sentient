# src/server/workers/pollers/gmail/service.py
import asyncio
import datetime
from datetime import timezone
import traceback
import time # For sleep

from .config import POLLING_INTERVALS_WORKER as POLL_CFG, GMAIL_POLL_KAFKA_TOPIC
from .db_utils import PollerMongoManager
from .utils import GmailKafkaProducer, get_gmail_credentials, fetch_emails # AES decryption is in get_gmail_credentials
from googleapiclient.errors import HttpError # Import HttpError

class GmailPollingService:
    def __init__(self, db_manager: PollerMongoManager):
        self.db_manager = db_manager
        self.service_name = "gmail"
        print(f"[{datetime.datetime.now()}] [GmailPollingService] Initialized.")

    async def _run_single_user_poll_cycle(self, user_id: str, polling_state: dict):
        print(f"[{datetime.datetime.now()}] [GmailPollingService] Starting poll cycle for user {user_id}")
        updated_state = polling_state.copy() # To modify and save later
        new_data_found = False

        try:
            creds = await get_gmail_credentials(user_id, self.db_manager)
            if not creds:
                print(f"[{datetime.datetime.now()}] [GmailPollingService_AUTH_ERROR] No valid Gmail credentials for user {user_id}. Disabling polling.")
                updated_state["is_enabled"] = False
                updated_state["last_successful_poll_status_message"] = "Disabled due to auth failure."
                updated_state["consecutive_failure_count"] = (updated_state.get("consecutive_failure_count", 0) + 1) % (POLL_CFG["MAX_CONSECUTIVE_FAILURES"] +1) # to prevent infinite loop
                # Optionally schedule a check much later or require manual re-enable
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1)
                return new_data_found, updated_state # Return immediately

            last_ts_unix = polling_state.get("last_successful_poll_timestamp_unix")
            emails = await fetch_emails(creds, last_ts_unix, max_results=20) # Fetch up to 20 new emails
            
            highest_email_ts_ms = 0
            processed_count = 0

            for email in emails:
                email_item_id = email["id"]
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
                    if await GmailKafkaProducer.send_gmail_data(kafka_payload, user_id):
                        await self.db_manager.log_processed_item(user_id, self.service_name, email_item_id)
                        processed_count += 1
                        new_data_found = True
                    else:
                        print(f"[{datetime.datetime.now()}] [GmailPollingService_KAFKA_ERROR] Failed to send email {email_item_id} to Kafka for user {user_id}.")
                        # Decide if this is a critical error that should stop further processing for this user in this cycle
                
                if email["timestamp_ms"] > highest_email_ts_ms:
                    highest_email_ts_ms = email["timestamp_ms"]
            
            if processed_count > 0:
                print(f"[{datetime.datetime.now()}] [GmailPollingService] Processed and sent {processed_count} new emails to Kafka for user {user_id}.")
            
            # Update last processed timestamp if new emails were found and processed
            if highest_email_ts_ms > 0 : # and new_data_found (implicit if highest_email_ts_ms is updated)
                 updated_state["last_successful_poll_timestamp_unix"] = highest_email_ts_ms // 1000 # Store as Unix seconds
            
            updated_state["last_successful_poll_status_message"] = f"Successfully polled. Found {len(emails)} messages, processed {processed_count} new."
            updated_state["consecutive_failure_count"] = 0
            updated_state["error_backoff_until_timestamp"] = None

        except HttpError as he: # Catch Google API specific errors
            print(f"[{datetime.datetime.now()}] [GmailPollingService_API_ERROR] User {user_id}: {he}")
            updated_state["last_successful_poll_status_message"] = f"API Error: {str(he)}. Status: {he.resp.status if he.resp else 'N/A'}"
            updated_state["consecutive_failure_count"] = polling_state.get("consecutive_failure_count", 0) + 1
            if he.resp and (he.resp.status == 401 or he.resp.status == 403): # Auth error
                updated_state["is_enabled"] = False # Disable polling
                print(f"[{datetime.datetime.now()}] [GmailPollingService_AUTH_ERROR] Disabling Gmail polling for user {user_id} due to {he.resp.status} error.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPollingService_ERROR] User {user_id}: {e}")
            traceback.print_exc()
            updated_state["last_successful_poll_status_message"] = f"Error: {str(e)}"
            updated_state["consecutive_failure_count"] = polling_state.get("consecutive_failure_count", 0) + 1
        
        finally:
            # Calculate next poll time (simplified, a more complex adaptive logic was in original)
            # For dummy, just set a fixed interval or simple backoff.
            failures = updated_state.get("consecutive_failure_count", 0)
            if failures > 0:
                backoff_seconds = min(
                    POLL_CFG["MIN_POLL_SECONDS"] * (POLL_CFG["FAILURE_BACKOFF_FACTOR"] ** failures),
                    POLL_CFG["MAX_FAILURE_BACKOFF_SECONDS"]
                )
                if failures >= POLL_CFG["MAX_CONSECUTIVE_FAILURES"]:
                    print(f"[{datetime.datetime.now()}] [GmailPollingService_MAX_FAILURES] User {user_id} reached max failures. Disabling polling.")
                    updated_state["is_enabled"] = False # Disable after too many failures
                    updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=1) # Check much later
                else:
                    updated_state["error_backoff_until_timestamp"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=backoff_seconds)
                    updated_state["next_scheduled_poll_time"] = updated_state["error_backoff_until_timestamp"]
                    print(f"[{datetime.datetime.now()}] [GmailPollingService_BACKOFF] User {user_id} experiencing {failures} failures. Backing off for {backoff_seconds}s.")
            else:
                # Simple fixed interval for successful polls for now
                updated_state["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=POLL_CFG["ACTIVE_USER_SECONDS"])
            
            updated_state["is_currently_polling"] = False # Release lock
            await self.db_manager.update_polling_state(user_id, self.service_name, updated_state)
            print(f"[{datetime.datetime.now()}] [GmailPollingService] Poll cycle finished for user {user_id}. Next poll at {updated_state['next_scheduled_poll_time']}.")
        
        return new_data_found, updated_state


    async def run_scheduler_loop(self):
        """
        Periodically checks MongoDB for users whose Gmail polling is due.
        """
        print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler] Starting loop (interval: {POLL_CFG['SCHEDULER_TICK_SECONDS']}s)")
        await self.db_manager.initialize_indices_if_needed()
        await self.db_manager.reset_stale_polling_locks(self.service_name) # Reset locks for "gmail"

        while True:
            try:
                due_tasks_states = await self.db_manager.get_due_polling_tasks_for_service(self.service_name)
                
                if not due_tasks_states:
                    # print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler] No due Gmail polling tasks.")
                    pass
                else:
                    print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler] Found {len(due_tasks_states)} due Gmail polling tasks.")

                for task_state in due_tasks_states:
                    user_id = task_state["user_id"]
                    
                    # Try to acquire a lock on the task
                    locked_task_state = await self.db_manager.set_polling_status_and_get(user_id, self.service_name)
                    
                    if locked_task_state:
                        print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler] Acquired lock for {user_id}. Triggering poll cycle.")
                        # Run the poll cycle in a new task to not block the scheduler loop
                        asyncio.create_task(self._run_single_user_poll_cycle(user_id, locked_task_state))
                    # else:
                        # print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler] Could not acquire lock for {user_id} (already processing or no longer due).")

            except Exception as e:
                print(f"[{datetime.datetime.now()}] [GmailPollingService_Scheduler_ERROR] Error in scheduler loop: {e}")
                traceback.print_exc()
            
            await asyncio.sleep(POLL_CFG["SCHEDULER_TICK_SECONDS"])