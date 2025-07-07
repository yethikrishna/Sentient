import httpx
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

MAIN_SERVER_URL = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")

async def notify_user(user_id: str, message: str, task_id: Optional[str] = None):
    """
    Calls the main server to create a notification for the user.
    """
    endpoint = f"{MAIN_SERVER_URL}/notifications/internal/create"
    payload = {
        "user_id": user_id,
        "message": message,
        "task_id": task_id
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent notification for user {user_id}: {message}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send notification for user {user_id}. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending notification for {user_id}: {e}", exc_info=True)