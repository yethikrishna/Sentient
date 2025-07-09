import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker
from main.notifications.whatsapp_client import check_phone_number_exists, send_whatsapp_message
from main.settings.models import WhatsAppNumberRequest, ProfileUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/settings",
    tags=["User Settings"]
)

@router.post("/whatsapp", summary="Set or Update WhatsApp Notification Number")
async def set_whatsapp_number(
    request: WhatsAppNumberRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    whatsapp_number = request.whatsapp_number.strip()
    
    # If the number is empty, it means the user is opting out.
    if not whatsapp_number:
        update_payload = {"userData.notificationPreferences.whatsapp.number": ""}
        await mongo_manager.update_user_profile(user_id, update_payload)
        return JSONResponse(content={"message": "WhatsApp notifications disabled."})

    # Validate the number format and check with WAHA
    try:
        validation_result = await check_phone_number_exists(whatsapp_number)
        if not validation_result or not validation_result.get("numberExists"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This phone number does not appear to be on WhatsApp."
            )
        
        chat_id = validation_result.get("chatId")
        if not chat_id:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve Chat ID for the number."
            )

        # Save to user profile
        update_payload = {
            "userData.notificationPreferences.whatsapp": {
                "number": whatsapp_number,
                "chatId": chat_id,
                "enabled": True
            }
        }
        await mongo_manager.update_user_profile(user_id, update_payload)
        
        return JSONResponse(content={"message": "WhatsApp number updated successfully."})

    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to WhatsApp service: {e}")
    except Exception as e:
        logger.error(f"Error setting WhatsApp number for user {user_id}: {e}", exc_info=True)
        # Re-raise HTTPException or handle others
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get("/whatsapp", summary="Get WhatsApp Notification Number")
async def get_whatsapp_number(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    if not user_profile:
        return JSONResponse(content={"whatsapp_number": ""})

    wa_prefs = user_profile.get("userData", {}).get("notificationPreferences", {}).get("whatsapp", {})
    return JSONResponse(content={"whatsapp_number": wa_prefs.get("number", "")})
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
