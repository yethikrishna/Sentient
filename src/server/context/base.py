from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import asyncio
import time # For random jitter
import random # For random jitter
import json
from server.db.mongo_manager import MongoManager
from typing import Optional, Dict, Any, List, Tuple

# --- Polling Configuration ---
# These should ideally be loaded from config (e.g., environment variables)
# For now, defined as constants. In app.py, you can load them from os.getenv
DEFAULT_INITIAL_INTERVAL_SECONDS = int(os.getenv("DEFAULT_INITIAL_INTERVAL_SECONDS", 900))
MIN_POLLING_INTERVAL_SECONDS = int(os.getenv("MIN_POLLING_INTERVAL_SECONDS", 300))
MAX_POLLING_INTERVAL_SECONDS = int(os.getenv("MAX_POLLING_INTERVAL_SECONDS", 86400))
ACTIVITY_FACTOR = float(os.getenv("ACTIVITY_FACTOR", 2.0))
INACTIVITY_THRESHOLD_POLLS = int(os.getenv("INACTIVITY_THRESHOLD_POLLS", 3))
INACTIVITY_FACTOR = float(os.getenv("INACTIVITY_FACTOR", 1.5))
RATE_LIMIT_BACKOFF_FACTOR = float(os.getenv("RATE_LIMIT_BACKOFF_FACTOR", 3.0))
MAX_POLL_INTERVAL_RATE_LIMIT_SECONDS = int(os.getenv("MAX_POLL_INTERVAL_RATE_LIMIT_SECONDS", 86400))
TRANSIENT_ERROR_BACKOFF_SECONDS = int(os.getenv("TRANSIENT_ERROR_BACKOFF_SECONDS", 900))
POLLING_JITTER_SECONDS = 30 # Add +/- 30 seconds jitter

# User activity thresholds (can also be from config)
ACTIVE_THRESHOLD_MINUTES = 15
RECENTLY_ACTIVE_THRESHOLD_HOURS = 2
PEAK_HOURS_START = 8  # User's local time
PEAK_HOURS_END = 22 # User's local time


class BaseContextEngine(ABC):
    def __init__(self, user_id: str, task_queue: Any, memory_backend: Any, 
                 websocket_manager: Any, mongo_manager_instance: MongoManager):
        self.user_id: str = user_id
        self.task_queue = task_queue # For creating agent tasks from context
        self.memory_backend = memory_backend # For storing context-derived memories
        self.websocket_manager = websocket_manager # For sending notifications
        self.mongo_manager = mongo_manager_instance
        self.category: Optional[str] = None # Must be set by child class (e.g., "gmail")
        print(f"[BaseContextEngine] Initialized for user {self.user_id}, category: {getattr(self, 'category', 'NOT_SET')}")

    async def initialize_polling_state(self):
        """Ensure an initial polling state exists for this user/engine."""
        if not self.category:
            print(f"[POLLING_INIT_ERROR] Category not set for engine for user {self.user_id}.")
            return

        existing_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        if not existing_state:
            print(f"[POLLING_INIT] No polling state for {self.user_id}/{self.category}. Creating initial state.")
            
            # Add a small random offset to the first poll time to distribute load
            random_offset_seconds = random.randint(0, MIN_POLLING_INTERVAL_SECONDS // 2)
            initial_next_poll_time = datetime.now(timezone.utc) + timedelta(seconds=random_offset_seconds)
            
            initial_state = {
                "user_id": self.user_id,
                "service_name": self.category, # Use service_name for consistency
                "last_polled_timestamp": None,
                "last_processed_item_id": None,
                "next_page_token": None,
                "last_successful_poll_status_message": "Polling state initialized.",
                "next_scheduled_poll_time": initial_next_poll_time,
                "current_polling_interval_seconds": DEFAULT_INITIAL_INTERVAL_SECONDS,
                "min_polling_interval_seconds": MIN_POLLING_INTERVAL_SECONDS,
                "max_polling_interval_seconds": MAX_POLLING_INTERVAL_SECONDS,
                "consecutive_empty_polls_count": 0,
                "last_activity_timestamp": None,
                "is_rate_limited": False,
                "error_backoff_until_timestamp": None,
                "is_enabled": True, # Default to enabled
                "created_at": datetime.now(timezone.utc),
            }
            await self.mongo_manager.update_polling_state(self.user_id, self.category, initial_state)
            print(f"[POLLING_INIT] Initial polling state created for {self.user_id}/{self.category}, next poll at {initial_next_poll_time.isoformat()}.")
        else:
            if existing_state.get("is_currently_polling", False):
                print(f"[POLLING_INIT_WARN] Polling lock was stale for {self.user_id}/{self.category}. Resetting is_currently_polling flag.")
                await self.mongo_manager.update_polling_state(self.user_id, self.category, {"is_currently_polling": False})
            print(f"[POLLING_INIT] Polling state already exists for {self.user_id}/{self.category}.")
            if not existing_state.get("is_enabled", False): # Check if it was disabled
                 print(f"[POLLING_INIT] Service {self.category} is disabled for {self.user_id}. No polling will occur until enabled.")


    async def run_poll_cycle(self):
        """
        The main polling logic for this engine instance.
        This is triggered by the central scheduler after a lock is acquired.
        """
        if not self.category:
            print(f"[POLL_CYCLE_ERROR] Category not set for engine user {self.user_id}")
            return

        print(f"[POLL_CYCLE] Starting poll for {self.user_id}/{self.category}")
        
        # Fetch current state to get markers etc.
        polling_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        if not polling_state:
            print(f"[POLL_CYCLE_ERROR] Polling state not found for {self.user_id}/{self.category} at start of cycle. Re-initializing.")
            await self.initialize_polling_state() # Attempt to re-initialize
            # Release lock and schedule for immediate retry if re-init was successful
            await self.mongo_manager.update_polling_state(self.user_id, self.category, {
                "is_currently_polling": False,
                "next_scheduled_poll_time": datetime.now(timezone.utc) # Poll again very soon
            })
            return

        last_marker_from_db = polling_state.get("last_processed_item_id")
        next_page_token_from_db = polling_state.get("next_page_token")

        new_data_found = False
        api_error_occurred = False
        rate_limited = False
        new_last_marker = last_marker_from_db
        
        try:
            print(f"[POLL_CYCLE] Fetching new data for {self.user_id}/{self.category} (Last Marker: {last_marker_from_db}, PageToken: {next_page_token_from_db})")
            # fetch_new_data needs to handle page_token
            fetch_result = await self.fetch_new_data(last_marker_from_db, next_page_token_from_db)
            
            if fetch_result is None: # Indicates an API error during fetch
                print(f"[POLL_CYCLE_API_ERROR] API error during fetch_new_data for {self.user_id}/{self.category}.")
                api_error_occurred = True
                # Specific error handling (like rate limits) should be within fetch_new_data or returned by it
                # For now, assume fetch_new_data might raise specific exceptions or return error indicators
            else:
                new_data_payload, new_last_marker_from_fetch, new_next_page_token = fetch_result

                if new_data_payload: # Check if any data was actually fetched
                    new_data_found = True
                    print(f"[POLL_CYCLE] Processing {len(new_data_payload)} new items for {self.user_id}/{self.category}")
                    
                    # This method should publish to Kafka and log processed items
                    await self.process_and_publish_data(new_data_payload) 
                    
                    new_last_marker = new_last_marker_from_fetch # Update marker only if processing was successful
                    print(f"[POLL_CYCLE] Data processed. New marker: {new_last_marker}. Next page token: {new_next_page_token}")

                    # Update next_page_token in DB immediately if there is one,
                    # or clear it if this was the last page of the current batch
                    await self.mongo_manager.update_polling_state(
                        self.user_id, self.category, {"next_page_token": new_next_page_token}
                    )

                    # If there's a next_page_token, we should schedule the next poll very soon to continue fetching
                    if new_next_page_token:
                        print(f"[POLL_CYCLE] More data to fetch (pagination). Scheduling next poll quickly for {self.user_id}/{self.category}.")
                        # This case will be handled by calculate_and_schedule_next_poll,
                        # as new_data_found is true, it will reduce interval.
                        # We could add a specific, very short interval here if needed.
                else:
                    print(f"[POLL_CYCLE] No new data found for {self.user_id}/{self.category}.")
                    # If no new data, and there was a next_page_token, it means we've exhausted pagination for now.
                    if next_page_token_from_db:
                         await self.mongo_manager.update_polling_state(self.user_id, self.category, {"next_page_token": None})


        except httpx.HTTPStatusError as e: # Assuming you use httpx and it raises this
            print(f"[POLL_CYCLE_HTTP_ERROR] HTTP error for {self.user_id}/{self.category}: {e.response.status_code} - {e.response.text}")
            api_error_occurred = True
            if e.response.status_code == 429: # Rate limit
                rate_limited = True
                retry_after_seconds = int(e.response.headers.get("Retry-After", TRANSIENT_ERROR_BACKOFF_SECONDS))
                await self.mongo_manager.update_polling_state(
                    self.user_id, self.category, 
                    {"is_rate_limited": True, 
                     "error_backoff_until_timestamp": datetime.now(timezone.utc) + timedelta(seconds=retry_after_seconds),
                     "last_successful_poll_status_message": f"Rate limited. Retry after {retry_after_seconds}s."
                    }
                )
            elif e.response.status_code >= 500: # Server error
                 await self.mongo_manager.update_polling_state(
                    self.user_id, self.category, 
                    {"error_backoff_until_timestamp": datetime.now(timezone.utc) + timedelta(seconds=TRANSIENT_ERROR_BACKOFF_SECONDS),
                     "last_successful_poll_status_message": f"Server error {e.response.status_code}."
                    }
                )
            else: # Other client errors
                await self.mongo_manager.update_polling_state(
                    self.user_id, self.category,
                    {"last_successful_poll_status_message": f"API Client Error {e.response.status_code}."}
                )
                # For some client errors (e.g. auth), we might want to disable polling
                # self.disable_polling("Persistent API client error")
        except Exception as e:
            print(f"[POLL_CYCLE_ERROR] General error during poll for {self.user_id}/{self.category}: {e}")
            traceback.print_exc()
            api_error_occurred = True
            await self.mongo_manager.update_polling_state(
                self.user_id, self.category,
                {"error_backoff_until_timestamp": datetime.now(timezone.utc) + timedelta(seconds=TRANSIENT_ERROR_BACKOFF_SECONDS),
                 "last_successful_poll_status_message": f"Polling cycle error: {str(e)[:100]}"
                }
            )
        finally:
            print(f"[POLL_CYCLE] Finalizing poll for {self.user_id}/{self.category}. Success: {not api_error_occurred}, New Data: {new_data_found}, Rate Limited: {rate_limited}")
            await self.calculate_and_schedule_next_poll(
                success=not api_error_occurred, 
                data_found=new_data_found, 
                rate_limited=rate_limited,
                current_marker=new_last_marker # Pass the marker that was successfully processed up to
            )
            print(f"[POLL_CYCLE] Poll cycle finished for {self.user_id}/{self.category}")

    async def calculate_and_schedule_next_poll(self, success: bool, data_found: bool, rate_limited: bool, current_marker: Optional[str]):
        if not self.category:
            print(f"[SCHEDULE_NEXT_ERROR] Category not set for user {self.user_id}")
            return

        polling_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        if not polling_state:
            print(f"[SCHEDULE_NEXT_ERROR] No polling state found for {self.user_id}/{self.category}. Cannot schedule.")
            return

        current_interval = polling_state.get("current_polling_interval_seconds", DEFAULT_INITIAL_INTERVAL_SECONDS)
        consecutive_empty = polling_state.get("consecutive_empty_polls_count", 0)
        
        next_interval_seconds = current_interval
        new_consecutive_empty = consecutive_empty
        status_message = polling_state.get("last_successful_poll_status_message", "Scheduled.")
        error_backoff_ts = polling_state.get("error_backoff_until_timestamp")
        is_currently_rate_limited = polling_state.get("is_rate_limited", False)

        if rate_limited:
            next_interval_seconds = min(current_interval * RATE_LIMIT_BACKOFF_FACTOR, MAX_POLL_INTERVAL_RATE_LIMIT_SECONDS)
            status_message = f"Rate limited. Backing off. Original interval: {current_interval}s."
            # error_backoff_until_timestamp is set by the error handler in run_poll_cycle
        elif not success: # API error, not rate limit
            next_interval_seconds = current_interval # Keep current, error_backoff_ts handles delay
            status_message = f"API error. Will retry after backoff. Original interval: {current_interval}s."
            # error_backoff_until_timestamp is set by the error handler
        elif data_found:
            next_interval_seconds = max(MIN_POLLING_INTERVAL_SECONDS, current_interval / ACTIVITY_FACTOR)
            new_consecutive_empty = 0
            status_message = "New data found. Increased polling frequency."
            is_currently_rate_limited = False # Clear rate limit flag on success
            error_backoff_ts = None # Clear error backoff on success
            await self.mongo_manager.update_polling_state(self.user_id, self.category, {"last_activity_timestamp": datetime.now(timezone.utc)})
        else: # Success, but no new data
            new_consecutive_empty += 1
            if new_consecutive_empty >= INACTIVITY_THRESHOLD_POLLS:
                next_interval_seconds = min(MAX_POLLING_INTERVAL_SECONDS, current_interval * INACTIVITY_FACTOR)
                new_consecutive_empty = 0 # Reset after adjustment
                status_message = "No new data after threshold. Decreased polling frequency."
            else:
                status_message = "No new data found."
            is_currently_rate_limited = False
            error_backoff_ts = None

        next_interval_seconds = int(max(MIN_POLLING_INTERVAL_SECONDS, min(next_interval_seconds, MAX_POLLING_INTERVAL_SECONDS)))
        
        # Add jitter
        jitter = random.randint(-POLLING_JITTER_SECONDS, POLLING_JITTER_SECONDS)
        next_poll_time = datetime.now(timezone.utc) + timedelta(seconds=next_interval_seconds + jitter)
        
        # If there's an error_backoff_until_timestamp, ensure next_poll_time respects it
        if error_backoff_ts:
            if isinstance(error_backoff_ts, str): # If stored as string
                error_backoff_ts = datetime.fromisoformat(error_backoff_ts.replace("Z", "+00:00"))
            if error_backoff_ts.tzinfo is None:
                error_backoff_ts = error_backoff_ts.replace(tzinfo=timezone.utc)
            
            if next_poll_time < error_backoff_ts:
                next_poll_time = error_backoff_ts + timedelta(seconds=jitter) # Schedule after backoff, with new jitter
                status_message += f" Respecting error backoff until {error_backoff_ts.isoformat()}."


        update_data: Dict[str, Any] = {
            "next_scheduled_poll_time": next_poll_time,
            "current_polling_interval_seconds": next_interval_seconds,
            "consecutive_empty_polls_count": new_consecutive_empty,
            "last_successful_poll_status_message": status_message,
            "is_rate_limited": is_currently_rate_limited, # Updated based on current poll outcome
            "error_backoff_until_timestamp": error_backoff_ts, # Persist or clear
            "is_currently_polling": False, # Release lock
        }
        if success: # Only update these on a successful poll, even if no data
            update_data["last_polled_timestamp"] = datetime.now(timezone.utc)
            if current_marker is not None: # Marker from this poll cycle
                update_data["last_processed_item_id"] = current_marker
        
        await self.mongo_manager.update_polling_state(self.user_id, self.category, update_data)
        print(f"[SCHEDULE_NEXT] Next poll for {self.user_id}/{self.category} scheduled at {next_poll_time.isoformat()} (Interval: {next_interval_seconds}s, Jitter: {jitter}s. Status: {status_message})")

    @abstractmethod
    async def fetch_new_data(self, last_marker: Optional[str], page_token: Optional[str]) -> Optional[Tuple[Optional[List[Any]], Optional[str], Optional[str]]]:
        """
        Fetch new data from the specific data source.
        Args:
            last_marker: The marker from the last successfully processed item (e.g., historyId for Gmail).
            page_token: The next page token if available from previous fetch.
        Returns:
            Tuple[Optional[List[Any]], Optional[str], Optional[str]]: 
            (new_data_payload_list, new_last_item_marker, next_page_token_for_more_data)
            Return (None, prev_marker, prev_page_token) or raise specific error on API failure.
            Return ([], current_marker, None) if no new data.
        """
        pass

    @abstractmethod
    async def process_and_publish_data(self, new_data_payload: List[Any]):
        """
        Process the fetched new data and publish relevant parts to Kafka.
        This method should also handle duplicate checking against ProcessedItemsLog.
        """
        pass

    # get_runnable and execute_outputs might be less relevant for polling
    # if the primary action is to publish to Kafka.
    # They were more for the context engine's LLM interaction part.
    # Let's keep them for now, but their role might change.

    @abstractmethod
    async def get_runnable(self):
        """Return the data source-specific runnable if needed for summarizing or deciding based on polled data."""
        pass

    async def execute_outputs(self, output):
        """
        This was originally for context engine's LLM output (tasks, memory_ops, message).
        For polling, this might be adapted to log success/failure or send a summary notification.
        The primary output of polling is now data published to Kafka via `process_and_publish_data`.
        """
        if not self.category:
            print("[BASE_CONTEXT_ENGINE_ERROR] Category not set. Cannot execute outputs.")
            return
        # This method might be simplified or repurposed for polling status updates.
        # For instance, sending a summary notification if significant data was found.
        print(f"BaseContextEngine.execute_outputs for {self.category}: {output if output else 'No output from runnable.'}")


    # --- Helper methods (can be kept or moved based on final design) ---
    async def get_chat_history(self):
        # ... (implementation remains same) ...
        print(f"BaseContextEngine.get_chat_history started for user {self.user_id}")
        user_profile = await self.mongo_manager.get_user_profile(self.user_id)
        active_chat_id = None
        if user_profile and "userData" in user_profile and "active_chat_id" in user_profile["userData"]:
            active_chat_id = user_profile["userData"]["active_chat_id"]

        if not active_chat_id:
            print(f"BaseContextEngine.get_chat_history - no active chat ID found for user {self.user_id}, returning empty list")
            return []

        print(f"BaseContextEngine.get_chat_history - active_chat_id: {active_chat_id} for user_id: {self.user_id}")
        history = await self.mongo_manager.get_chat_history(self.user_id, active_chat_id)
        last_10_messages = history[-10:] if history else []
        print(f"BaseContextEngine.get_chat_history - returning last {len(last_10_messages)} messages.")
        print("BaseContextEngine.get_chat_history finished")
        return last_10_messages