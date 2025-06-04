# src/server/main_server/app.py
import time
import datetime
from datetime import timezone
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Main Server application script execution started.")

import os
import asyncio
from contextlib import asynccontextmanager
import traceback
import json
from typing import Optional, Dict, Any, List, AsyncGenerator

from fastapi import FastAPI, status, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx # For making requests to other services

from dotenv import load_dotenv
import nest_asyncio

# --- Dependencies for this server ---
from server.main_server.dependencies import mongo_manager, auth, http_client
from server.main_server.ws_manager import main_websocket_manager
from server.main_server.utils import get_data_sources_config_for_user, toggle_data_source_for_user

from server.common_lib.utils.auth import PermissionChecker
from server.common_lib.utils.helpers import aes_encrypt, aes_decrypt, get_management_token
from server.common_lib.models import (
    OnboardingRequest, ChatMessageInput, DataSourceToggleRequest,
    EncryptionRequest, DecryptionRequest
)
from server.common_lib.utils.config import (
    GOOGLE_TOKEN_STORAGE_DIR # For /authenticate-google
)
import pickle # For /authenticate-google

print(f"[{datetime.datetime.now()}] [STARTUP] Main Server: Basic imports completed.")

# --- Environment Loading (Handled by common_lib.utils.config) ---
IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")
CHAT_SERVER_URL = os.getenv("CHAT_SERVER_URL", "http://localhost:5003") # Example
VOICE_SERVER_URL = os.getenv("VOICE_SERVER_URL", "http://localhost:5004") # Example

nest_asyncio.apply()
print(f"[{datetime.datetime.now()}] [STARTUP] Main Server: nest_asyncio applied.")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App startup...")
    await mongo_manager.initialize_db()
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App startup complete.")
    yield 
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App shutdown sequence initiated...")
    await http_client.aclose() # Close the httpx client
    if mongo_manager and mongo_manager.client:
        mongo_manager.client.close()
        print(f"[{datetime.datetime.now()}] [MAIN_SERVER_LIFECYCLE] MongoManager client closed.")
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App shutdown complete.")

app = FastAPI(
    title="Sentient Main Server", 
    description="Core API: Auth Callbacks, Onboarding, Profile, Settings, Proxy to other services.", 
    version="1.0.0_microservice_proxy",
    docs_url="/docs", 
    redoc_url="/redoc", 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["app://.", "http://localhost:3000", "http://localhost"],
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# === General Routes ===
@app.get("/", status_code=status.HTTP_200_OK, summary="Main Server Root", tags=["General"])
async def main_server_root():
    return {"message": "Sentient Main Server is running."}

@app.get("/health", status_code=status.HTTP_200_OK, summary="Main Server Health Check", tags=["General"])
async def health_check():
    return {"message": "Sentient Main Server is healthy."}

# === Onboarding Routes ===
@app.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data", tags=["Onboarding"])
async def save_onboarding_data_endpoint(
    request_body: OnboardingRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))
):
    print(f"[{datetime.datetime.now()}] [MAIN_ONBOARDING /] User {user_id}, Data keys: {list(request_body.data.keys())}")
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
        print(f"[{datetime.datetime.now()}] [MAIN_ONBOARDING_ERROR /] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save onboarding data: {str(e)}")

@app.post("/onboarding/check-profile", status_code=status.HTTP_200_OK, summary="Check Profile and Onboarding Status", tags=["Onboarding"])
async def check_user_profile_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    profile = await mongo_manager.get_user_profile(user_id)
    if profile:
        onboarding_complete = profile.get("userData", {}).get("onboardingComplete", False)
        return JSONResponse(content={"profile_exists": True, "onboarding_complete": onboarding_complete, "status": 200})
    return JSONResponse(content={"profile_exists": False, "onboarding_complete": False, "status": 200})

# === Profile Routes ===
@app.post("/profile/get-user-data", summary="Get User Profile's userData", tags=["User Profile"])
async def get_user_data_endpoint(user_id: str = Depends(auth.get_current_user_id)): # Assuming default permission from router
    profile_doc = await mongo_manager.get_user_profile(user_id)
    if profile_doc and "userData" in profile_doc:
        return JSONResponse(content={"data": profile_doc["userData"], "status": 200})
    return JSONResponse(content={"data": {}, "status": 200}) # Return empty if no userData

# === Settings Routes ===
@app.post("/settings/data-sources", summary="Get Data Sources Configuration", tags=["Settings"])
async def get_data_sources_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))):
    sources = await get_data_sources_config_for_user(user_id)
    return JSONResponse(content={"data_sources": sources})

@router.post("/settings/data-sources/toggle", summary="Enable/Disable Data Source Polling", tags=["Settings"])
async def toggle_data_source_endpoint_main(
    request: DataSourceToggleRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    try:
        await toggle_data_source_for_user(user_id, request.source, request.enabled)
        return JSONResponse(content={"status": "success", "message": f"Data source '{request.source}' status set to {request.enabled}."})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [MAIN_SETTINGS_TOGGLE_ERROR] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set data source status.")


# === Chat Proxy Routes ===
@app.post("/chat/history", summary="Proxy to Get Chat History", tags=["Chat Proxy"])
async def proxy_get_chat_history(token: str = Depends(oauth2_scheme)):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = await http_client.post(f"{CHAT_SERVER_URL}/chat/history", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", e.response.text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxying to chat server: {str(e)}")

@app.post("/chat/clear-history", summary="Proxy to Clear Chat History", tags=["Chat Proxy"])
async def proxy_clear_chat_history(token: str = Depends(oauth2_scheme)):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = await http_client.post(f"{CHAT_SERVER_URL}/chat/clear-history", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", e.response.text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxying to chat server: {str(e)}")

@app.post("/chat", summary="Proxy Chat Message (Streaming)", tags=["Chat Proxy"])
async def proxy_chat_message(request_body: ChatMessageInput, token: str = Depends(oauth2_scheme)):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/x-ndjson"}
    content = request_body.model_dump_json()

    async def stream_generator():
        try:
            async with http_client.stream("POST", f"{CHAT_SERVER_URL}/chat", content=content, headers=headers) as response:
                response.raise_for_status() # Check for HTTP errors before streaming
                async for chunk in response.aiter_bytes():
                    yield chunk
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get("detail", e.response.text) if e.response.content else str(e)
            print(f"[{datetime.datetime.now()}] [CHAT_PROXY_STREAM_ERROR] HTTP Error from chat server: {e.response.status_code} - {error_detail}")
            yield json.dumps({"type":"error", "message": f"Chat service error: {error_detail}"}) + "\n"
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [CHAT_PROXY_STREAM_ERROR] General error proxying chat stream: {str(e)}")
            yield json.dumps({"type":"error", "message": f"Proxy error: {str(e)}"}) + "\n"
            
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


# === Voice Proxy Routes (Signaling Only) ===
@app.post("/voice/offer", summary="Proxy Voice Offer/Answer to Voice Server", tags=["Voice Proxy"])
async def proxy_voice_offer(fastapi_request: Request, token: str = Depends(oauth2_scheme)):
    # This proxies the HTTP POST request used by FastRTC for signaling (offer/answer)
    # The actual WebRTC media connection will be direct client-to-voice-server
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        client_offer_data = await fastapi_request.json() # Get client's SDP offer
        # The voice server's /voice/webrtc/offer is the one that processes this
        response = await http_client.post(f"{VOICE_SERVER_URL}/voice/webrtc/offer", json=client_offer_data, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json()) # Return voice server's SDP answer
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail", e.response.text))
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [VOICE_PROXY_ERROR] /voice/offer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying voice offer to voice server: {str(e)}")


# === General Utility Routes ===
@app.post("/utils/encrypt", status_code=status.HTTP_200_OK, summary="Encrypt Data (AES)", tags=["Utilities"])
async def encrypt_data_endpoint(request: EncryptionRequest):
    return JSONResponse(content={"encrypted_data": aes_encrypt(request.data)})

@app.post("/utils/decrypt", status_code=status.HTTP_200_OK, summary="Decrypt Data (AES)", tags=["Utilities"])
async def decrypt_data_endpoint(request: DecryptionRequest):
    try:
        return JSONResponse(content={"decrypted_data": aes_decrypt(request.encrypted_data)})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@app.post("/utils/get-role", summary="Get User Role from Token Claims", tags=["Utilities"])
async def get_role_from_claims_endpoint(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    user_id = payload["user_id"]
    AUTH0_AUDIENCE_LOCAL = os.getenv("AUTH0_AUDIENCE")
    if not AUTH0_AUDIENCE_LOCAL:
        raise HTTPException(status_code=500, detail="Server configuration error: AUTH0_AUDIENCE not set.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE_LOCAL}/" if not AUTH0_AUDIENCE_LOCAL.endswith('/') else AUTH0_AUDIENCE_LOCAL
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@app.post("/utils/authenticate-google", summary="Validate or Refresh Google Token", tags=["Utilities"])
async def authenticate_google_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"]))):
    token_path = os.path.join(GOOGLE_TOKEN_STORAGE_DIR, f"token_gmail_{user_id}.pickle") #Gmail specific for now
    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as token_file:
            creds = pickle.load(token_file)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            try:
                creds.refresh(GoogleAuthRequest())
                with open(token_path, "wb") as token_file: pickle.dump(creds, token_file)
                return JSONResponse(content={"success": True, "message": "Google token refreshed."})
            except Exception as refresh_error:
                print(f"[{datetime.datetime.now()}] [MAIN_GOOGLE_AUTH_ERROR] Failed to refresh for {user_id}: {refresh_error}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google authentication required or token expired.")
    return JSONResponse(content={"success": True, "message": "Google token is valid."})


@app.post("/notifications/get", summary="Get User Notifications", tags=["Notifications"])
async def get_notifications_main_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:notifications"]))):
    notifications = await mongo_manager.get_notifications(user_id)
    return JSONResponse(content={"notifications": notifications, "status": 200})

@app.post("/activity/heartbeat", summary="User Activity Heartbeat", tags=["Activity"])
async def user_activity_heartbeat_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    success = await mongo_manager.update_user_last_active(user_id)
    if success:
        return JSONResponse(content={"message": "User activity timestamp updated."})
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user activity.")

# === WebSocket for Main Server (General Notifications) ===
@app.websocket("/ws")
async def main_server_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: Optional[str] = None
    try:
        authenticated_user_id = await auth.ws_authenticate(websocket) # Use AuthHelper instance
        if not authenticated_user_id: return
        
        await main_websocket_manager.connect(websocket, authenticated_user_id)
        while True:
            data = await websocket.receive_text()
            message_payload = json.loads(data)
            if message_payload.get("type") == "ping": # Simple keep-alive
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        print(f"[{datetime.datetime.now()}] [MAIN_WS] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [MAIN_WS_ERROR] Unexpected (User: {authenticated_user_id or 'unknown'}): {e}")
    finally:
        if authenticated_user_id: main_websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    
    log_config_main = uvicorn.config.LOGGING_CONFIG.copy() # Make a copy
    log_config_main["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER] %(request_line)s" %(status_code)s'
    log_config_main["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER] %(message)s'
    
    main_server_port = int(os.getenv("APP_SERVER_PORT", 5000))
    print(f"[{datetime.datetime.now()}] [UVICORN] Starting Main Server on host 0.0.0.0, port {main_server_port}...")
    
    uvicorn.run(
        "server.main_server.app:app",
        host="0.0.0.0",
        port=main_server_port,
        lifespan="on",
        reload=IS_DEV_ENVIRONMENT,
        workers=1,
        log_config=log_config_main
    )

END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP_COMPLETE] Main Server script execution and Uvicorn setup took {END_TIME - START_TIME:.2f} seconds.")