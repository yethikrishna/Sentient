# src/server/workers/pollers/gmail/db_utils.py
# Replicated MongoManager, tailored for poller needs
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError
from typing import Dict, List, Optional, Any
import datetime
from datetime import timezone # Ensure timezone imported

from workers.poller.gmail.config import MONGO_URI, MONGO_DB_NAME # Import from local config

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

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def get_polling_state(self, user_id: str, service_name: str, poll_type: str) -> Optional[Dict[str, Any]]:
        return await self.polling_state_collection.find_one({"user_id": user_id, "service_name": service_name, "poll_type": poll_type})

    async def update_polling_state(self, user_id: str, service_name: str, poll_type: str, state_data: Dict[str, Any]) -> bool:
        for key, value in state_data.items():
            if isinstance(value, datetime.datetime):
                state_data[key] = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        
        now_utc = datetime.datetime.now(timezone.utc)
        state_data["last_updated_at"] = now_utc

        # Do not attempt to re-set fields that are part of the unique index or are immutable.
        # This prevents the "Updating the path 'user_id' would create a conflict" error.
        if '_id' in state_data:
            del state_data['_id']
        if 'user_id' in state_data:
            del state_data['user_id']
        if 'service_name' in state_data:
            del state_data['service_name']
        if 'poll_type' in state_data:
            del state_data['poll_type']
        if 'created_at' in state_data: # Should only be set on insert
            del state_data['created_at']

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name, "poll_type": poll_type},
            {"$set": state_data, "$setOnInsert": {"created_at": now_utc, "user_id": user_id, "service_name": service_name, "poll_type": poll_type}},
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_due_polling_tasks_for_service(self, service_name: str, poll_type: str) -> List[Dict[str, Any]]:
        now_utc = datetime.datetime.now(timezone.utc)

        # For 'triggers', we only want to poll users who have active triggered tasks.
        if poll_type == 'triggers':
            pipeline = [
                # Stage 1: Find due polling states
                {
                    "$match": {
                        "service_name": service_name,
                        "poll_type": poll_type,
                        "is_enabled": True,
                        "next_scheduled_poll_time": {"$lte": now_utc},
                        "is_currently_polling": False,
                        "$or": [
                            {"error_backoff_until_timestamp": None},
                            {"error_backoff_until_timestamp": {"$lte": now_utc}}
                        ]
                    }
                },
                # Stage 2: Join with tasks collection to check for active triggers
                {
                    "$lookup": {
                        "from": "tasks", # The name of the tasks collection
                        "localField": "user_id",
                        "foreignField": "user_id",
                        "as": "user_tasks"
                    }
                },
                # Stage 3: Filter for users who have at least one active triggered task for this specific service
                {
                    "$match": {
                        "user_tasks": {
                            "$elemMatch": {
                                "status": "active",
                                "schedule.type": "triggered",
                                "schedule.source": service_name
                            }
                        }
                    }
                },
                {"$sort": {"next_scheduled_poll_time": ASCENDING}}
            ]
            cursor = self.polling_state_collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        else:
            # Original logic for other poll types like 'proactivity'
            query = {
                "service_name": service_name, "poll_type": poll_type,
                "is_enabled": True,
                "next_scheduled_poll_time": {"$lte": now_utc},
                "is_currently_polling": False,
                "$or": [{"error_backoff_until_timestamp": None}, {"error_backoff_until_timestamp": {"$lte": now_utc}}]
            }
            cursor = self.polling_state_collection.find(query).sort("next_scheduled_poll_time", ASCENDING)
            return await cursor.to_list(length=None)

    async def set_polling_status_and_get(self, user_id: str, service_name: str, poll_type: str) -> Optional[Dict[str, Any]]:
        now_utc = datetime.datetime.now(timezone.utc)
        doc = await self.polling_state_collection.find_one_and_update(
            {"user_id": user_id, "service_name": service_name, "poll_type": poll_type, "is_enabled": True,
             "next_scheduled_poll_time": {"$lte": now_utc}, "is_currently_polling": False,
             "$or": [{"error_backoff_until_timestamp": None}, {"error_backoff_until_timestamp": {"$lte": now_utc}}]},
            {"$set": {"is_currently_polling": True, "last_attempted_poll_timestamp": now_utc}},
            return_document=ReturnDocument.AFTER
        )
        return doc
    
    async def reset_stale_polling_locks(self, service_name: str, poll_type: str, timeout_minutes: int = 30):
        stale_threshold = datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=timeout_minutes)
        result = await self.polling_state_collection.update_many(
            {"service_name": service_name, "poll_type": poll_type, "is_currently_polling": True, "last_attempted_poll_timestamp": {"$lt": stale_threshold}},
            {"$set": {"is_currently_polling": False, "last_successful_poll_status_message": "Reset stale lock.",
                      "next_scheduled_poll_time": datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=60)}}
        )
        if result.modified_count > 0:
            print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] Reset {result.modified_count} stale GMAIL polling locks.")

    async def log_processed_item(self, user_id: str, service_name: str, item_id: str, processor: str) -> bool:
        """Logs that an item has been processed by a specific system (e.g., 'proactivity', 'triggers')."""
        try:
            await self.processed_items_collection.update_one(
                {"user_id": user_id, "service_name": service_name, "item_id": item_id},
                {
                    "$addToSet": {"processed_by": processor},
                    "$setOnInsert": {
                        "user_id": user_id, "service_name": service_name, "item_id": item_id,
                        "processing_timestamp": datetime.datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPoller_DB_ERROR] Logging processed item {user_id}/{service_name}/{item_id} by {processor}: {e}")
            return False

    async def is_item_processed(self, user_id: str, service_name: str, item_id: str, processor: str) -> bool:
        """Checks if an item has already been processed by a specific system."""
        doc = await self.processed_items_collection.find_one(
            {"user_id": user_id, "service_name": service_name, "item_id": item_id}
        )
        if doc and processor in doc.get("processed_by", []):
            return True
        return False

    async def close(self):
        if self.client:
            self.client.close()
            print(f"[{datetime.datetime.now()}] [GmailPoller_MongoManager] MongoDB connection closed.")