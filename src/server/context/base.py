from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone # Added timedelta, timezone
import asyncio
import time
import json
from server.db.mongo_manager import MongoManager
from typing import Optional, Dict, Any, List # Added for typing

# Define POLLING_INTERVALS and thresholds here or import from a config file
# For simplicity, defined here. In a larger app, move to a config.
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": 60,          # 1 minute for active users
    "RECENTLY_ACTIVE_SECONDS": 15 * 60, # 15 minutes
    "PEAK_HOURS_SECONDS": 30 * 60,      # 30 minutes during peak
    "OFF_PEAK_SECONDS": 2 * 60 * 60,    # 2 hours during off-peak
    "INACTIVE_SECONDS": 4 * 60 * 60,    # 4 hours for long inactive
    "MIN_POLL_SECONDS": 30,
    "MAX_POLL_SECONDS": 6 * 60 * 60,
    "FAILURE_BACKOFF_FACTOR": 2,
    "MAX_FAILURE_BACKOFF_SECONDS": 12 * 60 * 60,
}
ACTIVE_THRESHOLD_MINUTES = 15
RECENTLY_ACTIVE_THRESHOLD_HOURS = 2
PEAK_HOURS_START = 8  # User's local time
PEAK_HOURS_END = 22 # User's local time

class BaseContextEngine(ABC):
    def __init__(self, user_id, task_queue, memory_backend, websocket_manager, mongo_manager_instance: MongoManager):
        print(f"BaseContextEngine.__init__ for user_id: {user_id}, category: {getattr(self, 'category', 'N/A')}")
        self.user_id: str = user_id
        self.task_queue = task_queue
        self.memory_backend = memory_backend
        self.websocket_manager = websocket_manager
        self.mongo_manager = mongo_manager_instance
        self.category: Optional[str] = None # Must be set by child class
        # self.context is not needed here, polling state is in DB

    async def initialize_polling_state(self):
        """Ensure an initial polling state exists for this user/engine."""
        if not self.category:
            print(f"[POLLING_INIT_ERROR] Category not set for engine for user {self.user_id}.")
            return
        
        existing_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        if not existing_state:
            print(f"[POLLING_INIT] No polling state for {self.user_id}/{self.category}. Creating initial state.")
            initial_state = {
                "user_id": self.user_id,
                "engine_category": self.category,
                "last_successful_poll_timestamp": None,
                "last_processed_item_marker": None,
                "next_scheduled_poll_timestamp": datetime.now(timezone.utc), # Poll ASAP on first start
                "current_polling_tier": "initial",
                "consecutive_failure_count": 0,
                "is_currently_polling": False,
                "created_at": datetime.now(timezone.utc),
                "last_updated_at": datetime.now(timezone.utc)
            }
            await self.mongo_manager.update_polling_state(self.user_id, self.category, initial_state)
            print(f"[POLLING_INIT] Initial polling state created for {self.user_id}/{self.category}.")
        else:
             # If it exists but is_currently_polling is true (e.g. from a crash), reset it
            if existing_state.get("is_currently_polling", False):
                print(f"[POLLING_INIT_WARN] Polling lock was stale for {self.user_id}/{self.category}. Resetting.")
                await self.mongo_manager.update_polling_state(self.user_id, self.category, {"is_currently_polling": False, "next_scheduled_poll_timestamp": datetime.now(timezone.utc)})


    async def run_poll_cycle(self):
        """
        The main polling logic for this engine instance.
        This is triggered by the central scheduler.
        """
        if not self.category:
            print(f"[POLL_CYCLE_ERROR] Category not set for engine user {self.user_id}")
            return

        print(f"[POLL_CYCLE] Starting poll for {self.user_id}/{self.category}")
        
        # Get current polling state for this specific user/engine
        # The scheduler should have already marked it as is_currently_polling=True
        # For safety, we can re-fetch, but it's better if the scheduler passes the locked state.
        # For now, assuming the scheduler handles the lock, and we just proceed.
        # Alternatively, the engine itself tries to acquire the lock:
        
        # polling_state = await self.mongo_manager.set_polling_status_and_get(self.user_id, self.category)
        # if not polling_state:
        #     print(f"[POLL_CYCLE] Could not acquire polling lock or task not due for {self.user_id}/{self.category}. Skipping.")
        #     return
        # The above is better if the scheduler just identifies due tasks, and engines try to lock.
        # For the current prompt, the scheduler identifies and the engine runs.

        last_marker = None # Placeholder for last processed item marker
        success = False
        try:
            print(f"[POLL_CYCLE] Fetching new data for {self.user_id}/{self.category}")
            new_data, last_marker = await self.fetch_new_data() # fetch_new_data should return the new marker
            
            if new_data:
                print(f"[POLL_CYCLE] Processing new data for {self.user_id}/{self.category}")
                processed_data = await self.process_new_data(new_data)
                print(f"[POLL_CYCLE] Generating output for {self.user_id}/{self.category}")
                output = await self.generate_output(processed_data)
                print(f"[POLL_CYCLE] Executing outputs for {self.user_id}/{self.category}")
                await self.execute_outputs(output)
            else:
                print(f"[POLL_CYCLE] No new data for {self.user_id}/{self.category}")
            success = True
        except Exception as e:
            print(f"[POLL_CYCLE_ERROR] Error during poll for {self.user_id}/{self.category}: {e}")
            traceback.print_exc()
            success = False
        finally:
            print(f"[POLL_CYCLE] Calculating next poll for {self.user_id}/{self.category}, success: {success}")
            await self.calculate_and_schedule_next_poll(success, last_marker if success else None)
            print(f"[POLL_CYCLE] Poll cycle finished for {self.user_id}/{self.category}")

    async def calculate_and_schedule_next_poll(self, success: bool, last_processed_marker: Optional[str] = None):
        if not self.category:
            print(f"[SCHEDULE_NEXT_ERROR] Category not set for user {self.user_id}")
            return

        polling_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        if not polling_state:
            print(f"[SCHEDULE_NEXT_ERROR] No polling state found for {self.user_id}/{self.category}. Cannot schedule next poll.")
            # Attempt to initialize it if it's missing unexpectedly
            await self.initialize_polling_state()
            return

        user_activity = await self.mongo_manager.get_user_activity_and_timezone(self.user_id)
        last_active_ts = user_activity.get("last_active_timestamp")
        user_timezone_str = user_activity.get("timezone") # Expecting IANA timezone string

        current_failures = polling_state.get("consecutive_failure_count", 0)
        next_interval_seconds = POLLING_INTERVALS["INACTIVE_SECONDS"] # Default
        tier = "inactive_long"

        if not success:
            current_failures += 1
            backoff_seconds = POLLING_INTERVALS["PEAK_HOURS_SECONDS"] * (POLLING_INTERVALS["FAILURE_BACKOFF_FACTOR"] ** min(current_failures, 5)) # Limit backoff exponent
            next_interval_seconds = min(backoff_seconds, POLLING_INTERVALS["MAX_FAILURE_BACKOFF_SECONDS"])
            tier = f"failure_backoff_{current_failures}"
        else:
            current_failures = 0 # Reset on success
            now_utc = datetime.now(timezone.utc)
            
            # Active User Tier
            if last_active_ts and (now_utc - last_active_ts) < timedelta(minutes=ACTIVE_THRESHOLD_MINUTES):
                next_interval_seconds = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
                tier = "active_short"
            # Recently Active Tier
            elif last_active_ts and (now_utc - last_active_ts) < timedelta(hours=RECENTLY_ACTIVE_THRESHOLD_HOURS):
                next_interval_seconds = POLLING_INTERVALS["RECENTLY_ACTIVE_SECONDS"]
                tier = "recently_active_medium"
            # Timezone-based Tier (for less active users)
            else:
                current_hour_user_tz = now_utc.hour # Default to UTC if no timezone
                if user_timezone_str:
                    try:
                        from zoneinfo import ZoneInfo # Python 3.9+
                        user_tz = ZoneInfo(user_timezone_str)
                        current_hour_user_tz = now_utc.astimezone(user_tz).hour
                    except ImportError: # Fallback for < Python 3.9 or if zoneinfo not available
                        try:
                            import pytz
                            user_tz = pytz.timezone(user_timezone_str)
                            current_hour_user_tz = now_utc.astimezone(user_tz).hour
                        except Exception as tz_err:
                            print(f"[WARN] Invalid timezone '{user_timezone_str}' or pytz not installed for user {self.user_id}. Defaulting to UTC. Error: {tz_err}")
                    except Exception as e:
                         print(f"[WARN] Error processing timezone {user_timezone_str} for user {self.user_id}: {e}. Defaulting to UTC.")


                if POLLING_INTERVALS["PEAK_HOURS_START"] <= current_hour_user_tz < POLLING_INTERVALS["PEAK_HOURS_END"]:
                    next_interval_seconds = POLLING_INTERVALS["PEAK_HOURS_SECONDS"]
                    tier = "peak_normal"
                else:
                    next_interval_seconds = POLLING_INTERVALS["OFF_PEAK_SECONDS"]
                    tier = "offpeak_long"
        
        # Apply min/max bounds
        next_interval_seconds = max(POLLING_INTERVALS["MIN_POLL_SECONDS"], min(next_interval_seconds, POLLING_INTERVALS["MAX_POLL_SECONDS"]))
        
        next_poll_timestamp = datetime.now(timezone.utc) + timedelta(seconds=next_interval_seconds)
        
        update_data: Dict[str, Any] = {
            "next_scheduled_poll_timestamp": next_poll_timestamp,
            "current_polling_tier": tier,
            "consecutive_failure_count": current_failures,
            "is_currently_polling": False, # Release lock
            "last_updated_at": datetime.now(timezone.utc)
        }
        if success:
            update_data["last_successful_poll_timestamp"] = datetime.now(timezone.utc)
            if last_processed_marker is not None:
                update_data["last_processed_item_marker"] = last_processed_marker
        
        await self.mongo_manager.update_polling_state(self.user_id, self.category, update_data)
        print(f"[SCHEDULE_NEXT] Next poll for {self.user_id}/{self.category} scheduled at {next_poll_timestamp.isoformat()} (Tier: {tier}, Interval: {next_interval_seconds}s)")


    @abstractmethod
    async def fetch_new_data(self) -> Tuple[Optional[Any], Optional[str]]:
        """
        Fetch new data from the specific data source.
        Returns:
            Tuple[Optional[Any], Optional[str]]: (new_data_payload, last_processed_item_marker)
            Return (None, None) if no new data or error.
        """
        pass

    @abstractmethod
    async def process_new_data(self, new_data):
        """Process the fetched data into a format suitable for the runnable."""
        pass

    @abstractmethod
    async def get_runnable(self):
        """Return the data source-specific runnable for generating outputs."""
        pass

    async def generate_output(self, processed_data):
        # ... (generate_output method remains largely the same, ensure it gets self.category) ...
        if not self.category:
            print("[BASE_CONTEXT_ENGINE_ERROR] Category not set. Cannot generate output.")
            return {}
            
        print(f"BaseContextEngine.generate_output started for {self.category}")
        runnable = await self.get_runnable()
        print(f"BaseContextEngine.generate_output ({self.category}) - got runnable: {type(runnable)}")
        print(f"BaseContextEngine.generate_output ({self.category}) - retrieving related memories for category '{self.category}'")
        related_memories = await self.memory_backend.retrieve_memory(self.user_id, query=str(processed_data)[:100], type=self.category) 
        print(f"BaseContextEngine.generate_output ({self.category}) - retrieved related memories: {str(related_memories)[:200]}...")
        
        print(f"BaseContextEngine.generate_output ({self.category}) - getting ongoing tasks")
        all_user_tasks = await self.task_queue.get_tasks_for_user(self.user_id) 
        ongoing_tasks = [task for task in all_user_tasks if task.get("status") in ["pending", "processing"]]
        print(f"BaseContextEngine.generate_output ({self.category}) - ongoing tasks: {len(ongoing_tasks)}")
        
        print(f"BaseContextEngine.generate_output ({self.category}) - getting chat history")
        chat_history = await self.get_chat_history() 
        print(f"BaseContextEngine.generate_output ({self.category}) - chat history length: {len(chat_history)}")

        related_memories_list = related_memories if isinstance(related_memories, list) else ([related_memories] if related_memories else [])
        memories_str = "\n".join([mem.get("text", str(mem)) for mem in related_memories_list])

        ongoing_tasks_list = ongoing_tasks if ongoing_tasks is not None else [] 
        tasks_str = "\n".join([task.get("description", str(task)) for task in ongoing_tasks_list])

        chat_history_list = chat_history if chat_history is not None else [] 
        chat_str = "\n".join([f"{'User' if msg.get('isUser') else 'Assistant'}: {msg.get('message', str(msg))}" for msg in chat_history_list])

        print(f"BaseContextEngine.generate_output ({self.category}) - invoking runnable")
        
        runnable_input = {
            "new_information": processed_data,
            "related_memories": memories_str,
            "ongoing_tasks": tasks_str,
            "chat_history": chat_str
        }
        output = await asyncio.to_thread(runnable.invoke, runnable_input)
        print(f"BaseContextEngine.generate_output ({self.category}) - runnable output: {str(output)[:200]}...")
        print(f"BaseContextEngine.generate_output finished for {self.category}")
        return output

    async def get_chat_history(self):
        # ... (get_chat_history remains the same) ...
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


    async def execute_outputs(self, output):
        # ... (execute_outputs remains the same) ...
        if not self.category:
            print("[BASE_CONTEXT_ENGINE_ERROR] Category not set. Cannot execute outputs.")
            return

        print(f"BaseContextEngine.execute_outputs started for {self.category}")
        tasks = output.get("tasks", [])
        memory_ops = output.get("memory_operations", [])
        message_text = output.get("message", None) 

        print(f"BaseContextEngine.execute_outputs ({self.category}) - tasks: {tasks}")
        print(f"BaseContextEngine.execute_outputs ({self.category}) - memory_operations: {memory_ops}")
        print(f"BaseContextEngine.execute_outputs ({self.category}) - message: {message_text}")
        
        for task in tasks:
            if isinstance(task, dict) and "description" in task and "priority" in task:
                print(f"BaseContextEngine.execute_outputs ({self.category}) - adding task to queue: {task}")
                await self.task_queue.add_task(
                    user_id=self.user_id, 
                    chat_id="context_engine_tasks", 
                    description=task["description"],
                    priority=task["priority"],
                    username=self.user_id, 
                    use_personal_context=False, 
                    internet="None"
                )
            else:
                print(f"[WARN] Invalid task format: {task}")

        for op in memory_ops:
            if isinstance(op, dict) and "text" in op:
                print(f"BaseContextEngine.execute_outputs ({self.category}) - processing memory operation: {op}")
                await self.memory_backend.memory_queue.add_operation(self.user_id, {"type": "store", "query_text": op["text"], "category": self.category})
            else:
                print(f"[WARN] Invalid memory operation format: {op}")

        if message_text and isinstance(message_text, str): 
            
            new_message = {
                    "id": str(int(time.time() * 1000)), 
                    "message": message_text,
                    "isUser": False,
                    "isVisible": True, 
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "context_engine": self.category 
                }
            print(f"BaseContextEngine.execute_outputs ({self.category}) - processing message for user: {self.user_id}, Message: {message_text}")

            user_profile = await self.mongo_manager.get_user_profile(self.user_id)
            active_chat_id = "context_engine_updates" 
            if user_profile and "userData" in user_profile and "active_chat_id" in user_profile["userData"]:
                active_chat_id = user_profile["userData"]["active_chat_id"]

            await self.mongo_manager.add_chat_message(self.user_id, active_chat_id, new_message)
            print(f"BaseContextEngine.execute_outputs ({self.category}) - saved message to chat '{active_chat_id}' for user {self.user_id}")

            notification_payload = {
                "type": "context_engine_update", 
                "message_id": new_message["id"], 
                "text": message_text, 
                "timestamp": new_message["timestamp"],
                "source_engine": self.category
            }
            await self.mongo_manager.add_notification(self.user_id, notification_payload)
            print(f"BaseContextEngine.execute_outputs ({self.category}) - saved notification for user {self.user_id}")

            await self.websocket_manager.send_personal_message(json.dumps({"type": "notification", "data": notification_payload}), self.user_id)
            print(f"BaseContextEngine.execute_outputs ({self.category}) - sent WebSocket notification to user {self.user_id}")
        else:
            print(f"BaseContextEngine.execute_outputs ({self.category}) - no message to process or invalid format: {message_text}")
        print(f"BaseContextEngine.execute_outputs finished for {self.category}")