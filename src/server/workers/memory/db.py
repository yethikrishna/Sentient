# src/server/workers/memory/db.py
import motor.motor_asyncio
from pymongo import IndexModel, DESCENDING
import datetime
import logging

from .config import MONGO_URI, MONGO_DB_NAME

logger = logging.getLogger(__name__)

class MemoryWorkerMongoManager:
    """
    MongoDB manager for the memory worker, used for logging processed facts.
    """
    def __init__(self):
        self.client = None
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[MONGO_DB_NAME]
            self.processed_log_collection = self.db["memory_worker_processed_log"]
            logger.info("MemoryWorkerMongoManager initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryWorkerMongoManager: {e}")
            raise

    async def initialize_db(self):
        """Ensures necessary indexes exist."""
        try:
            await self.processed_log_collection.create_indexes([
                IndexModel([("processed_at", DESCENDING)], expireAfterSeconds=2592000) # 30 days TTL
            ])
            logger.info("Memory Worker MongoDB indexes ensured.")
        except Exception as e:
            logger.error(f"Error ensuring Memory Worker MongoDB indexes: {e}")

    async def log_processed_fact(self, user_id: str, fact: str, status: str, details: str):
        """Logs the result of processing a single memory fact."""
        try:
            await self.processed_log_collection.insert_one({
                "user_id": user_id,
                "fact": fact,
                "status": status,
                "details": details,
                "processed_at": datetime.datetime.now(datetime.timezone.utc)
            })
        except Exception as e:
            logger.error(f"Failed to log processed fact for user {user_id}: {e}")

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Memory Worker MongoDB connection closed.")