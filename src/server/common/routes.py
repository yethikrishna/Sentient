from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
import traceback
import asyncio
import json 
import uuid 
import datetime

from server.common.dependencies import (
    auth, # AuthHelper instance
    PermissionChecker,
    mongo_manager,
    manager as websocket_manager,
    get_chat_history_messages,
    add_message_to_db,
    load_user_profile,
    write_user_profile,
    # task_queue, # Keep if needed for Gmail -> Kafka pipeline, otherwise remove
    # memory_backend, # Removed
    # graph_driver, # Removed
    # embed_model, # Removed
    start_user_context_engines, # For enabling Gmail polling
    DATA_SOURCES_CONFIG,
    # active_context_engines # Not directly used in routes
)


from server.utils.helpers import (
    aes_encrypt,
    aes_decrypt,
    get_management_token
)

# For dummy chat response
from server.common.functions import generate_dummy_streaming_response, generate_dummy_response
# Removed: get_unified_classification_runnable, get_priority_runnable, etc.
# Removed: get_chat_runnable (dummy chat is handled directly)

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

router = APIRouter(
    tags=["Common (Simplified)"]
)

# --- Pydantic Models ---
class Message(BaseModel):
    input: str
    # pricing and credits are less relevant for dummy responses but client sends them
    pricing: Optional[str] = "free" 
    credits: Optional[int] = 0

class OnboardingData(BaseModel):
    data: Dict[str, Any]

class UpdateUserDataRequest(BaseModel):
    data: Dict[str, Any]

class AddUserDataRequest(BaseModel):
    data: Dict[str, Any]
    
class EncryptionRequest(BaseModel):
    data: str

class DecryptionRequest(BaseModel):
    encrypted_data: str

class SetReferrerRequest(BaseModel):
    referral_code: str

class SetDataSourceEnabledRequest(BaseModel):
    source: str
    enabled: bool

# --- Onboarding and User Profile Endpoints ---
@router.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data")
async def save_onboarding_data_endpoint(onboarding_data: OnboardingData, user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /onboarding] User {user_id}, Onboarding Data received.")
    try:
        # Prepare user data from onboarding answers
        # The client sends onboarding_data.data as a flat dictionary of answers
        # e.g., {"user-name": "Test User", "personal-info": ["Tech", "Travel"], ...}
        
        # We need to structure this into something like profile.userData
        # For simplicity, let's put all onboarding answers directly into userData.onboardingAnswers
        
        user_data_to_set = {
            "onboardingAnswers": onboarding_data.data,
            "onboardingComplete": True,
            "last_updated": datetime.datetime.now(datetime.timezone.utc)
        }
        
        # If personalInfo can be extracted (e.g., name), update that too
        if "user-name" in onboarding_data.data and isinstance(onboarding_data.data["user-name"], str):
            if "personalInfo" not in user_data_to_set:
                 user_data_to_set["personalInfo"] = {}
            user_data_to_set["personalInfo"]["name"] = onboarding_data.data["user-name"]

        # update_user_profile expects a flat structure for top-level fields, 
        # or keys prefixed with "userData." for nested userData fields.
        # Let's prepare the update payload accordingly.
        
        update_payload = {}
        for key, value in user_data_to_set.items():
            update_payload[f"userData.{key}"] = value
            
        success = await mongo_manager.update_user_profile(user_id, update_payload)

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save onboarding data to user profile.")

        # Neo4j graph building is removed.
        print(f"[{datetime.datetime.now()}] [ONBOARDING] Onboarding data saved to MongoDB for user {user_id}.")
        return JSONResponse(content={"message": "Onboarding data saved successfully.", "status": 200})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /onboarding] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save onboarding data: {str(e)}")

@router.post("/check-user-profile", status_code=status.HTTP_200_OK, summary="Check User Profile Existence")
async def check_user_profile_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /check-user-profile] Called by user {user_id}.")
    try:
        profile = await mongo_manager.get_user_profile(user_id)
        if profile:
            onboarding_complete = profile.get("userData", {}).get("onboardingComplete", False)
            return JSONResponse(content={"profile_exists": True, "onboarding_complete": onboarding_complete})
        else:
            # If profile doesn't exist, it means user is new post-Auth0 signup.
            # The main_index.js checkValidity flow will create a basic profile if this returns profile_exists: False.
            # Or, we can create it here too for robustness.
            print(f"[{datetime.datetime.now()}] [USER_PROFILE] Profile does NOT exist for user {user_id}. Will be created by client flow or onboarding.")
            return JSONResponse(content={"profile_exists": False, "onboarding_complete": False})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /check-user-profile] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check user profile.")


@router.post("/get-user-data", status_code=status.HTTP_200_OK, summary="Get User Profile Data (userData field)")
async def get_user_data_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /get-user-data] User {user_id}.")
    try:
        profile = await load_user_profile(user_id) # load_user_profile already handles default structure
        return JSONResponse(content={"data": profile.get("userData", {}), "status": 200})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /get-user-data] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user data.")

# --- Chat Endpoints (Simplified for Dummy Responses) ---
@router.post("/get-history", status_code=status.HTTP_200_OK, summary="Get Chat History")
async def get_history_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /get-history] User {user_id}.")
    try:
        messages, effective_chat_id = await get_chat_history_messages(user_id, None)
        return JSONResponse(content={"messages": messages, "activeChatId": effective_chat_id})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /get-history] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get chat history.")

@router.post("/clear-chat-history", status_code=status.HTTP_200_OK, summary="Clear Active Chat History")
async def clear_chat_history_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /clear-chat-history] User {user_id}.")
    try:
        # ... (logic from app.py, ensure mongo_manager is used correctly) ...
        user_profile = await mongo_manager.get_user_profile(user_id)
        active_chat_id = user_profile.get("userData", {}).get("active_chat_id")

        if active_chat_id:
            await mongo_manager.delete_chat_history(user_id, active_chat_id)
        
        # Always assign a new active_chat_id
        new_active_chat_id = str(uuid.uuid4())
        await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_active_chat_id})
        
        message = "Active chat history cleared and new session started." if active_chat_id else "New chat session started."
        print(f"[{datetime.datetime.now()}] [CHAT_HISTORY] User {user_id}: {message} New active ID: {new_active_chat_id}")
        return JSONResponse(content={"message": message, "activeChatId": new_active_chat_id})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /clear-chat-history] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear chat history.")


@router.post("/chat", summary="Process Chat Message (Dummy Response)")
async def chat_endpoint_dummy(message: Message, user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /chat DUMMY] User {user_id}. Input: '{message.input[:50]}...'")
    
    user_profile = await load_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
    _, active_chat_id = await get_chat_history_messages(user_id, None) # Ensure active_chat_id

    if not active_chat_id:
        # This should ideally not happen if get_chat_history_messages works correctly
        print(f"[{datetime.datetime.now()}] [CHAT_DUMMY_ERROR] Could not determine active_chat_id for user {user_id}.")
        async def error_gen():
            yield json.dumps({"type":"error", "message":"Failed to determine active chat session."})+"\n"
        return StreamingResponse(error_gen(), media_type="application/x-ndjson")

    # Save user's message
    user_msg_id = await add_message_to_db(user_id, active_chat_id, message.input, is_user=True, is_visible=True)
    if not user_msg_id:
        async def error_gen_db():
            yield json.dumps({"type":"error", "message":"Failed to save user message to database."})+"\n"
        return StreamingResponse(error_gen_db(), media_type="application/x-ndjson")

    async def dummy_response_generator():
        # First, yield confirmation of user message saved
        yield json.dumps({
            "type": "userMessage", 
            "id": user_msg_id, 
            "message": message.input, 
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }) + "\n"
        await asyncio.sleep(0.01) # Tiny delay for client processing

        # Simulate "Thinking..."
        assistant_temp_id = str(uuid.uuid4()) # Temporary ID for streaming visuals
        yield json.dumps({"type": "intermediary", "message": "Thinking...", "id": assistant_temp_id}) + "\n"
        await asyncio.sleep(0.5) # Simulate thinking time

        # Stream the dummy response
        full_dummy_text = ""
        async for token in generate_dummy_streaming_response(message.input, username):
            if token:
                full_dummy_text += token
                yield json.dumps({"type": "assistantStream", "token": token, "done": False, "messageId": assistant_temp_id}) + "\n"
            else: # End of stream signal from dummy generator
                break 
            await asyncio.sleep(0.02) # Small delay between tokens

        # Save the complete dummy assistant message to DB
        db_assistant_msg_id = await add_message_to_db(
            user_id, active_chat_id, full_dummy_text, 
            is_user=False, is_visible=True, 
            # Add dummy metadata flags
            memoryUsed=False, agentsUsed=False, internetUsed=False 
        )
        
        # Send final "done" signal with the actual DB ID
        yield json.dumps({
            "type": "assistantStream", 
            "token": "", # No more tokens
            "done": True, 
            "memoryUsed": False, "agentsUsed": False, "internetUsed": False, 
            "proUsed": False, # Dummy responses don't use pro features
            "messageId": db_assistant_msg_id or assistant_temp_id # Use DB ID if available
        }) + "\n"

    return StreamingResponse(dummy_response_generator(), media_type="application/x-ndjson")


# --- Data Source Management Endpoints ---
@router.post("/get_data_sources", summary="Get Data Sources Configuration")
async def get_data_sources_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))):
    """Returns the configuration of available data sources, primarily Gmail for this revamp."""
    print(f"[{datetime.datetime.now()}] [ENDPOINT /get_data_sources] User {user_id}")
    
    # Simplified: only return Gmail and its current enabled status for the user
    gmail_polling_state = await mongo_manager.get_polling_state(user_id, "gmail")
    gmail_enabled = False
    if gmail_polling_state:
        gmail_enabled = gmail_polling_state.get("is_enabled", False)
    else:
        # If no state, check default from DATA_SOURCES_CONFIG (but user must enable it)
        gmail_enabled = DATA_SOURCES_CONFIG.get("gmail", {}).get("enabled_by_default", False)


    # The client expects a list of source objects
    # Reconstruct what client expects: [{name: "gmail", enabled: true/false, ...other_props_if_needed...}]
    # For now, just name and enabled status
    sources_to_return = [{"name": "gmail", "enabled": gmail_enabled}]
    
    return JSONResponse(content={"data_sources": sources_to_return})

@router.post("/set_data_source_enabled", summary="Enable/Disable Data Source Polling")
async def set_data_source_enabled_endpoint(request: SetDataSourceEnabledRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /set_data_source_enabled] User {user_id}, Source: {request.source}, Enabled: {request.enabled}")
    
    if request.source != "gmail":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Data source '{request.source}' is not supported for toggling.")

    try:
        # Get current state or initialize if not present
        current_state = await mongo_manager.get_polling_state(user_id, request.source)
        if not current_state and request.enabled: # If enabling and no state, initialize it
            print(f"[{datetime.datetime.now()}] Initializing polling state for {user_id}/{request.source} as it's being enabled.")
            engine_class = DATA_SOURCES_CONFIG[request.source]['engine_class']
            engine_instance = engine_class(user_id=user_id, db_manager=mongo_manager) # Pass db_manager
            await engine_instance.initialize_polling_state()
            # After init, fetch state again to apply further updates
            current_state = await mongo_manager.get_polling_state(user_id, request.source)


        update_payload = {"is_enabled": request.enabled}
        if request.enabled:
            # If enabling, ensure it's scheduled to poll soon and reset any error state
            update_payload["next_scheduled_poll_time"] = datetime.datetime.now(timezone.utc)
            update_payload["is_currently_polling"] = False
            update_payload["error_backoff_until_timestamp"] = None
            update_payload["consecutive_failure_count"] = 0
            if current_state: # If state existed, keep its current interval or reset to active
                 update_payload["current_polling_interval_seconds"] = current_state.get("current_polling_interval_seconds", POLLING_INTERVALS["ACTIVE_USER_SECONDS"])
                 update_payload["current_polling_tier"] = current_state.get("current_polling_tier", "enabled_by_user")
            else: # New state, use default active
                 update_payload["current_polling_interval_seconds"] = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
                 update_payload["current_polling_tier"] = "newly_enabled"

        success = await mongo_manager.update_polling_state(user_id, request.source, update_payload)
        
        if not success:
            # This can happen if the document didn't exist and upsert also failed, which is unlikely with correct MongoDB setup.
            # Or if the update_one call itself had an issue.
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update data source '{request.source}' status in database.")

        # If a service is enabled, ensure its context engine and polling states are initialized/updated
        if request.enabled:
            await start_user_context_engines(user_id) # This will specifically look at Gmail for now

        return JSONResponse(content={"status": "success", "message": f"Data source '{request.source}' status set to {request.enabled}."})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /set_data_source_enabled] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set data source status.")


# --- WebSocket Endpoint for real-time notifications (can be kept simple) ---
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): # WebSocket type is imported from FastAPI
    await websocket.accept()
    authenticated_user_id: Optional[str] = None
    try:
        # Authenticate WebSocket connection
        authenticated_user_id = await auth.ws_authenticate(websocket) # Using the auth instance
        if not authenticated_user_id:
            print(f"[{datetime.datetime.now()}] [WS /ws] WebSocket authentication failed or connection closed during auth.")
            return # ws_authenticate already closes the websocket on failure
        
        await websocket_manager.connect(websocket, authenticated_user_id)
        
        # Keep connection alive and listen for pings or control messages
        while True:
            data = await websocket.receive_text()
            try:
                message_payload = json.loads(data)
                if message_payload.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                # else:
                    # print(f"[{datetime.datetime.now()}] [WS /ws] Received unhandled message from {authenticated_user_id}: {message_payload}")
            except json.JSONDecodeError:
                print(f"[{datetime.datetime.now()}] [WS /ws] Received non-JSON message from {authenticated_user_id}. Ignoring.")
            except Exception as e_ws_loop:
                print(f"[{datetime.datetime.now()}] [WS /ws] Error in WebSocket loop for user {authenticated_user_id}: {e_ws_loop}")
                # Consider breaking loop or specific error handling for robustness
                break # Example: break on unexpected errors in loop

    except WebSocketDisconnect:
        print(f"[{datetime.datetime.now()}] [WS /ws] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [WS /ws] Unexpected WebSocket error (User: {authenticated_user_id or 'unknown'}): {e}")
        traceback.print_exc()
        try:
            # Ensure graceful close if possible
            if websocket.client_state != WebSocketState.DISCONNECTED: # Check if not already disconnected
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except RuntimeError as re:
            print(f"[{datetime.datetime.now()}] [WS /ws] Error during explicit close in exception handler (likely already closing/closed): {re}")
        except Exception as e_close:
            print(f"[{datetime.datetime.now()}] [WS /ws] Unexpected error during explicit close in exception handler: {e_close}")
    finally:
        if authenticated_user_id: 
            websocket_manager.disconnect(websocket)
        print(f"[{datetime.datetime.now()}] [WS /ws] WebSocket connection cleaned up for user: {authenticated_user_id or 'unknown'}")


# --- User Activity and Sync Endpoints ---
@router.post("/users/activity/heartbeat", status_code=status.HTTP_200_OK, summary="User Activity Heartbeat")
async def user_activity_heartbeat_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    # print(f"[{datetime.datetime.now()}] [ENDPOINT /users/activity/heartbeat] Received heartbeat for user {user_id}") # Can be verbose
    try:
        success = await mongo_manager.update_user_last_active(user_id)
        if success:
            return JSONResponse(content={"message": "User activity timestamp updated."})
        else:
            # This case implies the user_id might not exist, or a DB write failed.
            # update_user_last_active uses upsert=True, so it should create if not exist.
            print(f"[{datetime.datetime.now()}] [ERROR] Failed to update last_active_timestamp for user {user_id} via MongoManager.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user activity.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /users/activity/heartbeat] for {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing heartbeat.")

@router.post("/users/force-sync/{engine_category}", status_code=status.HTTP_200_OK, summary="Force Sync for a Service")
async def force_sync_service_endpoint(engine_category: str, user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))):
    print(f"[{datetime.datetime.now()}] [ENDPOINT /users/force-sync] User {user_id} requests force sync for {engine_category}")
    
    if engine_category != "gmail":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Service '{engine_category}' not supported for force sync in this version.")
        
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Set next_scheduled_poll_time to now to trigger immediate consideration by scheduler
        # Also ensure is_currently_polling is false and error backoff is cleared.
        update_payload = {
            "next_scheduled_poll_time": now_utc,
            "is_currently_polling": False,
            "error_backoff_until_timestamp": None, # Clear any error backoff
            "consecutive_failure_count": 0, # Reset failures
            "current_polling_tier": "forced_sync_request" # Optional: Mark how it was triggered
        }
        
        success = await mongo_manager.update_polling_state(user_id, engine_category, update_payload)
        
        if not success:
            # This could mean the polling state document for this user/service doesn't exist.
            # Try to initialize it, which will also set next_scheduled_poll_time to now.
            print(f"[{datetime.datetime.now()}] [FORCE_SYNC_WARN] Failed to directly update polling state for {user_id}/{engine_category}. Attempting initialization.")
            engine_class = DATA_SOURCES_CONFIG[engine_category]['engine_class']
            temp_engine = engine_class(user_id=user_id, db_manager=mongo_manager)
            await temp_engine.initialize_polling_state() # This sets next_poll_time to now
            # No need to update again, initialize_polling_state handles it.
            print(f"[{datetime.datetime.now()}] [FORCE_SYNC] Polling state initialized and scheduled for {user_id}/{engine_category}.")
        else:
            print(f"[{datetime.datetime.now()}] [FORCE_SYNC] Polling for {user_id}/{engine_category} scheduled immediately.")
            
        return JSONResponse(content={"message": f"Sync requested for {engine_category}. It will be processed shortly."})

    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ERROR /users/force-sync] for {user_id}/{engine_category}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing force sync request.")
    
    
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import traceback
import pickle # For Google Auth
import os


# Pydantic models moved from app.py

# Define Google OAuth specific configurations locally or import from a dedicated config module
# For this fix, we define them locally to break the cycle with app.py.
SCOPES_UTIL = ["https://www.googleapis.com/auth/gmail.send",
             "https://www.googleapis.com/auth/gmail.compose",
             "https://www.googleapis.com/auth/gmail.modify",
             "https://www.googleapis.com/auth/gmail.readonly",
             "https://www.googleapis.com/auth/documents",
             "https://www.googleapis.com/auth/calendar",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/presentations",
             "https://www.googleapis.com/auth/drive",
             "https://mail.google.com/"]

CREDENTIALS_DICT_UTIL = {"installed": {"client_id": os.environ.get("GOOGLE_CLIENT_ID"), "project_id": os.environ.get("GOOGLE_PROJECT_ID"), "auth_uri": os.environ.get("GOOGLE_AUTH_URI"), "token_uri": os.environ.get("GOOGLE_TOKEN_URI"), "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"), "redirect_uris": ["http://localhost"]}}

_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVER_DIR = os.path.dirname(_UTILS_DIR)
_SRC_DIR = os.path.dirname(_SERVER_DIR)
TOKEN_DIR = os.path.join(_SRC_DIR, "tokens")


@router.post("/encrypt", status_code=status.HTTP_200_OK, summary="Encrypt Data")
async def encrypt_data_route(request: EncryptionRequest): # Added _route to avoid conflict
    try:
        return JSONResponse(content={"encrypted_data": aes_encrypt(request.data)})
    except Exception as e:
        print(f"[ERROR] /utils/encrypt: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption failed.")

@router.post("/decrypt", status_code=status.HTTP_200_OK, summary="Decrypt Data")
async def decrypt_data_route(request: DecryptionRequest): # Added _route to avoid conflict
    try:
        return JSONResponse(content={"decrypted_data": aes_decrypt(request.encrypted_data)})
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decryption failed: Invalid data or key.")
    except Exception as e:
        print(f"[ERROR] /utils/decrypt: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Decryption failed.")

@router.post("/get-role", status_code=status.HTTP_200_OK, summary="Get User Role from Token")
async def get_role_route(payload: dict = Depends(auth.get_decoded_payload_with_claims)): # Added _route
    user_id = payload["user_id"]
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if AUTH0_AUDIENCE and not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    print(f"[ENDPOINT /utils/get-role] Called by user {user_id} (from token claims).")
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free")
    print(f"User {user_id} role from token claim: {user_role}")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@router.post("/get-referral-code", status_code=status.HTTP_200_OK, summary="Get Referral Code from Token")
async def get_referral_code_route(payload: dict = Depends(auth.get_decoded_payload_with_claims)): # Added _route
    user_id = payload["user_id"]
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if AUTH0_AUDIENCE and not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    print(f"[ENDPOINT /utils/get-referral-code] Called by user {user_id} (from token claims).")
    referral_code = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referralCode", None)
    if not referral_code:
        print(f"User {user_id} referral code not found in token claims.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": None})
    print(f"User {user_id} referral code from token claim found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": referral_code})

@router.post("/get-referrer-status", status_code=status.HTTP_200_OK, summary="Get Referrer Status from Token")
async def get_referrer_status_route(payload: dict = Depends(auth.get_decoded_payload_with_claims)): # Added _route
    user_id = payload["user_id"]
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if AUTH0_AUDIENCE and not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    print(f"[ENDPOINT /utils/get-referrer-status] Called by user {user_id} (from token claims).")
    referrer_status = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referrerStatus", False)
    print(f"User {user_id} referrer status from token claim: {referrer_status}")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referrerStatus": referrer_status})

@router.post("/set-referrer-status", status_code=status.HTTP_200_OK, summary="Set Referrer Status by Code (Admin Action)")
async def set_referrer_status_route( # Renamed to avoid conflict with app.py if it was there
    request: SetReferrerRequest,
    user_id_making_request: str = Depends(PermissionChecker(required_permissions=["admin:user_metadata"]))
):
    referral_code_to_find = request.referral_code
    AUTH0_DOMAIN_LOCAL = os.getenv("AUTH0_DOMAIN") # Use local var to avoid shadowing
    print(f"[ENDPOINT /utils/set-referrer-status] User {user_id_making_request} trying to set referrer for code {referral_code_to_find}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="M2M token unavailable.")

        headers_search = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        search_url = f"https://{AUTH0_DOMAIN_LOCAL}/api/v2/users"
        params = {'q': f'app_metadata.referralCode:"{referral_code_to_find}"', 'search_engine': 'v3'}
        async with httpx.AsyncClient() as client:
            search_response = await client.get(search_url, headers=headers_search, params=params)
        if search_response.status_code != 200:
            raise HTTPException(status_code=search_response.status_code, detail=f"Auth0 User Search Error: {search_response.text}")
        
        users_found = search_response.json()
        if not users_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No user with referral code: {referral_code_to_find}")

        user_to_update_id = users_found[0].get("user_id")
        if not user_to_update_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Found user, but ID missing.")

        update_url = f"https://{AUTH0_DOMAIN_LOCAL}/api/v2/users/{user_to_update_id}"
        update_payload = {"app_metadata": {"referrer": True}} # Assuming this is the correct claim name
        headers_update = {"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            update_response = await client.patch(update_url, headers=headers_update, json=update_payload)
        if update_response.status_code != 200:
            raise HTTPException(status_code=update_response.status_code, detail=f"Auth0 User Update Error: {update_response.text}")

        print(f"Referrer status set to True for user {user_to_update_id} (referred by code {referral_code_to_find}).")
        return JSONResponse(content={"message": "Referrer status updated successfully for the user who was referred."})
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERROR] /utils/set-referrer-status: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set referrer status.")

# --- Google Authentication Endpoint ---
@router.post("/authenticate-google", status_code=status.HTTP_200_OK, summary="Authenticate Google Services")
async def authenticate_google_route(user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"]))): # Added _route
    print(f"[ENDPOINT /utils/authenticate-google] User {user_id}.")
    os.makedirs(TOKEN_DIR, exist_ok=True)
    token_path = os.path.join(TOKEN_DIR, f"token_{user_id}.pickle")
    
    creds = None
    try:
        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                creds = pickle.load(token_file)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                 # This flow assumes frontend handles initial auth. Server validates/refreshes.
                 # For now, if token is invalid/expired and cannot be refreshed, raise an error.
                 # The frontend should handle the initial OAuth flow.
                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google auth required or token expired. Please re-authenticate via the frontend.")
            with open(token_path, "wb") as token_file:
                pickle.dump(creds, token_file)
        return JSONResponse(content={"success": True, "message": "Google auth successful."})
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[ERROR] Google auth for {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Google auth failed: {str(e)}")
