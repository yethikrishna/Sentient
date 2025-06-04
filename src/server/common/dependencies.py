import os
import asyncio
import json
import traceback
import datetime
from datetime import timezone, timedelta
from typing import Optional, Any, Dict, List, Tuple, Union
import uuid # For new chat_id

from server.db import MongoManager
# TaskQueue and MemoryBackend might be simplified or removed if not central to core features
# For now, keep TaskQueue if Gmail polling uses it to send data to Kafka.
# from server.agents.base import TaskQueue
# from server.memory.backend import MemoryBackend # Remove if complex memory graph is gone

from server.context.polling.base import BasePollingEngine # For type hinting
from server.context.polling.gmail import GmailPollingEngine # Only Gmail engine

from neo4j import GraphDatabase # Remove if Neo4j is not used at all
from llama_index.embeddings.huggingface import HuggingFaceEmbedding # Remove if Neo4j/embeddings are not used

from server.common.auth import AuthHelper, PermissionChecker, oauth2_scheme # Corrected import
from server.utils.producers import KafkaProducerManager # Import Kafka Producer

# Global variables from app.py that are dependencies
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    print(f"[{datetime.datetime.now()}] [ERROR] FATAL: AUTH0_DOMAIN or AUTH0_AUDIENCE not set in dependencies.py!")
    # This will likely cause issues downstream if not caught earlier by auth.py
    # Consider exiting or raising a more prominent error if app.py doesn't handle this.

# JWKS fetching is handled within utils.auth.py now.

auth = AuthHelper() # Instantiate AuthHelper
print(f"[{datetime.datetime.now()}] [INIT] AuthHelper (auth) initialized in dependencies.")

# --- Task Queue ---
print(f"[{datetime.datetime.now()}] [INIT] Initializing TaskQueue (for Gmail polling to Kafka)...")
# task_queue = TaskQueue() # Keep if Gmail polling might use it as an intermediary before Kafka.
                         # If GmailPollingEngine sends directly to Kafka, this can be removed.
print(f"[{datetime.datetime.now()}] [INIT] TaskQueue initialized.")

# --- MongoDB Manager ---
print(f"[{datetime.datetime.now()}] [INIT] Initializing MongoManager...")
mongo_manager = MongoManager()
print(f"[{datetime.datetime.now()}] [INIT] MongoManager initialized.")

# --- WebSocket Manager ---
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Any] = {} # WebSocket type hint can be tricky here
        print(f"[{datetime.datetime.now()}] [WS_MANAGER] WebSocketManager initialized.")
    async def connect(self, websocket: Any, user_id: str): # Use Any for websocket type
        if user_id in self.active_connections:
            print(f"[{datetime.datetime.now()}] [WS_MANAGER] User {user_id} already connected. Closing old one.")
            old_ws = self.active_connections[user_id]
            try:
                await old_ws.close(code=1008, reason="New connection established by the same user.") # Use a valid close code
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [WS_MANAGER_ERROR] Error closing old WebSocket for {user_id}: {e}")
        self.active_connections[user_id] = websocket
        print(f"[{datetime.datetime.now()}] [WS_MANAGER] WebSocket connected: {user_id} ({len(self.active_connections)} total)")

    def disconnect(self, websocket: Any): # Use Any for websocket type
        uid_to_remove = next((uid for uid, ws in self.active_connections.items() if ws == websocket), None)
        if uid_to_remove:
            del self.active_connections[uid_to_remove]
            print(f"[{datetime.datetime.now()}] [WS_MANAGER] WebSocket disconnected: {uid_to_remove} ({len(self.active_connections)} total)")

    async def send_personal_message(self, message: str, user_id: str):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [WS_MANAGER_ERROR] Error sending message to {user_id}: {e}")
                self.disconnect(ws) # Disconnect on send error
    
    async def broadcast_json(self, data: dict):
        message_str = json.dumps(data)
        for ws in list(self.active_connections.values()): 
            try:
                await ws.send_text(message_str)
            except Exception:
                self.disconnect(ws)

manager = WebSocketManager()
print(f"[{datetime.datetime.now()}] [INIT] WebSocketManager instance (manager) created.")

# --- Memory Backend (Remove if not used by simplified features) ---
# For the revamped version focusing on profile storage in MongoDB and no complex memory graph,
# the full MemoryBackend might be overkill. If any aspect of it is still needed
# (e.g., simplified short-term memory for chat context not covered by chat history),
# it could be kept in a simplified form. Otherwise, remove.
# For now, assuming it's removed for max simplification.
memory_backend = None 
# print(f"[{datetime.datetime.now()}] [INIT] MemoryBackend is NOT initialized (revamped server).")


# --- Context Engines and Polling ---
active_context_engines: Dict[str, Dict[str, BasePollingEngine]] = {}
polling_scheduler_task_handle: Optional[asyncio.Task] = None

# Use constants from utils.config
from server.utils.config import POLLING_INTERVALS
POLLING_SCHEDULER_INTERVAL_SECONDS = POLLING_INTERVALS.get("SCHEDULER_TICK_SECONDS", 30)


DATA_SOURCES_CONFIG: Dict[str, Dict[str, Any]] = {
    "gmail": {
        "engine_class": GmailPollingEngine, # Ensure GmailPollingEngine is imported
        "enabled_by_default": False, # Default to false, user enables it
    },
    # Other data sources like gcalendar, internet_search are removed
}

# --- Database Interaction Helper Functions (moved from app.py, simplified) ---
async def load_user_profile(user_id: str) -> Dict[str, Any]:
    """Loads user profile from MongoDB."""
    profile = await mongo_manager.get_user_profile(user_id)
    return profile if profile else {"user_id": user_id, "userData": {}} # Return a default structure

async def write_user_profile(user_id: str, data: Dict[str, Any]) -> bool:
    """Writes user profile data to MongoDB."""
    return await mongo_manager.update_user_profile(user_id, data)

async def get_chat_history_messages(user_id: str, chat_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    """
    Retrieves chat history messages for a user and a specific chat ID.
    If no chat_id is provided, it tries to use the active_chat_id from the user's profile.
    If no active_chat_id, it takes the most recent chat_id.
    If no chats exist, it creates a new chat_id and sets it as active.
    """
    effective_chat_id = chat_id
    if not effective_chat_id: # Covers None or ""
        user_profile = await mongo_manager.get_user_profile(user_id)
        if user_profile and user_profile.get("userData", {}).get("active_chat_id"):
            effective_chat_id = user_profile["userData"]["active_chat_id"]
        else:
            # Try to get the most recent chat_id if no active one is set
            all_chat_ids = await mongo_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids: # get_all_chat_ids_for_user sorts by last_updated desc
                effective_chat_id = all_chat_ids[0]
                if user_profile: # Update profile if it exists
                    await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
                # else: profile will be created with this active_chat_id if user interacts
            else: # No chats exist at all for this user
                new_chat_id = str(uuid.uuid4())
                print(f"[{datetime.datetime.now()}] [CHAT_HISTORY] No chats found for user {user_id}. Creating new active_chat_id: {new_chat_id}")
                # Update (or create) profile with this new active_chat_id
                update_payload = {"userData.active_chat_id": new_chat_id}
                if not user_profile: # if profile didn't exist, set user_id and createdAt
                    update_payload["user_id"] = user_id
                    update_payload["createdAt"] = datetime.datetime.now(timezone.utc)
                await mongo_manager.update_user_profile(user_id, update_payload)
                effective_chat_id = new_chat_id
    
    if not effective_chat_id: # Should be practically impossible now
        print(f"[{datetime.datetime.now()}] [CHAT_HISTORY_ERROR] Critical: No chat_id determined for user {user_id}.")
        return [], ""
 
    messages_from_db = await mongo_manager.get_chat_history(user_id, effective_chat_id)
    
    # Ensure timestamps are ISO strings for JSON serialization compatibility
    serialized_messages = []
    for m in messages_from_db:
        if not isinstance(m, dict): continue
        if 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
        
    return [m for m in serialized_messages if m.get("isVisible", True)], effective_chat_id


async def add_message_to_db(user_id: str, chat_id: Union[int, str], message_text: str, is_user: bool, is_visible: bool = True, **kwargs) -> Optional[str]:
    """Adds a message to the chat history in MongoDB."""
    try:
        target_chat_id = str(chat_id) # Ensure chat_id is string
    except (ValueError, TypeError):
        print(f"[{datetime.datetime.now()}] [DB_ERROR] Invalid chat_id for add_message: {chat_id}")
        return None
    
    message_data = {
        "message": message_text,
        "isUser": is_user,
        "isVisible": is_visible,
        **kwargs # Include any other metadata like memoryUsed, agentsUsed etc.
    }
    # Remove None values from kwargs before saving
    message_data = {k: v for k, v in message_data.items() if v is not None}

    try:
        message_id = await mongo_manager.add_chat_message(user_id, target_chat_id, message_data)
        return message_id
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [DB_ERROR] Error adding message for user {user_id}, chat {target_chat_id}: {e}")
        traceback.print_exc()
        return None

# --- Polling Scheduler Loop (Simplified for Gmail) ---
async def polling_scheduler_loop():
    print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Starting loop (interval: {POLLING_SCHEDULER_INTERVAL_SECONDS}s)")
    if not mongo_manager:
        print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER_ERROR] MongoManager not initialized. Scheduler cannot run.")
        return

    # Reset any stale locks at startup
    await mongo_manager.reset_stale_polling_locks() 
    
    while True:
        try:
            due_tasks_states = await mongo_manager.get_due_polling_tasks() 
            
            if not due_tasks_states:
                # print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] No due polling tasks.") # Can be verbose
                pass
            else:
                print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Found {len(due_tasks_states)} due polling tasks.")

            for task_state in due_tasks_states:
                user_id = task_state["user_id"]
                service_name = task_state["service_name"] 
                
                if service_name != "gmail": # Only process Gmail for this revamp
                    print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Skipping non-Gmail task: {service_name} for user {user_id}")
                    continue
                
                print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Attempting to process task for {user_id}/{service_name}")

                # Try to acquire a lock on the task
                locked_task_state = await mongo_manager.set_polling_status_and_get(user_id, service_name)
                
                if locked_task_state: # If lock acquired (document found and updated)
                    print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Acquired lock for {user_id}/{service_name}. Triggering poll.")
                    
                    # Get or create engine instance
                    engine_instance = active_context_engines.get(user_id, {}).get(service_name)
                    
                    if not engine_instance:
                        engine_config = DATA_SOURCES_CONFIG.get(service_name)
                        if engine_config and engine_config.get("engine_class"):
                            engine_class = engine_config["engine_class"]
                            print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Creating new {engine_class.__name__} instance for {user_id}/{service_name}")
                            # Ensure all necessary dependencies are passed to the engine
                            engine_instance = engine_class(
                                user_id=user_id,
                                db_manager=mongo_manager # Pass MongoManager instance
                                # task_queue=task_queue, # If Gmail engine needs it
                                # memory_backend=memory_backend, # If Gmail engine needs it
                                # websocket_manager=manager # If Gmail engine needs it
                            )
                            if user_id not in active_context_engines:
                                active_context_engines[user_id] = {}
                            active_context_engines[user_id][service_name] = engine_instance
                        else:
                            print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER_ERROR] No engine class configured for service: {service_name}")
                            # Release lock and schedule for later
                            await mongo_manager.update_polling_state(user_id, service_name, {"is_currently_polling": False, "next_scheduled_poll_time": datetime.datetime.now(timezone.utc) + timedelta(hours=1)})
                            continue
                    
                    # Run the poll cycle for the specific engine
                    asyncio.create_task(engine_instance.run_poll_cycle()) 
                else:
                    # Lock not acquired, means another worker might have picked it up or conditions changed
                    print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER] Could not acquire lock for {user_id}/{service_name} (already processing or no longer due).")

        except Exception as e:
            print(f"[{datetime.datetime.now()}] [POLLING_SCHEDULER_ERROR] Error in scheduler loop: {e}")
            traceback.print_exc() # Log full traceback for debugging
        
        await asyncio.sleep(POLLING_SCHEDULER_INTERVAL_SECONDS)

async def start_user_context_engines(user_id: str):
    """
    Initializes polling states for a user's enabled data sources.
    This is called when a user logs in or when a data source is enabled.
    """
    print(f"[{datetime.datetime.now()}] [CONTEXT_ENGINE_MGR] Ensuring polling states for user {user_id}.")
    if user_id not in active_context_engines: 
        active_context_engines[user_id] = {}
    
    if not mongo_manager:
        print(f"[{datetime.datetime.now()}] [CONTEXT_ENGINE_MGR_ERROR] MongoManager not initialized. Cannot start engines for user {user_id}.")
        return

    user_profile = await mongo_manager.get_user_profile(user_id)
    # User settings would determine which sources are enabled.
    # For this revamp, we assume only Gmail can be enabled.
    # Check a hypothetical setting like `user_profile.get("userData", {}).get("gmail_polling_enabled", False)`
    
    # For Gmail, if it's enabled (or enabled by default and not explicitly disabled by user)
    gmail_config = DATA_SOURCES_CONFIG.get("gmail")
    if gmail_config:
        # This logic should be more robust: check user's actual setting for "gmail"
        # For now, let's assume if we call this, we intend to init/check its polling state.
        # The actual decision to poll is in the scheduler based on `is_enabled`.
        
        engine_instance = active_context_engines.get(user_id, {}).get("gmail")
        if not engine_instance:
            engine_class = gmail_config["engine_class"]
            print(f"[{datetime.datetime.now()}] [CONTEXT_ENGINE_MGR] Creating transient {engine_class.__name__} instance for {user_id}/gmail for state init.")
            engine_instance = engine_class(
                user_id=user_id,
                db_manager=mongo_manager
            )
            # No need to store transient instance in active_context_engines here,
            # scheduler will create one if needed and if it's actually enabled.
        
        # This ensures the polling state document exists in MongoDB.
        # The engine's initialize_polling_state should create it if not found.
        await engine_instance.initialize_polling_state() 
        print(f"[{datetime.datetime.now()}] [CONTEXT_ENGINE_MGR] Polling state ensured for gmail for user {user_id}.")
    else:
        print(f"[{datetime.datetime.now()}] [CONTEXT_ENGINE_MGR_WARN] Gmail not found in DATA_SOURCES_CONFIG.")


# --- Global LLM Models and Drivers (Remove if not used) ---
# For the revamp, Neo4j and complex embedding models are removed.
graph_driver = None
embed_model = None
# print(f"[{datetime.datetime.now()}] [DEPENDENCIES_INIT] Neo4j Driver and Embedding Model are NOT initialized (revamped server).")


# Define USER_PROFILE_DB_DIR here as it's a shared configuration
print(f"[{datetime.datetime.now()}] [CONFIG] Defining database file paths in dependencies.py...")
_COMMON_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVER_DIR = os.path.dirname(_COMMON_DIR)
_SRC_DIR = os.path.dirname(_SERVER_DIR)
USER_PROFILE_DB_DIR = os.path.join(_SRC_DIR, "user_databases") # Used by LowDB if it were still here. Not relevant for MongoDB.
os.makedirs(USER_PROFILE_DB_DIR, exist_ok=True) # Still good practice for potential local file storage
print(f"[{datetime.datetime.now()}] [CONFIG] USER_PROFILE_DB_DIR (for local files, if any) set to {USER_PROFILE_DB_DIR}")

# --- Kafka Producer (Initialize at startup) ---
# The KafkaProducerManager will handle lazy initialization on first use.
# We can trigger an early init if desired.
async def initialize_kafka_producer_on_startup():
    print(f"[{datetime.datetime.now()}] [INIT] Attempting to initialize Kafka producer on startup...")
    await KafkaProducerManager.get_producer() # This will trigger initialization
    # No need to store the result, get_producer handles the singleton instance.

# This should be called in the lifespan startup if early init is desired.
# For now, producer initializes on first `send_message` call.