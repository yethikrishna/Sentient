import datetime
import uuid
import json
import traceback
import secrets
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging

from ..models import OnboardingRequest
from ..auth.utils import PermissionChecker, AuthHelper, aes_encrypt, aes_decrypt
from ..config import AUTH0_AUDIENCE
from ..dependencies import mongo_manager, auth_helper, websocket_manager as main_websocket_manager
from pydantic import BaseModel


# Google API libraries for validation
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# For dispatching memory tasks
from ...workers.tasks import process_memory_item

class PrivacyFiltersRequest(BaseModel):
    filters: List[str]

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Miscellaneous API"]
)

@router.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data")
async def save_onboarding_data_endpoint(
    request_body: OnboardingRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))
):
    logger.info(f"[{datetime.datetime.now()}] [ONBOARDING] User {user_id}, Data keys: {list(request_body.data.keys())}")
    try:
        # Generate and add supermemory_user_id
        supermemory_user_id = secrets.token_urlsafe(16)

        default_privacy_filters = [
            "bank statement", "account statement", "OTP", "one-time password",
            "password reset", "credit card", "debit card", "financial statement",
            "confidential", "do not share", "ssn", "social security"
        ]

        onboarding_data = request_body.data

        # --- Prepare data for MongoDB ---
        user_data_to_set: Dict[str, Any] = {
            "onboardingAnswers": onboarding_data,
            "onboardingComplete": True,
            "supermemory_user_id": supermemory_user_id,
            "privacyFilters": default_privacy_filters,
        }

        # Parse specific answers into structured fields
        personal_info = {}
        if "user-name" in onboarding_data and isinstance(onboarding_data["user-name"], str):
            personal_info["name"] = onboarding_data["user-name"]

        if "timezone" in onboarding_data and isinstance(onboarding_data["timezone"], str):
             personal_info["timezone"] = onboarding_data["timezone"]

        if "location" in onboarding_data:
            location_val = onboarding_data["location"]
            if isinstance(location_val, dict) and location_val.get('latitude') is not None:
                personal_info["location"] = location_val
            elif isinstance(location_val, str) and location_val.strip():
                personal_info["location"] = location_val.strip()

        if personal_info:
            user_data_to_set["personalInfo"] = personal_info

        preferences = {}
        if "communication-style" in onboarding_data:
            preferences["communicationStyle"] = onboarding_data["communication-style"]
        if "core-priorities" in onboarding_data and isinstance(onboarding_data["core-priorities"], list):
            preferences["corePriorities"] = onboarding_data["core-priorities"]

        if preferences:
            user_data_to_set["preferences"] = preferences

        # Create the final update payload for MongoDB
        update_payload = {f"userData.{key}": value for key, value in user_data_to_set.items()}
        
        # Save to DB
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save onboarding data.")

        # --- Dispatch facts to Supermemory ---
        try:
            fact_templates = {
                "user-name": "The user's name is {}.",
                "location": "The user's location is at latitude {latitude}, longitude {longitude}.",
                "timezone": "The user's timezone is {}.",
                "professional-context": "Professionally, the user has shared: {}",
                "personal-context": "Personally, the user is interested in: {}",
                "communication-style": "The user prefers a {} communication style.",
                "core-priorities": "The user's current life priorities are: {}."
            }
            onboarding_facts = []
            for key, value in onboarding_data.items():
                if not value or key not in fact_templates:
                    continue

                fact = ""
                if key == "location":
                    if isinstance(value, dict) and value.get('latitude') is not None:
                        fact = fact_templates[key].format(latitude=value.get('latitude'), longitude=value.get('longitude'))
                    elif isinstance(value, str) and value.strip():
                        # Use a different phrasing for manual location
                        fact = f"The user's location is around '{value}'."
                elif key == "core-priorities" and isinstance(value, list) and value:
                    fact = fact_templates[key].format(", ".join(value))
                elif isinstance(value, str) and value.strip():
                    fact = fact_templates[key].format(value)

                if fact:
                    onboarding_facts.append(fact)

            for fact in onboarding_facts:
                process_memory_item.delay(user_id, fact)
            
            logger.info(f"Dispatched {len(onboarding_facts)} onboarding facts to memory queue for user {user_id}")
        except Exception as celery_e:
            logger.error(f"Failed to dispatch onboarding facts to Celery for user {user_id}: {celery_e}", exc_info=True)
            # Don't fail the whole request, just log the error. Onboarding is still complete.

        return JSONResponse(content={"message": "Onboarding data saved successfully.", "status": 200})
    except Exception as e:
        logger.error(f"[{datetime.datetime.now()}] [ONBOARDING_ERROR] User {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save onboarding data: {str(e)}")

@router.post("/check-user-profile", status_code=status.HTTP_200_OK, summary="Check User Profile and Onboarding Status")
async def check_user_profile_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    profile_doc = await mongo_manager.get_user_profile(user_id)
    onboarding_complete = False
    if profile_doc and profile_doc.get("userData"):
        onboarding_complete = profile_doc["userData"].get("onboardingComplete", False)
    
    return JSONResponse(content={"profile_exists": bool(profile_doc), "onboarding_complete": onboarding_complete, "status": 200})

# === User Profile Routes ===
@router.post("/get-user-data", summary="Get User Profile's userData field")
async def get_user_data_endpoint(payload: dict = Depends(auth_helper.get_decoded_payload_with_claims)):
    user_id = payload.get("sub")
    profile_doc = await mongo_manager.get_user_profile(user_id)
    
    user_email_from_token = payload.get("email")
    stored_email = profile_doc.get("userData", {}).get("personalInfo", {}).get("email") if profile_doc else None

    if user_email_from_token and (not profile_doc or stored_email != user_email_from_token):
        logger.info(f"Updating stored email for user {user_id}.")
        await mongo_manager.update_user_profile(user_id, {"userData.personalInfo.email": user_email_from_token})
        # Re-fetch the profile after update if it was missing before
        if not profile_doc:
            profile_doc = await mongo_manager.get_user_profile(user_id)

    if profile_doc and "userData" in profile_doc:
        return JSONResponse(content={"data": profile_doc["userData"], "status": 200})
    print(f"[{datetime.datetime.now()}] [GET_USER_DATA] No profile/userData for {user_id}. Creating basic entry.")
    await mongo_manager.update_user_profile(user_id, {"userData": {}}) 
    return JSONResponse(content={"data": {}, "status": 200})

@router.websocket("/ws/notifications")
async def notifications_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: str | None = None
    try:
        authenticated_user_id = await auth_helper.ws_authenticate(websocket)
        if not authenticated_user_id: return

        await main_websocket_manager.connect_notifications(websocket, authenticated_user_id)
        print(f"[{datetime.datetime.now()}] [NOTIF_WS] User {authenticated_user_id} connected to notifications WebSocket.")
        while True:
            data = await websocket.receive_text() 
            message_payload = json.loads(data)
            if message_payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        print(f"[{datetime.datetime.now()}] [NOTIF_WS] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    finally:
        if authenticated_user_id: 
            await main_websocket_manager.disconnect_notifications(websocket)
            print(f"[{datetime.datetime.now()}] [NOTIF_WS] User {authenticated_user_id} notification WebSocket cleanup complete.")

# === Utility Endpoints (Token introspection, etc.) ===
@router.post("/utils/get-role", summary="Get User Role from Token Claims")
async def get_role_from_claims_endpoint(payload: dict = Depends(auth_helper.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@router.post("/utils/authenticate-google", summary="Validate or Refresh Stored Google Token (Dummy)")
async def authenticate_google_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"]))):
    user_profile = await mongo_manager.get_user_profile(user_id)
    
    encrypted_google_refresh_token_gmail = (
        user_profile.get("userData", {})
        .get("google_services", {})
        .get("gmail", {})
        .get("encrypted_refresh_token")
    ) if user_profile else None

    if not encrypted_google_refresh_token_gmail:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google Gmail credentials not found for user. Please authenticate via client.")

    print(f"[{datetime.datetime.now()}] [GOOGLE_AUTH_DUMMY_VALIDATION] Found stored Google Gmail token for user {user_id}. Assuming valid for dummy purposes.")
    return JSONResponse(content={"success": True, "message": "Google Gmail token present and assumed valid (dummy check)."})

# === Activity Route ===
@router.post("/activity/heartbeat", summary="User Activity Heartbeat")
async def user_activity_heartbeat_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    success = await mongo_manager.update_user_last_active(user_id)
    if success:
        return JSONResponse(content={"message": "User activity timestamp updated."})
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user activity.")

@router.get("/settings/privacy-filters", summary="Get User Privacy Filters")
async def get_privacy_filters_endpoint(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))
):
    profile = await mongo_manager.get_user_profile(user_id)
    filters = []
    if profile and profile.get("userData"):
        filters = profile["userData"].get("privacyFilters", [])
    
    return JSONResponse(content={"filters": filters})

@router.post("/settings/privacy-filters", summary="Update User Privacy Filters")
async def update_privacy_filters_endpoint(
    request: PrivacyFiltersRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    update_payload = {"userData.privacyFilters": request.filters}
    success = await mongo_manager.update_user_profile(user_id, update_payload)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update privacy filters.")
    return JSONResponse(content={"message": "Privacy filters updated successfully."})