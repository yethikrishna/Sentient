import logging
from typing import Optional, Dict, Any
import datetime

from main.dependencies import mongo_manager, websocket_manager
from main.notifications.whatsapp_client import send_whatsapp_message # Import the new client

logger = logging.getLogger(__name__)

async def create_and_push_notification(user_id: str, message: str, task_id: Optional[str] = None, notification_type: str = "general", payload: Optional[Dict[str, Any]] = None):
    """
    Saves a notification to the database, pushes it via WebSocket, and sends it via WhatsApp if configured.
    Handles different notification types.
    """

    notification_data = {}

    if notification_type == "proactive_suggestion" and payload:
        notification_data = {
            "type": "proactive_suggestion",
            "message": message,
            "is_actioned": False,
            "suggestion_payload": {
                "suggestion_type": payload.get("suggestion_type"),
                "action_details": payload.get("action_details"),
                "gathered_context": payload.get("gathered_context")
            }
        }
    else: # Default, general notification
        notification_data = {
            "type": "general",
            "message": message,
            "task_id": task_id,
            "read": False
        }

    try:
        # 1. Save to DB
        new_notification = await mongo_manager.add_notification(user_id, notification_data)
        if not new_notification:
            logger.error(f"Failed to save notification to DB for user {user_id}")
            return

        # Convert datetime to string for JSON serialization before pushing
        if isinstance(new_notification.get("timestamp"), datetime.datetime):
            new_notification["timestamp"] = new_notification["timestamp"].isoformat()
        
        # 2. Push via WebSocket to UI
        push_payload = {
            "type": "new_notification",
            "notification": new_notification
        }
        await websocket_manager.send_personal_json_message(
            push_payload, user_id, connection_type="notifications"
        )
        logger.info(f"Pushed new notification to user {user_id} via WebSocket.")

        # 3. Send via WhatsApp (only for general notifications for now)
        if notification_type == "general":
            user_profile = await mongo_manager.get_user_profile(user_id)
            if user_profile:
                wa_prefs = user_profile.get("userData", {}).get("notificationPreferences", {}).get("whatsapp", {})
                if wa_prefs.get("enabled") and wa_prefs.get("chatId"):
                    logger.info(f"Attempting to send WhatsApp notification to user {user_id}")
                    await send_whatsapp_message(wa_prefs["chatId"], message)
                else:
                    logger.info(f"WhatsApp notifications disabled or not configured for user {user_id}.")

    except Exception as e:
        logger.error(f"Error creating/pushing notification for user {user_id}: {e}", exc_info=True)