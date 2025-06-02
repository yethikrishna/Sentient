import os
import datetime
import uuid # For generating unique IDs
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from typing import Dict, List, Optional, Any

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")
USER_PROFILES_COLLECTION = "user_profiles"
CHAT_HISTORY_COLLECTION = "chat_history"
NOTIFICATIONS_COLLECTION = "notifications"
CONTEXT_ENGINE_STATES_COLLECTION = "context_engine_states" # Used for dynamic polling state
MEMORY_COLLECTION_NAME = "memory_operations"

class MongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.chat_history_collection = self.db[CHAT_HISTORY_COLLECTION]
        self.notifications_collection = self.db[NOTIFICATIONS_COLLECTION]
        self.context_engine_states_collection = self.db[CONTEXT_ENGINE_STATES_COLLECTION]
        self.memory_collection = self.db[MEMORY_COLLECTION_NAME]

    async def initialize_db(self):
        print("[DB_INIT] Ensuring indexes for MongoManager collections...")
        # User Profiles Indexes
        user_profile_indexes = [
            IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique_idx"),
            IndexModel([("userData.last_active_timestamp", DESCENDING)], name="user_last_active_idx") # For activity
        ]
        try:
            await self.user_profiles_collection.create_indexes(user_profile_indexes)
            print(f"[DB_INIT] Indexes ensured for: {self.user_profiles_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Index creation for {self.user_profiles_collection.name}: {e}")

        # Chat History Indexes
        chat_history_indexes = [
            IndexModel([("user_id", ASCENDING), ("chat_id", ASCENDING)], name="user_chat_id_idx"),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)], name="user_timestamp_idx")
        ]
        try:
            await self.chat_history_collection.create_indexes(chat_history_indexes)
            print(f"[DB_INIT] Indexes ensured for: {self.chat_history_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Index creation for {self.chat_history_collection.name}: {e}")
        
        # Notifications Indexes
        notifications_indexes = [
            IndexModel([("user_id", ASCENDING)], name="notification_user_id_idx")
        ]
        try:
            await self.notifications_collection.create_indexes(notifications_indexes)
            print(f"[DB_INIT] Indexes ensured for: {self.notifications_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Index creation for {self.notifications_collection.name}: {e}")

        # Context Engine State (Polling State) Indexes
        context_engine_states_indexes = [
            IndexModel([("user_id", ASCENDING), ("engine_category", ASCENDING)], unique=True, name="polling_user_engine_category_unique_idx"),
            IndexModel([("next_scheduled_poll_timestamp", ASCENDING), ("is_currently_polling", ASCENDING)], name="polling_due_tasks_idx"),
            IndexModel([("is_currently_polling", ASCENDING)], name="polling_is_polling_idx")
        ]
        try:
            await self.context_engine_states_collection.create_indexes(context_engine_states_indexes)
            print(f"[DB_INIT] Indexes ensured for: {self.context_engine_states_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Index creation for {self.context_engine_states_collection.name}: {e}")
        
        memory_operations_indexes = [
            IndexModel([("user_id", ASCENDING), ("operation_id", ASCENDING)], name="mem_op_user_operation_id_idx", unique=True),
            IndexModel([("status", ASCENDING), ("timestamp", ASCENDING)], name="mem_op_global_pending_operations_idx"),
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="mem_op_user_status_idx"),
            IndexModel([("user_id", ASCENDING), ("timestamp", ASCENDING)], name="mem_op_user_timestamp_idx"),
            IndexModel([("status", ASCENDING), ("completed_at", ASCENDING)], name="mem_op_global_completed_operations_idx")
        ]
        try:
            await self.memory_collection.create_indexes(memory_operations_indexes)
            print(f"[DB_INIT] Indexes ensured for: {self.memory_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Index creation for {self.memory_collection.name}: {e}")


    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        if not user_id: return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        if not user_id or not profile_data: return False
        if "_id" in profile_data: del profile_data["_id"]
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id}, {"$set": profile_data}, upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def update_user_last_active(self, user_id: str) -> bool:
        if not user_id: return False
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {"userData.last_active_timestamp": now_utc, "userData.last_updated": now_utc}}, # Ensure last_updated is also set
            upsert=True # Create userData if it doesn't exist
        )
        # If upsert creates userData, ensure user_id field exists at top level
        if result.upserted_id:
             await self.user_profiles_collection.update_one({"_id": result.upserted_id}, {"$setOnInsert": {"user_id": user_id}})
        return result.matched_count > 0 or result.upserted_id is not None
        
    async def get_user_activity_and_timezone(self, user_id: str) -> Dict[str, Any]:
        profile = await self.get_user_profile(user_id)
        if profile and profile.get("userData"):
            return {
                "last_active_timestamp": profile["userData"].get("last_active_timestamp"),
                "timezone": profile["userData"].get("personalInfo", {}).get("timezone") # Assuming timezone is in personalInfo
            }
        return {"last_active_timestamp": None, "timezone": None}

    async def get_polling_state(self, user_id: str, engine_category: str) -> Optional[Dict[str, Any]]:
        if not user_id or not engine_category: return None
        return await self.context_engine_states_collection.find_one(
            {"user_id": user_id, "engine_category": engine_category}
        )

    async def update_polling_state(self, user_id: str, engine_category: str, state_data: Dict[str, Any]) -> bool:
        if not user_id or not engine_category or state_data is None: return False
        
        # Ensure all datetimes are BSON compatible
        for key, value in state_data.items():
            if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                state_data[key] = datetime.datetime.combine(value, datetime.time.min, tzinfo=datetime.timezone.utc)
            elif isinstance(value, datetime.datetime) and value.tzinfo is None:
                 state_data[key] = value.replace(tzinfo=datetime.timezone.utc)


        result = await self.context_engine_states_collection.update_one(
            {"user_id": user_id, "engine_category": engine_category},
            {"$set": state_data, "$setOnInsert": {"created_at": datetime.datetime.now(datetime.timezone.utc)}},
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_due_polling_tasks(self) -> List[Dict[str, Any]]:
        """Fetches polling tasks that are due and not currently polling."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cursor = self.context_engine_states_collection.find({
            "next_scheduled_poll_timestamp": {"$lte": now_utc},
            "is_currently_polling": False
        }).sort("next_scheduled_poll_timestamp", ASCENDING) # Prioritize older due tasks
        return await cursor.to_list(length=None)

    async def set_polling_status_and_get(self, user_id: str, engine_category: str) -> Optional[Dict[str, Any]]:
        """Atomically sets is_currently_polling to True and returns the document if successful."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Find a task that is due and not polling, and set its polling status to true
        doc = await self.context_engine_states_collection.find_one_and_update(
            {
                "user_id": user_id, 
                "engine_category": engine_category,
                "next_scheduled_poll_timestamp": {"$lte": now_utc},
                "is_currently_polling": False
            },
            {"$set": {"is_currently_polling": True, "last_attempted_poll_timestamp": now_utc}},
            return_document=ReturnDocument.AFTER
        )
        return doc

    async def release_polling_lock(self, user_id: str, engine_category: str, next_poll_at: datetime.datetime, 
                                   last_successful_poll_at: Optional[datetime.datetime] = None,
                                   last_marker: Optional[str] = None, tier: Optional[str] = None,
                                   failures: Optional[int] = None) -> bool:
        """Releases the polling lock and updates scheduling info."""
        update_fields = {
            "is_currently_polling": False,
            "next_scheduled_poll_timestamp": next_poll_at.replace(tzinfo=datetime.timezone.utc) if next_poll_at.tzinfo is None else next_poll_at,
        }
        if last_successful_poll_at is not None:
            update_fields["last_successful_poll_timestamp"] = last_successful_poll_at.replace(tzinfo=datetime.timezone.utc) if last_successful_poll_at.tzinfo is None else last_successful_poll_at
        if last_marker is not None:
            update_fields["last_processed_item_marker"] = last_marker
        if tier is not None:
            update_fields["current_polling_tier"] = tier
        if failures is not None:
            update_fields["consecutive_failure_count"] = failures
        
        result = await self.context_engine_states_collection.update_one(
            {"user_id": user_id, "engine_category": engine_category},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    # ... (other methods like chat history, notifications, etc., remain the same) ...
    async def add_chat_message(self, user_id: str, chat_id: str, message_data: Dict) -> str:
        if not user_id or not chat_id or not message_data:
            raise ValueError("user_id, chat_id, and message_data are required.")
        message_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        message_id = str(uuid.uuid4()) 
        message_data["id"] = message_id
        result = await self.chat_history_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$push": {"messages": message_data},
             "$set": {"last_updated": datetime.datetime.now(datetime.timezone.utc)}},
            upsert=True
        )
        if result.modified_count == 0 and result.upserted_id is None:
            raise Exception("Failed to add chat message.")
        return message_id

    async def get_chat_history(self, user_id: str, chat_id: str) -> Optional[List[Dict]]:
        if not user_id or not chat_id: return None
        chat_doc = await self.chat_history_collection.find_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"messages": 1, "_id": 0} 
        )
        return chat_doc.get("messages", []) if chat_doc else []

    async def get_all_chat_ids_for_user(self, user_id: str) -> List[str]:
        if not user_id: return []
        cursor = self.chat_history_collection.find(
            {"user_id": user_id}, {"chat_id": 1, "_id": 0} 
        ).sort("last_updated", DESCENDING) 
        chat_ids = [doc["chat_id"] for doc in await cursor.to_list(length=None)] 
        return chat_ids

    async def delete_chat_history(self, user_id: str, chat_id: str) -> bool:
        if not user_id or not chat_id: return False
        result = await self.chat_history_collection.delete_one({"user_id": user_id, "chat_id": chat_id})
        return result.deleted_count > 0

    async def get_notifications(self, user_id: str) -> List[Dict]:
        if not user_id: return []
        user_doc = await self.notifications_collection.find_one({"user_id": user_id})
        return user_doc.get("notifications", []) if user_doc else []

    async def add_notification(self, user_id: str, notification_data: Dict) -> bool:
        if not user_id or not notification_data: return False
        notification_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        notification_data["id"] = str(uuid.uuid4())
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$push": {"notifications": {"$each": [notification_data], "$slice": -50}}}, 
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def clear_notifications(self, user_id: str) -> bool:
        if not user_id: return False
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$set": {"notifications": []}} 
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_collection(self, collection_name: str):
        if not hasattr(self.db, collection_name):
            raise ValueError(f"Collection '{collection_name}' not found in database '{self.db.name}'.")
        return self.db[collection_name]