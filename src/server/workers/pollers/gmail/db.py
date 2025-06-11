# src/server/workers/pollers/gmail/db_utils.py
# Replicated MongoManager, tailored for poller needs
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError
from typing import Dict, List, Optional, Any
import datetime
from datetime import timezone # Ensure timezone imported

from .config import MONGO_URI, MONGO_DB_NAME # Import from local config

USER_PROFILES_COLLECTION = "user_profiles"
POLLING_STATE_COLLECTION = "polling_state_store"
PROCESSED_ITEMS_COLLECTION = "processed_items_log"

class PollerMongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.polling_state_collection = self.db[POLLING_STATE_COLLECTION]
        self.processed_items_collection = self.db[PROCESSED_ITEMS_COLLECTION]
        print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] Initialized for poller.")

    async def initialize_indices_if_needed(self):
        # Simplified: Main server usually handles index creation. Poller assumes they exist.
        # Or, replicate specific index checks if this poller might run before main server.
        print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] Assuming indexes are managed by main server.")
        pass

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def get_polling_state(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        return await self.polling_state_collection.find_one({"user_id": user_id, "service_name": service_name})

    async def update_polling_state(self, user_id: str, service_name: str, state_data: Dict[str, Any]) -> bool:
        for key, value in state_data.items():
            if isinstance(value, datetime.datetime):
                state_data[key] = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        
        now_utc = datetime.datetime.now(timezone.utc)
        state_data["last_updated_at"] = now_utc

        # Do not attempt to re-set fields that should be immutable after creation.
        if 'created_at' in state_data:
            del state_data['created_at']

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name},
            {"$set": state_data, "$setOnInsert": {"created_at": now_utc, "user_id": user_id, "service_name": service_name}},
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_due_polling_tasks_for_service(self, service_name: str) -> List[Dict[str, Any]]:
        now_utc = datetime.datetime.now(timezone.utc)
        query = {
            "service_name": service_name,
            "is_enabled": True,
            "next_scheduled_poll_time": {"$lte": now_utc},
            "is_currently_polling": False,
            "$or": [{"error_backoff_until_timestamp": None}, {"error_backoff_until_timestamp": {"$lte": now_utc}}]
        }
        cursor = self.polling_state_collection.find(query).sort("next_scheduled_poll_time", ASCENDING)
        return await cursor.to_list(length=None) # Get all due tasks for this service

    async def set_polling_status_and_get(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        now_utc = datetime.datetime.now(timezone.utc)
        doc = await self.polling_state_collection.find_one_and_update(
            {"user_id": user_id, "service_name": service_name, "is_enabled": True, 
             "next_scheduled_poll_time": {"$lte": now_utc}, "is_currently_polling": False,
             "$or": [{"error_backoff_until_timestamp": None}, {"error_backoff_until_timestamp": {"$lte": now_utc}}]},
            {"$set": {"is_currently_polling": True, "last_attempted_poll_timestamp": now_utc}},
            return_document=ReturnDocument.AFTER
        )
        return doc
    
    async def reset_stale_polling_locks(self, service_name: str, timeout_minutes: int = 30):
        stale_threshold = datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=timeout_minutes)
        result = await self.polling_state_collection.update_many(
            {"service_name": service_name, "is_currently_polling": True, "last_attempted_poll_timestamp": {"$lt": stale_threshold}},
            {"$set": {"is_currently_polling": False, "last_successful_poll_status_message": "Reset stale lock.",
                      "next_scheduled_poll_time": datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=60)}}
        )
        if result.modified_count > 0:
            print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] Reset {result.modified_count} stale GMAIL polling locks.")


    async def log_processed_item(self, user_id: str, service_name: str, item_id: str) -> bool:
        try:
            await self.processed_items_collection.insert_one({
                "user_id": user_id, "service_name": service_name, "item_id": item_id,
                "processing_timestamp": datetime.datetime.now(timezone.utc)
            })
            return True
        except DuplicateKeyError: return True # Already processed
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPoller_DB_ERROR] Logging processed item {user_id}/{service_name}/{item_id}: {e}")
            return False

    async def is_item_processed(self, user_id: str, service_name: str, item_id: str) -> bool:
        count = await self.processed_items_collection.count_documents(
            {"user_id": user_id, "service_name": service_name, "item_id": item_id}
        )
        return count > 0

    async def close(self):
        if self.client:
            self.client.close()
            print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] MongoDB connection closed.")