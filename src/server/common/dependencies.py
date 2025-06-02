import os
import asyncio
import json
import traceback
import datetime
from datetime import timezone, timedelta
from typing import Optional, Any, Dict, List, Tuple, Union
import requests
from jose import jwt, JWTError
from jose.exceptions import JOSEError
from fastapi import HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer

from server.db import MongoManager
from server.agents.base import TaskQueue
from server.memory.backend import MemoryBackend
from server.context.base import BaseContextEngine
from server.context.gmail import GmailContextEngine
from server.context.gcalendar import GCalendarContextEngine
from server.context.internet import InternetSearchContextEngine
import uuid

from neo4j import GraphDatabase # For graph_driver
from llama_index.embeddings.huggingface import HuggingFaceEmbedding # For embed_model

# Global variables from app.py that are dependencies
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    print("[ERROR] FATAL: AUTH0_DOMAIN or AUTH0_AUDIENCE not set!")
    exit(1)

jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
try:
    print(f"[INIT] {datetime.datetime.now()}: Fetching JWKS from {jwks_url}...")
    jwks_response = requests.get(jwks_url)
    jwks_response.raise_for_status()
    jwks = jwks_response.json()
    print(f"[INIT] {datetime.datetime.now()}: JWKS fetched successfully.")
except requests.exceptions.RequestException as e:
    print(f"[ERROR] FATAL: Could not fetch JWKS from Auth0: {e}")
    exit(1)
except Exception as e:
    print(f"[ERROR] FATAL: Error processing JWKS: {e}")
    exit(1)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Auth:
    async def _validate_token_and_get_payload(self, token: str) -> dict:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            if "kid" not in unverified_header:
                print("[AUTH_VALIDATION_ERROR] 'kid' not found in token header.")
                raise credentials_exception

            token_kid = unverified_header["kid"]
            if not isinstance(jwks, dict) or "keys" not in jwks or not isinstance(jwks["keys"], list):
                print(f"[AUTH_VALIDATION_ERROR] JWKS structure is invalid.")
                raise credentials_exception

            rsa_key_data = {}
            found_matching_key = False
            for key_entry in jwks["keys"]:
                if isinstance(key_entry, dict) and key_entry.get("kid") == token_kid:
                    required_rsa_components = ["kty", "kid", "use", "n", "e"]
                    if all(comp in key_entry for comp in required_rsa_components):
                        rsa_key_data = {comp: key_entry[comp] for comp in required_rsa_components}
                        found_matching_key = True
                        break

            if not found_matching_key or not rsa_key_data:
                print(f"[AUTH_VALIDATION_ERROR] RSA key not found in JWKS for kid: {token_kid}")
                raise credentials_exception

            payload = jwt.decode(
                token, rsa_key_data, algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE, 
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
            return payload
        except JWTError as e:
            print(f"[AUTH_VALIDATION_ERROR] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e:
            print(f"[AUTH_VALIDATION_ERROR] JOSE Error: {e}")
            raise credentials_exception
        except HTTPException: 
            raise
        except Exception as e:
            print(f"[AUTH_VALIDATION_ERROR] Unexpected error: {e}")
            traceback.print_exc()
            raise credentials_exception

    async def get_current_user_with_permissions(self, token: str = Depends(oauth2_scheme)) -> Tuple[str, List[str]]:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            print("[AUTH_VALIDATION_ERROR] Token payload missing 'sub' (user_id).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")

        permissions: List[str] = payload.get("permissions", [])
        return user_id, permissions

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> str:
        user_id, _ = await self.get_current_user_with_permissions(token=token)
        return user_id

    async def get_decoded_payload_with_claims(self, token: str = Depends(oauth2_scheme)) -> dict:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        payload["user_id"] = user_id 
        return payload

    async def ws_authenticate(self, websocket: WebSocket) -> Optional[str]:
        try:
            auth_data = await websocket.receive_text()
            message = json.loads(auth_data)
            if message.get("type") != "auth":
                await websocket.send_text(json.dumps({"type": "auth_failure", "message": "Auth message expected"}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None
            token = message.get("token")
            if not token:
                await websocket.send_text(json.dumps({"type": "auth_failure", "message": "Token missing"}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None

            payload = await self._validate_token_and_get_payload(token) 
            user_id: Optional[str] = payload.get("sub")
            if user_id:
                await websocket.send_text(json.dumps({"type": "auth_success", "user_id": user_id}))
                print(f"[WS_AUTH] WebSocket authenticated for user: {user_id}")
                return user_id
            else: 
                print(f"[WS_AUTH] Auth failed: Invalid token (user_id missing post-validation).")
                await websocket.send_text(json.dumps({"type": "auth_failure", "message": "Invalid token"}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None
        except WebSocketDisconnect:
            print("[WS_AUTH] Client disconnected during auth.")
            return None
        except json.JSONDecodeError:
            print("[WS_AUTH_ERROR] Non-JSON auth message.")
            return None
        except HTTPException as e: 
            print(f"[WS_AUTH_ERROR] Auth failed: {e.detail}")
            try:
                await websocket.send_text(json.dumps({"type": "auth_failure", "message": e.detail}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail[:123])
            except Exception: pass
            return None
        except Exception as e:
            print(f"[WS_AUTH_ERROR] Unexpected error: {e}")
            traceback.print_exc()
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except: pass
            return None

auth = Auth()
print(f"[INIT] {datetime.datetime.now()}: Authentication helper initialized.")

class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)

    async def __call__(self, user_id_and_permissions: Tuple[str, List[str]] = Depends(auth.get_current_user_with_permissions)):
        user_id, token_permissions_list = user_id_and_permissions
        token_permissions_set = set(token_permissions_list)

        if not self.required_permissions.issubset(token_permissions_set):
            missing_perms = self.required_permissions - token_permissions_set
            print(f"User {user_id} missing permissions. Required: {self.required_permissions}, Has: {token_permissions_set}, Missing: {missing_perms}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Missing: {', '.join(missing_perms)}"
            )
        return user_id

print(f"[INIT] {datetime.datetime.now()}: Initializing TaskQueue...")
task_queue = TaskQueue()
print(f"[INIT] {datetime.datetime.now()}: TaskQueue initialized.")

print(f"[INIT] {datetime.datetime.now()}: Initializing MongoManager...")
mongo_manager = MongoManager()
print(f"[INIT] {datetime.datetime.now()}: MongoManager initialized.")

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        print(f"[WS_MANAGER] {datetime.datetime.now()}: WebSocketManager initialized.")
    async def connect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            print(f"[WS_MANAGER] User {user_id} already connected. Closing old one.")
            old_ws = self.active_connections[user_id]
            try:
                await old_ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="New connection")
            except Exception:
                pass
        self.active_connections[user_id] = websocket
        print(f"[WS_MANAGER] WebSocket connected: {user_id} ({len(self.active_connections)} total)")
    def disconnect(self, websocket: WebSocket):
        uid_to_remove = next((uid for uid, ws in self.active_connections.items() if ws == websocket), None)
        if uid_to_remove:
            del self.active_connections[uid_to_remove]
            print(f"[WS_MANAGER] WebSocket disconnected: {uid_to_remove} ({len(self.active_connections)} total)")
    async def send_personal_message(self, message: str, user_id: str):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"[WS_MANAGER] Error sending to {user_id}: {e}")
                self.disconnect(ws)
    async def broadcast(self, message: str):
        for ws in list(self.active_connections.values()): 
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws) 
    async def broadcast_json(self, data: dict):
        await self.broadcast(json.dumps(data))

manager = WebSocketManager()
print(f"[INIT] {datetime.datetime.now()}: WebSocketManager instance created.")

print(f"[INIT] {datetime.datetime.now()}: Initializing MemoryBackend...")
memory_backend = MemoryBackend(mongo_manager=mongo_manager)
print(f"[INIT] {datetime.datetime.now()}: MemoryBackend initialized.")

active_context_engines: Dict[str, Dict[str, BaseContextEngine]] = {}
polling_scheduler_task_handle: Optional[asyncio.Task] = None

POLLING_SCHEDULER_INTERVAL_SECONDS = int(os.getenv("POLLING_SCHEDULER_INTERVAL_SECONDS", 30))

DATA_SOURCES_CONFIG: Dict[str, Dict[str, Any]] = {
    "gmail": {
        "engine_class": GmailContextEngine,
        "enabled_by_default": True,
    },
    # "gcalendar": {
    #     "engine_class": GCalendarContextEngine,
    #     "enabled_by_default": True,
    # },
    # "internet_search": {
    #     "engine_class": InternetSearchContextEngine,
    #     "enabled_by_default": False,
    # }
}

async def load_user_profile(user_id: str) -> Dict[str, Any]:
    profile = await mongo_manager.get_user_profile(user_id)
    return profile if profile else {"user_id": user_id, "userData": {}}

async def write_user_profile(user_id: str, data: Dict[str, Any]) -> bool:
    return await mongo_manager.update_user_profile(user_id, data)

async def get_chat_history_messages(user_id: str, chat_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    effective_chat_id = chat_id
    if effective_chat_id is None or effective_chat_id == "":
        user_profile = await mongo_manager.get_user_profile(user_id)
        if user_profile and "userData" in user_profile and user_profile["userData"].get("active_chat_id") not in [None, ""]:
            effective_chat_id = user_profile["userData"]["active_chat_id"]
        else:
            all_chat_ids = await mongo_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids:
                effective_chat_id = all_chat_ids[0]
                await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else:
                new_chat_id = str(uuid.uuid4())
                await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_chat_id})
                effective_chat_id = new_chat_id
    
    if effective_chat_id is None or effective_chat_id == "":
        print(f"[CHAT_HISTORY_ERROR] No chat_id determined for user {user_id} after all attempts.")
        return [], ""
 
    messages = await mongo_manager.get_chat_history(user_id, effective_chat_id)
    s_messages = []
    for m in messages:
        if not isinstance(m, dict): continue
        if isinstance(m.get('timestamp'), datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        s_messages.append(m)
    return [m for m in s_messages if m.get("isVisible", True)], effective_chat_id


async def add_message_to_db(user_id: str, chat_id: Union[int, str], message_text: str, is_user: bool, is_visible: bool = True, **kwargs) -> Optional[str]:
    try:
        target_chat_id = str(chat_id)
    except (ValueError, TypeError):
        print(f"[ERROR] Invalid chat_id for add_message: {chat_id}")
        return None
    
    message_data = {
        "message": message_text,
        "isUser": is_user,
        "isVisible": is_visible,
        **kwargs }
    message_data = {k: v for k, v in message_data.items() if v is not None}

    try:
        message_id = await mongo_manager.add_chat_message(user_id, target_chat_id, message_data)
        return message_id
    except Exception as e:
        print(f"[ERROR] Adding message for {user_id}, chat {target_chat_id}: {e}")
        traceback.print_exc()
        return None

async def polling_scheduler_loop():
    print(f"[POLLING_SCHEDULER] Starting loop (interval: {POLLING_SCHEDULER_INTERVAL_SECONDS}s)")
    if not mongo_manager:
        print("[POLLING_SCHEDULER_ERROR] MongoManager not initialized. Scheduler cannot run.")
        return

    await mongo_manager.reset_stale_polling_locks() 
    
    while True:
        try:
            due_tasks_states = await mongo_manager.get_due_polling_tasks() 
            
            if not due_tasks_states:
                pass
            else:
                print(f"[POLLING_SCHEDULER] Found {len(due_tasks_states)} due polling tasks.")

            for task_state in due_tasks_states:
                user_id = task_state["user_id"]
                service_name = task_state["service_name"] 
                
                print(f"[POLLING_SCHEDULER] Attempting to process task for {user_id}/{service_name}")

                locked_task_state = await mongo_manager.set_polling_status_and_get(user_id, service_name)
                
                if locked_task_state:
                    print(f"[POLLING_SCHEDULER] Acquired lock for {user_id}/{service_name}. Triggering poll.")
                    
                    engine_instance = active_context_engines.get(user_id, {}).get(service_name)
                    
                    if not engine_instance:
                        engine_config = DATA_SOURCES_CONFIG.get(service_name)
                        if engine_config and engine_config.get("engine_class"):
                            engine_class = engine_config["engine_class"]
                            print(f"[POLLING_SCHEDULER] Creating new {engine_class.__name__} instance for {user_id}/{service_name}")
                            engine_instance = engine_class(
                                user_id=user_id,
                                task_queue=task_queue, 
                                memory_backend=memory_backend,
                                websocket_manager=manager,
                                mongo_manager_instance=mongo_manager
                            )
                            if user_id not in active_context_engines:
                                active_context_engines[user_id] = {}
                            active_context_engines[user_id][service_name] = engine_instance
                        else:
                            print(f"[POLLING_SCHEDULER_ERROR] No engine class configured for service: {service_name}")
                            await mongo_manager.update_polling_state(user_id, service_name, {"is_currently_polling": False})
                            continue
                    
                    asyncio.create_task(engine_instance.run_poll_cycle()) 
                else:
                    print(f"[POLLING_SCHEDULER] Could not acquire lock for {user_id}/{service_name} (already processing or no longer due).")

        except Exception as e:
            print(f"[POLLING_SCHEDULER_ERROR] Error in scheduler loop: {e}")
            traceback.print_exc() 
        
        await asyncio.sleep(POLLING_SCHEDULER_INTERVAL_SECONDS)

async def start_user_context_engines(user_id: str):
    print(f"[CONTEXT_ENGINE_MGR] Starting/Ensuring context engines and polling states for user {user_id}.")
    if user_id not in active_context_engines: 
        active_context_engines[user_id] = {}
    
    if not mongo_manager:
        print(f"[CONTEXT_ENGINE_MGR_ERROR] MongoManager not initialized. Cannot start engines for user {user_id}.")
        return

    user_profile = await mongo_manager.get_user_profile(user_id)
    user_settings = user_profile.get("userData", {}) if user_profile else {}

    for service_name, config in DATA_SOURCES_CONFIG.items():
        is_service_explicitly_enabled_in_profile = user_settings.get(f"{service_name}_polling_enabled")

        is_service_considered_enabled = False
        if is_service_explicitly_enabled_in_profile is not None:
            is_service_considered_enabled = is_service_explicitly_enabled_in_profile
        else:
            is_service_considered_enabled = config.get("enabled_by_default", True)

        if is_service_considered_enabled:
            engine_instance = active_context_engines.get(user_id, {}).get(service_name)
            if not engine_instance:
                engine_class = config["engine_class"]
                print(f"[CONTEXT_ENGINE_MGR] Creating transient {engine_class.__name__} instance for {user_id}/{service_name} for state init.")
                engine_instance = engine_class(
                    user_id=user_id,
                    task_queue=task_queue, 
                    memory_backend=memory_backend,
                    websocket_manager=manager,
                    mongo_manager_instance=mongo_manager
                )
            
            await engine_instance.initialize_polling_state() 
            print(f"[CONTEXT_ENGINE_MGR] Polling state ensured for {service_name} for user {user_id}.")
        else:
            print(f"[CONTEXT_ENGINE_MGR] Service {service_name} is disabled for user {user_id}. Skipping engine start/state init.")
            await mongo_manager.update_polling_state(user_id, service_name, {"is_enabled": False})

print(f"[DEPENDENCIES_INIT] {datetime.datetime.now()}: Initializing HuggingFace Embedding model ({os.environ.get('EMBEDDING_MODEL_REPO_ID', 'N/A')})...")
try:
    embed_model = HuggingFaceEmbedding(model_name=os.environ["EMBEDDING_MODEL_REPO_ID"])
    print(f"[DEPENDENCIES_INIT] {datetime.datetime.now()}: HuggingFace Embedding model initialized.")
except KeyError:
    print(f"[DEPENDENCIES_ERROR] {datetime.datetime.now()}: EMBEDDING_MODEL_REPO_ID not set. Embedding model not initialized.")
    embed_model = None
except Exception as e:
    print(f"[DEPENDENCIES_ERROR] {datetime.datetime.now()}: Failed to initialize Embedding model: {e}")
    embed_model = None

print(f"[DEPENDENCIES_INIT] {datetime.datetime.now()}: Initializing Neo4j Graph Driver (URI: {os.environ.get('NEO4J_URI', 'N/A')})...")
try:
    graph_driver = GraphDatabase.driver(uri=os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
    graph_driver.verify_connectivity() # Ensure this is okay to call here (it's synchronous)
    print(f"[DEPENDENCIES_INIT] {datetime.datetime.now()}: Neo4j Graph Driver initialized and connected.")
except KeyError:
    print(f"[DEPENDENCIES_ERROR] {datetime.datetime.now()}: NEO4J_URI/USERNAME/PASSWORD not set. Neo4j Driver not initialized.")
    graph_driver = None
except Exception as e:
    print(f"[DEPENDENCIES_ERROR] {datetime.datetime.now()}: Failed to initialize Neo4j Driver: {e}")
    graph_driver = None
# Define USER_PROFILE_DB_DIR here as it's a shared configuration
print(f"[CONFIG] {datetime.datetime.now()}: Defining database file paths in dependencies.py...")
# Path to the 'src' directory from 'src/server/common/dependencies.py'
_COMMON_DIR = os.path.dirname(os.path.abspath(__file__))
_SERVER_DIR = os.path.dirname(_COMMON_DIR)
_SRC_DIR = os.path.dirname(_SERVER_DIR)
USER_PROFILE_DB_DIR = os.path.join(_SRC_DIR, "user_databases")
os.makedirs(USER_PROFILE_DB_DIR, exist_ok=True)
print(f"[CONFIG] {datetime.datetime.now()}: USER_PROFILE_DB_DIR set to {USER_PROFILE_DB_DIR}")
