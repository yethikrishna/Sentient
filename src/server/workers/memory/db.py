import motor.motor_asyncio
import logging
from typing import Optional, Dict

from .config import MONGO_URI, MONGO_DB_NAME

logger = logging.getLogger(__name__)

class MemoryMongoManager:
    """MongoDB manager for the memory worker."""
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db["user_profiles"]
        logger.info("MemoryMongoManager initialized.")

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Fetches a user's full profile document."""
        if not user_id:
            return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Memory worker MongoDB connection closed.")