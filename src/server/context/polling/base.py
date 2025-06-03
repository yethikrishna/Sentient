from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import asyncio
import time 
import traceback 
from typing import Optional, Any, List, Tuple, Dict

# Assuming mongo_manager is passed or globally available as per your structure
# from server.db import MongoManager
# Assuming config constants are available
# from server.utils.config import POLLING_INTERVALS, ACTIVE_THRESHOLD_MINUTES, RECENTLY_ACTIVE_THRESHOLD_HOURS, PEAK_HOURS_START, PEAK_HOURS_END
# For Kafka:
from server.utils.producers import KafkaProducerManager # Kafka producer

# Attempt to import ZoneInfo, fallback to pytz, then to None
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None 
    try:
        import pytz
    except ImportError:
        pytz = None 
        print("[TIMEZONE_WARN] zoneinfo and pytz not available. Timezone features rely on UTC/system default.")


class BasePollingEngine(ABC):
    def __init__(self, user_id: str, db_manager: Any, service_name: str): # db_manager type hinted as Any for now
        self.user_id = user_id
        self.db_manager = db_manager # This should be an instance of MongoManager
        self.service_name = service_name 
        
        # Dynamically import POLLING_INTERVALS and other constants from config
        # This is to avoid circular imports if config itself imports parts of this module
        from server.utils.config import POLLING_INTERVALS, ACTIVE_THRESHOLD_MINUTES, RECENTLY_ACTIVE_THRESHOLD_HOURS, PEAK_HOURS_START, PEAK_HOURS_END
        self.POLLING_INTERVALS = POLLING_INTERVALS
        self.ACTIVE_THRESHOLD_MINUTES = ACTIVE_THRESHOLD_MINUTES
        self.RECENTLY_ACTIVE_THRESHOLD_HOURS = RECENTLY_ACTIVE_THRESHOLD_HOURS
        self.PEAK_HOURS_START = PEAK_HOURS_START
        self.PEAK_HOURS_END = PEAK_HOURS_END
        
        print(f"[{datetime.now()}] [BasePollingEngine] Initialized for user {user_id}, service {service_name}")

    async def initialize_polling_state(self):
        """Initializes or ensures the polling state for this user/service in the database."""
        print(f"[{datetime.now()}] [BasePollingEngine] Initializing polling state for {self.user_id}/{self.service_name}...")
        await self.db_manager.update_polling_state(
            self.user_id,
            self.service_name,
            { # Ensure these fields are set if it's a new document
                "is_enabled": True, # Default to enabled, can be overridden by user settings
                "next_scheduled_poll_time": datetime.now(timezone.utc), # Poll soon
                "is_currently_polling": False,
                "last_processed_item_marker": None,
                "consecutive_failure_count": 0,
                "error_backoff_until_timestamp": None,
                "current_polling_tier": "initial",
                "current_polling_interval_seconds": self.POLLING_INTERVALS["ACTIVE_USER_SECONDS"],
            }
        )
        print(f"[{datetime.now()}] [BasePollingEngine] Polling state initialized for {self.user_id}/{self.service_name}.")


    async def run_poll_cycle(self):
        print(f"[{datetime.now()}] [POLL_CYCLE] Starting poll for {self.user_id}/{self.service_name}")
        
        current_polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
        if not current_polling_state:
            print(f"[{datetime.now()}] [POLL_CYCLE_ERROR] Polling state missing for {self.user_id}/{self.service_name}, re-initializing.")
            await self.initialize_polling_state()
            current_polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
            if not current_polling_state:
                print(f"[{datetime.now()}] [POLL_CYCLE_FATAL] Could not initialize polling state for {self.user_id}/{self.service_name}. Aborting poll.")
                # Schedule a retry much later to avoid rapid failing loops
                await self.db_manager.update_polling_state(
                    self.user_id, self.service_name, 
                    {
                        "next_scheduled_poll_time": datetime.now(timezone.utc) + timedelta(hours=1),
                        "is_currently_polling": False,
                        "last_successful_poll_status_message": "Error: Polling state unrecoverable."
                    }
                )
                return

        last_marker_from_fetch: Optional[str] = None 
        success = False
        new_data_payload = None

        try:
            print(f"[{datetime.now()}] [POLL_CYCLE] Fetching new data for {self.user_id}/{self.service_name}. Current marker: {current_polling_state.get('last_processed_item_marker')}")
            new_data_items, last_marker_from_fetch = await self.fetch_new_data(current_polling_state)
            
            if new_data_items: # This should be a list of items
                num_items = len(new_data_items)
                print(f"[{datetime.now()}] [POLL_CYCLE] Fetched {num_items} new items for {self.user_id}/{self.service_name}")
                
                # Simplified processing: directly format for Kafka
                kafka_payload_data = await self.generate_kafka_payload(new_data_items)
                
                # Get the Kafka topic from config
                from server.utils.config import GMAIL_POLL_KAFKA_TOPIC # Assuming Gmail for now
                kafka_topic = GMAIL_POLL_KAFKA_TOPIC # Generalize if other services use different topics

                # Send to Kafka
                kafka_success = await KafkaProducerManager.send_message(kafka_topic, kafka_payload_data, key=self.user_id)
                if kafka_success:
                    print(f"[{datetime.now()}] [POLL_CYCLE] Successfully sent {num_items} items for {self.user_id}/{self.service_name} to Kafka topic '{kafka_topic}'.")
                else:
                    print(f"[{datetime.now()}] [POLL_CYCLE_ERROR] Failed to send items for {self.user_id}/{self.service_name} to Kafka.")
                    # Decide if this constitutes a poll failure for backoff purposes
                    # For now, let's say if Kafka fails, the poll cycle itself didn't "succeed" fully.
                    success = False # Mark as not fully successful if Kafka send fails
                    # Do not update last_marker_from_fetch if Kafka send failed, to reprocess these items next time.
                    last_marker_from_fetch = current_polling_state.get("last_processed_item_marker")

            else:
                print(f"[{datetime.now()}] [POLL_CYCLE] No new data for {self.user_id}/{self.service_name}")
            
            if new_data_items is not None: # If fetch_new_data returned (even if empty list), consider it a success
                success = True

        except Exception as e:
            print(f"[{datetime.now()}] [POLL_CYCLE_ERROR] Error during poll for {self.user_id}/{self.service_name}: {e}")
            traceback.print_exc()
            success = False
            last_marker_from_fetch = current_polling_state.get("last_processed_item_marker") # Don't advance marker on error
        finally:
            await self.calculate_and_schedule_next_poll(success, last_marker_from_fetch, bool(new_data_items))
            print(f"[{datetime.now()}] [POLL_CYCLE] Poll cycle finished for {self.user_id}/{self.service_name}")

    async def calculate_and_schedule_next_poll(self, success: bool, last_marker_from_fetch: Optional[str], new_data_found: bool):
        polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
        if not polling_state:
             print(f"[{datetime.now()}] [SCHEDULE_NEXT_ERROR] Polling state missing for {self.user_id}/{self.service_name}. Cannot schedule next poll.")
             return

        user_profile = await self.db_manager.get_user_profile(self.user_id)
        user_data = user_profile.get("userData", {}) if user_profile else {}
        
        last_active_ts_val = user_data.get("last_active_timestamp")
        user_timezone_str = user_data.get("personalInfo", {}).get("timezone", "UTC")


        current_failures = polling_state.get("consecutive_failure_count", 0)
        current_empty_polls = polling_state.get("consecutive_empty_polls_count", 0)
        
        next_interval_seconds = self.POLLING_INTERVALS["INACTIVE_SECONDS"] # Default to inactive
        tier = "inactive_long_default"

        if not success:
            current_failures += 1
            base_fail_interval = self.POLLING_INTERVALS.get("PEAK_HOURS_SECONDS", 1800) # Default to 30 mins for failure base
            backoff_seconds = base_fail_interval * (self.POLLING_INTERVALS["FAILURE_BACKOFF_FACTOR"] ** min(current_failures, 5))
            next_interval_seconds = min(backoff_seconds, self.POLLING_INTERVALS["MAX_FAILURE_BACKOFF_SECONDS"])
            tier = f"failure_backoff_{current_failures}"
            current_empty_polls = 0 # Reset empty polls on failure
        else:
            current_failures = 0 # Reset failures on success
            if new_data_found:
                current_empty_polls = 0 # Reset empty polls if new data was found
            else: # No new data
                current_empty_polls += 1
            
            now_utc = datetime.now(timezone.utc)
            last_active_ts = None
            if last_active_ts_val:
                if isinstance(last_active_ts_val, str):
                    try:
                        if last_active_ts_val.endswith("Z"): last_active_ts_val = last_active_ts_val[:-1] + "+00:00"
                        last_active_ts = datetime.fromisoformat(last_active_ts_val)
                    except ValueError: last_active_ts = None
                elif isinstance(last_active_ts_val, datetime):
                    last_active_ts = last_active_ts_val
                if last_active_ts and last_active_ts.tzinfo is None:
                    last_active_ts = last_active_ts.replace(tzinfo=timezone.utc)

            if last_active_ts:
                if (now_utc - last_active_ts) < timedelta(minutes=self.ACTIVE_THRESHOLD_MINUTES):
                    next_interval_seconds = self.POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
                    tier = "active_user"
                elif (now_utc - last_active_ts) < timedelta(hours=self.RECENTLY_ACTIVE_THRESHOLD_HOURS):
                    next_interval_seconds = self.POLLING_INTERVALS["RECENTLY_ACTIVE_SECONDS"]
                    tier = "recently_active"
                else: 
                    # For less active users, check peak hours
                    current_hour_user_tz = now_utc.hour # Default to UTC hour
                    if user_timezone_str and user_timezone_str.lower() != "utc":
                        user_tz_info = None
                        if ZoneInfo:
                            try: user_tz_info = ZoneInfo(user_timezone_str)
                            except Exception: pass
                        elif pytz:
                            try: user_tz_info = pytz.timezone(user_timezone_str)
                            except Exception: pass
                        
                        if user_tz_info:
                            try: current_hour_user_tz = now_utc.astimezone(user_tz_info).hour
                            except Exception as e_tz: print(f"[{datetime.now()}] [WARN_TZ] Error converting time for {user_timezone_str}: {e_tz}")
                        else: print(f"[{datetime.now()}] [WARN_TZ] Invalid timezone '{user_timezone_str}' for user {self.user_id}. Using UTC hour.")
                    
                    if self.PEAK_HOURS_START <= current_hour_user_tz < self.PEAK_HOURS_END:
                        next_interval_seconds = self.POLLING_INTERVALS["PEAK_HOURS_SECONDS"]
                        tier = "peak_hours_inactive_user"
                    else:
                        next_interval_seconds = self.POLLING_INTERVALS["OFF_PEAK_SECONDS"]
                        tier = "off_peak_inactive_user"
            else: # No last_active_timestamp found, assume off-peak
                next_interval_seconds = self.POLLING_INTERVALS["OFF_PEAK_SECONDS"]
                tier = "off_peak_no_activity_data"
            
            # Increase interval if many consecutive empty polls
            if current_empty_polls > 0:
                # Example: double interval for every 3 empty polls, up to a max
                backoff_factor = 1.5 ** (current_empty_polls // 3) 
                next_interval_seconds = min(next_interval_seconds * backoff_factor, self.POLLING_INTERVALS["MAX_POLL_SECONDS"])
                tier += f"_empty_polls_backoff_{current_empty_polls}"

        next_interval_seconds = max(self.POLLING_INTERVALS["MIN_POLL_SECONDS"], min(next_interval_seconds, self.POLLING_INTERVALS["MAX_POLL_SECONDS"]))
        next_poll_timestamp = datetime.now(timezone.utc) + timedelta(seconds=next_interval_seconds)
        
        update_payload = {
            "next_scheduled_poll_time": next_poll_timestamp,
            "is_currently_polling": False,
            "consecutive_failure_count": current_failures,
            "consecutive_empty_polls_count": current_empty_polls,
            "current_polling_tier": tier,
            "current_polling_interval_seconds": int(next_interval_seconds),
            "last_successful_poll_status_message": "Poll successful." if success else polling_state.get("last_successful_poll_status_message", "Poll failed."),
            "last_processed_item_marker": last_marker_from_fetch if success and new_data_found else polling_state.get("last_processed_item_marker"), # Only update marker if data processed and no Kafka error
            "error_backoff_until_timestamp": None if success else (datetime.now(timezone.utc) + timedelta(seconds=next_interval_seconds)) # Set backoff on failure
        }
        if success:
             update_payload["last_successful_poll_timestamp"] = datetime.now(timezone.utc)


        await self.db_manager.update_polling_state(self.user_id, self.service_name, update_payload)
        
        print(f"[{datetime.now()}] [SCHEDULE_NEXT] Next poll for {self.user_id}/{self.service_name} at {next_poll_timestamp.isoformat()} (Tier: {tier}, Interval: {next_interval_seconds:.0f}s, Failures: {current_failures}, Empty Polls: {current_empty_polls})")


    @abstractmethod
    async def fetch_new_data(self, current_polling_state: Dict[str, Any]) -> Tuple[Optional[List[Any]], Optional[str]]:
        """
        Fetches new data from the source.
        Returns a tuple: (list_of_new_items, new_marker_or_None_if_error_or_no_change).
        If no new data, returns ([], current_marker_or_new_marker).
        If error, returns (None, current_marker).
        """
        pass

    async def generate_kafka_payload(self, new_data_items: List[Any]) -> Dict[str, Any]:
        """
        Prepares the payload to be sent to Kafka.
        For this simplified version, it might just wrap the new_data_items.
        """
        return {
            "user_id": self.user_id,
            "service_name": self.service_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "item_count": len(new_data_items),
            "data_items": new_data_items # The actual fetched and processed items
        }