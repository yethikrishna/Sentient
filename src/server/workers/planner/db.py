import uuid
import datetime
import motor.motor_asyncio
import logging
from typing import List, Dict, Any
import json

from .config import MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG
from server.main.auth.utils import aes_decrypt

logger = logging.getLogger(__name__)

def get_all_mcp_descriptions() -> Dict[str, str]:
    """
    Creates a dictionary of all available services and their high-level descriptions
    from the main server's integration config.
    """
    if not INTEGRATIONS_CONFIG:
        logging.warning("INTEGRATIONS_CONFIG is empty. No tools will be available to the planner.")
        return {}
    
    mcp_descriptions = {}
    for name, config in INTEGRATIONS_CONFIG.items():
        display_name = config.get("display_name")
        description = config.get("description")
        if display_name and description:
            # Use the simple name (e.g., 'gmail') as the key for the planner
            mcp_descriptions[name] = description
            
    return mcp_descriptions


class PlannerMongoManager:
    """A MongoDB manager for the planner worker."""
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db["user_profiles"]
        self.tasks_collection = self.db["tasks"]
        self.journal_blocks_collection = self.db["journal_blocks"]
        logger.info("PlannerMongoManager initialized.")

    async def save_plan_as_task(self, user_id: str, description: str, plan: list, original_context: dict, source_event_id: str):
        """Saves a generated plan to the tasks collection for user approval."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "description": description,
            "status": "approval_pending",
            "priority": 1,
            "plan": plan,
            "original_context": original_context,
            "source_event_id": source_event_id,
            "progress_updates": [],
            "created_at": now_utc,
            "updated_at": now_utc,
            "result": None,
            "error": None,
            "agent_id": "planner_agent"
        }
        await self.tasks_collection.insert_one(task_doc)
        logger.info(f"Saved new plan with task_id: {task_id} for user: {user_id}")
        
        # If the plan originated from a journal block, link it back
        if original_context.get("service_name") == "journal_block":
            block_id = original_context.get("event_id")
            if block_id:
                await self.journal_blocks_collection.update_one(
                    {"block_id": block_id, "user_id": user_id},
                    {"$set": {"linked_task_id": task_id, "task_status": "approval_pending"}}
                )
                logger.info(f"Linked new task {task_id} to journal block {block_id}.")
        
        return task_id

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Planner MongoDB connection closed.")