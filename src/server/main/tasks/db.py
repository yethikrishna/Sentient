import motor.motor_asyncio
import datetime
import uuid
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TaskDatabase:
    def __init__(self, mongo_uri: str, db_name: str = "task_manager_db"):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.task_collection = self.db["tasks"]
        self.user_collection = self.db["users"] # Assuming a user collection might exist or be needed

    async def _ensure_indexes(self):
        """Ensures that necessary indexes are created for efficient querying."""
        try:
            await self.task_collection.create_index("task_id", unique=True)
            await self.task_collection.create_index("user_id")
            await self.task_collection.create_index("status")
            await self.task_collection.create_index("next_execution_at")
            logger.info("Task indexes ensured.")
        except Exception as e:
            logger.error(f"Error ensuring task indexes: {e}")

    async def create_task(self, user_id: str, task_data: dict) -> dict:
        """Creates a new task document, typically from a manual user request."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        schedule = task_data.get("schedule")
        if isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError:
                schedule = None

        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "description": task_data.get("description", "New Task"),
            "status": "planning",  # As per spec for new tasks
            "priority": task_data.get("priority", 1),
            "plan": [],
            "schedule": schedule,
            "enabled": True, 
            "original_context": {"source": "manual_creation"},
            "created_at": now_utc,
            "updated_at": now_utc,
            "clarifying_questions": [],
            "progress_updates": [],
            "result": None,
            "error": None,
            "next_execution_at": None,
            "last_execution_at": None,
        }
        
        await self.task_collection.insert_one(task_doc)
        logger.info(f"Created new manual task {task_id} for user {user_id} with status 'planning'.")
        return task_doc

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Fetches a single task by its ID."""
        return await self.task_collection.find_one({"task_id": task_id})

    async def get_tasks_for_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Fetches all tasks for a given user, optionally filtered by status."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        cursor = self.task_collection.find(query).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def update_task(self, task_id: str, updates: Dict) -> bool:
        """Updates an existing task document."""
        # Ensure updated_at is always set
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        result = await self.task_collection.update_one(
            {"task_id": task_id},
            {"$set": updates}
        )

        return result.modified_count > 0 or result.upserted_id is not None

    async def add_answers_to_task(self, task_id: str, answers: List[Dict], user_id: str) -> bool:
        """Finds a task and updates its clarifying questions with user answers."""
        task = await self.get_task(task_id)
        if not task or task.get("user_id") != user_id:
            return False

        current_questions = task.get("clarifying_questions", [])
        for answer_data in answers:
            for question in current_questions:
                if question.get("question_id") == answer_data.get("question_id"):
                    question["answer"] = answer_data.get("answer_text")
                    break
        return await self.update_task(task_id, {"clarifying_questions": current_questions})