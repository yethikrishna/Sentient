# src/server/main/proactivity/routes.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker
from main.proactivity.models import SuggestionActionRequest
from main.proactivity.learning import record_user_feedback
from workers.tasks import create_task_from_suggestion

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/proactivity",
    tags=["Proactivity"]
)

@router.post("/action", summary="Handle user action on a proactive suggestion")
async def handle_suggestion_action(
    request: SuggestionActionRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"])) # Reuse existing permission
):
    # 1. Find the notification and atomically mark it as actioned
    user_notif_doc = await mongo_manager.find_and_action_suggestion_notification(user_id, request.notification_id)

    if not user_notif_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found, it may have already been actioned or expired."
        )

    # Extract the specific notification from the user's document
    notification = next((n for n in user_notif_doc.get("notifications", []) if n["id"] == request.notification_id), None)

    if not notification:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification data could not be extracted.")

    # 2. Extract payload for further processing
    suggestion_payload = notification.get("suggestion_payload")
    if not suggestion_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid suggestion payload in notification.")

    suggestion_type = suggestion_payload.get("suggestion_type")

    # 3. Process based on user action
    if request.user_action == "approved":
        logger.info(f"User '{user_id}' approved suggestion '{request.notification_id}' of type '{suggestion_type}'.")

        # Re-extract with default for robustness, as suggested by diff
        suggestion_payload = notification.get("suggestion_payload", {})
        gathered_context = suggestion_payload.get("gathered_context")

        # 3a. Trigger Celery task to create the actual task
        create_task_from_suggestion.delay( # noqa
            user_id=user_id,
            suggestion_payload=suggestion_payload,
            context=gathered_context
        )

        # 3b. Record positive feedback
        await record_user_feedback(user_id, suggestion_type, "positive")

        return {"message": "Suggestion approved. A new task is being created."}

    elif request.user_action == "dismissed":
        logger.info(f"User '{user_id}' dismissed suggestion '{request.notification_id}' of type '{suggestion_type}'.")

        # 3c. Record negative feedback
        await record_user_feedback(user_id, suggestion_type, "negative")

        return {"message": "Suggestion dismissed. We'll learn from your feedback."}

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user action.")