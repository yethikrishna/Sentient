import os
import datetime
import uuid 
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError
from typing import Dict, List, Optional, Any, Tuple # Added Tuple

from server.common_lib.utils.config import MONGO_URI, MONGO_DB_NAME

USER_PROFILES_COLLECTION = "user_profiles" 
CHAT_HISTORY_COLLECTION = "chat_history" 
NOTIFICATIONS_COLLECTION = "notifications" 
POLLING_STATE_COLLECTION = "polling_state_store"
PROCESSED_ITEMS_COLLECTION = "processed_items_log"
CONSUMED_KAFKA_MESSAGES_COLLECTION = "consumed_kafka_messages" # For context_operations

class MongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.chat_history_collection = self.db[CHAT_HISTORY_COLLECTION]
        self.notifications_collection = self.db[NOTIFICATIONS_COLLECTION]
        self.polling_state_collection = self.db[POLLING_STATE_COLLECTION]
        self.processed_items_collection = self.db[PROCESSED_ITEMS_COLLECTION]
        self.consumed_kafka_messages_collection = self.db[CONSUMED_KAFKA_MESSAGES_COLLECTION]
        
        print(f"[{datetime.datetime.now()}] [MongoManager] Initialized. Database: {MONGO_DB_NAME}")

    async def initialize_db(self):
        print(f"[{datetime.datetime.now()}] [DB_INIT] Ensuring indexes for MongoManager collections...")
        
        collections_with_indexes = {
            self.user_profiles_collection: [
                IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique_idx"),
                IndexModel([("userData.last_active_timestamp", DESCENDING)], name="user_last_active_idx")
            ],
            self.chat_history_collection: [
                IndexModel([("user_id", ASCENDING), ("chat_id", ASCENDING)], name="user_chat_id_idx"),
                IndexModel([("user_id", ASCENDING), ("last_updated", DESCENDING)], name="chat_last_updated_idx"),
                IndexModel([("user_id", ASCENDING), ("messages.timestamp", DESCENDING)], name="message_timestamp_idx", sparse=True)
            ],
            self.notifications_collection: [
                IndexModel([("user_id", ASCENDING)], name="notification_user_id_idx"),
                IndexModel([("user_id", ASCENDING), ("notifications.timestamp", DESCENDING)], name="notification_timestamp_idx", sparse=True)
            ],
            self.polling_state_collection: [
                IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING)], unique=True, name="polling_user_service_unique_idx"),
                IndexModel([
                    ("is_enabled", ASCENDING), 
                    ("next_scheduled_poll_time", ASCENDING), 
                    ("is_currently_polling", ASCENDING),
                    ("error_backoff_until_timestamp", ASCENDING) 
                ], name="polling_due_tasks_idx"),
                IndexModel([("is_currently_polling", ASCENDING), ("last_attempted_poll_timestamp", ASCENDING)], name="polling_stale_locks_idx")
            ],
            self.processed_items_collection: [
                IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING), ("item_id", ASCENDING)], unique=True, name="processed_item_unique_idx"),
                IndexModel([("processing_timestamp", DESCENDING)], name="processed_timestamp_idx", expireAfterSeconds=2592000) # Expire after 30 days
            ],
            self.consumed_kafka_messages_collection: [
                IndexModel([("consumed_at_utc", DESCENDING)], name="kafka_consumed_at_idx", expireAfterSeconds=604800) # Expire after 7 days
            ]
        }

        for collection, indexes in collections_with_indexes.items():
            try:
                await collection.create_indexes(indexes)
                print(f"[{datetime.datetime.now()}] [DB_INIT] Indexes ensured for: {collection.name}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [DB_ERROR] Index creation for {collection.name}: {e}")

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        if not user_id: return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        if not user_id or not profile_data: return False
        if "_id" in profile_data: del profile_data["_id"] 
        
        update_operations = {"$set": {}, "$setOnInsert": {}}
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for key, value in profile_data.items():
            update_operations["$set"][key] = value
        
        update_operations["$set"]["last_updated"] = now_utc
        update_operations["$setOnInsert"]["user_id"] = user_id
        update_operations["$setOnInsert"]["createdAt"] = now_utc
        update_operations["$setOnInsert"]["userData"] = {} # Ensure userData field exists on insert

        # Ensure empty $set or $setOnInsert are removed to avoid MongoDB errors
        if not update_operations["$set"]: del update_operations["$set"]
        if not update_operations["$setOnInsert"]: del update_operations["$setOnInsert"]
        if not update_operations: return False

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
            "last_updated": now_utc
        }
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": update_payload, "$setOnInsert": {"user_id": user_id, "createdAt": now_utc, "userData": {}}},
            upsert=True 
        )
        return result.matched_count > 0 or result.upserted_id is not None
        
    async def get_polling_state(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]: 
        if not user_id or not service_name: return None
        return await self.polling_state_collection.find_one(
            {"user_id": user_id, "service_name": service_name}
        )

    async def update_polling_state(self, user_id: str, service_name: str, state_data: Dict[str, Any]) -> bool: 
        if not user_id or not service_name or state_data is None: return False
        
        for key, value in state_data.items():
            if isinstance(value, datetime.datetime):
                state_data[key] = value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
            elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                 state_data[key] = datetime.datetime.combine(value, datetime.time.min, tzinfo=datetime.timezone.utc)
        
        if "_id" in state_data: del state_data["_id"]
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        state_data["last_updated_at"] = now_utc

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name}, 
            {"$set": state_data, "$setOnInsert": {"created_at": now_utc, "user_id": user_id, "service_name": service_name}}, 
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
        return await cursor.to_list(length=None)

    async def set_polling_status_and_get(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]: 
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        doc = await self.polling_state_collection.find_one_and_update(
            {
                "user_id": user_id, 
                "service_name": service_name, 
                "is_enabled": True,
                "next_scheduled_poll_time": {"$lte": now_utc},
                "is_currently_polling": False,
                "$or": [
                    {"error_backoff_until_timestamp": None},
                    {"error_backoff_until_timestamp": {"$lte": now_utc}}
                ]
            },
            {"$set": {"is_currently_polling": True, "last_attempted_poll_timestamp": now_utc}},
            return_document=ReturnDocument.AFTER
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
                    "next_scheduled_poll_time": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60) 
                }
            }
        )
        if result.modified_count > 0:
            print(f"[{datetime.datetime.now()}] [MongoManager] Reset {result.modified_count} stale polling locks.")
        return result.modified_count

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
        except DuplicateKeyError:
            print(f"[{datetime.datetime.now()}] [ProcessedItemsLog] Item {user_id}/{service_name}/{item_id} already processed.")
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ProcessedItemsLog_ERROR] Error logging item {user_id}/{service_name}/{item_id}: {e}")
            return False

    async def is_item_processed(self, user_id: str, service_name: str, item_id: str) -> bool:
        if not user_id or not service_name or not item_id: return True
        count = await self.processed_items_collection.count_documents({
            "user_id": user_id,
            "service_name": service_name,
            "item_id": item_id
        })
        return count > 0
    
    async def add_chat_message(self, user_id: str, chat_id: str, message_data: Dict) -> str:
        if not user_id or not chat_id or not message_data:
            raise ValueError("user_id, chat_id, and message_data are required.")
        
        message_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
        message_id = message_data.get("id", str(uuid.uuid4())) 
        message_data["id"] = message_id

        result = await self.chat_history_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$push": {"messages": message_data},
             "$set": {"last_updated": datetime.datetime.now(datetime.timezone.utc)},
             "$setOnInsert": {"user_id": user_id, "chat_id": chat_id, "created_at": datetime.datetime.now(datetime.timezone.utc)}
            },
            upsert=True
        )
        # Check if the operation was successful (either matched and modified, or upserted)
        if result.matched_count > 0 or result.upserted_id is not None:
            return message_id
        else:
            raise Exception(f"Failed to add/update chat message for user {user_id}, chat {chat_id}")


    async def get_chat_history(self, user_id: str, chat_id: str) -> List[Dict]: # Return List[Dict] instead of Optional
        if not user_id or not chat_id: return []
        chat_doc = await self.chat_history_collection.find_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"messages": 1, "_id": 0}
        )
        return chat_doc.get("messages", []) if chat_doc else []

    async def get_all_chat_ids_for_user(self, user_id: str) -> List[str]:
        if not user_id: return []
        cursor = self.chat_history_collection.find(
            {"user_id": user_id}, {"chat_id": 1, "last_updated":1, "_id": 0}
        ).sort("last_updated", DESCENDING)
        chat_docs = await cursor.to_list(length=None)
        return [doc["chat_id"] for doc in chat_docs]


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
            {"$push": {"notifications": {"$each": [notification_data], "$slice": -50}},
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
        return result.matched_count > 0

    async def store_consumed_kafka_message(self, message_doc: Dict) -> bool:
        if not message_doc: return False
        try:
            await self.consumed_kafka_messages_collection.insert_one(message_doc)
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [MongoManager_ERROR] Failed to store consumed Kafka message: {e}")
            return False