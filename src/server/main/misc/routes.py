# src/server/main/misc/routes.py
import datetime
import uuid
import json
import traceback
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

# Assuming models like OnboardingRequest are in the main models.py or a shared location
from ..models import OnboardingRequest, DataSourceToggleRequest 
# UserProfile might not be directly used as request/response here but good for context.

from ..auth.utils import PermissionChecker 
from ..config import (
    AUTH0_AUDIENCE, DATA_SOURCES_CONFIG, SUPPORTED_POLLING_SERVICES, POLLING_INTERVALS
)
from ..dependencies import mongo_manager, auth_helper, websocket_manager as main_websocket_manager
from ..db import MongoManager

# Router instance for miscellaneous routes
router = APIRouter(
    prefix="/api", # Using /api prefix as it seems common for such routes
    tags=["Miscellaneous API"]
)


# --- Utilities for data sources (moved here from original api/routes.py for clarity) ---
async def get_data_sources_config_for_user_api(user_id: str, db_manager: MongoManager):
    user_sources_config = []
    for source_name in SUPPORTED_POLLING_SERVICES:
        if source_name in DATA_SOURCES_CONFIG:
            general_config = DATA_SOURCES_CONFIG[source_name]
            polling_state = await db_manager.get_polling_state(user_id, source_name)
            
            is_enabled = False
            if polling_state:
                is_enabled = polling_state.get("is_enabled", False)
            else: 
                is_enabled = general_config.get("enabled_by_default", False)
            
            user_sources_config.append({
                "name": source_name,
                "display_name": general_config.get("display_name", source_name.capitalize()),
                "enabled": is_enabled,
                "configurable": general_config.get("configurable", True)
            })
    return user_sources_config

async def toggle_data_source_for_user_api(user_id: str, source_name: str, enable: bool, db_manager: MongoManager):
    if source_name not in SUPPORTED_POLLING_SERVICES or source_name not in DATA_SOURCES_CONFIG:
        raise ValueError(f"Data source '{source_name}' is not supported or configured.")

    update_payload = {"is_enabled": enable}
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if enable:
        update_payload["next_scheduled_poll_time"] = now_utc
        update_payload["is_currently_polling"] = False 
        update_payload["error_backoff_until_timestamp"] = None
        update_payload["consecutive_failure_count"] = 0
        update_payload["current_polling_tier"] = "user_enabled" 
        update_payload["current_polling_interval_seconds"] = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
    
    success = await db_manager.update_polling_state(user_id, source_name, update_payload)
    if not success:
        raise Exception(f"Failed to update data source '{source_name}' status in database.")
    
    print(f"[{datetime.datetime.now()}] [API_Utils] Polling state for {user_id}/{source_name} set to enabled={enable}")
    return success

# === Onboarding Routes ===
@router.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data")
async def save_onboarding_data_endpoint(
    request_body: OnboardingRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))
):
    print(f"[{datetime.datetime.now()}] [ONBOARDING] User {user_id}, Data keys: {list(request_body.data.keys())}")
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
        print(f"[{datetime.datetime.now()}] [ONBOARDING_ERROR] User {user_id}: {e}")
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
async def get_user_data_endpoint(user_id: str = Depends(auth_helper.get_current_user_id)):
    profile_doc = await mongo_manager.get_user_profile(user_id)
    if profile_doc and "userData" in profile_doc:
        return JSONResponse(content={"data": profile_doc["userData"], "status": 200})
    print(f"[{datetime.datetime.now()}] [GET_USER_DATA] No profile/userData for {user_id}. Creating basic entry.")
    await mongo_manager.update_user_profile(user_id, {"userData": {}}) 
    return JSONResponse(content={"data": {}, "status": 200}) 

# === Settings Routes (Data Sources) ===
@router.post("/get_data_sources", summary="Get Data Sources Configuration")
async def get_data_sources_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))):
    sources = await get_data_sources_config_for_user_api(user_id, mongo_manager)
    return JSONResponse(content={"data_sources": sources})

@router.post("/set_data_source_enabled", summary="Enable/Disable Data Source Polling")
async def set_data_source_enabled_endpoint(
    request_body: DataSourceToggleRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    try:
        await toggle_data_source_for_user_api(user_id, request_body.source, request_body.enabled, mongo_manager)
        return JSONResponse(content={"status": "success", "message": f"Data source '{request_body.source}' status set to {request_body.enabled}."})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [SETTINGS_TOGGLE_ERROR] User {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set data source status.")

# === Notifications Routes ===
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
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [NOTIF_WS_ERROR] Error (User: {authenticated_user_id or 'unknown'}): {e}")
    finally:
        if authenticated_user_id: 
            main_websocket_manager.disconnect_notifications(websocket)
            print(f"[{datetime.datetime.now()}] [NOTIF_WS] User {authenticated_user_id} notification WebSocket cleanup complete.")


@router.post("/notifications/get", summary="Get User Notifications")
async def get_notifications_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:notifications"]))):
    notifications = await mongo_manager.get_notifications(user_id)
    return JSONResponse(content={"notifications": notifications, "status": 200})

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