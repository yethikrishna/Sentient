import httpx
import logging
import os
import motor.motor_asyncio
import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional, Any

logger = logging.getLogger(__name__)

MAIN_SERVER_URL = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

async def get_user_preferences_from_db(user_id: str):
    """Helper to fetch user preferences directly."""
    client = None
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        user_profile = await db.user_profiles.find_one(
            {"user_id": user_id},
            {"userData.preferences": 1}
        )
        return user_profile.get("userData", {}).get("preferences", {}) if user_profile else {}
    finally:
        if client:
            client.close()

async def notify_user(user_id: str, message: str, task_id: Optional[str] = None, notification_type: str = "general", payload: Optional[dict] = None):
    """
    Calls the main server to create a notification for the user, after checking preferences.
    """
    endpoint = f"{MAIN_SERVER_URL}/notifications/internal/create"
    request_payload = {
        "user_id": user_id,
        "message": message,
        "task_id": task_id,
        "notification_type": notification_type,
        "payload": payload
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=request_payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent notification for user {user_id}: {message}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send notification for user {user_id}. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending notification for {user_id}: {e}", exc_info=True)

async def push_progress_update(user_id: str, task_id: str, run_id: str, message: Any):
    """
    Calls the main server's internal endpoint to push a progress update via WebSocket.
    """
    endpoint = f"{MAIN_SERVER_URL}/tasks/internal/progress-update"
    payload = {
        "user_id": user_id,
        "task_id": task_id,
        "run_id": run_id,
        "message": message
    }
    try:
        async with httpx.AsyncClient() as client:
            # This is a fire-and-forget call, we don't need to wait long or handle the response extensively.
            await client.post(endpoint, json=payload, timeout=5)
            logger.info(f"Pushed progress update for task {task_id} to main server.")
    except Exception as e:
        # Log the error but don't let it crash the worker task.
        logger.error(f"Failed to push progress update to main server for task {task_id}: {e}", exc_info=False)
async def push_task_list_update(user_id: str, task_id: str, run_id: str):
    """
    Calls the main server's internal endpoint to tell the client to refetch its task list.
    """
    endpoint = f"{MAIN_SERVER_URL}/tasks/internal/task-update-push"
    # We can reuse the ProgressUpdateRequest model for simplicity as it has the required fields.
    payload = {
        "user_id": user_id,
        "task_id": task_id,
        "run_id": run_id,
        "message": "refresh" # Message content isn't used but good to have
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(endpoint, json=payload, timeout=5)
            logger.info(f"Pushed task list update notification for user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to push task list update to main server for task {task_id}: {e}", exc_info=False)