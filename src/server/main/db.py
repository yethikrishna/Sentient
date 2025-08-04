# src/server/main/db.py
import os
import datetime
import uuid
import json
import logging
import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from typing import Dict, List, Optional, Any, Tuple

# Import config from the current 'main' directory
from main.config import MONGO_URI, MONGO_DB_NAME

USER_PROFILES_COLLECTION = "user_profiles" 
NOTIFICATIONS_COLLECTION = "notifications" 
POLLING_STATE_COLLECTION = "polling_state_store" 
PROCESSED_ITEMS_COLLECTION = "processed_items_log" 
TASK_COLLECTION = "tasks"
MESSAGES_COLLECTION = "messages"
USER_PROACTIVE_PREFERENCES_COLLECTION = "user_proactive_preferences"
PROACTIVE_SUGGESTION_TEMPLATES_COLLECTION = "proactive_suggestion_templates"

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
        self.messages_collection = self.db[MESSAGES_COLLECTION]
        self.user_proactive_preferences_collection = self.db[USER_PROACTIVE_PREFERENCES_COLLECTION]
        self.proactive_suggestion_templates_collection = self.db[PROACTIVE_SUGGESTION_TEMPLATES_COLLECTION]
        
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
                IndexModel([("user_id", ASCENDING), ("service_name", ASCENDING), ("poll_type", ASCENDING)], unique=True, name="polling_user_service_type_unique_idx"),
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
                IndexModel([("description", "text")], name="task_description_text_idx"),
            ],
            self.messages_collection: [
                IndexModel([("message_id", ASCENDING)], unique=True, name="message_id_unique_idx"),
                IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)], name="message_user_timestamp_idx"),
            ],
            self.user_proactive_preferences_collection: [
                IndexModel([("user_id", ASCENDING), ("suggestion_type", ASCENDING)], unique=True, name="user_suggestion_preference_unique_idx")
            ],
            self.proactive_suggestion_templates_collection: [
                IndexModel([("type_name", ASCENDING)], unique=True, name="suggestion_type_name_unique_idx")
            ],
        }

        for collection, indexes in collections_with_indexes.items():
            try:
                await collection.create_indexes(indexes)
                print(f"[{datetime.datetime.now()}] [MainServer_DB_INIT] Indexes ensured for: {collection.name}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [MainServer_DB_ERROR] Index creation for {collection.name}: {e}")

        # Pre-populate suggestion templates if the collection is empty
        if await self.proactive_suggestion_templates_collection.count_documents({}) == 0:
            print(f"[{datetime.datetime.now()}] [MainServer_DB_INIT] Pre-populating proactive suggestion templates...")
            initial_templates = [
                {"type_name": "draft_meeting_confirmation_email", "description": "Drafts an email to confirm a meeting, check availability, or ask for an agenda."},
                {"type_name": "schedule_calendar_event", "description": "Creates a new event on the user's calendar based on details from a message."},
                {"type_name": "create_follow_up_task", "description": "Creates a new task in the user's task list to follow up on a specific item or conversation."},
                {"type_name": "summarize_document_or_thread", "description": "Summarizes a long document, email thread, or message chain for the user."},
            ]
            await self.proactive_suggestion_templates_collection.insert_many(initial_templates)
            print(f"[{datetime.datetime.now()}] [MainServer_DB_INIT] Inserted {len(initial_templates)} templates.")


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

    async def find_and_action_suggestion_notification(self, user_id: str, notification_id: str) -> Optional[Dict]:
        """
        Atomically finds a proactive_suggestion notification, marks it as actioned, and returns it.
        This prevents race conditions from multiple clicks.
        """
        if not user_id or not notification_id:
            return None

        # Find the document containing the notification
        user_notif_doc = await self.notifications_collection.find_one(
            {"user_id": user_id, "notifications.id": notification_id}
        )
        if not user_notif_doc:
            return None

        # Atomically update the specific notification inside the array
        result = await self.notifications_collection.find_one_and_update(
            {"user_id": user_id, "notifications.id": notification_id, "notifications.is_actioned": False},
            {"$set": {"notifications.$.is_actioned": True}},
        )

        return user_notif_doc if result else None

    # --- Polling State Store Methods ---
    async def get_polling_state(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        if not user_id or not service_name: return None
        return await self.polling_state_collection.find_one(
            {"user_id": user_id, "service_name": service_name}
        )

    async def update_polling_state(self, user_id: str, service_name: str, poll_type: str, state_data: Dict[str, Any]) -> bool:
        if not user_id or not service_name or not poll_type or state_data is None: return False
        for key, value in state_data.items(): 
            if isinstance(value, datetime.datetime):
                state_data[key] = value.replace(tzinfo=datetime.timezone.utc) if value.tzinfo is None else value.astimezone(datetime.timezone.utc)
        
        # Prevent conflict errors by not trying to $set fields that are part of the unique index
        # or are immutable.
        if '_id' in state_data: del state_data['_id']
        if 'user_id' in state_data: del state_data['user_id']
        if 'service_name' in state_data: del state_data['service_name']
        if 'poll_type' in state_data: del state_data['poll_type']
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        state_data["last_updated_at"] = now_utc

        result = await self.polling_state_collection.update_one(
            {"user_id": user_id, "service_name": service_name, "poll_type": poll_type},
            {"$set": state_data, "$setOnInsert": {"created_at": now_utc, "user_id": user_id, "service_name": service_name, "poll_type": poll_type}},
            upsert=True
        )
        return result.matched_count > 0 or result.upserted_id is not None

    # --- Task Methods ---
    async def add_task(self, user_id: str, task_data: dict) -> str:
        """Creates a new task document and returns its ID."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        schedule = task_data.get("schedule")
        if isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError:
                schedule = None

        initial_run = {
            "run_id": str(uuid.uuid4()),
            "status": "planning",
            "plan": [],
            "clarifying_questions": [],
            "progress_updates": [],
            "result": None,
            "error": None,
            "prompt": task_data.get("description") or task_data.get("name")
        }

        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "name": task_data.get("name", "New Task"),
            "description": task_data.get("description", ""),
            "status": "planning",
            "assignee": "ai",
            "priority": task_data.get("priority", 1),
            "runs": [initial_run],
            "schedule": schedule,
            "enabled": True,
            "original_context": task_data.get("original_context", {"source": "manual_creation"}),
            "created_at": now_utc,
            "updated_at": now_utc,
            "chat_history": [],
            "next_execution_at": None,
            "last_execution_at": None,
        }

        await self.task_collection.insert_one(task_doc)
        logger.info(f"Created new task {task_id} for user {user_id} with status 'planning'.")
        return task_id

    async def get_task(self, task_id: str, user_id: str) -> Optional[Dict]:
        """Fetches a single task by its ID, ensuring it belongs to the user."""
        return await self.task_collection.find_one({"task_id": task_id, "user_id": user_id})

    async def get_all_tasks_for_user(self, user_id: str) -> List[Dict]:
        """Fetches all tasks for a given user."""
        cursor = self.task_collection.find({"user_id": user_id}).sort("created_at", -1)
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
        new_task_doc["last_execution_at"] = None
        new_task_doc["next_execution_at"] = None

        await self.task_collection.insert_one(new_task_doc)
        return new_task_id

    # --- Message Methods ---
    async def add_message(self, user_id: str, role: str, content: str, message_id: Optional[str] = None) -> Dict:
        """
        Adds a single message to the messages collection.
        If a message_id is provided, it's used. Otherwise, a new one is generated.
        For user messages with a provided ID, it prevents duplicate insertions.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        final_message_id = message_id if message_id else str(uuid.uuid4())

        # Prevent duplicate user messages if client retries
        if role == "user" and message_id:
            existing = await self.messages_collection.find_one({"message_id": final_message_id, "user_id": user_id})
            if existing:
                logger.info(f"Message with ID {final_message_id} already exists for user {user_id}. Skipping.")
                return existing

        message_doc = {
            "message_id": final_message_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "is_summarized": False,
            "summary_id": None,
        }
        await self.messages_collection.insert_one(message_doc)
        logger.info(f"Added message for user {user_id} with role {role}")
        return message_doc

    async def get_message_history(self, user_id: str, limit: int, before_timestamp_iso: Optional[str] = None) -> List[Dict]:
        """Fetches a paginated history of messages for a user."""
        query = {"user_id": user_id}
        if before_timestamp_iso:
            try:
                # Ensure the timestamp is parsed correctly as UTC
                before_timestamp = datetime.datetime.fromisoformat(before_timestamp_iso.replace("Z", "+00:00"))
                query["timestamp"] = {"$lt": before_timestamp}
            except (ValueError, TypeError):
                logger.warning(f"Invalid before_timestamp format: {before_timestamp_iso}, ignoring.")
                pass

        cursor = self.messages_collection.find(query).sort("timestamp", DESCENDING).limit(limit)
        messages = await cursor.to_list(length=limit)

        # Serialize datetime and ObjectId objects for JSON response
        for msg in messages:
            if isinstance(msg.get("_id"), ObjectId):
                msg["_id"] = str(msg["_id"])
            if isinstance(msg.get("timestamp"), datetime.datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()

        return messages

    async def delete_message(self, user_id: str, message_id: str) -> bool:
        """Deletes a single message by its ID for a specific user."""
        if not user_id or not message_id:
            return False
        result = await self.messages_collection.delete_one({"user_id": user_id, "message_id": message_id})
        return result.deleted_count > 0

    async def delete_all_messages(self, user_id: str) -> int:
        """Deletes all messages for a specific user."""
        if not user_id:
            return 0
        result = await self.messages_collection.delete_many({"user_id": user_id})
        logger.info(f"Deleted {result.deleted_count} messages for user {user_id}.")
        return result.deleted_count

    async def close(self):
        if self.client:
            self.client.close()
            print(f"[{datetime.datetime.now()}] [MainServer_MongoManager] MongoDB connection closed.")

    # --- Proactive Suggestion Template Methods ---
    async def get_all_proactive_suggestion_templates(self) -> List[Dict]:
        """Fetches all documents from the proactive_suggestion_templates collection."""
        cursor = self.proactive_suggestion_templates_collection.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    # --- Proactive Learning Methods ---
    async def update_proactive_preference_score(self, user_id: str, suggestion_type: str, increment_value: int):
        """Finds or creates a user preference document and increments/decrements the score."""
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # FIX: Removed 'score' from $setOnInsert to prevent conflict with $inc on upsert.
        # $inc will create the field with the specified value if it doesn't exist.
        await self.user_proactive_preferences_collection.update_one(
            {"user_id": user_id, "suggestion_type": suggestion_type},
            {
                "$inc": {"score": increment_value},
                "$set": {"last_updated": now_utc}
            },
            upsert=True
        )
    
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