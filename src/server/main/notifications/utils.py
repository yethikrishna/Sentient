import logging
from typing import Optional

from ..dependencies import mongo_manager, websocket_manager

logger = logging.getLogger(__name__)

async def create_and_push_notification(user_id: str, message: str, task_id: Optional[str] = None):
    """
    Saves a notification to the database and pushes it to the user via WebSocket.
    """
    notification_data = {
        "message": message,
        "task_id": task_id,
        "read": False
    }

    # Save to DB
    try:
        new_notification = await mongo_manager.add_notification(user_id, notification_data)
        if not new_notification:
            logger.error(f"Failed to save notification to DB for user {user_id}")
            return
        
        # Push via WebSocket
        push_payload = {
            "type": "new_notification",
            "notification": new_notification
        }
        await websocket_manager.send_personal_json_message(
            push_payload, user_id, connection_type="notifications"
        )
        logger.info(f"Pushed new notification to user {user_id}")

    except Exception as e:
        logger.error(f"Error creating/pushing notification for user {user_id}: {e}", exc_info=True)