# src/server/main/utils.py
import os
import datetime
from datetime import timezone
import json
import traceback
from typing import Optional, Dict, Any, List, AsyncGenerator, Tuple
import uuid
import requests # Sync requests for JWKS

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

from jose import jwt, JWTError
from jose.exceptions import JOSEError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

# Import config from the current 'main' directory
from .config import (
    AES_SECRET_KEY, AES_IV,
    AUTH0_DOMAIN, AUTH0_AUDIENCE, ALGORITHMS,
    AUTH0_MANAGEMENT_CLIENT_ID, AUTH0_MANAGEMENT_CLIENT_SECRET,
    POLLING_INTERVALS, SUPPORTED_POLLING_SERVICES, DATA_SOURCES_CONFIG
)
from .db_utils import MongoManager # db_utils will contain MongoManager

# --- Authentication Utilities ---
jwks = None
if AUTH0_DOMAIN:
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        print(f"[{datetime.datetime.now()}] [MainServer_AuthUtils] Fetching JWKS from {jwks_url}...")
        jwks_response = requests.get(jwks_url, timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
        print(f"[{datetime.datetime.now()}] [MainServer_AuthUtils] JWKS fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.datetime.now()}] [MainServer_AuthUtils_FATAL_ERROR] Could not fetch JWKS: {e}")
        jwks = None
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [MainServer_AuthUtils_FATAL_ERROR] Error processing JWKS: {e}")
        jwks = None
else:
    print(f"[{datetime.datetime.now()}] [MainServer_AuthUtils_FATAL_ERROR] AUTH0_DOMAIN not set. Cannot fetch JWKS.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Placeholder, real tokenUrl depends on OAuth flow

class AuthHelper:
    async def _validate_token_and_get_payload(self, token: str) -> dict:
        if not jwks:
            print(f"[{datetime.datetime.now()}] [MainServer_AuthHelper_VALIDATION_ERROR] JWKS not available.")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth service config error (JWKS).")

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            token_kid = unverified_header.get("kid")
            if not token_kid:
                raise credentials_exception

            rsa_key_data = {}
            for key_entry in jwks.get("keys", []):
                if isinstance(key_entry, dict) and key_entry.get("kid") == token_kid:
                    rsa_key_data = {comp: key_entry[comp] for comp in ["kty", "kid", "use", "n", "e"] if comp in key_entry}
                    if all(k in rsa_key_data for k in ["kty", "n", "e"]): break
            
            if not rsa_key_data or not all(k in rsa_key_data for k in ["kty", "n", "e"]):
                raise credentials_exception

            payload = jwt.decode(
                token, rsa_key_data, algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE, issuer=f"https://{AUTH0_DOMAIN}/"
            )
            return payload
        except JWTError as e:
            print(f"[{datetime.datetime.now()}] [MainServer_AuthHelper_VALIDATION_ERROR] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e: # Catch specific JOSE errors
            print(f"[{datetime.datetime.now()}] [MainServer_AuthHelper_VALIDATION_ERROR] JOSE Error: {e}")
            raise credentials_exception
        except HTTPException: # Re-raise if it's already an HTTPException
            raise
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [MainServer_AuthHelper_VALIDATION_ERROR] Unexpected token validation error: {e}")
            traceback.print_exc()
            raise credentials_exception

    async def get_current_user_id_and_permissions(self, token: str = Depends(oauth2_scheme)) -> Tuple[str, List[str]]:
        payload = await self._validate_token_and_get_payload(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID (sub) not in token")
        permissions = payload.get("permissions", [])
        return user_id, permissions

    async def get_current_user_id(self, token: str = Depends(oauth2_scheme)) -> str:
        user_id, _ = await self.get_current_user_id_and_permissions(token=token)
        return user_id
    
    async def get_decoded_payload_with_claims(self, token: str = Depends(oauth2_scheme)) -> dict:
        payload = await self._validate_token_and_get_payload(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID (sub) not in token")
        payload["user_id"] = user_id 
        return payload

    async def ws_authenticate(self, websocket: Any) -> Optional[str]: # WebSocket type hint from FastAPI
        try:
            auth_message_str = await websocket.receive_text()
            auth_message = json.loads(auth_message_str)
            
            if auth_message.get("type") != "auth" or not auth_message.get("token"):
                await websocket.send_json({"type": "auth_failure", "message": "Invalid auth message format."})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None

            token = auth_message["token"]
            payload = await self._validate_token_and_get_payload(token)
            user_id = payload.get("sub")

            if not user_id:
                await websocket.send_json({"type": "auth_failure", "message": "User ID not found in token."})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None
            
            await websocket.send_json({"type": "auth_success", "user_id": user_id})
            return user_id
        except WebSocketDisconnect: # Import from FastAPI
            print(f"[{datetime.datetime.now()}] [WS_AUTH] WebSocket disconnected during auth.")
            return None
        except json.JSONDecodeError:
            await websocket.send_json({"type": "auth_failure", "message": "Auth message must be JSON."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        except HTTPException as e: # From _validate_token_and_get_payload
            await websocket.send_json({"type": "auth_failure", "message": f"Token validation failed: {e.detail}"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        except Exception as e:
            traceback.print_exc()
            try:
                await websocket.send_json({"type": "auth_failure", "message": "Internal server error during auth."})
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except: pass # Ignore errors if WS already closed
            return None


class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)
        self.auth_helper = AuthHelper() # Instantiate AuthHelper here

    async def __call__(self, token: str = Depends(oauth2_scheme)):
        user_id, token_permissions_list = await self.auth_helper.get_current_user_id_and_permissions(token=token)
        token_permissions_set = set(token_permissions_list)

        if not self.required_permissions.issubset(token_permissions_set):
            missing = self.required_permissions - token_permissions_set
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permissions: {', '.join(missing)}")
        return user_id

# --- AES Encryption/Decryption ---
def aes_encrypt(data: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        raise ValueError("AES encryption keys are not configured.")
    backend = default_backend()
    cipher = Cipher(algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=backend)
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted).decode()

def aes_decrypt(encrypted_data: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        raise ValueError("AES encryption keys are not configured.")
    backend = default_backend()
    cipher = Cipher(algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=backend)
    decryptor = cipher.decryptor()
    encrypted_bytes = base64.b64decode(encrypted_data)
    decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    unpadded_data = unpadder.update(decrypted) + unpadder.finalize()
    return unpadded_data.decode()

# --- Auth0 Management API Token ---
def get_management_token() -> str:
    # Ensure all required Auth0 management API config values are present
    if not all([AUTH0_DOMAIN, AUTH0_MANAGEMENT_CLIENT_ID, AUTH0_MANAGEMENT_CLIENT_SECRET]):
        print(f"[{datetime.datetime.now()}] [MainServer_MGMT_TOKEN_ERROR] Auth0 Management API credentials not fully configured.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth0 Management API config error.")
    
    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_MANAGEMENT_CLIENT_ID,
        "client_secret": AUTH0_MANAGEMENT_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid token response from Auth0 Mgmt API.")
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.datetime.now()}] [MainServer_MGMT_TOKEN_ERROR] Failed to get management token: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to get management token: {e}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [MainServer_MGMT_TOKEN_ERROR] Error processing management token response: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing management token response.")


# --- Data Source Utilities (Specific to Main Server's handling of settings) ---
async def get_data_sources_config_for_user(user_id: str, db_manager: MongoManager):
    user_sources_config = []
    for source_name in SUPPORTED_POLLING_SERVICES:
        if source_name in DATA_SOURCES_CONFIG:
            general_config = DATA_SOURCES_CONFIG[source_name]
            polling_state = await db_manager.get_polling_state(user_id, source_name)
            
            is_enabled = False
            if polling_state:
                is_enabled = polling_state.get("is_enabled", False)
            else: # If no specific state, check general default
                is_enabled = general_config.get("enabled_by_default", False)
            
            user_sources_config.append({
                "name": source_name,
                "display_name": general_config.get("display_name", source_name.capitalize()),
                "enabled": is_enabled,
                "configurable": general_config.get("configurable", True)
            })
    return user_sources_config

async def toggle_data_source_for_user(user_id: str, source_name: str, enable: bool, db_manager: MongoManager):
    if source_name not in SUPPORTED_POLLING_SERVICES or source_name not in DATA_SOURCES_CONFIG:
        raise ValueError(f"Data source '{source_name}' is not supported or configured.")

    update_payload = {"is_enabled": enable}
    now_utc = datetime.datetime.now(timezone.utc)

    if enable:
        # When enabling, schedule the next poll immediately and reset error/backoff states.
        update_payload["next_scheduled_poll_time"] = now_utc
        update_payload["is_currently_polling"] = False 
        update_payload["error_backoff_until_timestamp"] = None
        update_payload["consecutive_failure_count"] = 0
        update_payload["current_polling_tier"] = "user_enabled"
        update_payload["current_polling_interval_seconds"] = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
    
    # This will create the document if it doesn't exist, or update it.
    # The polling worker's engine `initialize_polling_state` also ensures creation.
    success = await db_manager.update_polling_state(user_id, source_name, update_payload)
    if not success:
        raise Exception(f"Failed to update data source '{source_name}' status in database.")
    
    print(f"[{datetime.datetime.now()}] [MainServer_Utils] Polling state for {user_id}/{source_name} set to enabled={enable}")
    return success

# --- Chat Utilities (Dummy for now) ---
async def generate_dummy_chat_stream_logic(user_input: str, username: str) -> AsyncGenerator[Dict[str, Any], None]:
    print(f"[{datetime.datetime.now()}] [MainServer_ChatUtils] Generating dummy stream for input: '{user_input[:30]}...' by {username}")
    
    assistant_message_id = str(uuid.uuid4())
    dummy_texts = [
        f"Hello {username}! ", "This ", "is ", "a ", "main server ", "dummy ", "chat ", 
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

# --- Voice Utilities (Dummy STT/TTS) ---
async def dummy_stt_logic(audio_chunk: bytes) -> str:
    # In a real scenario, this would process the audio_chunk
    # For dummy, just acknowledge receipt and maybe return a canned phrase
    await asyncio.sleep(0.1) # Simulate processing
    return "User audio received and acknowledged by dummy STT."

async def generate_dummy_voice_stream_logic(text_to_speak: str) -> AsyncGenerator[bytes, None]:
    print(f"[{datetime.datetime.now()}] [MainServer_VoiceUtils] Generating dummy voice stream for text: '{text_to_speak[:30]}...'")
    # Simulate sending audio chunks. In a real TTS, these would be actual audio data.
    # For dummy, we can send small pieces of silent or placeholder audio data, or just text markers.
    # For simplicity, let's send text markers indicating audio chunks.
    # Real PCM audio would be `bytes` objects.
    
    # Example: 16kHz, 16-bit mono, 100ms chunks = 16000 * 2 * 0.1 = 3200 bytes per chunk
    # Dummy silence chunk (3200 zero bytes for 16-bit PCM)
    dummy_audio_chunk = b'\x00' * 3200 

    response_words = text_to_speak.split()
    for i, word in enumerate(response_words):
        # In a real TTS, this would be actual audio for the word/phrase
        print(f"[{datetime.datetime.now()}] [MainServer_VoiceUtils] Dummy TTS yielding chunk for: '{word}'")
        yield dummy_audio_chunk # Send a silent chunk for demonstration
        if i < 5: # Limit dummy chunks to avoid flooding
            await asyncio.sleep(0.1) # Simulate time to generate/send chunk
        else:
            break
    print(f"[{datetime.datetime.now()}] [MainServer_VoiceUtils] Dummy voice stream finished.")