import motor.motor_asyncio
import os
import uuid
import datetime
from typing import Optional, Dict, List, Any

# Inherit from the main server .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

class JournalDBManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.blocks_collection = self.db["journal_blocks"]

    async def add_block(self, user_id: str, content: str, date_str: str, order: int) -> Dict:
        now = datetime.datetime.now(datetime.timezone.utc)
        block_doc = {
            "block_id": str(uuid.uuid4()),
            "user_id": user_id,
            "page_date": date_str,
            "content": content,
            "order": order,
            "created_by": "sentient",
            "created_at": now,
            "updated_at": now
        }
        await self.blocks_collection.insert_one(block_doc)
        block_doc["_id"] = str(block_doc["_id"])
        return block_doc

    async def update_block(self, user_id: str, block_id: str, new_content: str) -> bool:
        result = await self.blocks_collection.update_one(
            {"user_id": user_id, "block_id": block_id},
            {"$set": {"content": new_content, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
        )
        return result.modified_count > 0

    async def delete_block(self, user_id: str, block_id: str) -> bool:
        result = await self.blocks_collection.delete_one(
            {"user_id": user_id, "block_id": block_id}
        )
        return result.deleted_count > 0

    async def add_progress_update(self, block_id: str, update_message: str) -> bool:
        update = {
            "message": update_message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        result = await self.blocks_collection.update_one(
            {"block_id": block_id},
            {"$push": {"task_progress": update}}
        )
        return result.modified_count > 0

    async def get_block(self, block_id: str) -> Optional[Dict]:
        return await self.blocks_collection.find_one({"block_id": block_id})