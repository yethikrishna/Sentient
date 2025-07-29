import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker
from main.notifications.whatsapp_client import check_phone_number_exists, send_whatsapp_message
from main.settings.models import WhatsAppNumberRequest, ProfileUpdateRequest
from main.settings.models import WhatsAppMcpRequest, WhatsAppNotificationNumberRequest, WhatsAppNotificationRequest, ProfileUpdateRequest, LinkedInUrlRequest, AIPersonalitySettingsRequest
from workers.tasks import process_linkedin_profile

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

@router.get("/linkedin", summary="Get LinkedIn Profile URL")
async def get_linkedin_url(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    if not user_profile:
        return JSONResponse(content={"linkedin_url": ""})
    
    linkedin_url = user_profile.get("userData", {}).get("onboardingAnswers", {}).get("linkedin-url", "")
    return JSONResponse(content={"linkedin_url": linkedin_url})


@router.post("/linkedin", summary="Set or Update LinkedIn Profile URL")
async def set_linkedin_url(
    request: LinkedInUrlRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))
):
    linkedin_url = request.linkedin_url.strip() if request.linkedin_url else ""

    # Update the URL in the database
    update_payload = {"userData.onboardingAnswers.linkedin-url": linkedin_url}
    success = await mongo_manager.update_user_profile(user_id, update_payload)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update LinkedIn URL in profile.")

    # If a new URL is provided, trigger the scraping task
    if linkedin_url and "linkedin.com/in/" in linkedin_url:
        try:
            process_linkedin_profile.delay(user_id, linkedin_url)
            logger.info(f"Dispatched LinkedIn scraping task for user {user_id} from settings.")
            return JSONResponse(content={"message": "LinkedIn URL updated and profile import initiated."})
        except Exception as e:
            logger.error(f"Failed to dispatch LinkedIn scraping task for user {user_id} from settings: {e}", exc_info=True)
            # Still return success as the URL was saved, but with a warning.
            return JSONResponse(content={"message": "LinkedIn URL updated, but failed to initiate profile import."})
    
    # If URL is empty, it's being removed.
    if not linkedin_url:
        return JSONResponse(content={"message": "LinkedIn URL removed."})

    # If URL is invalid but not empty
    return JSONResponse(content={"message": "LinkedIn URL updated."})

@router.get("/ai-personality", summary="Get AI Personality Settings")
async def get_ai_personality_settings(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    profile = await mongo_manager.get_user_profile(user_id)
    if not profile or "userData" not in profile:
        raise HTTPException(status_code=404, detail="User profile not found.")

    preferences = profile.get("userData", {}).get("preferences", {})

    # Ensure all keys exist with default values if not present
    defaults = {
        "agentName": "Sentient",
        "responseVerbosity": "Balanced",
        "humorLevel": "Balanced",
        "useEmojis": True,
        "quietHours": {"enabled": False, "start": "22:00", "end": "08:00"},
        "notificationControls": {
            "taskNeedsApproval": True, "taskCompleted": True, "taskFailed": False,
            "proactiveSummary": False, "importantInsights": False
        }
    }

    for key, value in defaults.items():
        if key not in preferences:
            preferences[key] = value

    return JSONResponse(content=preferences)


@router.post("/ai-personality", summary="Update AI Personality Settings")
async def update_ai_personality_settings(
    request: AIPersonalitySettingsRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    update_payload = {f"userData.preferences.{key}": value for key, value in request.dict().items()}
    success = await mongo_manager.update_user_profile(user_id, update_payload)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update AI settings.")
    return JSONResponse(content={"message": "AI settings updated successfully."})
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