# src/server/main/main.py
import time
import datetime
from datetime import timezone, timedelta
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Main Server application script execution started.")

import os
import asyncio
from contextlib import asynccontextmanager
import traceback
import json
import uuid 
from typing import Optional, Dict, Any, List, AsyncGenerator, Tuple 

from fastapi import FastAPI, status, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx 

from server.main.utils import (
    AuthHelper, PermissionChecker, oauth2_scheme,
    aes_encrypt, aes_decrypt, get_management_token,
    # generate_dummy_chat_stream_logic, # Replaced by LLM logic
    # dummy_stt_logic, generate_dummy_voice_stream_logic, # Replaced by actual STT/TTS
    get_data_sources_config_for_user, toggle_data_source_for_user
)
from server.main.db_utils import MongoManager
from server.main.models import (
    OnboardingRequest, ChatMessageInput, DataSourceToggleRequest,
    EncryptionRequest, DecryptionRequest, AuthTokenStoreRequest,
    VoiceOfferRequest, VoiceAnswerResponse,
    GoogleTokenStoreRequest
)
from server.main.config import (
    AUTH0_DOMAIN, AUTH0_AUDIENCE, ALGORITHMS,
    GOOGLE_TOKEN_STORAGE_DIR, 
    DATA_SOURCES_CONFIG, POLLING_INTERVALS, SUPPORTED_POLLING_SERVICES,
    IS_DEV_ENVIRONMENT, TTS_PROVIDER, ELEVENLABS_API_KEY, ORPHEUS_MODEL_PATH # Added new configs
)
from server.main.ws_manager import MainWebSocketManager 
from server.main.runnables import OllamaRunnable # For dev LLM (simplified)

# --- STT/TTS Imports ---
from server.legacy.voice.stt import FasterWhisperSTT
from server.legacy.voice.orpheus_tts import OrpheusTTS, TTSOptions as OrpheusTTSOptions, VoiceId as OrpheusVoiceId, AVAILABLE_VOICES as ORPHEUS_VOICES
from server.legacy.voice.elevenlabs_tts import ElevenLabsTTS
from server.legacy.voice.gcp_tts import GCPTTS

print(f"[{datetime.datetime.now()}] [STARTUP] Main Server: Basic imports completed.")

# --- Global Instances ---
mongo_manager = MongoManager()
auth = AuthHelper()
main_websocket_manager = MainWebSocketManager()
http_client = httpx.AsyncClient() 

# --- STT/TTS Model Initialization ---
stt_model_instance = None
tts_model_instance = None

def initialize_stt_tts():
    global stt_model_instance, tts_model_instance
    print(f"[{datetime.datetime.now()}] [STARTUP] Initializing STT/TTS models...")
    
    # Initialize STT (Always FasterWhisper)
    try:
        stt_model_instance = FasterWhisperSTT(model_size="base", device="cpu", compute_type="int8")
        print(f"[{datetime.datetime.now()}] [STARTUP] FasterWhisper STT initialized.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [STARTUP_ERROR] Failed to initialize FasterWhisper STT: {e}")
        stt_model_instance = None # Ensure it's None on failure

    # Initialize TTS based on environment
    if IS_DEV_ENVIRONMENT:
        try:
            if not ORPHEUS_MODEL_PATH or not os.path.exists(ORPHEUS_MODEL_PATH):
                 print(f"[{datetime.datetime.now()}] [STARTUP_WARNING] Orpheus model path not found or not set. TTS might not work. Path: {ORPHEUS_MODEL_PATH}")
                 tts_model_instance = None
            else:
                tts_model_instance = OrpheusTTS(model_path=ORPHEUS_MODEL_PATH, verbose=False, default_voice_id="tara")
                print(f"[{datetime.datetime.now()}] [STARTUP] OrpheusTTS initialized for Development.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [STARTUP_ERROR] Failed to initialize OrpheusTTS for Development: {e}")
            tts_model_instance = None
    else: # Production
        if TTS_PROVIDER == "ELEVENLABS":
            try:
                if not ELEVENLABS_API_KEY:
                    print(f"[{datetime.datetime.now()}] [STARTUP_ERROR] ELEVENLABS_API_KEY not set for Production TTS.")
                    tts_model_instance = None
                else:
                    tts_model_instance = ElevenLabsTTS()
                    print(f"[{datetime.datetime.now()}] [STARTUP] ElevenLabsTTS initialized for Production.")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [STARTUP_ERROR] Failed to initialize ElevenLabsTTS for Production: {e}")
                tts_model_instance = None
        elif TTS_PROVIDER == "GCP":
            try:
                tts_model_instance = GCPTTS()
                print(f"[{datetime.datetime.now()}] [STARTUP] GCPTTS initialized for Production.")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [STARTUP_ERROR] Failed to initialize GCPTTS for Production: {e}")
                tts_model_instance = None
        else: # Fallback or DUMMY if TTS_PROVIDER is not set or invalid
            print(f"[{datetime.datetime.now()}] [STARTUP_WARNING] TTS_PROVIDER is '{TTS_PROVIDER}'. No specific production TTS loaded. Voice will be dummy.")
            tts_model_instance = None # Explicitly none, dummy logic will be used in endpoint

    print(f"[{datetime.datetime.now()}] [STARTUP] STT/TTS model initialization complete.")


nest_asyncio_applied = False
if not asyncio.get_event_loop().is_running(): 
    try:
        import nest_asyncio
        nest_asyncio.apply()
        nest_asyncio_applied = True
        print(f"[{datetime.datetime.now()}] [STARTUP] Main Server: nest_asyncio applied.")
    except ImportError:
        print(f"[{datetime.datetime.now()}] [STARTUP_WARNING] Main Server: nest_asyncio not found, not applying.")
else:
    print(f"[{datetime.datetime.now()}] [STARTUP] Main Server: asyncio loop already running, nest_asyncio not applied directly here.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App startup...")
    await mongo_manager.initialize_db()
    initialize_stt_tts() # Initialize models on startup
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App startup complete.")
    yield 
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App shutdown sequence initiated...")
    await http_client.aclose()
    if mongo_manager and mongo_manager.client:
        mongo_manager.client.close() 
        print(f"[{datetime.datetime.now()}] [MAIN_SERVER_LIFECYCLE] MongoManager client closed.")
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [MAIN_SERVER_LIFECYCLE] App shutdown complete.")

app = FastAPI(
    title="Sentient Main Server", 
    description="Core API: Auth, Onboarding, Profile, Chat, Voice, Settings.", 
    version="2.0.0", 
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

# === Token Management (Auth0 & Google) ===
@app.post("/auth/store_session", tags=["Authentication"])
async def store_session_tokens(
    request: AuthTokenStoreRequest, 
    user_id: str = Depends(auth.get_current_user_id) 
):
    print(f"[{datetime.datetime.now()}] [AUTH_STORE_SESSION] Storing Auth0 refresh token for user {user_id}")
    try:
        encrypted_refresh_token = aes_encrypt(request.refresh_token)
        update_payload = {"userData.encrypted_refresh_token": encrypted_refresh_token}
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store Auth0 refresh token.")
        return JSONResponse(content={"message": "Auth0 session tokens stored securely."})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AUTH_STORE_SESSION_ERROR] User {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing Auth0 session: {str(e)}")

@app.post("/auth/google/store_token", summary="Store Google OAuth Refresh Token", tags=["Authentication"])
async def store_google_token_endpoint(
    request_body: GoogleTokenStoreRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"])) 
):
    print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE] Storing Google refresh token for user {user_id}, service: {request_body.service_name}")
    if not request_body.service_name or request_body.service_name not in DATA_SOURCES_CONFIG: 
        raise HTTPException(status_code=400, detail=f"Invalid service name: {request_body.service_name}")
    try:
        encrypted_google_refresh_token = aes_encrypt(request_body.google_refresh_token)
        field_path = f"userData.google_services.{request_body.service_name}.encrypted_refresh_token"
        update_payload = {field_path: encrypted_google_refresh_token}
        
        success = await mongo_manager.update_user_profile(user_id, update_payload)

        if not success:
            print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] Failed to store token for user {user_id}, service {request_body.service_name}.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store Google refresh token.")
        
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE] Successfully stored Google refresh token for user {user_id}, service {request_body.service_name}.")
        return JSONResponse(content={"message": f"Google refresh token for {request_body.service_name} stored successfully."})
    except ValueError as ve: 
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] User {user_id}: Encryption error - {ve}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server configuration error: {str(ve)}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error storing Google refresh token: {str(e)}")


# === Onboarding Routes ===
@app.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data", tags=["Onboarding"])
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

@app.post("/check-user-profile", status_code=status.HTTP_200_OK, summary="Check User Profile and Onboarding Status", tags=["Onboarding"])
async def check_user_profile_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    profile_doc = await mongo_manager.get_user_profile(user_id)
    onboarding_complete = False
    if profile_doc and profile_doc.get("userData"):
        onboarding_complete = profile_doc["userData"].get("onboardingComplete", False)
    
    return JSONResponse(content={"profile_exists": bool(profile_doc), "onboarding_complete": onboarding_complete, "status": 200})

# === User Profile Routes ===
@app.post("/get-user-data", summary="Get User Profile's userData field", tags=["User Profile"])
async def get_user_data_endpoint_main(user_id: str = Depends(auth.get_current_user_id)):
    profile_doc = await mongo_manager.get_user_profile(user_id)
    if profile_doc and "userData" in profile_doc:
        return JSONResponse(content={"data": profile_doc["userData"], "status": 200})
    print(f"[{datetime.datetime.now()}] [GET_USER_DATA] No profile/userData for {user_id}. Creating basic entry.")
    await mongo_manager.update_user_profile(user_id, {"userData": {}}) 
    return JSONResponse(content={"data": {}, "status": 200}) 

# === Settings Routes (Data Sources) ===
@app.post("/get_data_sources", summary="Get Data Sources Configuration", tags=["Settings"])
async def get_data_sources_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))):
    sources = await get_data_sources_config_for_user(user_id, mongo_manager)
    return JSONResponse(content={"data_sources": sources})

@app.post("/set_data_source_enabled", summary="Enable/Disable Data Source Polling", tags=["Settings"])
async def set_data_source_enabled_endpoint(
    request: DataSourceToggleRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))
):
    try:
        await toggle_data_source_for_user(user_id, request.source, request.enabled, mongo_manager)
        return JSONResponse(content={"status": "success", "message": f"Data source '{request.source}' status set to {request.enabled}."})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [SETTINGS_TOGGLE_ERROR] User {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set data source status.")

# === Chat Routes ===
async def get_chat_history_util(user_id: str, chat_id_param: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    effective_chat_id = chat_id_param
    if not effective_chat_id:
        user_profile = await mongo_manager.get_user_profile(user_id)
        active_chat_id_from_profile = user_profile.get("userData", {}).get("active_chat_id") if user_profile else None
        
        if active_chat_id_from_profile:
            effective_chat_id = active_chat_id_from_profile
        else:
            all_chat_ids = await mongo_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids:
                effective_chat_id = all_chat_ids[0]
                if user_profile: 
                    await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else:
                new_chat_id = str(uuid.uuid4())
                update_payload = {"userData.active_chat_id": new_chat_id}
                await mongo_manager.update_user_profile(user_id, update_payload)
                effective_chat_id = new_chat_id
    
    messages_from_db = await mongo_manager.get_chat_history(user_id, effective_chat_id)
    serialized_messages = []
    for m in messages_from_db:
        if isinstance(m, dict) and 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
    return [m for m in serialized_messages if m.get("isVisible", True)], effective_chat_id

@app.post("/get-history", summary="Get Chat History", tags=["Chat"])
async def get_chat_history_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    messages, active_chat_id = await get_chat_history_util(user_id)
    return JSONResponse(content={"messages": messages, "activeChatId": active_chat_id})

@app.post("/clear-chat-history", summary="Clear Active Chat History", tags=["Chat"])
async def clear_chat_history_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    user_profile = await mongo_manager.get_user_profile(user_id)
    active_chat_id = user_profile.get("userData", {}).get("active_chat_id") if user_profile else None
    if active_chat_id:
        await mongo_manager.delete_chat_history(user_id, active_chat_id)
    
    new_active_chat_id = str(uuid.uuid4())
    await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_active_chat_id})
    return JSONResponse(content={"message": "Chat history cleared.", "activeChatId": new_active_chat_id})

# Simplified OllamaRunnable logic for dummy response
async def generate_ollama_dummy_stream(user_input: str, username: str) -> AsyncGenerator[Dict[str, Any], None]:
    assistant_message_id = str(uuid.uuid4())
    dummy_texts = [
        f"Hello {username}! ", "This ", "is ", "a ", "dummy ", "Ollama ", 
        "response. ", f"You said: '{user_input[:20]}...'. "
    ]
    full_response_text = "".join(dummy_texts)
    for text_part in dummy_texts:
        yield {
            "type": "assistantStream", "token": text_part, "done": False, "messageId": assistant_message_id
        }
        await asyncio.sleep(0.05)
    yield {
        "type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id,
        "full_message": full_response_text,
        "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "proUsed": False
    }


@app.post("/chat", summary="Process Chat Message (Text)", tags=["Chat"])
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
    _, active_chat_id = await get_chat_history_util(user_id)

    user_msg_id = await mongo_manager.add_chat_message(user_id, active_chat_id, {
        "message": request_body.input, "isUser": True, "isVisible": True
    })

    async def response_generator():
        yield json.dumps({
            "type": "userMessage", "id": user_msg_id, "message": request_body.input, 
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }) + "\n"
        
        assistant_temp_id = str(uuid.uuid4())
        yield json.dumps({"type": "intermediary", "message": "Thinking...", "id": assistant_temp_id}) + "\n"
        await asyncio.sleep(0.1)

        full_llm_response_text = ""
        
        if IS_DEV_ENVIRONMENT:
            print(f"[{datetime.datetime.now()}] [CHAT_LLM_DEV] Using Ollama (dummy) for chat response.")
            async for item in generate_ollama_dummy_stream(request_body.input, username):
                full_llm_response_text += item.get("token", "")
                yield json.dumps(item) + "\n"
        else: # Production
            print(f"[{datetime.datetime.now()}] [CHAT_LLM_PROD] Placeholder for OpenRouter Llama3.2b. Using dummy stream.")
            # TODO: Implement OpenRouter API call here
            # For now, using the same dummy stream as dev
            async for item in generate_ollama_dummy_stream(request_body.input, username): # Placeholder
                full_llm_response_text += item.get("token", "")
                yield json.dumps(item) + "\n"
        
        await mongo_manager.add_chat_message(user_id, active_chat_id, {
            "id": assistant_temp_id, "message": full_llm_response_text, "isUser": False, "isVisible": True,
            "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "proUsed": False
        })
            
    return StreamingResponse(response_generator(), media_type="application/x-ndjson")


# === Voice Routes ===
@app.post("/voice/webrtc/offer", summary="Handle WebRTC Offer (Dummy/Simplified)", tags=["Voice"])
async def handle_webrtc_offer(
    offer_request: VoiceOfferRequest, 
    user_id: str = Depends(auth.get_current_user_id) 
):
    print(f"[{datetime.datetime.now()}] [VOICE_OFFER] Received WebRTC offer from {user_id}, type: {offer_request.type}")
    return VoiceAnswerResponse(sdp="dummy-answer-sdp", type="answer")

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: Optional[str] = None
    try:
        authenticated_user_id = await auth.ws_authenticate(websocket)
        if not authenticated_user_id: return

        await main_websocket_manager.connect_voice(websocket, authenticated_user_id)

        while True:
            audio_bytes = await websocket.receive_bytes()
            
            if not stt_model_instance:
                await websocket.send_json({"type": "error", "message": "STT service not available."})
                continue
            
            # STT
            # Assuming audio_bytes is raw PCM data compatible with FasterWhisperSTT
            # Convert bytes to numpy array (example for int16 PCM)
            # This might need adjustment based on how client sends audio
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            # The STT model expects (sample_rate, audio_array)
            # Assuming client sends 16kHz audio as configured in webSocketAudioClient.js
            transcribed_text = stt_model_instance.stt((16000, audio_np))
            await websocket.send_json({"type": "stt_result", "text": transcribed_text})

            # Dummy LLM response (could be replaced by a call to /chat logic or similar)
            llm_response_text = f"Voice agent acknowledges: '{transcribed_text}'"
            await websocket.send_json({"type": "llm_response", "text": llm_response_text})
            
            # TTS
            if not tts_model_instance:
                await websocket.send_json({"type": "error", "message": "TTS service not available."})
                await websocket.send_json({"type": "tts_stream_end"}) # Signal end anyway
                continue

            tts_options: OrpheusTTSOptions = {} # Use default voice configured in TTS instance
            async for audio_chunk_bytes in tts_model_instance.stream_tts(llm_response_text, options=tts_options):
                # Ensure audio_chunk_bytes is actual bytes. OrpheusTTS yields (sr, np.ndarray).
                # ElevenLabs/GCP yield bytes directly.
                if isinstance(audio_chunk_bytes, tuple): # OrpheusTTS output
                    _sr, chunk_np_array = audio_chunk_bytes
                    if isinstance(chunk_np_array, np.ndarray):
                        # Convert float32 numpy array to bytes (e.g., 16-bit PCM)
                        # This matches common WebRTC expectations.
                        # Multiply by 32767 and convert to int16
                        audio_int16 = (chunk_np_array * 32767).astype(np.int16)
                        await websocket.send_bytes(audio_int16.tobytes())
                    else: # Should not happen with OrpheusTTS
                        print(f"[{datetime.datetime.now()}] [VOICE_WS_TTS_ERROR] OrpheusTTS yielded non-numpy array: {type(chunk_np_array)}")
                elif isinstance(audio_chunk_bytes, bytes): # ElevenLabs/GCP output
                     await websocket.send_bytes(audio_chunk_bytes)
                else:
                    print(f"[{datetime.datetime.now()}] [VOICE_WS_TTS_ERROR] TTS yielded unexpected type: {type(audio_chunk_bytes)}")


            await websocket.send_json({"type": "tts_stream_end"})

    except WebSocketDisconnect:
        print(f"[{datetime.datetime.now()}] [VOICE_WS] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [VOICE_WS_ERROR] Error (User: {authenticated_user_id or 'unknown'}): {e}")
        traceback.print_exc()
        try: # Attempt to inform client about the error
            await websocket.send_json({"type": "error", "message": "An internal server error occurred during voice processing."})
        except: pass
    finally:
        if authenticated_user_id: main_websocket_manager.disconnect_voice(websocket)


# === Notifications WebSocket (General Purpose) ===
@app.websocket("/ws/notifications")
async def notifications_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: Optional[str] = None
    try:
        authenticated_user_id = await auth.ws_authenticate(websocket)
        if not authenticated_user_id: return

        await main_websocket_manager.connect_notifications(websocket, authenticated_user_id)
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
        if authenticated_user_id: main_websocket_manager.disconnect_notifications(websocket)

# === Utility Endpoints ===
@app.post("/utils/encrypt", summary="Encrypt Data (AES)", tags=["Utilities"])
async def encrypt_data_endpoint_main(request: EncryptionRequest):
    return JSONResponse(content={"encrypted_data": aes_encrypt(request.data)})

@app.post("/utils/decrypt", summary="Decrypt Data (AES)", tags=["Utilities"])
async def decrypt_data_endpoint_main(request: DecryptionRequest):
    try:
        return JSONResponse(content={"decrypted_data": aes_decrypt(request.encrypted_data)})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@app.post("/utils/get-role", summary="Get User Role from Token Claims", tags=["Utilities"])
async def get_role_from_claims_endpoint_main(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@app.post("/utils/get-referral-code", summary="Get Referral Code from Token", tags=["Utilities"])
async def get_referral_code_endpoint_main(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    referral_code = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referralCode")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": referral_code})

@app.post("/utils/get-referrer-status", summary="Get Referrer Status from Token", tags=["Utilities"])
async def get_referrer_status_endpoint_main(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    if not AUTH0_AUDIENCE: raise HTTPException(status_code=500, detail="Server config error: AUTH0_AUDIENCE missing.")
    CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if not AUTH0_AUDIENCE.endswith('/') else AUTH0_AUDIENCE
    referrer_status = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referrerStatus", False)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referrerStatus": referrer_status})

@app.post("/utils/authenticate-google", summary="Validate or Refresh Stored Google Token", tags=["Utilities"])
async def authenticate_google_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"]))):
    user_profile = await mongo_manager.get_user_profile(user_id)
    
    encrypted_google_refresh_token_gmail = user_profile.get("userData", {}).get("google_services", {}).get("gmail", {}).get("encrypted_refresh_token")

    if not encrypted_google_refresh_token_gmail:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google Gmail credentials not found for user. Please authenticate via client.")

    print(f"[{datetime.datetime.now()}] [GOOGLE_AUTH_DUMMY_VALIDATION] Found stored Google Gmail token for user {user_id}. Assuming valid for dummy purposes.")
    return JSONResponse(content={"success": True, "message": "Google Gmail token present and assumed valid (dummy check)."})

@app.post("/notifications/get", summary="Get User Notifications", tags=["Notifications"])
async def get_notifications_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["read:notifications"]))):
    notifications = await mongo_manager.get_notifications(user_id)
    return JSONResponse(content={"notifications": notifications, "status": 200})

@app.post("/activity/heartbeat", summary="User Activity Heartbeat", tags=["Activity"])
async def user_activity_heartbeat_endpoint_main(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    success = await mongo_manager.update_user_last_active(user_id)
    if success:
        return JSONResponse(content={"message": "User activity timestamp updated."})
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user activity.")


# --- General App Information ---
@app.get("/", tags=["General"], summary="Root endpoint for the Main Server")
async def root():
    return {"message": "Sentient Main Server Operational."}

@app.get("/health", tags=["General"], summary="Health check for the Main Server")
async def health():
    return {"status": "healthy", "timestamp": datetime.datetime.now(timezone.utc).isoformat()}

END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [MAIN_SERVER_APP_PY_LOADED] Main Server app.py loaded in {END_TIME - START_TIME:.2f} seconds.")