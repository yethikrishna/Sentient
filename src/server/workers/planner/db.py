import uuid
import datetime
import motor.motor_asyncio
import logging
from typing import List, Dict, Any

from .config import MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG

logger = logging.getLogger(__name__)

class PlannerMongoManager:
    """A MongoDB manager for the planner worker."""
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db["user_profiles"]
        self.tasks_collection = self.db["tasks"]
        logger.info("PlannerMongoManager initialized.")

    async def get_available_tools(self, user_id: str) -> List[str]:
        """Fetches the names of tools the user has connected."""
        user_profile = await self.user_profiles_collection.find_one({"user_id": user_id})
        if not user_profile:
            return []
        
        user_integrations = user_profile.get("userData", {}).get("integrations", {})
        available_tools = []
        
        for name, config in INTEGRATIONS_CONFIG.items():
            is_connected = user_integrations.get(name, {}).get("connected", False)
            is_builtin = config.get("auth_type") == "builtin"
            if is_connected or is_builtin:
                available_tools.append(name)
        
        return available_tools

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
        return task_id

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Planner MongoDB connection closed.")