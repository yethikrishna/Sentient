from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import asyncio
import time 
import traceback 
from typing import Optional, Any, List, Tuple, Dict

from core.db_manager import DBManager # Adjusted import path
from core.config import POLLING_INTERVALS, ACTIVE_THRESHOLD_MINUTES, RECENTLY_ACTIVE_THRESHOLD_HOURS, PEAK_HOURS_START, PEAK_HOURS_END

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None 
    try:
        import pytz
    except ImportError:
        pytz = None 
        print("[TIMEZONE_WARN] zoneinfo and pytz not available. Timezone features rely on UTC/system default.")


class BasePollingEngine(ABC): # Renamed from BaseContextEngine
    def __init__(self, user_id: str, db_manager: DBManager, service_name: str):
        self.user_id = user_id
        self.db_manager = db_manager
        self.service_name = service_name 
        print(f"[BasePollingEngine] Initialized for user {user_id}, service {service_name}")

    async def initialize_polling_state(self):
        await self.db_manager.initialize_polling_state_if_not_exists(self.user_id, self.service_name)

    async def run_poll_cycle(self):
        print(f"[POLL_CYCLE] Starting poll for {self.user_id}/{self.service_name}")
        
        current_polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
        if not current_polling_state:
            print(f"[POLL_CYCLE_ERROR] Polling state missing for {self.user_id}/{self.service_name}, re-initializing.")
            await self.initialize_polling_state()
            current_polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
            if not current_polling_state:
                print(f"[POLL_CYCLE_FATAL] Could not initialize polling state for {self.user_id}/{self.service_name}. Aborting poll.")
                await self.db_manager.release_polling_task_lock(
                    self.user_id, self.service_name, 
                    datetime.now(timezone.utc) + timedelta(hours=1), "error_no_state", 1, None, None
                )
                return

        last_marker_from_fetch: Optional[str] = None # Initialize to ensure it's always defined
        success = False
        new_data_payload = None

        try:
            print(f"[POLL_CYCLE] Fetching new data for {self.user_id}/{self.service_name}. Current marker: {current_polling_state.get('last_processed_item_marker')}")
            new_data_payload, last_marker_from_fetch = await self.fetch_new_data(current_polling_state)
            
            if new_data_payload:
                num_items = len(new_data_payload) if isinstance(new_data_payload, list) else 1
                print(f"[POLL_CYCLE] Processing {num_items} new items for {self.user_id}/{self.service_name}")
                
                # This now involves LLM calls to generate a payload for Kafka
                kafka_payload_data = await self.generate_kafka_payload(new_data_payload)
                
                # Simulate Kafka push by logging
                from kafka_producer import produce_to_kafka # Local import
                produce_to_kafka(self.user_id, self.service_name, kafka_payload_data)
            else:
                print(f"[POLL_CYCLE] No new data for {self.user_id}/{self.service_name}")
            success = True
        except Exception as e:
            print(f"[POLL_CYCLE_ERROR] Error during poll for {self.user_id}/{self.service_name}: {e}")
            traceback.print_exc()
            success = False
        finally:
            await self.calculate_and_schedule_next_poll(success, last_marker_from_fetch)
            print(f"[POLL_CYCLE] Poll cycle finished for {self.user_id}/{self.service_name}")

    async def calculate_and_schedule_next_poll(self, success: bool, last_marker_from_fetch: Optional[str]):
        # ... (This logic remains the same as in polling_sandbox/context_engine.py) ...
        # Ensure it uses self.db_manager correctly
        polling_state = await self.db_manager.get_polling_state(self.user_id, self.service_name)
        if not polling_state:
             print(f"[SCHEDULE_NEXT_ERROR] Polling state gone for {self.user_id}/{self.service_name}")
             return

        user_profile_data = await self.db_manager.get_user_profile_data(self.user_id)
        last_active_ts_iso = user_profile_data.get("last_active_timestamp") if user_profile_data else None
        user_timezone_str = user_profile_data.get("timezone", "UTC") if user_profile_data else "UTC"

        current_failures = polling_state.get("consecutive_failure_count", 0)
        next_interval_seconds = POLLING_INTERVALS["INACTIVE_SECONDS"]
        tier = "inactive_long"

        if not success:
            current_failures += 1
            base_fail_interval = POLLING_INTERVALS.get("PEAK_HOURS_SECONDS", 1800)
            backoff_seconds = base_fail_interval * (POLLING_INTERVALS["FAILURE_BACKOFF_FACTOR"] ** min(current_failures, 5))
            next_interval_seconds = min(backoff_seconds, POLLING_INTERVALS["MAX_FAILURE_BACKOFF_SECONDS"])
            tier = f"failure_backoff_{current_failures}"
        else:
            current_failures = 0
            now_utc = datetime.now(timezone.utc)
            
            last_active_ts = None
            if last_active_ts_iso:
                if isinstance(last_active_ts_iso, str):
                    last_active_ts = datetime.fromisoformat(last_active_ts_iso.replace("Z", "+00:00"))
                elif isinstance(last_active_ts_iso, datetime):
                    last_active_ts = last_active_ts_iso
                
                if last_active_ts and last_active_ts.tzinfo is None:
                    last_active_ts = last_active_ts.replace(tzinfo=timezone.utc)

            if last_active_ts:
                if (now_utc - last_active_ts) < timedelta(minutes=ACTIVE_THRESHOLD_MINUTES):
                    next_interval_seconds = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
                    tier = "active_short"
                elif (now_utc - last_active_ts) < timedelta(hours=RECENTLY_ACTIVE_THRESHOLD_HOURS):
                    next_interval_seconds = POLLING_INTERVALS["RECENTLY_ACTIVE_SECONDS"]
                    tier = "recently_active_medium"
                else: 
                    current_hour_user_tz = now_utc.hour
                    if user_timezone_str and user_timezone_str.lower() != "utc":
                        user_tz = None
                        if ZoneInfo:
                            try: user_tz = ZoneInfo(user_timezone_str)
                            except Exception: pass
                        elif pytz:
                            try: user_tz = pytz.timezone(user_timezone_str)
                            except Exception: pass
                        if user_tz:
                            try: current_hour_user_tz = now_utc.astimezone(user_tz).hour
                            except Exception as e_tz: print(f"[WARN_TZ] Error converting time for {user_timezone_str}: {e_tz}")
                        else: print(f"[WARN_TZ] Invalid timezone '{user_timezone_str}' for user {self.user_id}.")
                    
                    if PEAK_HOURS_START <= current_hour_user_tz < PEAK_HOURS_END:
                        next_interval_seconds = POLLING_INTERVALS["PEAK_HOURS_SECONDS"]
                        tier = "peak_normal"
                    else:
                        next_interval_seconds = POLLING_INTERVALS["OFF_PEAK_SECONDS"]
                        tier = "offpeak_long"
            else: 
                next_interval_seconds = POLLING_INTERVALS["OFF_PEAK_SECONDS"]
                tier = "offpeak_long_no_activity"
        
        next_interval_seconds = max(POLLING_INTERVALS["MIN_POLL_SECONDS"], min(next_interval_seconds, POLLING_INTERVALS["MAX_POLL_SECONDS"]))
        next_poll_timestamp = datetime.now(timezone.utc) + timedelta(seconds=next_interval_seconds)
        
        last_success_time = polling_state.get("last_successful_poll_timestamp")
        if success:
            last_success_time = datetime.now(timezone.utc)

        await self.db_manager.release_polling_task_lock(
            self.user_id, self.service_name, next_poll_timestamp, tier, current_failures,
            last_successful_poll_timestamp=last_success_time,
            last_processed_item_marker=last_marker_from_fetch if success else polling_state.get("last_processed_item_marker")
        )
        print(f"[SCHEDULE_NEXT] Next poll for {self.user_id}/{self.service_name} at {next_poll_timestamp.isoformat()} (Tier: {tier}, Interval: {next_interval_seconds}s)")


    @abstractmethod
    async def fetch_new_data(self, current_polling_state: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
        pass

    @abstractmethod
    async def process_new_data(self, new_data: Any) -> Any:
        """This will now be more lightweight, mostly formatting for the LLM or direct Kafka push."""
        pass

    @abstractmethod
    async def get_llm_runnable_for_processing(self) -> Any: # 'Any' because it's your BaseRunnable type
        """Returns the LLM runnable used by this engine to process fetched data."""
        pass
    
    async def generate_kafka_payload(self, processed_data: Any) -> Dict[str, Any]:
        """
        Processes fetched data using an LLM (if necessary) to generate a payload for Kafka.
        This replaces the old generate_output and execute_outputs.
        """
        # This is where the logic from your original BaseContextEngine's generate_output and execute_outputs
        # related to LLM processing of `processed_data` would go.
        # For example, if you need to summarize emails before pushing to Kafka:
        
        runnable = await self.get_llm_runnable_for_processing()
        if runnable:
            # Construct inputs for your runnable based on processed_data and other context
            # This part is highly specific to what your context engine's LLM does.
            # Example placeholder:
            # kafka_data_content = await asyncio.to_thread(runnable.invoke, {"new_information": processed_data, ...})
            # For simplicity, let's assume the processed_data is directly what we want,
            # or that process_new_data already did any necessary LLM work.
            # If process_new_data is just formatting, then the LLM call is here.
            # Let's assume for Gmail, process_new_data gives a simple list of email dicts.
            # The LLM might summarize these or extract actions.
            
            # Example: If the runnable expects the direct processed_data
            llm_processed_content = await asyncio.to_thread(runnable.invoke, {"new_information": processed_data})
            # llm_processed_content might be a dict with "tasks", "memory_operations", "message"
            # We need to decide what from this goes to Kafka.

            print(f"[KAFKA_GEN] LLM processing for {self.service_name} output: {str(llm_processed_content)[:200]}...")
            # For now, let's assume the entire LLM output (if it's a dict) is the data part of the Kafka payload.
            # If it's just a string summary, that becomes the data.
            return llm_processed_content if isinstance(llm_processed_content, dict) else {"summary": llm_processed_content}
        else:
            # No LLM runnable defined, push processed_data directly
            print(f"[KAFKA_GEN] No LLM runnable for {self.service_name}. Pushing processed data directly.")
            return processed_data # or format it slightly