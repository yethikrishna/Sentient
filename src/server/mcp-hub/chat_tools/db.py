import motor.motor_asyncio
from pymongo import IndexModel
from .config import MONGO_URI, MONGO_DB_NAME

class TaskDBManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.tasks_collection = self.db["tasks"]
        # Ensure text index exists for searching descriptions
        self.tasks_collection.create_indexes([IndexModel([("description", "text")], name="description_text_idx")])

    async def find_task(self, user_id: str, query: str):
        # A simple text search on the description
        return await self.tasks_collection.find_one(
            {"user_id": user_id, "$text": {"$search": query}},
            {"_id": 0, "task_id": 1, "description": 1, "status": 1, "result": 1, "error": 1, "created_at": 1}
        )
    
    async def close(self):
        self.client.close()