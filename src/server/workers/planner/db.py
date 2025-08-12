import uuid
import datetime
import logging
import motor.motor_asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import json
import uuid

from workers.planner.config import MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG, ENVIRONMENT
from workers.utils.crypto import aes_encrypt, aes_decrypt

DB_ENCRYPTION_ENABLED = ENVIRONMENT == 'stag'

def _encrypt_field(data: Any) -> Any:
    if not DB_ENCRYPTION_ENABLED or data is None:
        return data
    data_str = json.dumps(data)
    return aes_encrypt(data_str)

def _decrypt_field(data: Any) -> Any:
    if not DB_ENCRYPTION_ENABLED or data is None or not isinstance(data, str):
        return data
    try:
        decrypted_str = aes_decrypt(data)
        return json.loads(decrypted_str)
    except Exception:
        return data

def _encrypt_doc(doc: Dict, fields: List[str]):
    if not DB_ENCRYPTION_ENABLED or not doc:
        return
    for field in fields:
        if field in doc and doc[field] is not None:
            doc[field] = _encrypt_field(doc[field])

def _decrypt_doc(doc: Optional[Dict], fields: List[str]):
    if not DB_ENCRYPTION_ENABLED or not doc:
        return
    for field in fields:
        if field in doc and doc[field] is not None:
            doc[field] = _decrypt_field(doc[field])


logger = logging.getLogger(__name__)

def get_date_from_text(text: str) -> str:
    """Extracts YYYY-MM-DD from text, defaults to today."""
    match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if match:
        return match.group(1)
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')

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
        # The planner agent should not have access to the tasks MCP,
        # as it can lead to recursive loops. The tasks MCP is for the chat agent.
        if name == "tasks":
            continue
        display_name = config.get("display_name")
        description = config.get("description")
        if display_name and description:
            # Use the simple name (e.g., 'gmail') as the key for the planner
            mcp_descriptions[name] = description
            
    return mcp_descriptions


class PlannerMongoManager:  # noqa: E501
    """A MongoDB manager for the planner worker."""
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db["user_profiles"]
        self.tasks_collection = self.db["tasks"]
        self.messages_collection = self.db["messages"]
        self.proactive_suggestion_templates_collection = self.db["proactive_suggestion_templates"]
        self.user_proactive_preferences_collection = self.db["user_proactive_preferences"]
        logger.info("PlannerMongoManager initialized.")

    async def create_initial_task(self, user_id: str, name: str, description: str, action_items: list, topics: list, original_context: dict, source_event_id: str) -> Dict:
        """Creates an initial task document when an action item is first processed."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "status": "planning", # As per spec
            "assignee": "ai", # Proactive tasks are assigned to AI
            "priority": 1,
            "plan": [],
            "runs": [],
            "original_context": original_context,
            "source_event_id": source_event_id,
            "created_at": now_utc,
            "updated_at": now_utc,
            "chat_history": [],
        }

        SENSITIVE_TASK_FIELDS = ["name", "description", "original_context"]
        _encrypt_doc(task_doc, SENSITIVE_TASK_FIELDS)

        await self.tasks_collection.insert_one(task_doc)
        logger.info(f"Created initial task {task_id} for user {user_id}")
        return task_doc

    async def update_task_field(self, task_id: str, fields: dict):
        """Updates specific fields of a task document."""
        if DB_ENCRYPTION_ENABLED:
            SENSITIVE_TASK_FIELDS = ["name", "description", "plan", "runs", "original_context", "chat_history", "error", "found_context", "clarifying_questions", "result", "swarm_details"]
            encrypted_fields = {}
            for field, value in fields.items():
                if field in SENSITIVE_TASK_FIELDS:
                    encrypted_fields[field] = _encrypt_field(value)
                else:
                    encrypted_fields[field] = value
            fields = encrypted_fields

        await self.tasks_collection.update_one(
            {"task_id": task_id},
            {"$set": fields}
        )
        logger.info(f"Updated fields for task {task_id}: {list(fields.keys())}")

    async def update_task_with_plan(self, task_id: str, plan_data: dict, is_change_request: bool = False):
        """Updates a task with a generated plan and sets it to pending approval."""
        if DB_ENCRYPTION_ENABLED:
            SENSITIVE_PLAN_FIELDS = ["name", "description", "plan"]
            encrypted_plan_data = plan_data.copy()
            _encrypt_doc(encrypted_plan_data, SENSITIVE_PLAN_FIELDS)
            plan_data = encrypted_plan_data

        plan_steps = plan_data.get("plan", [])

        update_doc = {
            "status": "approval_pending",
            "plan": plan_steps,
            "updated_at": datetime.datetime.now(datetime.timezone.utc)
        }

        # Only set the main description for the very first run.
        if not is_change_request:
            name = plan_data.get("name", "Proactively generated plan")
            update_doc["name"] = name
            update_doc["description"] = plan_data.get("description", "")

        result = await self.tasks_collection.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
        logger.info(f"Updated task {task_id} with a generated plan. Matched: {result.matched_count}")

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Fetches a single task by its ID."""
        doc = await self.tasks_collection.find_one({"task_id": task_id})
        SENSITIVE_TASK_FIELDS = ["name", "description", "plan", "runs", "original_context", "chat_history", "error", "found_context", "clarifying_questions", "result", "swarm_details"]
        _decrypt_doc(doc, SENSITIVE_TASK_FIELDS)
        return doc

    async def update_task_status(self, task_id: str, status: str, details: Optional[Dict] = None):
        """Updates the status and optionally other fields of a task."""
        update_doc = {"status": status, "updated_at": datetime.datetime.now(datetime.timezone.utc)}
        if details:
            if "error" in details:
                update_doc["error"] = details["error"]

        SENSITIVE_TASK_FIELDS = ["error"]
        _encrypt_doc(update_doc, SENSITIVE_TASK_FIELDS)

        await self.tasks_collection.update_one({"task_id": task_id}, {"$set": update_doc})
        logger.info(f"Updated status of task {task_id} to {status}")

    async def save_plan_as_task(self, user_id: str, name: str, description: str, plan: list, original_context: dict, source_event_id: str):
        """Saves a generated plan to the tasks collection for user approval."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "status": "approval_pending",
            "priority": 1,
            "plan": plan,
            "runs": [],
            "original_context": original_context,
            "source_event_id": source_event_id,
            "created_at": now_utc,
            "updated_at": now_utc,
            "agent_id": "planner_agent"
        }

        SENSITIVE_TASK_FIELDS = ["name", "description", "plan", "original_context"]
        _encrypt_doc(task_doc, SENSITIVE_TASK_FIELDS)

        await self.tasks_collection.insert_one(task_doc)
        logger.info(f"Saved new plan with task_id: {task_id} for user: {user_id}")
        return task_id

    async def update_chat(self, user_id: str, chat_id: str, updates: Dict) -> bool:
        """Updates fields of a chat document, like the title."""
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        result = await self.messages_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def get_all_proactive_suggestion_templates(self) -> List[Dict]:
        """Fetches all documents from the proactive_suggestion_templates collection."""
        cursor = self.proactive_suggestion_templates_collection.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    async def get_user_proactive_preferences(self, user_id: str) -> Dict[str, int]:
        """
        Fetches all proactive suggestion preferences for a user and returns them
        as a dictionary of {suggestion_type: score}.
        """
        if not user_id:
            return {}
        
        preferences = {}
        cursor = self.user_proactive_preferences_collection.find(
            {"user_id": user_id},
            {"_id": 0, "suggestion_type": 1, "score": 1}
        )
        async for doc in cursor:
            if "suggestion_type" in doc and "score" in doc:
                preferences[doc["suggestion_type"]] = doc["score"]
        
        logger.info(f"Fetched {len(preferences)} proactive preferences for user {user_id}.")
        return preferences

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Planner MongoDB connection closed.")