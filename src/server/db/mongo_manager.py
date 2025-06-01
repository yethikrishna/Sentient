import os
import datetime
import uuid # For generating unique IDs
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel
from typing import Dict, List, Optional, Any

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")
USER_PROFILES_COLLECTION = "user_profiles"
CHAT_HISTORY_COLLECTION = "chat_history"
NOTIFICATIONS_COLLECTION = "notifications" # Added for app/helpers.py migration
CONTEXT_ENGINE_STATE_COLLECTION = "context_engine_states"

class MongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.chat_history_collection = self.db[CHAT_HISTORY_COLLECTION]
        self.notifications_collection = self.db[NOTIFICATIONS_COLLECTION]
        self.context_engine_state_collection = self.db[CONTEXT_ENGINE_STATE_COLLECTION]

    async def initialize_db(self):
        """
        Initializes the database by ensuring necessary indexes are created for all collections.
        Should be called once on application startup.
        """
        print("[DB_INIT] Ensuring indexes for MongoManager collections...")
        # User Profiles Indexes
        user_profile_indexes = [
            IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique_idx")
        ]
        try:
            await self.user_profiles_collection.create_indexes(user_profile_indexes)
            print(f"[DB_INIT] Indexes ensured for collection: {self.user_profiles_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Failed to create indexes for {self.user_profiles_collection.name}: {e}")

        # Chat History Indexes
        chat_history_indexes = [
            IndexModel([("user_id", ASCENDING), ("chat_id", ASCENDING)], name="user_chat_id_idx"),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)], name="user_timestamp_idx")
        ]
        try:
            await self.chat_history_collection.create_indexes(chat_history_indexes)
            print(f"[DB_INIT] Indexes ensured for collection: {self.chat_history_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Failed to create indexes for {self.chat_history_collection.name}: {e}")

        # Notifications Indexes
        notifications_indexes = [
            IndexModel([("user_id", ASCENDING)], unique=True, name="notification_user_id_unique_idx")
        ]
        try:
            await self.notifications_collection.create_indexes(notifications_indexes)
            print(f"[DB_INIT] Indexes ensured for collection: {self.notifications_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Failed to create indexes for {self.notifications_collection.name}: {e}")

        # Context Engine State Indexes
        context_engine_indexes = [
            IndexModel([("user_id", ASCENDING), ("engine_category", ASCENDING)], unique=True, name="user_engine_category_unique_idx")
        ]
        try:
            await self.context_engine_state_collection.create_indexes(context_engine_indexes)
            print(f"[DB_INIT] Indexes ensured for collection: {self.context_engine_state_collection.name}")
        except Exception as e:
            print(f"[DB_ERROR] Failed to create indexes for {self.context_engine_state_collection.name}: {e}")


    # --- User Profile Methods ---
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Retrieve a user's profile."""
        if not user_id:
            return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Update or create a user's profile."""
        if not user_id or not profile_data:
            return False
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile_data},
            upsert=True # Create if not exists
        )
        # The operation is considered successful if a document was matched/modified or a new one was upserted.
        # This handles cases where data is identical, but the intent was still to "save".
        return result.matched_count > 0 or result.upserted_id is not None

    # --- Chat History Methods ---
    async def add_chat_message(self, user_id: str, chat_id: str, message_data: Dict) -> str:
        """Add a new message to a user's chat history."""
        if not user_id or not chat_id or not message_data:
            raise ValueError("user_id, chat_id, and message_data are required.")
        
        message_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        message_data["message_id"] = str(uuid.uuid4()) # Unique ID for each message

        # Find the chat document and push the new message to its 'messages' array
        result = await self.chat_history_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$push": {"messages": message_data},
             "$set": {"last_updated": datetime.datetime.now(datetime.timezone.utc)}},
            upsert=True
        )
        if result.modified_count == 0 and result.upserted_id is None:
            raise Exception("Failed to add chat message.")
        return message_data["message_id"]

    async def get_chat_history(self, user_id: str, chat_id: str) -> Optional[List[Dict]]:
        """Retrieve chat history for a specific chat_id and user_id."""
        if not user_id or not chat_id:
            return None
        chat_doc = await self.chat_history_collection.find_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"messages": 1} # Only retrieve the messages array
        )
        return chat_doc.get("messages", []) if chat_doc else []

    async def get_all_chat_ids_for_user(self, user_id: str) -> List[str]:
        """Retrieve all chat IDs for a given user."""
        # Modified to sort by last_updated to help determine the most recent chat
        if not user_id:
            return []
        cursor = self.chat_history_collection.find(
            {"user_id": user_id}, {"chat_id": 1, "last_updated": 1}
        ).sort("last_updated", DESCENDING)
        chat_ids = [doc["chat_id"] for doc in await cursor.to_list(length=None)]
        return chat_ids

    async def delete_chat_history(self, user_id: str, chat_id: str) -> bool:
        """Delete chat history for a specific chat_id and user_id."""
        if not user_id or not chat_id:
            return False
        result = await self.chat_history_collection.delete_one({"user_id": user_id, "chat_id": chat_id})
        return result.deleted_count > 0

    # --- Notifications Methods ---
    async def get_notifications(self, user_id: str) -> List[Dict]:
        """Retrieve all notifications for a user."""
        if not user_id:
            return []
        # Notifications are stored as an array within a single user document
        user_doc = await self.notifications_collection.find_one({"user_id": user_id})
        return user_doc.get("notifications", []) if user_doc else []

    async def add_notification(self, user_id: str, notification_data: Dict) -> bool:
        """Add a new notification for a user."""
        if not user_id or not notification_data:
            return False
        
        notification_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        notification_data["notification_id"] = str(uuid.uuid4())

        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$push": {"notifications": notification_data}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def clear_notifications(self, user_id: str) -> bool:
        """Clear all notifications for a user."""
        if not user_id:
            return False
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$set": {"notifications": []}}
        )
        return result.modified_count > 0

    # --- Context Engine State Methods ---
    async def get_context_engine_state(self, user_id: str, engine_category: str) -> Optional[Dict]:
        """Retrieve the state for a specific context engine for a user."""
        if not user_id or not engine_category:
            return None
        state_doc = await self.context_engine_state_collection.find_one(
            {"user_id": user_id, "engine_category": engine_category}
        )
        return state_doc.get("state_data") if state_doc else None

    async def update_context_engine_state(self, user_id: str, engine_category: str, state_data: Dict) -> bool:
        """Update or create the state for a specific context engine for a user."""
        if not user_id or not engine_category or state_data is None: # Allow empty dict for state_data
            return False
        result = await self.context_engine_state_collection.update_one(
            {"user_id": user_id, "engine_category": engine_category},
            {"$set": {"state_data": state_data, "last_updated": datetime.datetime.now(datetime.timezone.utc)}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None