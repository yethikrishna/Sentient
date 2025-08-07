import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker
from main.notifications.whatsapp_client import check_phone_number_exists
from main.settings.models import WhatsAppMcpRequest, WhatsAppNotificationNumberRequest, ProfileUpdateRequest, ProactivitySettingsRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/settings",
    tags=["User Settings"]
)

@router.post("/whatsapp-mcp", summary="Connect or disconnect WhatsApp for the agent (MCP)")
async def set_whatsapp_mcp_number(
    request: WhatsAppMcpRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    whatsapp_number = request.whatsapp_mcp_number.strip() if request.whatsapp_mcp_number else ""

    if not whatsapp_number:
        update_payload = {
            "userData.integrations.whatsapp": {
                "connected": False,
                "credentials": None
            }
        }
        await mongo_manager.update_user_profile(user_id, update_payload)
        return JSONResponse(content={"message": "WhatsApp Agent disconnected."})

    try:
        validation_result = await check_phone_number_exists(whatsapp_number)
        if not validation_result or not validation_result.get("numberExists"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This phone number does not appear to be on WhatsApp.")

        chat_id = validation_result.get("chatId")
        if not chat_id:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve Chat ID for the number.")

        # For MCP, we store credentials under integrations
        update_payload = {
            "userData.integrations.whatsapp": {
                "connected": True,
                "auth_type": "manual_config",
                "credentials": { # Store unencrypted, as it's just a number/ID
                    "number": whatsapp_number,
                    "chatId": chat_id
                }
            }
        }
        await mongo_manager.update_user_profile(user_id, update_payload)
        return JSONResponse(content={"message": "WhatsApp Agent connected successfully."})

    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to WhatsApp service: {e}")
    except Exception as e:
        logger.error(f"Error setting WhatsApp MCP number for user {user_id}: {e}", exc_info=True)
        # Re-raise HTTPException or handle others
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get("/whatsapp-mcp", summary="Get WhatsApp MCP connection status")
async def get_whatsapp_mcp_number(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    if not user_profile:
        return JSONResponse(content={"whatsapp_mcp_number": "", "connected": False})

    wa_integration = user_profile.get("userData", {}).get("integrations", {}).get("whatsapp", {})
    return JSONResponse(content={
        "whatsapp_mcp_number": wa_integration.get("credentials", {}).get("number", ""),
        "connected": wa_integration.get("connected", False)
    })


@router.post("/whatsapp-notifications", summary="Set or Update WhatsApp number for notifications")
async def set_whatsapp_notification_number(
    request: WhatsAppNotificationNumberRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    whatsapp_number = request.whatsapp_notifications_number.strip() if request.whatsapp_notifications_number else ""
    if not whatsapp_number:
        update_payload = {
            "userData.notificationPreferences.whatsapp.number": "",
            "userData.notificationPreferences.whatsapp.chatId": "",
            "userData.notificationPreferences.whatsapp.enabled": False,
        }
        await mongo_manager.update_user_profile(user_id, update_payload)
        return JSONResponse(content={"message": "WhatsApp notification number removed."})

    try:
        validation_result = await check_phone_number_exists(whatsapp_number)
        if not validation_result or not validation_result.get("numberExists"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This phone number does not appear to be on WhatsApp.")

        chat_id = validation_result.get("chatId")
        if not chat_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve Chat ID for the number.")

        update_payload = {
            "userData.notificationPreferences.whatsapp.number": whatsapp_number,
            "userData.notificationPreferences.whatsapp.chatId": chat_id,
            "userData.notificationPreferences.whatsapp.enabled": True,
        }
        await mongo_manager.update_user_profile(user_id, update_payload)
        return JSONResponse(content={"message": "WhatsApp notification number updated successfully."})

    except ConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to WhatsApp service: {e}")
    except Exception as e:
        logger.error(f"Error setting WhatsApp notification number for user {user_id}: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get("/whatsapp-notifications", summary="Get WhatsApp Notification settings")
async def get_whatsapp_notification_settings(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    if not user_profile:
        return JSONResponse(content={"whatsapp_notifications_number": "", "notifications_enabled": False})

    wa_prefs = user_profile.get("userData", {}).get("notificationPreferences", {}).get("whatsapp", {})
    return JSONResponse(content={
        "whatsapp_notifications_number": wa_prefs.get("number", ""),
        "notifications_enabled": wa_prefs.get("enabled", False)
    })

@router.post("/profile", summary="Update User Profile and Onboarding Data")
async def update_profile_data(
    request: ProfileUpdateRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))
):
    """
    Updates the user's profile, including personal info, preferences,
    and the original onboarding answers.
    """
    try:
        update_payload = {
            "userData.onboardingAnswers": request.onboardingAnswers,
            "userData.personalInfo": request.personalInfo,
            "userData.preferences": request.preferences,
        }
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile.")
        return JSONResponse(content={"message": "Profile updated successfully."})
    except Exception as e:
        logger.error(f"Error updating profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
@router.get("/proactivity", summary="Get proactivity settings")
async def get_proactivity_settings(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    if not user_profile:
        return JSONResponse(content={"enabled": False})

    is_enabled = user_profile.get("userData", {}).get("preferences", {}).get("proactivityEnabled", False)
    return JSONResponse(content={"enabled": is_enabled})

@router.post("/proactivity", summary="Update proactivity settings")
async def update_proactivity_settings(
    request: ProactivitySettingsRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    is_enabled = request.enabled

    update_payload = {"userData.preferences.proactivityEnabled": is_enabled}
    profile_success = await mongo_manager.update_user_profile(user_id, update_payload)
    if not profile_success:
        raise HTTPException(status_code=500, detail="Failed to update user preference.")

    supported_services = ["gmail", "gcalendar"]
    polling_update_payload = {"is_enabled": is_enabled}

    polling_result = await mongo_manager.polling_state_collection.update_many(
        {
            "user_id": user_id,
            "service_name": {"$in": supported_services},
            "poll_type": "proactivity"
        },
        {"$set": polling_update_payload}
    )

    logger.info(f"Updated proactivity for user {user_id} to {is_enabled}. Matched {polling_result.matched_count} polling states.")

    message = "Proactivity enabled. I will now start monitoring your connected apps for helpful suggestions." if is_enabled else "Proactivity disabled."
    return JSONResponse(content={"message": message})
