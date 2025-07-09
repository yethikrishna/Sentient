import motor.motor_asyncio
import os
import uuid
import datetime
from typing import Optional, Dict, List, Any

from dotenv import load_dotenv

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
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

    async def search_journal_content(self, user_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Performs a text search on the journal content for a given user."""
        cursor = self.blocks_collection.find(
            {"user_id": user_id, "$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        
        results = await cursor.to_list(length=limit)
        for doc in results:
            doc["_id"] = str(doc["_id"])
        return results

    async def get_day_summary(self, user_id: str, date_str: str) -> str:
        """Fetches all blocks for a given day and concatenates their content."""
        cursor = self.blocks_collection.find(
            {"user_id": user_id, "page_date": date_str}
        ).sort("order", 1)
        
        blocks = await cursor.to_list(length=None)
        if not blocks:
            return f"No journal entries found for {date_str}."
            
        # Concatenate content from all blocks for that day
        full_content = "\n- ".join([block['content'] for block in blocks])
        return f"Journal for {date_str}:\n- {full_content}"