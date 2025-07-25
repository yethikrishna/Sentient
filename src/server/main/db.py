# src/server/main/db.py
import os
import datetime
import uuid
import json
import logging
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError
from typing import Dict, List, Optional, Any, Tuple
from workers.tasks import execute_task_plan

# Import config from the current 'main' directory
from main.config import MONGO_URI, MONGO_DB_NAME

USER_PROFILES_COLLECTION = "user_profiles" 
NOTIFICATIONS_COLLECTION = "notifications" 
POLLING_STATE_COLLECTION = "polling_state_store" 
PROCESSED_ITEMS_COLLECTION = "processed_items_log" 
TASK_COLLECTION = "tasks"
CHATS_COLLECTION = "chats"
# New Collections for Projects
PROJECTS_COLLECTION = "projects"
PROJECT_MEMBERS_COLLECTION = "project_members"
PROJECT_CONTEXT_ITEMS_COLLECTION = "project_context_items"

logger = logging.getLogger(__name__)

class MongoManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        
        self.user_profiles_collection = self.db[USER_PROFILES_COLLECTION]
        self.notifications_collection = self.db[NOTIFICATIONS_COLLECTION]
        self.polling_state_collection = self.db[POLLING_STATE_COLLECTION]
        self.processed_items_collection = self.db[PROCESSED_ITEMS_COLLECTION]
        self.task_collection = self.db[TASK_COLLECTION]
        self.chats_collection = self.db[CHATS_COLLECTION]
        # New Collections
        self.projects_collection = self.db[PROJECTS_COLLECTION]
        self.project_members_collection = self.db[PROJECT_MEMBERS_COLLECTION]
        self.project_context_items_collection = self.db[PROJECT_CONTEXT_ITEMS_COLLECTION]
        
        print(f"[{datetime.datetime.now()}] [MainServer_MongoManager] Initialized. Database: {MONGO_DB_NAME}")

    async def initialize_db(self):
        print(f"[{datetime.datetime.now()}] [MainServer_DB_INIT] Ensuring indexes for MongoManager collections...")
        
        collections_with_indexes = {
            self.user_profiles_collection: [
                IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique_idx"),
                IndexModel([("userData.last_active_timestamp", DESCENDING)], name="user_last_active_idx"),
                IndexModel([("userData.google_services.gmail.encrypted_refresh_token", ASCENDING)], 
                           name="google_gmail_token_idx", sparse=True),
                IndexModel([("userData.onboardingComplete", ASCENDING)], name="user_onboarding_status_idx", sparse=True)
            ],
            self.notifications_collection: [
                IndexModel([("user_id", ASCENDING)], name="notification_user_id_idx"),
                IndexModel([("user_id", ASCENDING), ("notifications.timestamp", DESCENDING)], name="notification_timestamp_idx", sparse=True)
            ],
            self.polling_state_collection: [
                IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING)], unique=True, name="polling_user_service_unique_idx"),
                IndexModel([
                    ("is_enabled", ASCENDING), ("next_scheduled_poll_time", ASCENDING), 
                    ("is_currently_polling", ASCENDING), ("error_backoff_until_timestamp", ASCENDING) 
                ], name="polling_due_tasks_idx"),
                IndexModel([("is_currently_polling", ASCENDING), ("last_attempted_poll_timestamp", ASCENDING)], name="polling_stale_locks_idx")
            ],
            self.processed_items_collection: [ 
                IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING), ("item_id", ASCENDING)], unique=True, name="processed_item_unique_idx_main"),
                IndexModel([("processing_timestamp", DESCENDING)], name="processed_timestamp_idx_main", expireAfterSeconds=2592000) # 30 days
            ],
            self.task_collection: [
                IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="task_user_created_idx"),
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING), ("priority", ASCENDING)], name="task_user_status_priority_idx"),
                IndexModel([("status", ASCENDING), ("agent_id", ASCENDING)], name="task_status_agent_idx", sparse=True), 
                IndexModel([("task_id", ASCENDING)], unique=True, name="task_id_unique_idx"),
                IndexModel([("project_id", ASCENDING)], name="task_project_id_idx", sparse=True)
            ],
            self.chats_collection: [
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)], name="chat_user_updated_idx"),
                IndexModel([("chat_id", ASCENDING)], unique=True, name="chat_id_unique_idx"),
                IndexModel([("user_id", ASCENDING)], name="chat_user_id_idx"),
                IndexModel([("project_id", ASCENDING)], name="chat_project_id_idx", sparse=True)
            ],
            # New Collections and Indexes
            self.projects_collection: [
                IndexModel([("project_id", ASCENDING)], unique=True, name="project_id_unique_idx"),
                IndexModel([("owner_id", ASCENDING)], name="project_owner_id_idx")
            ],
            self.project_members_collection: [
                IndexModel([("project_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="project_member_unique_idx"),
                IndexModel([("user_id", ASCENDING)], name="project_member_user_id_idx")
            ],
            self.project_context_items_collection: [
                IndexModel([("project_id", ASCENDING)], name="context_project_id_idx"),
                IndexModel([("item_id", ASCENDING)], unique=True, name="context_item_id_unique_idx")
            ],
        }

        for collection, indexes in collections_with_indexes.items():
            try:
                await collection.create_indexes(indexes)
                print(f"[{datetime.datetime.now()}] [MainServer_DB_INIT] Indexes ensured for: {collection.name}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [MainServer_DB_ERROR] Index creation for {collection.name}: {e}")

    # --- User Profile Methods ---
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        if not user_id: return None
        return await self.user_profiles_collection.find_one({"user_id": user_id})

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        if not user_id or not profile_data: return False
        if "_id" in profile_data: del profile_data["_id"] 
        
        update_operations = {"$set": {}, "$setOnInsert": {}}
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for key, value in profile_data.items():
            update_operations["$set"][key] = value
        
        update_operations["$set"]["last_updated"] = now_utc
        update_operations["$setOnInsert"]["user_id"] = user_id
        update_operations["$setOnInsert"]["createdAt"] = now_utc
        
        if "userData" not in profile_data and not any(k.startswith("userData.") for k in profile_data):
             update_operations["$setOnInsert"]["userData"] = {}

        for key_to_set in profile_data.keys():
            if key_to_set.startswith("userData.google_services."):
                parts = key_to_set.split('.')
                if len(parts) >= 3: 
                    service_name_for_insert = parts[2] 
                    
                    user_data_on_insert = update_operations["$setOnInsert"].setdefault("userData", {})
                    google_services_on_insert = user_data_on_insert.setdefault("google_services", {})
                    google_services_on_insert.setdefault(service_name_for_insert, {})
                break 

        if not update_operations["$set"]: del update_operations["$set"] 
        if not update_operations["$setOnInsert"]: del update_operations["$setOnInsert"]
        
        if not update_operations.get("$set") and not update_operations.get("$setOnInsert"): 
            return True 

        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id}, update_operations, upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None
        
    async def update_user_last_active(self, user_id: str) -> bool:
        if not user_id: return False
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        update_payload = {
            "userData.last_active_timestamp": now_utc,
            "last_updated": now_utc
        }
        result = await self.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": update_payload, 
             "$setOnInsert": {"user_id": user_id, "createdAt": now_utc, "userData": {"last_active_timestamp": now_utc}}},
            upsert=True 
        )
        return result.matched_count > 0 or result.upserted_id is not None

    # --- Notification Methods ---
    async def get_notifications(self, user_id: str) -> List[Dict]:
        if not user_id: return []
        user_doc = await self.notifications_collection.find_one( # noqa: E501
            {"user_id": user_id}, {"notifications": 1}
        )
        notifications_list = user_doc.get("notifications", []) if user_doc else []

        # Serialize datetime objects before returning, as they are not JSON-serializable by default.
        for notification in notifications_list:
            if isinstance(notification.get("timestamp"), datetime.datetime):
                notification["timestamp"] = notification["timestamp"].isoformat()
        return notifications_list

    async def add_notification(self, user_id: str, notification_data: Dict) -> Optional[Dict]:
        if not user_id or not notification_data: return None
        # Store timestamp as an ISO 8601 string to ensure timezone correctness
        # across all database and application layers.
        notification_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        notification_data["id"] = str(uuid.uuid4())
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$push": {
                "notifications": {
                    "$each": [notification_data],
                    "$position": 0, # Add to the beginning of the array
                    "$slice": -50
                }
            },
             "$setOnInsert": {"user_id": user_id, "created_at": datetime.datetime.now(datetime.timezone.utc)}},
            upsert=True
        )
        if result.matched_count > 0 or result.upserted_id is not None:
            return notification_data
        return None

    async def delete_notification(self, user_id: str, notification_id: str) -> bool:
        if not user_id or not notification_id: return False
        result = await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"notifications": {"id": notification_id}}}
        )
        return result.modified_count > 0

    # --- Polling State Store Methods ---
    async def get_polling_state(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        if not user_id or not service_name: return None
        return await self.polling_state_collection.find_one(
            {"user_id": user_id, "service_name": service_name}
        )

    async def update_polling_state(self, user_id: str, service_name: str, state_data: Dict[str, Any]) -> bool: 
        if not user_id or not service_name or state_data is None: return False
        for key, value in state_data.items(): 
            if isinstance(value, datetime.datetime):
                state_data[key] = value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
        
        # Prevent conflict errors by not trying to $set fields that are part of the unique index
        # or are immutable.
        if '_id' in state_data:
            del state_data['_id']
        if 'user_id' in state_data:
            del state_data['user_id']
        if 'service_name' in state_data:
            del state_data['service_name']
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        state_data["last_updated_at"] = now_utc

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name}, 
            {"$set": state_data, "$setOnInsert": {"created_at": now_utc, "user_id": user_id, "service_name": service_name}}, 
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    # --- Task Methods ---
    async def add_task(self, user_id: str, task_data: dict, project_id: Optional[str] = None) -> str:
        """Creates a new task document, optionally associating it with a project."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        schedule = task_data.get("schedule")
        if isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError:
                schedule = None

        # All new tasks are assigned to AI and start in the 'planning' state.
        initial_run = {
            "run_id": str(uuid.uuid4()),
            "status": "planning",
            "plan": [],
            "clarifying_questions": [],
            "progress_updates": [],
            "result": None,
            "error": None,
            "prompt": task_data.get("description")
        }

        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "creator_id": user_id,
            "project_id": project_id,
            "description": task_data.get("description", "New Task"),
            "status": "planning",
            "assignee": "ai",
            "priority": task_data.get("priority", 1),
            "runs": [initial_run],
            "schedule": schedule,
            "enabled": True,
            "original_context": {"source": "manual_creation"},
            "created_at": now_utc,
            "updated_at": now_utc,
            "chat_history": [],
            "next_execution_at": None,
            "last_execution_at": None,
        }

        await self.task_collection.insert_one(task_doc)
        logger.info(f"Created new manual task {task_id} for user {user_id} with status 'planning'.")
        return task_id

    async def get_task(self, task_id: str, user_id: str) -> Optional[Dict]:
        """Fetches a single task by its ID, ensuring it belongs to the user."""
        return await self.task_collection.find_one({"task_id": task_id, "user_id": user_id})

    async def get_all_tasks_for_user(self, user_id: str) -> List[Dict]:
        """Fetches all personal (non-project) tasks for a given user."""
        cursor = self.task_collection.find({"user_id": user_id, "project_id": None}).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def update_task(self, task_id: str, updates: Dict) -> bool:
        """Updates an existing task document."""
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        result = await self.task_collection.update_one(
            {"task_id": task_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def add_answers_to_task(self, task_id: str, answers: List[Dict], user_id: str) -> bool:
        """Finds a task and updates its clarifying questions with user answers."""
        task = await self.get_task(task_id, user_id)
        if not task:
            return False

        runs = task.get("runs", [])
        if not runs:
            # Fallback for older task structure without runs
            current_questions = task.get("clarifying_questions", [])
            for answer_data in answers:
                for question in current_questions:
                    if question.get("question_id") == answer_data.get("question_id"):
                        question["answer"] = answer_data.get("answer_text")
            return await self.update_task(task_id, {"clarifying_questions": current_questions})

        # New logic for tasks with runs
        latest_run = runs[-1]
        if "clarifying_questions" not in latest_run:
            return False # Nothing to update

        current_questions = latest_run["clarifying_questions"]
        answer_map = {ans.get("question_id"): ans.get("answer_text") for ans in answers}

        for answer_data in answers:
            for question in current_questions:
                q_id = question.get("question_id")
                if q_id in answer_map:
                    question["answer"] = answer_map[q_id]

        return await self.update_task(task_id, {"runs": runs})

    async def delete_task(self, task_id: str, user_id: str) -> str:
        """Deletes a task."""
        result = await self.task_collection.delete_one({"task_id": task_id, "user_id": user_id})
        return "Task deleted successfully." if result.deleted_count > 0 else None

    async def decline_task(self, task_id: str, user_id: str) -> str:
        """Declines a task by setting its status to 'declined'."""
        success = await self.update_task(task_id, {"status": "declined"})
        return "Task declined." if success else None

    async def execute_task_immediately(self, task_id: str, user_id: str) -> str:
        """Triggers the immediate execution of a task."""
        task = await self.get_task(task_id, user_id)
        if not task:
            return None
        execute_task_plan.delay(task_id, user_id)
        return "Task execution has been initiated."

    async def cancel_latest_run(self, task_id: str) -> bool:
        """Pops the last run from the array and reverts the task status to completed."""
        update_payload = {
            "$set": {
                "status": "completed",
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            },
            "$pop": {"runs": 1}  # Removes the last element from the 'runs' array
        }
        result = await self.task_collection.update_one({"task_id": task_id}, update_payload) # noqa: E501
        return result.modified_count > 0

    async def delete_notifications_for_task(self, user_id: str, task_id: str):
        """Deletes all notifications associated with a specific task_id for a user."""
        if not user_id or not task_id:
            return
        await self.notifications_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"notifications": {"task_id": task_id}}}
        )
        logger.info(f"Deleted notifications for task {task_id} for user {user_id}.")

    async def rerun_task(self, original_task_id: str, user_id: str) -> Optional[str]:
        """Duplicates a task to be re-run."""
        original_task = await self.get_task(original_task_id, user_id)
        if not original_task:
            return None

        new_task_doc = original_task.copy()
        new_task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # Reset fields for a new run
        if "_id" in new_task_doc:
            del new_task_doc["_id"] # Let Mongo generate a new one
        new_task_doc["task_id"] = new_task_id
        new_task_doc["status"] = "planning"
        new_task_doc["created_at"] = now_utc
        new_task_doc["updated_at"] = now_utc
        new_task_doc["progress_updates"] = []
        new_task_doc["result"] = None
        new_task_doc["error"] = None
        new_task_doc["last_execution_at"] = None
        new_task_doc["next_execution_at"] = None

        await self.task_collection.insert_one(new_task_doc)
        return new_task_id

    # --- Chat Methods ---
    async def get_user_chats(self, user_id: str) -> List[Dict]: # noqa: E501
        """Fetches all personal (non-project) chat sessions for a user, sorted by last updated."""
        cursor = self.chats_collection.find(
            {"user_id": user_id, "project_id": None},
            {"chat_id": 1, "title": 1, "updated_at": 1, "_id": 0}
        ).sort("updated_at", DESCENDING)
        return await cursor.to_list(length=100) # Limit to 100 chats

    async def get_chat(self, user_id: str, chat_id: str) -> Optional[Dict]:
        """
        Fetches a single chat session. The route handler is responsible for permission checking
        (i.e., if it's a personal chat or if the user is a member of the project chat).
        """
        return await self.chats_collection.find_one({"chat_id": chat_id})

    async def create_chat(self, user_id: str, first_message: Dict, project_id: Optional[str] = None) -> str:
        """Creates a new chat session, optionally associating it with a project."""
        chat_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)
        chat_doc = {
            "chat_id": chat_id,
            "user_id": user_id,
            "title": first_message.get("content", "New Chat")[:50], # Temporary title
            "created_at": now,
            "updated_at": now,
            "messages": [first_message],
            "project_id": project_id
        }
        await self.chats_collection.insert_one(chat_doc)
        return chat_id

    async def add_message_to_chat(self, chat_id: str, message: Dict) -> bool:
        """Adds a message to an existing chat session."""
        # Ensure message has a timestamp
        if "timestamp" not in message:
            message["timestamp"] = datetime.datetime.now(datetime.timezone.utc)

        result = await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
            }
        )
        return result.modified_count > 0

    async def update_chat(self, user_id: str, chat_id: str, updates: Dict) -> bool:
        """Updates fields of a chat document, like the title."""
        updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        result = await self.chats_collection.update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def delete_chat(self, user_id: str, chat_id: str) -> bool:
        """Deletes a chat session for a user."""
        result = await self.chats_collection.delete_one(
            {"user_id": user_id, "chat_id": chat_id}
        )
        return result.deleted_count > 0

    # --- Project Methods ---
    async def create_project(self, name: str, description: str, owner_id: str) -> Dict:
        project_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)
        project_doc = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now
        }
        await self.projects_collection.insert_one(project_doc)
        return project_doc

    async def add_project_member(self, project_id: str, user_id: str, role: str) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc)
        member_doc = {
            "project_id": project_id,
            "user_id": user_id,
            "role": role,
            "joined_at": now
        }
        try:
            await self.project_members_collection.insert_one(member_doc)
            return True
        except DuplicateKeyError:
            logger.warning(f"User {user_id} is already a member of project {project_id}.")
            return False

    async def get_projects_for_user(self, user_id: str) -> List[Dict]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$lookup": {
                "from": "projects",
                "localField": "project_id",
                "foreignField": "project_id",
                "as": "project_details"
            }},
            {"$unwind": "$project_details"},
            {"$replaceRoot": {"newRoot": "$project_details"}}
        ]
        cursor = self.project_members_collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def get_project_by_id(self, project_id: str) -> Optional[Dict]:
        return await self.projects_collection.find_one({"project_id": project_id})

    async def is_user_in_project(self, user_id: str, project_id: str) -> bool:
        count = await self.project_members_collection.count_documents(
            {"project_id": project_id, "user_id": user_id}
        )
        return count > 0

    async def is_project_owner(self, user_id: str, project_id: str) -> bool:
        project = await self.get_project_by_id(project_id)
        return project is not None and project.get("owner_id") == user_id

    async def get_project_members(self, project_id: str) -> List[Dict]:
        cursor = self.project_members_collection.find({"project_id": project_id})
        return await cursor.to_list(length=None)

    async def remove_project_member(self, project_id: str, user_id_to_remove: str) -> bool:
        result = await self.project_members_collection.delete_one(
            {"project_id": project_id, "user_id": user_id_to_remove}
        )
        return result.deleted_count > 0

    async def delete_project_and_members(self, project_id: str) -> bool:
        await self.project_members_collection.delete_many({"project_id": project_id})
        await self.chats_collection.delete_many({"project_id": project_id})
        await self.task_collection.delete_many({"project_id": project_id})
        await self.project_context_items_collection.delete_many({"project_id": project_id})
        result = await self.projects_collection.delete_one({"project_id": project_id})
        return result.deleted_count > 0

    async def get_chats_for_project(self, project_id: str) -> List[Dict]:
        cursor = self.chats_collection.find(
            {"project_id": project_id},
            {"chat_id": 1, "title": 1, "updated_at": 1, "_id": 0}
        ).sort("updated_at", DESCENDING)
        return await cursor.to_list(length=None)

    async def get_tasks_for_project(self, project_id: str) -> List[Dict]:
        cursor = self.task_collection.find({"project_id": project_id}).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def add_context_item(self, project_id: str, creator_id: str, item_type: str, content: Any) -> Dict:
        item_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)
        item_doc = {"item_id": item_id, "project_id": project_id, "creator_id": creator_id, "type": item_type, "content": content, "created_at": now}
        await self.project_context_items_collection.insert_one(item_doc)
        return item_doc

    async def get_context_items(self, project_id: str) -> List[Dict]:
        cursor = self.project_context_items_collection.find({"project_id": project_id}).sort("created_at", ASCENDING)
        return await cursor.to_list(length=None)

    async def delete_context_item(self, item_id: str) -> bool:
        result = await self.project_context_items_collection.delete_one({"item_id": item_id})
        return result.deleted_count > 0

    async def close(self):
        if self.client:
            self.client.close()
            print(f"[{datetime.datetime.now()}] [MainServer_MongoManager] MongoDB connection closed.")