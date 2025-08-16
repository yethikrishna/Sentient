import logging
import uuid
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body

from main.config import ENVIRONMENT
from main.dependencies import auth_helper
from main.notifications.whatsapp_client import (check_phone_number_exists,
                                                 send_whatsapp_message)
from main.notifications.utils import create_and_push_notification
from workers.tasks import (cud_memory_task, run_due_tasks,
                           schedule_trigger_polling)

from .models import ContextInjectionRequest, WhatsAppTestRequest, TestNotificationRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/testing",
    tags=["Testing Utilities"]
)

def _check_allowed_environments(allowed_envs: List[str], detail_message: str):
    """
    Helper to enforce environment restrictions for endpoints.
    """
    if ENVIRONMENT not in allowed_envs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_message
        )

@router.post("/whatsapp", summary="Send a test WhatsApp notification")
async def send_test_whatsapp(
    request: WhatsAppTestRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    _check_allowed_environments(
        ["dev-local", "selfhost"],
        "This endpoint is only available in development or self-host environments."
    )

    phone_number = request.phone_number
    if not phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_number is required.")

    try:
        validation_result = await check_phone_number_exists(phone_number)
        if validation_result is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not connect to WhatsApp service to verify number.")
        
        if not validation_result.get("numberExists"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This phone number does not appear to be on WhatsApp."
            )

        chat_id = validation_result.get("chatId")
        if not chat_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve Chat ID for the number.")

        test_message = f"Hello from Sentient! 👋 This is a test notification for user {user_id}."
        result = await send_whatsapp_message(chat_id, test_message)

        if result and result.get("id"):
            logger.info(f"Successfully sent test WhatsApp message to {phone_number} for user {user_id}.")
            return {"message": "Test notification sent successfully.", "details": result}
        else:
            logger.error(f"Failed to send test WhatsApp message to {phone_number}. Result: {result}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send message via WAHA service.")
    except Exception as e:
        logger.error(f"Error sending test WhatsApp message for user {user_id}: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/trigger-scheduler", summary="Manually trigger the task scheduler")
async def trigger_scheduler(
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    _check_allowed_environments(
        ["dev-local", "selfhost"],
        "This endpoint is only available in development or self-host environments."
    )
    try:
        run_due_tasks.delay()
        logger.info(f"Manually triggered task scheduler by user {user_id}")
        return {"message": "Task scheduler (run_due_tasks) triggered successfully. Check Celery worker logs for execution."}
    except Exception as e:
        logger.error(f"Failed to manually trigger scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trigger scheduler task.")

@router.post("/trigger-poller", summary="Manually trigger the proactive polling scheduler")
async def trigger_poller(
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    _check_allowed_environments(
        ["dev-local", "selfhost"],
        "This endpoint is only available in development or self-host environments."
    )
    try:
        schedule_trigger_polling.delay()
        logger.info(f"Manually triggered trigger poller by user {user_id}")
        return {"message": "Trigger poller triggered successfully. Check Celery worker logs for execution."}
    except Exception as e:
        logger.error(f"Failed to manually trigger poller: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger poller task."
        )

@router.post("/notification", summary="Send a test notification")
async def send_test_notification(
    request: TestNotificationRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    _check_allowed_environments(
        ["dev-local", "selfhost"],
        "This endpoint is only available in development or self-host environments."
    )

    if request.type == "in-app":
        try:
            await create_and_push_notification(
                user_id=user_id,
                message="This is a test in-app notification from the developer tools.",
                notification_type="general"
            )
            return {"message": "Test in-app notification sent successfully."}
        except Exception as e:
            logger.error(f"Failed to send test in-app notification for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to send test notification.")
    else:
        raise HTTPException(status_code=400, detail="Invalid notification type specified.")


@router.post("/whatsapp/verify", summary="Verify if a WhatsApp number exists")
async def verify_whatsapp_number(
    request: WhatsAppTestRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    _check_allowed_environments(
        ["dev-local"],
        "This endpoint is only available in development environments."
    )
    
    phone_number = request.phone_number
    if not phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_number is required.")
        
    try:
        validation_result = await check_phone_number_exists(phone_number)
        if validation_result is None:
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not connect to WhatsApp service to verify number.")
        
        return validation_result
    except Exception as e:
        logger.error(f"Error verifying WhatsApp number for user {user_id}: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))