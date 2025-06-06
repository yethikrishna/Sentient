# src/server/queues/context-operations/db_utils.py
# Replicated MongoManager, tailored for queue needs
import motor.motor_asyncio
from pymongo import IndexModel, DESCENDING
from typing import Dict, Optional
import datetime

from .config import MONGO_URI, MONGO_DB_NAME

# Collection for storing data processed by this queue worker, if needed beyond just printing.
# Or, this worker might update user_profiles directly. For simplicity, let's assume
# it stores a log of consumed messages, and potentially updates user context in user_profiles.
CONSUMED_KAFKA_MESSAGES_COLLECTION = "consumed_kafka_messages_log" 
USER_CONTEXT_COLLECTION = "user_context_data" # Example: if storing aggregated context

class ContextQueueMongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.consumed_log_collection = self.db[CONSUMED_KAFKA_MESSAGES_COLLECTION]
        self.user_context_collection = self.db[USER_CONTEXT_COLLECTION] # If used
        print(f"[{datetime.datetime.now()}] [ContextQueue_MongoManager] Initialized.")

    async def initialize_indices_if_needed(self):
        print(f"[{datetime.datetime.now()}] [ContextQueue_DB_INIT] Ensuring indexes...")
        await self.consumed_log_collection.create_indexes([
            IndexModel([("consumed_at_utc", DESCENDING)], name="kafka_consumed_at_idx", expireAfterSeconds=604800) # Expire after 7 days
        ])
        # Add indexes for user_context_collection if it's used
        print(f"[{datetime.datetime.now()}] [ContextQueue_DB_INIT] Indexes ensured for consumed_log.")
        pass

    async def log_consumed_message(self, message_payload: Dict) -> bool:
        try:
            doc = {
                "topic": message_payload.get("topic", "unknown"),
                "partition": message_payload.get("partition", -1),
                "offset": message_payload.get("offset", -1),
                "key": message_payload.get("key"),
                "value": message_payload.get("value"), # The actual data from Kafka
                "consumed_at_utc": datetime.datetime.now(datetime.timezone.utc)
            }
            await self.consumed_log_collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ContextQueue_DB_ERROR] Logging consumed message: {e}")
            return False
            
    async def store_user_context_data(self, user_id: str, service_name: str, item_id: str, data_to_store: Dict) -> bool:
        """
        Example: Stores or updates context data for a user from a specific service.
        This is a placeholder for actual context storage logic.
        """
        if not all([user_id, service_name, item_id, data_to_store]): return False
        try:
            # Example: Store each item with its own document or update a larger user context document.
            # For now, let's just log it as "stored" conceptually.
            # A real implementation would structure this based on how context is used later.
            
            # Placeholder: update a document keyed by user_id, service_name, and item_id
            await self.user_context_collection.update_one(
                {"user_id": user_id, "service_name": service_name, "item_id": item_id},
                {"$set": {"data": data_to_store, "last_updated_utc": datetime.datetime.now(datetime.timezone.utc)}},
                upsert=True
            )
            print(f"[{datetime.datetime.now()}] [ContextQueue_DB] Stored/Updated context for {user_id}/{service_name}/{item_id}")
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ContextQueue_DB_ERROR] Storing context data for {user_id}/{service_name}/{item_id}: {e}")
            return False


    async def close(self):
        if self.client:
            self.client.close()
            print(f"[{datetime.datetime.now()}] [ContextQueue_MongoManager] MongoDB connection closed.")