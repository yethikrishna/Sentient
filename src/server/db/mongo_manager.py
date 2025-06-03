import os
import datetime
import uuid 
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError # Import DuplicateKeyError
from typing import Dict, List, Optional, Any

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db") 

USER_PROFILES_COLLECTION = "user_profiles" 
CHAT_HISTORY_COLLECTION = "chat_history" 
NOTIFICATIONS_COLLECTION = "notifications" 
# MEMORY_COLLECTION_NAME = "memory_operations" # Removed, no complex memory operations

POLLING_STATE_COLLECTION = "polling_state_store"
PROCESSED_ITEMS_COLLECTION = "processed_items_log" # Keep for Gmail polling de-duplication

class MongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.chat_history_collection = self.db[CHAT_HISTORY_COLLECTION]
        self.notifications_collection = self.db[NOTIFICATIONS_COLLECTION]
        # self.memory_collection = self.db[MEMORY_COLLECTION_NAME] # Removed

        self.polling_state_collection = self.db[POLLING_STATE_COLLECTION]
        self.processed_items_collection = self.db[PROCESSED_ITEMS_COLLECTION]
        
        print(f"[{datetime.datetime.now()}] [MongoManager] Initialized. Database: {MONGO_DB_NAME}")

    async def initialize_db(self):
        print(f"[{datetime.datetime.now()}] [DB_INIT] Ensuring indexes for MongoManager collections...")
        user_profile_indexes = [
            IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique_idx"),
            IndexModel([("userData.last_active_timestamp", DESCENDING)], name="user_last_active_idx")
        ]
        try:
            await self.user_profiles_collection.create_indexes(user_profile_indexes)
            print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {self.user_profiles_collection.name}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {self.user_profiles_collection.name}: {e}")

        chat_history_indexes = [
            IndexModel([("user_id", ASCENDING), ("chat_id", ASCENDING)], name="user_chat_id_idx"),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)], name="user_timestamp_idx")
        ]
        try:
            await self.chat_history_collection.create_indexes(chat_history_indexes)
            print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {self.chat_history_collection.name}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {self.chat_history_collection.name}: {e}")
        
        notifications_indexes = [
            IndexModel([("user_id", ASCENDING)], name="notification_user_id_idx")
        ]
        try:
            await self.notifications_collection.create_indexes(notifications_indexes)
            print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {self.notifications_collection.name}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {self.notifications_collection.name}: {e}")

        polling_state_indexes = [
            IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING)], unique=True, name="polling_user_service_unique_idx"),
            IndexModel([
                ("is_enabled", ASCENDING), 
                ("next_scheduled_poll_time", ASCENDING), 
                ("error_backoff_until_timestamp", ASCENDING), 
                ("is_currently_polling", ASCENDING) 
            ], name="polling_due_tasks_idx"),
            IndexModel([("is_currently_polling", ASCENDING), ("last_attempted_poll_timestamp", ASCENDING)], name="polling_stale_locks_idx")
        ]
        try:
            await self.polling_state_collection.create_indexes(polling_state_indexes)
            print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {self.polling_state_collection.name}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {self.polling_state_collection.name}: {e}")

        processed_items_indexes = [
            IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING), ("item_id", ASCENDING)], unique=True, name="processed_item_unique_idx")
        ]
        try:
            await self.processed_items_collection.create_indexes(processed_items_indexes)
            print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {self.processed_items_collection.name}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {self.processed_items_collection.name}: {e}")
        
        # Memory operations collection removed, so no indexes for it.

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        if not user_id: return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        if not user_id or not profile_data: return False
        if "_id" in profile_data: del profile_data["_id"] 
        
        update_operations = {}
        flat_profile_data = {} 
        user_data_updates = {} 

        for key, value in profile_data.items():
            if key.startswith("userData."):
                sub_key = key.split(".", 1)[1]
                user_data_updates[sub_key] = value
            elif key == "userData" and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    user_data_updates[sub_key] = sub_value
            else:
                flat_profile_data[key] = value
        
        if flat_profile_data:
            update_operations["$set"] = flat_profile_data
        
        if user_data_updates:
            if "$set" not in update_operations: update_operations["$set"] = {}
            for k, v in user_data_updates.items():
                update_operations["$set"][f"userData.{k}"] = v
        
        if not update_operations: 
            print(f"[{datetime.datetime.now()}] [MongoManager_WARN] update_user_profile called for user {user_id} with no operations to perform.")
            return False # Or True if no change means success

        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            update_operations, 
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None
        
    async def update_user_last_active(self, user_id: str) -> bool:
        if not user_id: return False
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        update_payload = {
            "userData.last_active_timestamp": now_utc,
            "userData.last_updated": now_utc # Also update a general last_updated if you have one
        }
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": update_payload, "$setOnInsert": {"user_id": user_id, "createdAt": now_utc}}, # Ensure user_id and createdAt on insert
            upsert=True 
        )
        return result.matched_count > 0 or result.upserted_id is not None
        
    # --- Polling State Methods (largely unchanged but now use self.db) ---
    async def get_polling_state(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]: 
        if not user_id or not service_name: return None
        return await self.polling_state_collection.find_one(
            {"user_id": user_id, "service_name": service_name}
        )

    async def update_polling_state(self, user_id: str, service_name: str, state_data: Dict[str, Any]) -> bool: 
        if not user_id or not service_name or state_data is None: return False
        
        # Ensure datetime objects are timezone-aware (UTC)
        for key, value in state_data.items():
            if isinstance(value, datetime.datetime):
                if value.tzinfo is None:
                    state_data[key] = value.replace(tzinfo=datetime.timezone.utc)
                else: # If already timezone-aware, convert to UTC
                    state_data[key] = value.astimezone(datetime.timezone.utc)
            elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime): # Handle date objects
                 state_data[key] = datetime.datetime.combine(value, datetime.time.min, tzinfo=datetime.timezone.utc)
        
        if "_id" in state_data: del state_data["_id"] # Don't try to update _id
        state_data["last_updated_at"] = datetime.datetime.now(datetime.timezone.utc)

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name}, 
            {"$set": state_data, "$setOnInsert": {"created_at": datetime.datetime.now(datetime.timezone.utc), "user_id": user_id, "service_name": service_name}}, 
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_due_polling_tasks(self) -> List[Dict[str, Any]]:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        query = {
            "is_enabled": True, 
            "next_scheduled_poll_time": {"$lte": now_utc},
            "is_currently_polling": False,
            "$or": [
                {"error_backoff_until_timestamp": None},
                {"error_backoff_until_timestamp": {"$lte": now_utc}}
            ]
        }
        cursor = self.polling_state_collection.find(query).sort("next_scheduled_poll_time", ASCENDING)
        return await cursor.to_list(length=None) # Fetch all due tasks

    async def set_polling_status_and_get(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]: 
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Atomic find and update to "lock" the task for processing
        doc = await self.polling_state_collection.find_one_and_update(
            {
                "user_id": user_id, 
                "service_name": service_name, 
                "is_enabled": True,
                "next_scheduled_poll_time": {"$lte": now_utc},
                "is_currently_polling": False,
                "$or": [ # Ensure not in error backoff
                    {"error_backoff_until_timestamp": None},
                    {"error_backoff_until_timestamp": {"$lte": now_utc}}
                ]
            },
            {"$set": {"is_currently_polling": True, "last_attempted_poll_timestamp": now_utc}},
            return_document=ReturnDocument.AFTER # Return the document *after* the update
        )
        return doc

    async def reset_stale_polling_locks(self, timeout_minutes: int = 30):
        stale_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=timeout_minutes)
        result = await self.polling_state_collection.update_many(
            {
                "is_currently_polling": True,
                "last_attempted_poll_timestamp": {"$lt": stale_threshold}
            },
            {
                "$set": {
                    "is_currently_polling": False, 
                    "last_successful_poll_status_message": "Reset stale lock by scheduler.",
                    # Reschedule soon, but not immediately to avoid thundering herd if many locks reset
                    "next_scheduled_poll_time": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60) 
                }
            }
        )
        if result.modified_count > 0:
            print(f"[{datetime.datetime.now()}] [MongoManager] Reset {result.modified_count} stale polling locks.")
        return result.modified_count

    # --- Processed Items Log Methods (for Gmail polling deduplication) ---
    async def log_processed_item(self, user_id: str, service_name: str, item_id: str) -> bool:
        if not user_id or not service_name or not item_id: return False
        try:
            await self.processed_items_collection.insert_one({
                "user_id": user_id,
                "service_name": service_name,
                "item_id": item_id,
                "processing_timestamp": datetime.datetime.now(datetime.timezone.utc)
            })
            return True
        except DuplicateKeyError: # Handle if item already logged (e.g., due to retry)
            print(f"[{datetime.datetime.now()}] [ProcessedItemsLog] Item {user_id}/{service_name}/{item_id} already processed (DuplicateKeyError).")
            return True # Considered success as it's already processed
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ProcessedItemsLog] Error logging item {user_id}/{service_name}/{item_id}: {e}")
            return False

    async def is_item_processed(self, user_id: str, service_name: str, item_id: str) -> bool:
        if not user_id or not service_name or not item_id: return True # Treat invalid input as "processed" to avoid issues
        count = await self.processed_items_collection.count_documents({
            "user_id": user_id,
            "service_name": service_name,
            "item_id": item_id
        })
        return count > 0
    
    # --- Chat History Methods ---
    async def add_chat_message(self, user_id: str, chat_id: str, message_data: Dict) -> str:
        if not user_id or not chat_id or not message_data:
            raise ValueError("user_id, chat_id, and message_data are required for adding chat message.")
        
        message_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        # Generate a unique ID for the message if not provided (client might send one for optimistic UI)
        message_id = message_data.get("id", str(uuid.uuid4())) 
        message_data["id"] = message_id # Ensure 'id' is part of the message_data

        result = await self.chat_history_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$push": {"messages": message_data},
             "$set": {"last_updated": datetime.datetime.now(datetime.timezone.utc)},
             "$setOnInsert": {"user_id": user_id, "chat_id": chat_id, "created_at": datetime.datetime.now(datetime.timezone.utc)}
            },
            upsert=True
        )
        if result.modified_count == 0 and result.upserted_id is None:
            # Check if it truly failed or if it was an upsert that didn't modify an existing doc but created a new one.
            # An upsert is successful if upserted_id is not None.
            # If no modification and no upsert, then something went wrong.
            chat_exists = await self.chat_history_collection.count_documents({"user_id": user_id, "chat_id": chat_id}) > 0
            if not chat_exists: 
                 raise Exception(f"Failed to add chat message for user {user_id}, chat {chat_id}: No document modified or upserted.")
        return message_id

    async def get_chat_history(self, user_id: str, chat_id: str) -> Optional[List[Dict]]:
        if not user_id or not chat_id: return None
        chat_doc = await self.chat_history_collection.find_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"messages": 1, "_id": 0} # Projection to get only messages array
        )
        return chat_doc.get("messages", []) if chat_doc else []

    async def get_all_chat_ids_for_user(self, user_id: str) -> List[str]:
        if not user_id: return []
        cursor = self.chat_history_collection.find(
            {"user_id": user_id}, {"chat_id": 1, "_id": 0} # Projection
        ).sort("last_updated", DESCENDING) # Sort by last_updated, newest first
        chat_ids = [doc["chat_id"] for doc in await cursor.to_list(length=None)] # Fetch all
        return chat_ids

    async def delete_chat_history(self, user_id: str, chat_id: str) -> bool:
        if not user_id or not chat_id: return False
        result = await self.chat_history_collection.delete_one({"user_id": user_id, "chat_id": chat_id})
        return result.deleted_count > 0
        
    # --- Notification Methods ---
    async def get_notifications(self, user_id: str) -> List[Dict]:
        if not user_id: return []
        user_doc = await self.notifications_collection.find_one({"user_id": user_id})
        return user_doc.get("notifications", []) if user_doc else []

    async def add_notification(self, user_id: str, notification_data: Dict) -> bool:
        if not user_id or not notification_data: return False
        
        notification_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        notification_data["id"] = str(uuid.uuid4()) # Ensure unique ID for notification

        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$push": {"notifications": {"$each": [notification_data], "$slice": -50}}, # Keep last 50
             "$setOnInsert": {"user_id": user_id, "created_at": datetime.datetime.now(datetime.timezone.utc)}
            }, 
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def clear_notifications(self, user_id: str) -> bool:
        if not user_id: return False
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$set": {"notifications": []}} 
        )
        # Success if a document was matched (and updated) or if a new one was upserted (though less likely for clear)
        return result.matched_count > 0 or result.upserted_id is not None
    
    # Generic collection getter - Remove if not broadly used, or restrict to known collections
    async def get_collection(self, collection_name: str):
        # List of known/allowed collection names for safety
        allowed_collections = [
            USER_PROFILES_COLLECTION, CHAT_HISTORY_COLLECTION, NOTIFICATIONS_COLLECTION,
            POLLING_STATE_COLLECTION, PROCESSED_ITEMS_COLLECTION
        ]
        if collection_name not in allowed_collections:
            raise ValueError(f"Access to collection '{collection_name}' is not allowed or it's unknown.")
        return self.db[collection_name]