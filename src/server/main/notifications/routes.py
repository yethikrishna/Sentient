import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from main.notifications.models import CreateNotificationRequest, DeleteNotificationRequest
from main.notifications.utils import create_and_push_notification
from main.dependencies import mongo_manager, auth_helper
from main.auth.utils import PermissionChecker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/internal/create", status_code=status.HTTP_201_CREATED, summary="Create a Notification (Internal Worker Use)", include_in_schema=False)
async def create_notification_internal(request: CreateNotificationRequest):
    # This is an internal endpoint called by workers.
    # It trusts the user_id provided in the payload.
    # In a production environment, this should be secured (e.g., with a shared secret/API key).
    try:
        await create_and_push_notification(
            request.user_id,
            request.message,
            request.task_id,
            request.notification_type,
            request.payload
        )
        return {"message": "Notification created and pushed successfully."}
    except Exception as e:
        logger.error(f"Internal notification creation failed for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("", summary="Get All User Notifications")
async def get_notifications(user_id: str = Depends(PermissionChecker(required_permissions=["read:notifications"]))):
    notifications = await mongo_manager.get_notifications(user_id)
    return JSONResponse(content={"notifications": notifications})

@router.post("/delete", summary="Delete a User Notification")
async def delete_notification(
    request: DeleteNotificationRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:notifications"]))
):
    if request.delete_all:
        await mongo_manager.delete_all_notifications(user_id)
        return JSONResponse(content={"message": "All notifications deleted successfully."})

    if request.notification_id:
        success = await mongo_manager.delete_notification(user_id, request.notification_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or user does not have permission.")
        return JSONResponse(content={"message": "Notification deleted successfully."})

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either 'notification_id' or 'delete_all' must be provided."
    )
