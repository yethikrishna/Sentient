import datetime
import uuid
import json
import traceback
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging

from ..models import OnboardingRequest, GoogleAuthSettings
from ..auth.utils import PermissionChecker, AuthHelper, aes_encrypt
from ..config import AUTH0_AUDIENCE
from ..dependencies import mongo_manager, auth_helper, websocket_manager as main_websocket_manager

# Google API libraries for validation
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
        user_data_to_set = {
            "onboardingAnswers": request_body.data,
            "onboardingComplete": True,
        }
        if "user-name" in request_body.data and isinstance(request_body.data["user-name"], str):
            user_data_to_set.setdefault("personalInfo", {})["name"] = request_body.data["user-name"]

        update_payload = {f"userData.{key}": value for key, value in user_data_to_set.items()}
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save onboarding data.")
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

async def _validate_gcp_credentials(creds_json_str: str, user_email: str) -> bool:
    """
    Attempts to use the provided service account credentials to make a test API call.
    Returns True if successful, raises an exception otherwise.
    """
    try:
        creds_info = json.loads(creds_json_str)
        # We need drive scope for the about.get call and cloud-platform for maps
        scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=scopes, subject=user_email
        )
        
        # Use asyncio.to_thread to run the synchronous Google API call
        def run_validation():
            service = build('drive', 'v3', credentials=creds)
            # A simple, low-permission call to check if auth works
            service.about().get(fields='user').execute()
        
        await asyncio.to_thread(run_validation)
        return True
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="The provided credentials are not valid JSON.")
    except HttpError as e:
        error_details = json.loads(e.content).get('error', {})
        error_reason = error_details.get('errors', [{}])[0].get('reason', 'unknown')
        logger.error(f"Google API validation failed for {user_email}: {error_reason}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Google API Error: {error_details.get('message', 'Validation failed.')} Reason: {error_reason}. Please check your Service Account permissions and Domain-Wide Delegation setup.")
    except Exception as e:
        logger.error(f"Unexpected error during GCP credential validation for {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during validation: {str(e)}")


@router.post("/settings/google-auth", summary="Set user's Google authentication mode and credentials")
async def set_google_auth_settings(
    request_body: GoogleAuthSettings,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    update_payload = {"userData.googleAuth.mode": request_body.mode}
    
    if request_body.mode == "custom":
        if not request_body.credentialsJson:
            raise HTTPException(status_code=400, detail="credentialsJson is required for custom mode.")
        
        user_profile = await mongo_manager.get_user_profile(user_id)
        user_email = user_profile.get("userData", {}).get("personalInfo", {}).get("email") if user_profile else None
        if not user_email:
            raise HTTPException(status_code=400, detail="User email is required for custom credentials but was not found.")

        # Validate credentials before saving
        await _validate_gcp_credentials(request_body.credentialsJson, user_email)
        
        try:
            encrypted_creds = aes_encrypt(request_body.credentialsJson)
            update_payload["userData.googleAuth.encryptedCredentials"] = encrypted_creds
        except Exception as e:
            logger.error(f"Error encrypting Google credentials for user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not save credentials due to encryption error.")
    else: # mode is 'default'
        # Unset the credentials when switching back to default
        unset_payload = {"userData.googleAuth.encryptedCredentials": ""}
        await mongo_manager.user_profiles_collection.update_one({"user_id": user_id}, {"$unset": unset_payload})

    success = await mongo_manager.update_user_profile(user_id, update_payload)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update Google auth settings in database.")
        
    return JSONResponse(content={"message": "Google API settings saved and validated successfully."})


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
            main_websocket_manager.disconnect_notifications(websocket)
            print(f"[{datetime.datetime.now()}] [NOTIF_WS] User {authenticated_user_id} notification WebSocket cleanup complete.")

# === Utility Endpoints (Token introspection, etc.) ===
@router.post("/utils/get-role", summary="Get User Role from Token Claims")
async def get_role_from_claims_endpoint(payload: dict = Depends(auth_helper.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@router.post("/utils/get-referral-code", summary="Get Referral Code from Token")
async def get_referral_code_endpoint(payload: dict = Depends(auth_helper.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    referral_code = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referralCode")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": referral_code})

@router.post("/utils/get-referrer-status", summary="Get Referrer Status from Token")
async def get_referrer_status_endpoint(payload: dict = Depends(auth_helper.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    referrer_status = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referrerStatus", False)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referrerStatus": referrer_status})

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