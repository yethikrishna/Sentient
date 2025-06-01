# Record script start time for performance monitoring and logging
import time
import datetime # Moved for early use and combined

START_TIME = time.time()
print(f"[STARTUP] {datetime.datetime.now()}: Script execution started.")

# --- Core Python and System Imports ---
import os
import asyncio
import pickle
import multiprocessing
import traceback # For detailed error printing
import json # Keep json for websocket messages

# --- MongoDB Manager Import ---
from server.db import MongoManager

# --- Third-Party Library Imports ---
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    status,
    Security # For SecurityScopes with Depends
    # WebSocketState removed from here
)
from fastapi.security import OAuth2PasswordBearer, SecurityScopes # For Authentication
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse # For various response types
from fastapi.middleware.cors import CORSMiddleware # For Cross-Origin Resource Sharing
from fastapi.staticfiles import StaticFiles # For serving static files
from pydantic import BaseModel, Field # For data validation and settings management
from typing import Optional, Any, Dict, List, AsyncGenerator, Union, Tuple # For type hinting

# --- Authentication Specific Imports ---
import requests # For fetching JWKS (JSON Web Key Set)
from jose import jwt, JWTError # For JWT (JSON Web Token) validation
from jose.exceptions import JOSEError # For handling JOSE specific errors

# --- Machine Learning and NLP Imports ---
from neo4j import GraphDatabase # For Neo4j graph database interaction
from llama_index.embeddings.huggingface import HuggingFaceEmbedding # For text embeddings

# --- Google API Imports ---
from google_auth_oauthlib.flow import InstalledAppFlow # For Google OAuth flow
from google.auth.transport.requests import Request # For Google API requests

# --- Environment and Configuration Imports ---
from dotenv import load_dotenv # For loading environment variables from .env files
import nest_asyncio # For allowing nested asyncio event loops (e.g., in Jupyter)
import uvicorn # For running the FastAPI application

# --- Utility and Other Imports ---
import numpy as np # For numerical operations, often used with ML models
import gradio as gr # Still needed for FastRTC internals (real-time communication)
from fastrtc import Stream, ReplyOnPause, AlgoOptions, SileroVadOptions # For FastRTC components
import httpx # For asynchronous HTTP requests

print(f"[STARTUP] {datetime.datetime.now()}: Basic imports completed.")

# --- Application-Specific Module Imports ---
# Assuming PERSONALITY_DESCRIPTIONS are defined in these imports
print(f"[STARTUP] {datetime.datetime.now()}: Importing model components...")
from server.agents.runnables import *
from server.agents.functions import * # Contains Google API auth and functions
from server.agents.prompts import *
from server.agents.formats import *
from server.agents.base import TaskQueue # TaskQueue is now here
from server.agents.helpers import * # Contains parse_and_execute_tool_calls
from server.agents.background import AgentTaskProcessor, APPROVAL_PENDING_SIGNAL # For background task processing

# Memory: Short-term and long-term memory management
from server.memory.runnables import *
from server.memory.functions import * # Contains query_user_profile, build_initial_knowledge_graph etc.
from server.memory.prompts import *
from server.memory.constants import *
from server.memory.formats import *
from server.memory.backend import MemoryBackend

# Utils: General utility functions
from server.utils.helpers import *

# Auth: Authentication related helpers (e.g., AES encryption, management tokens)
from server.auth.helpers import * # Contains AES, get_management_token

# Common: Shared components across different modules
from server.common.functions import * # Contains get_reframed_internet_query, get_search_results, get_search_summary
from server.common.runnables import *
from server.common.prompts import *
from server.common.formats import *

# Chat: Chat-specific logic and runnables
from server.chat.runnables import *
from server.chat.prompts import *
from server.chat.functions import *

# Context: Engines for pulling context from various sources
from server.context.gmail import GmailContextEngine
from server.context.internet import InternetSearchContextEngine
from server.context.gcalendar import GCalendarContextEngine

# Voice: Speech-to-Text (STT) and Text-to-Speech (TTS) functionalities
from server.voice.stt import FasterWhisperSTT
from server.voice.orpheus_tts import OrpheusTTS, TTSOptions, VoiceId, AVAILABLE_VOICES
from server.voice.gcp_tts import GCPTTS
from server.voice.elevenlabs_tts import ElevenLabsTTS

# --- Environment Variable Loading ---
print(f"[STARTUP] {datetime.datetime.now()}: Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env") # Adjusted path for app.py in app folder
load_dotenv(dotenv_path=dotenv_path)
print(f"[STARTUP] {datetime.datetime.now()}: Environment variables loaded from {dotenv_path}")

# --- Development/Production Environment Flag ---
IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS").upper() # Default to ORPHEUS if not set
print(f"[STARTUP] {datetime.datetime.now()}: Development environment flag set to {IS_DEV_ENVIRONMENT}")
print(f"[STARTUP] {datetime.datetime.now()}: TTS Provider set to {TTS_PROVIDER}")

# --- Asyncio Configuration ---
print(f"[STARTUP] {datetime.datetime.now()}: Applying nest_asyncio...")
nest_asyncio.apply()
print(f"[STARTUP] {datetime.datetime.now()}: nest_asyncio applied.")

# --- Global Initializations ---
print(f"[INIT] {datetime.datetime.now()}: Starting global initializations...")
DATA_SOURCES = ["gmail", "internet_search", "gcalendar"]

# --- Auth0 Configuration & JWKS (JSON Web Key Set) ---
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") 
ALGORITHMS = ["RS256"]
CUSTOM_CLAIMS_NAMESPACE = f"{AUTH0_AUDIENCE}/" if AUTH0_AUDIENCE and AUTH0_AUDIENCE.endswith('/') else f"{AUTH0_AUDIENCE}/" 

if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    print("[ERROR] FATAL: AUTH0_DOMAIN or AUTH0_AUDIENCE (for custom API) not set!")
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

# --- JWT Validation and Permission Handling Logic ---
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
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return None
        except HTTPException as e: 
            print(f"[WS_AUTH_ERROR] Auth failed: {e.detail}")
            await websocket.send_text(json.dumps({"type": "auth_failure", "message": e.detail}))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail[:123])
            return None
        except Exception as e:
            print(f"[WS_AUTH_ERROR] Unexpected error: {e}")
            traceback.print_exc()
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except: # NOSONAR
                pass
            return None

auth = Auth()
print(f"[INIT] {datetime.datetime.now()}: Authentication helper initialized for custom API.")

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


# --- Initialize embedding model, Neo4j driver, WebSocketManager, runnables, TaskQueue, voice models etc. ---
print(f"[INIT] {datetime.datetime.now()}: Initializing HuggingFace Embedding model ({os.environ.get('EMBEDDING_MODEL_REPO_ID', 'N/A')})...")
try:
    embed_model = HuggingFaceEmbedding(model_name=os.environ["EMBEDDING_MODEL_REPO_ID"])
    print(f"[INIT] {datetime.datetime.now()}: HuggingFace Embedding model initialized.")
except KeyError:
    print(f"[ERROR] {datetime.datetime.now()}: EMBEDDING_MODEL_REPO_ID not set. Embedding model not initialized.")
    embed_model = None
except Exception as e:
    print(f"[ERROR] {datetime.datetime.now()}: Failed to initialize Embedding model: {e}")
    embed_model = None

print(f"[INIT] {datetime.datetime.now()}: Initializing Neo4j Graph Driver (URI: {os.environ.get('NEO4J_URI', 'N/A')})...")
try:
    graph_driver = GraphDatabase.driver(uri=os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
    graph_driver.verify_connectivity()
    print(f"[INIT] {datetime.datetime.now()}: Neo4j Graph Driver initialized and connected.")
except KeyError:
    print(f"[ERROR] {datetime.datetime.now()}: NEO4J_URI/USERNAME/PASSWORD not set. Neo4j Driver not initialized.")
    graph_driver = None
except Exception as e:
    print(f"[ERROR] {datetime.datetime.now()}: Failed to initialize Neo4j Driver: {e}")
    graph_driver = None

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
print(f"[INIT] {datetime.datetime.now()}: Initializing runnables...")
reflection_runnable = get_reflection_runnable()
inbox_summarizer_runnable = get_inbox_summarizer_runnable()
priority_runnable = get_priority_runnable()
graph_decision_runnable = get_graph_decision_runnable()
information_extraction_runnable = get_information_extraction_runnable()
graph_analysis_runnable = get_graph_analysis_runnable()
text_dissection_runnable = get_text_dissection_runnable()
text_conversion_runnable = get_text_conversion_runnable()
query_classification_runnable = get_query_classification_runnable()
fact_extraction_runnable = get_fact_extraction_runnable()
text_summarizer_runnable = get_text_summarizer_runnable()
text_description_runnable = get_text_description_runnable()
# chat_history = get_chat_history() # Removed, history is now passed dynamically
chat_runnable = get_chat_runnable() # No longer takes chat_history at init
agent_runnable = get_agent_runnable() # No longer takes chat_history at init
unified_classification_runnable = get_unified_classification_runnable() # No longer takes chat_history at init
internet_query_reframe_runnable = get_internet_query_reframe_runnable()
internet_summary_runnable = get_internet_summary_runnable()
print(f"[INIT] {datetime.datetime.now()}: Runnables initialization complete.")
tool_handlers: Dict[str, callable] = {}
print(f"[INIT] {datetime.datetime.now()}: Tool handlers registry initialized.")

print(f"[INIT] {datetime.datetime.now()}: Initializing TaskQueue...")
task_queue = TaskQueue() # Uses MongoDB TaskQueue from agents.base
print(f"[INIT] {datetime.datetime.now()}: TaskQueue initialized.")

print(f"[INIT] {datetime.datetime.now()}: Initializing MongoManager...")
mongo_manager = MongoManager()
print(f"[INIT] {datetime.datetime.now()}: MongoManager initialized.")

# --- Helper Functions (User-Specific DB Operations) ---
async def load_user_profile(user_id: str) -> Dict[str, Any]:
    """Load user profile from MongoDB."""
    profile = await mongo_manager.get_user_profile(user_id)
    return profile if profile else {"user_id": user_id, "userData": {}}

async def write_user_profile(user_id: str, data: Dict[str, Any]) -> bool:
    """Write user profile to MongoDB."""
    return await mongo_manager.update_user_profile(user_id, data)

async def load_notifications_db(user_id: str) -> Dict[str, Any]:
    """Load notifications for a user from MongoDB."""
    notifications = await mongo_manager.get_notifications(user_id)
    return {"notifications": notifications, "next_notification_id": len(notifications) + 1} # Simulate old structure

async def save_notifications_db(user_id: str, data: Dict[str, Any]):
    """Save notifications for a user to MongoDB (simplified to add/clear)."""
    # This function's original purpose was to overwrite the entire notifications.json.
    # With MongoDB, we typically add individual notifications or clear all.
    # For now, this function will not be directly used for saving the whole "db".
    # Individual add_notification calls will be made where needed.
    # If the intent was to replace all notifications, clear_notifications + add_many would be needed.
    # Given the context, this function will likely be removed or its calls replaced.
    print(f"[WARN] save_notifications_db called for user {user_id}. This function is deprecated for MongoDB.")
    # No direct equivalent for saving the whole "db" structure.
    # The add_notification and clear_notifications methods in MongoManager should be used.

async def load_db(user_id: str) -> Dict[str, Any]: # Chat DB
    """Load chat history for a user from MongoDB."""
    # This function's original purpose was to load the entire chatsDb.json.
    # With MongoDB, we fetch messages for a specific chat_id.
    # This function will be refactored to return a structure compatible with existing calls,
    # but the underlying data will come from MongoDB.
    print(f"[WARN] load_db (chat) called for user {user_id}. This function needs refactoring.")
    # For now, return a dummy structure. The actual chat messages will be fetched by get_chat_history_messages.
    # The "active_chat_id" and "next_chat_id" logic will need to be managed differently.
    # For multi-tenancy, active_chat_id should probably be stored in user profile or session.
    # For simplicity, let's assume active_chat_id is managed by the frontend or passed explicitly.
    # For now, we'll return a default structure that doesn't rely on file loading.
    return {"chats": [], "active_chat_id": 0, "next_chat_id": 1}

async def save_db(user_id: str, data: Dict[str, Any]): # Chat DB
    """Save chat history for a user to MongoDB (deprecated)."""
    print(f"[WARN] save_db (chat) called for user {user_id}. This function is deprecated for MongoDB.")
    # This function's original purpose was to overwrite the entire chatsDb.json.
    # With MongoDB, individual messages are added. This function will be removed or its calls replaced.

async def update_neo4j_with_personal_info(user_id: str, personal_info: dict, graph_driver_instance: GraphDatabase.driver):
    if not graph_driver_instance:
        print(f"[NEO4J_PERSONAL_INFO_UPDATE_ERROR] Neo4j driver not available for user {user_id}.")
        return

    name = personal_info.get("name")
    location = personal_info.get("location")
    dob = personal_info.get("dateOfBirth") 

    if not name: 
        print(f"[NEO4J_PERSONAL_INFO_UPDATE_WARN] User name not provided for {user_id}. Skipping Neo4j update for personal info.")
        return

    try:
        def _update_graph_db(tx, user_id, name, location, dob):
            tx.run("""
                MERGE (u:User {userId: $userId})
                ON CREATE SET u.name = $name, u.location = $location, u.dateOfBirth = $dob, u.username = $name, u.createdAt = timestamp()
                ON MATCH SET u.name = $name, u.location = $location, u.dateOfBirth = $dob, u.username = $name, u.updatedAt = timestamp()
                MERGE (up:UserProfile {userId: $userId}) 
                ON CREATE SET up.createdAt = timestamp()
                ON MATCH SET up.updatedAt = timestamp()
                MERGE (u)-[:HAS_PROFILE]->(up)
            """, userId=user_id, name=name, location=location, dob=dob)

        with graph_driver_instance.session(database="neo4j") as session:
            await asyncio.to_thread(session.execute_write, _update_graph_db, user_id, name, location, dob)
        print(f"[NEO4J_PERSONAL_INFO_UPDATE] Successfully updated personal info for user {user_id} in Neo4j.")

    except Exception as e:
        print(f"[NEO4J_PERSONAL_INFO_UPDATE_ERROR] Failed to update personal info for user {user_id} in Neo4j: {e}")
        traceback.print_exc()

import uuid # Added for generating chat_id


async def get_chat_history_messages(user_id: str, chat_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    """Retrieve chat history messages for a specific user and chat_id from MongoDB.
    If chat_id is None, it will try to find an active one or create a new one.
    Returns a tuple of (messages, effective_chat_id).
    """
    effective_chat_id = chat_id
    print(f"[CHAT_HISTORY] Fetching chat history for user {user_id}, initial chat_id: {chat_id}.")
    

    if effective_chat_id is None or effective_chat_id == "":
        # If no chat_id is provided, try to get the active chat ID from user profile
        user_profile = await mongo_manager.get_user_profile(user_id)
        
        # Check if active_chat_id exists and is not None/empty in user profile
        if user_profile and "userData" in user_profile and user_profile["userData"].get("active_chat_id") not in [None, ""]:
            effective_chat_id = user_profile["userData"]["active_chat_id"]
            print(f"[CHAT_HISTORY] Using active chat ID from profile: {effective_chat_id}")
        else:
            # If no active chat ID in profile, try to find the most recent chat or create a new one
            all_chat_ids = await mongo_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids:
                effective_chat_id = all_chat_ids[0]
                print(f"[CHAT_HISTORY] No active chat ID in profile, using most recent chat: {effective_chat_id}")
                # Update user profile with this found active chat ID
                await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else:
                # No chats exist, create a new one
                new_chat_id = str(uuid.uuid4())
                await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_chat_id})
                print(f"[CHAT_HISTORY] No chats found, created new chat ID: {new_chat_id}")
                effective_chat_id = new_chat_id
    
    if effective_chat_id is None or effective_chat_id == "": # This final check should now truly indicate an error
        print(f"[CHAT_HISTORY_ERROR] No chat_id determined for user {user_id} after all attempts.")
        return [], "" # Return empty messages and empty chat_id if still no ID
 
    messages = await mongo_manager.get_chat_history(user_id, effective_chat_id)
    # Convert datetime objects to ISO format for JSON serialization
    s_messages = []
    for m in messages:
        if not isinstance(m, dict):
            print(f"[CHAT_HISTORY_WARN] Skipping non-dictionary message: {m}")
            continue # Skip this item if it's not a dictionary
        print(f"[CHAT_HISTORY_DEBUG] Processing message type: {type(m)}")
        if isinstance(m.get('timestamp'), datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        s_messages.append(m)
    # Filter for visible messages as per original logic
    print(f"[CHAT_HISTORY_DEBUG] s_messages before final filter: {[type(item) for item in s_messages]}")
    return [m for m in s_messages if m.get("isVisible", True)], effective_chat_id

async def add_message_to_db(user_id: str, chat_id: Union[int, str], message_text: str, is_user: bool, is_visible: bool = True, **kwargs) -> Optional[str]:
    """Add a new message to a user's chat history in MongoDB."""
    try:
        target_chat_id = str(chat_id) # Ensure chat_id is string for MongoDB
    except (ValueError, TypeError):
        print(f"[ERROR] Invalid chat_id for add_message: {chat_id}")
        return None
    
    message_data = {
        "message": message_text,
        "isUser": is_user,
        "isVisible": is_visible,
        **kwargs
    }
    # Filter out None values from kwargs before adding
    message_data = {k: v for k, v in message_data.items() if v is not None}

    try:
        message_id = await mongo_manager.add_chat_message(user_id, target_chat_id, message_data)
        return message_id
    except Exception as e:
        print(f"[ERROR] Adding message for {user_id}, chat {target_chat_id}: {e}")
        traceback.print_exc()
        return None

# Initialize AgentTaskProcessor
print(f"[INIT] {datetime.datetime.now()}: Initializing AgentTaskProcessor...")
agent_task_processor = AgentTaskProcessor(
    task_queue=task_queue,
    tool_handlers=tool_handlers, 
    load_user_profile_func=load_user_profile, # Defined below
    add_message_to_db_func=add_message_to_db, # Defined below
    graph_driver_instance=graph_driver,
    embed_model_instance=embed_model,
    reflection_runnable_instance=reflection_runnable,
    agent_runnable_instance=agent_runnable,
    internet_query_reframe_runnable_instance=internet_query_reframe_runnable,
    internet_summary_runnable_instance=internet_summary_runnable,
    query_user_profile_func=query_user_profile, # From server.memory.functions
    text_conversion_runnable_instance=text_conversion_runnable,
    query_classification_runnable_instance=query_classification_runnable,
    get_reframed_internet_query_func=get_reframed_internet_query, # From server.common.functions
    get_search_results_func=get_search_results, # From server.common.functions
    get_search_summary_func=get_search_summary # From server.common.functions
)
print(f"[INIT] {datetime.datetime.now()}: AgentTaskProcessor initialized.")


stt_model = None
tts_model = None
SELECTED_TTS_VOICE: VoiceId = "tara"
print(f"[CONFIG] {datetime.datetime.now()}: Defining database file paths...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_PROFILE_DB_DIR = os.path.join(BASE_DIR, "..", "..", "user_databases") # Keep for now for input_docs
# CHAT_DB_DIR = os.path.join(BASE_DIR, "..", "..", "chat_databases") # Removed, no longer needed for JSON
# NOTIFICATIONS_DB_DIR = os.path.join(BASE_DIR, "..", "..", "notification_databases") # Removed, no longer needed for JSON
os.makedirs(USER_PROFILE_DB_DIR, exist_ok=True) # Keep for now for input_docs
# os.makedirs(CHAT_DB_DIR, exist_ok=True) # Removed
# os.makedirs(NOTIFICATIONS_DB_DIR, exist_ok=True) # Removed
def get_user_profile_db_path(user_id: str) -> str: # Keep for now for input_docs
    return os.path.join(USER_PROFILE_DB_DIR, f"{user_id}_profile.json")
# def get_user_chat_db_path(user_id: str) -> str: # Removed
#     return os.path.join(CHAT_DB_DIR, f"{user_id}_chats.json")
# def get_user_notifications_db_path(user_id: str) -> str: # Removed
#     return os.path.join(NOTIFICATIONS_DB_DIR, f"{user_id}_notifications.json")
print(f"[CONFIG] {datetime.datetime.now()}: User-specific database directories set (for file-based inputs).")
# db_lock = asyncio.Lock() # Removed, replaced by MongoDB concurrency
# notifications_db_lock = asyncio.Lock() # Removed, replaced by MongoDB concurrency
# profile_db_lock = asyncio.Lock() # Removed, replaced by MongoDB concurrency
print(f"[INIT] {datetime.datetime.now()}: Global database locks removed (using MongoDB concurrency).")
# initial_db = {"chats": [], "active_chat_id": 0, "next_chat_id": 1} # Removed, replaced by MongoDB
print(f"[CONFIG] {datetime.datetime.now()}: Initial chat DB structure removed (using MongoDB).")
print(f"[INIT] {datetime.datetime.now()}: Initializing MemoryBackend...")
memory_backend = MemoryBackend(mongo_manager=mongo_manager)
print(f"[INIT] {datetime.datetime.now()}: MemoryBackend initialized.")
def register_tool(name: str):
    def decorator(func: callable):
        print(f"[TOOL_REGISTRY] Registering tool '{name}'")
        tool_handlers[name] = func
        return func
    return decorator
print(f"[CONFIG] {datetime.datetime.now()}: Setting up Google OAuth2 configuration...")
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.compose", "https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive", "https://mail.google.com/"]
CREDENTIALS_DICT = {"installed": {"client_id": os.environ.get("GOOGLE_CLIENT_ID"), "project_id": os.environ.get("GOOGLE_PROJECT_ID"), "auth_uri": os.environ.get("GOOGLE_AUTH_URI"), "token_uri": os.environ.get("GOOGLE_TOKEN_URI"), "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"), "redirect_uris": ["http://localhost"]}}
print(f"[CONFIG] {datetime.datetime.now()}: Google OAuth2 config complete.")
MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID_M2M")
MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET_M2M")
MANAGEMENT_API_AUDIENCE = os.getenv("AUTH0_MANAGEMENT_API_AUDIENCE") 
print(f"[CONFIG] {datetime.datetime.now()}: Auth0 Management API (M2M) config loaded.")


# --- FastAPI Application Setup ---
print(f"[FASTAPI] {datetime.datetime.now()}: Initializing FastAPI app...")
app = FastAPI(title="Sentient API", description="API for Sentient application.", version="1.0.0", docs_url="/docs", redoc_url=None)
print(f"[FASTAPI] {datetime.datetime.now()}: FastAPI app initialized.")
app.add_middleware(CORSMiddleware, allow_origins=["app://.", "http://localhost:3000", "http://localhost"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
print(f"[FASTAPI] {datetime.datetime.now()}: CORS middleware added.")

agent_task_processor_instance: Optional[AgentTaskProcessor] = None 

@app.on_event("startup")
async def startup_event():
    print(f"[FASTAPI_LIFECYCLE] App startup.")
    global stt_model, tts_model, agent_task_processor_instance

    agent_task_processor_instance = agent_task_processor 

    print("[LIFECYCLE] Loading STT...")
    try:
        stt_model = FasterWhisperSTT(model_size="base", device="cpu", compute_type="int8")
        print("[LIFECYCLE] STT loaded.")
    except Exception as e:
        print(f"[ERROR] STT model failed to load. Voice features will be unavailable. Details: {e}")
        stt_model = None
    
    print("[LIFECYCLE] Loading TTS...")
    try:
        if IS_DEV_ENVIRONMENT:
            tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
            print("[LIFECYCLE] Orpheus TTS loaded (Developer Mode).")
        else:
            if TTS_PROVIDER == "GCP":
                tts_model = GCPTTS()
                print("[LIFECYCLE] GCP TTS loaded (Production Mode).")
            elif TTS_PROVIDER == "ELEVENLABS":
                tts_model = ElevenLabsTTS()
                print("[LIFECYCLE] ElevenLabs TTS loaded (Production Mode).")
            else:
                print(f"[WARN] Unknown TTS_PROVIDER '{TTS_PROVIDER}'. Defaulting to Orpheus TTS.")
                tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
                print("[LIFECYCLE] Orpheus TTS loaded (Default Fallback).")
    except Exception as e:
        print(f"[ERROR] TTS model failed to load. Voice features will be unavailable. Details: {e}")
        tts_model = None
    
    await task_queue.initialize_db()
    await mongo_manager.initialize_db() # Initialize MongoManager collections
    await memory_backend.memory_queue.initialize_db() # Initialize MemoryQueue collections
    
    if agent_task_processor_instance:
        asyncio.create_task(agent_task_processor_instance.process_queue())
        asyncio.create_task(agent_task_processor_instance.cleanup_tasks_periodically())
    else:
        print("[ERROR] AgentTaskProcessor not initialized. Task processing will not start.")
        
    asyncio.create_task(memory_backend.process_memory_operations())
    
    print(f"[FASTAPI_LIFECYCLE] App startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    print(f"[FASTAPI_LIFECYCLE] App shutdown.")
    # No explicit save_operations needed for MongoDB, data is persisted on write.
    # However, we might want to close the MongoDB client connection.
    if mongo_manager.client:
        mongo_manager.client.close()
        print("[FASTAPI_LIFECYCLE] MongoDB client closed.")
    if task_queue.client:
        task_queue.client.close()
        print("[FASTAPI_LIFECYCLE] TaskQueue MongoDB client closed.")
    if memory_backend.memory_queue.client:
        memory_backend.memory_queue.client.close()
        print("[FASTAPI_LIFECYCLE] MemoryQueue MongoDB client closed.")
    print(f"[FASTAPI_LIFECYCLE] All MongoDB clients closed.")

# --- Pydantic Models ---
class Message(BaseModel):
    input: str
    pricing: str
    credits: int
class ElaboratorMessage(BaseModel):
    input: str
    purpose: str
class EncryptionRequest(BaseModel):
    data: str
class DecryptionRequest(BaseModel):
    encrypted_data: str
class SetReferrerRequest(BaseModel):
    referral_code: str
class DeleteSubgraphRequest(BaseModel):
    source: str
class GraphRequest(BaseModel):
    information: str
class GraphRAGRequest(BaseModel):
    query: str
class SetDataSourceEnabledRequest(BaseModel):
    source: str
    enabled: bool
class CreateTaskRequest(BaseModel):
    description: str
class UpdateTaskRequest(BaseModel):
    task_id: str
    description: str
    priority: int = Field(..., ge=0, le=2) 
class DeleteTaskRequest(BaseModel):
    task_id: str
class GetShortTermMemoriesRequest(BaseModel):
    category: str
    limit: int = Field(10, ge=1)
class UpdateUserDataRequest(BaseModel):
    data: Dict[str, Any]
class AddUserDataRequest(BaseModel):
    data: Dict[str, Any]
class OnboardingData(BaseModel):
    # This model will dynamically accept any keys from the frontend onboarding form
    # The values will be strings (for single choice) or lists of strings (for multiple choice)
    # For now, we'll use a generic Dict[str, Any] to capture all answers.
    # More specific validation can be added later if needed.
    data: Dict[str, Any]
class AddMemoryRequest(BaseModel):
    text: str
    category: str
    retention_days: int = Field(..., ge=1)
class UpdateMemoryRequest(BaseModel):
    id: int
    text: str
    category: str
    retention_days: int = Field(..., ge=1)
class DeleteMemoryRequest(BaseModel):
    id: int
    category: str
class TaskIdRequest(BaseModel):
    task_id: str
class TaskApprovalDataResponse(BaseModel):
    approval_data: Optional[Dict[str, Any]] = None
class ApproveTaskResponse(BaseModel):
    message: str
    result: Any

# --- API Endpoints ---

@app.get("/", status_code=status.HTTP_200_OK, summary="API Root", tags=["General"])
async def main_root():
    return {"message": "Sentient API is running."}

@app.post("/onboarding", status_code=status.HTTP_200_OK, summary="Save Onboarding Data", tags=["User Profile"])
async def save_onboarding_data_endpoint(onboarding_data: OnboardingData, user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[ENDPOINT /onboarding] User {user_id}, Onboarding Data: {str(onboarding_data.data)[:100]}...")
    try:
        # Save to MongoDB user profile
        # Load existing profile to merge data
        existing_profile = await load_user_profile(user_id)
        user_data_to_update = existing_profile.get("userData", {}) if existing_profile else {}

        # Merge new onboarding data into existing userData
        for key, new_val in onboarding_data.data.items():
            if key in user_data_to_update and isinstance(user_data_to_update[key], list) and isinstance(new_val, list):
                user_data_to_update[key].extend(item for item in new_val if item not in user_data_to_update[key])
            elif key in user_data_to_update and isinstance(user_data_to_update[key], dict) and isinstance(new_val, dict):
                user_data_to_update[key].update(new_val)
            else:
                user_data_to_update[key] = new_val

        # Update only the 'userData' field in the user profile document
        success = await write_user_profile(user_id, {"userData": user_data_to_update})
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save onboarding data to user profile.")

        # Save to Neo4j
        if graph_driver:
            print(f"[NEO4J_ONBOARDING] Initiating Neo4j update for onboarding data for user {user_id}.")
            await update_neo4j_with_onboarding_data(user_id, onboarding_data.data, graph_driver, embed_model)
        else:
            print(f"[WARN] Neo4j driver not available. Skipping Neo4j update for onboarding data for user {user_id}.")

        return JSONResponse(content={"message": "Onboarding data saved successfully.", "status": 200})
    except Exception as e:
        print(f"[ERROR] /onboarding {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save onboarding data.")

@app.post("/check-user-profile", status_code=status.HTTP_200_OK, summary="Check and Create User Profile", tags=["User Profile"])
async def check_and_create_user_profile(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile", "write:profile"]))):
    print(f"[ENDPOINT /check-user-profile] Called by user {user_id}.")
    try:
        profile = await mongo_manager.get_user_profile(user_id)
        if profile:
            print(f"[USER_PROFILE] Profile exists for user {user_id}.")
            return JSONResponse(content={"profile_exists": True})
        else:
            print(f"[USER_PROFILE] Profile does NOT exist for user {user_id}. Creating initial profile.")
            initial_profile_data = {
                "user_id": user_id,
                "createdAt": datetime.datetime.now(datetime.timezone.utc),
                "userData": {
                    "personalInfo": {
                        "name": "New User", # Placeholder, will be updated by onboarding
                        "email": user_id # Use user_id as a default email if available
                    },
                    "onboardingComplete": False,
                    "active_chat_id": str(uuid.uuid4()) # Assign a new chat ID for first-time users
                }
            }
            success = await mongo_manager.update_user_profile(user_id, initial_profile_data)
            if not success:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create initial user profile.")
            print(f"[USER_PROFILE] Initial profile created for user {user_id}.")
            return JSONResponse(content={"profile_exists": False})
    except Exception as e:
        print(f"[ERROR] /check-user-profile {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check or create user profile.")
 
@app.post("/get-history", status_code=status.HTTP_200_OK, summary="Get Chat History", tags=["Chat"])
async def get_history(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    print(f"[ENDPOINT /get-history] Called by user {user_id}.")
    try:
        # The frontend should ideally provide the active_chat_id.
        # Call get_chat_history_messages with None, allowing it to determine/create the active chat ID.
        # It now returns a tuple: (messages, effective_chat_id)
        messages, effective_chat_id = await get_chat_history_messages(user_id, None)
        
        # The effective_chat_id returned by the function is the definitive one to use.
        return JSONResponse(content={"messages": messages, "activeChatId": effective_chat_id})
    except Exception as e:
        print(f"[ERROR] /get-history {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get chat history.")

@app.post("/clear-chat-history", status_code=status.HTTP_200_OK, summary="Clear Chat History", tags=["Chat"])
async def clear_chat_history_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    print(f"[ENDPOINT /clear-chat-history] Called by user {user_id}.")
    try:
        # Get the active chat ID from the user's profile
        user_profile = await mongo_manager.get_user_profile(user_id)
        active_chat_id = user_profile.get("userData", {}).get("active_chat_id", None)

        if active_chat_id:
            deleted = await mongo_manager.delete_chat_history(user_id, active_chat_id)
            if deleted:
                # Optionally, reset active_chat_id in user profile or set to a new default
                await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": None})
                print(f"[CHAT_HISTORY] Cleared active chat {active_chat_id} for user {user_id}.")
                return JSONResponse(content={"message": "Active chat history cleared.", "activeChatId": None})
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No active chat found with ID {active_chat_id} for user {user_id}.")
        else:
            return JSONResponse(content={"message": "No active chat to clear.", "activeChatId": None})
    except Exception as e:
        print(f"[ERROR] /clear-chat-history {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear chat history.")

@app.post("/get-all-chat-ids", status_code=status.HTTP_200_OK, summary="Get All Chat IDs for User", tags=["Chat"])
async def get_all_chat_ids_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    print(f"[ENDPOINT /get-all-chat-ids] Called by user {user_id}.")
    try:
        chat_ids = await mongo_manager.get_all_chat_ids_for_user(user_id)
        return JSONResponse(content={"chat_ids": chat_ids})
    except Exception as e:
        print(f"[ERROR] /get-all-chat-ids {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve chat IDs.")

@app.post("/chat", status_code=status.HTTP_200_OK, summary="Process Chat Message", tags=["Chat"])
async def chat(message: Message, user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    print(f"[ENDPOINT /chat] User {user_id}. Input: '{message.input[:50]}...'")
    try:
        user_profile_data = await load_user_profile(user_id)
        username = user_profile_data.get("userData", {}).get("personalInfo", {}).get("name", "User")
        # Call get_chat_history_messages with None, allowing it to determine/create the active chat ID.
        # It now returns a tuple: (messages, effective_chat_id)
        # We only need the effective_chat_id here for subsequent calls.
        _, active_chat_id = await get_chat_history_messages(user_id, None)
        
        if not active_chat_id:
            # This should ideally not be reached if get_chat_history_messages works as expected
            print(f"[ERROR] /chat: Failed to determine active chat ID for user {user_id} after history init.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine active chat ID.")

        # Fetch chat history for the current request using the determined active_chat_id
        current_chat_history, _ = await get_chat_history_messages(user_id, active_chat_id)
        
        unified_output = unified_classification_runnable.invoke({"query": message.input, "chat_history": current_chat_history})
        category = unified_output.get("category", "chat")
        use_personal_context = unified_output.get("use_personal_context", False)
        internet_search_type = unified_output.get("internet", "None")
        transformed_input = unified_output.get("transformed_input", message.input)

        async def response_generator():
            memory_used, agents_used, internet_used, pro_features_used = False, False, False, False
            user_context_str, internet_context_str, additional_notes = None, None, ""

            user_msg_id = await add_message_to_db(user_id, active_chat_id, message.input, is_user=True, is_visible=True)
            if not user_msg_id:
                yield json.dumps({"type":"error", "message":"Failed to save message."})+"\n"
                return
            yield json.dumps({"type": "userMessage", "id": user_msg_id, "message": message.input, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n"
            await asyncio.sleep(0.01)
            assistant_msg_id_ts = str(int(time.time() * 1000))
            assistant_msg_base = {"id": assistant_msg_id_ts, "message": "", "isUser": False, "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "isVisible": True}

            if category == "agent":
                agents_used = True
                assistant_msg_base["agentsUsed"] = True
                print(f"[CHAT_DEBUG] Agent category detected. Transformed input: {transformed_input[:100]}...")
                try:
                    priority_response = priority_runnable.invoke({"task_description": transformed_input})
                    priority = priority_response.get("priority", 2)
                    print(f"[CHAT_DEBUG] Priority determined: {priority}")
                    await task_queue.add_task(user_id=user_id, chat_id=active_chat_id, description=transformed_input, priority=priority, username=username, use_personal_context=use_personal_context, internet=internet_search_type)
                    assistant_msg_base["message"] = "Okay, I'll get right on that."
                    await add_message_to_db(user_id, active_chat_id, assistant_msg_base["message"], is_user=False, is_visible=True, agentsUsed=True, task=transformed_input)
                    yield json.dumps({"type": "assistantMessage", "messageId": assistant_msg_base["id"], "message": assistant_msg_base["message"], "done": True, "proUsed": False}) + "\n"
                    print(f"[CHAT_DEBUG] Agent response sent and task added.")
                    return
                except Exception as e:
                    print(f"[ERROR] Agent task processing failed: {e}")
                    traceback.print_exc()
                    yield json.dumps({"type":"error", "message":"Failed to process agent task."})+"\n"
                    return

            if category == "memory" or use_personal_context:
                memory_used = True
                assistant_msg_base["memoryUsed"] = True
                yield json.dumps({"type": "intermediary", "message": "Checking context...", "id": assistant_msg_id_ts}) + "\n"
                print(f"[CHAT_DEBUG] Memory/Personal context requested. Retrieving memory for user {user_id} with input: {transformed_input[:100]}...")
                try:
                    user_context_str = await memory_backend.retrieve_memory(user_id, transformed_input)
                    print(f"[CHAT_DEBUG] Memory retrieval complete. Context length: {len(user_context_str) if user_context_str else 0}")
                except Exception as e:
                    user_context_str = f"Error retrieving context: {e}"
                    print(f"[ERROR] Memory retrieval failed: {e}")
                    traceback.print_exc()
                if category == "memory":
                    if message.pricing == "free" and message.credits <= 0:
                        additional_notes += " (Memory update skipped: Pro)"
                        print(f"[CHAT_DEBUG] Memory update skipped due to free tier/credits.")
                    else:
                        pro_features_used = True
                        asyncio.create_task(memory_backend.add_operation(user_id, transformed_input))
                        print(f"[CHAT_DEBUG] Memory add operation scheduled.")

            if internet_search_type and internet_search_type != "None":
                internet_used = True
                assistant_msg_base["internetUsed"] = True
                if message.pricing == "free" and message.credits <= 0:
                    additional_notes += " (Search skipped: Pro)"
                    print(f"[CHAT_DEBUG] Internet search skipped due to free tier/credits.")
                else:
                    pro_features_used = True
                    yield json.dumps({"type": "intermediary", "message": "Searching internet...", "id": assistant_msg_id_ts}) + "\n"
                    print(f"[CHAT_DEBUG] Internet search requested. Type: {internet_search_type}. Input: {transformed_input[:100]}...")
                    try:
                        reframed = get_reframed_internet_query(internet_query_reframe_runnable, transformed_input)
                        print(f"[CHAT_DEBUG] Internet query reframed: {reframed[:100]}...")
                        results = get_search_results(reframed)
                        print(f"[CHAT_DEBUG] Search results obtained. Number of results: {len(results) if results else 0}")
                        internet_context_str = get_search_summary(internet_summary_runnable, results)
                        print(f"[CHAT_DEBUG] Internet summary obtained. Context length: {len(internet_context_str) if internet_context_str else 0}")
                    except Exception as e:
                        internet_context_str = f"Error searching: {e}"
                        print(f"[ERROR] Internet search failed: {e}")
                        traceback.print_exc()

            if category in ["chat", "memory"]:
                yield json.dumps({"type": "intermediary", "message": "Thinking...", "id": assistant_msg_id_ts}) + "\n"
                full_response_text = ""
                print(f"[CHAT_DEBUG] Generating streaming response. User context: {bool(user_context_str)}, Internet context: {bool(internet_context_str)}")
                try:
                    # Fetch chat history right before generating response.
                    # The `build_prompt` method in BaseRunnable expects `chat_history` to contain
                    # all previous messages *excluding* the current user input, which it adds separately.
                    # So, we need to ensure `history_for_llm` contains only the prior conversation.
                    full_chat_history_from_db, _ = await get_chat_history_messages(user_id, active_chat_id)
                    print(f"[CHAT_DEBUG] Full chat history fetched. Length: {len(full_chat_history_from_db)}")
                    
                    # Filter out the current user message from the history if it's the last one.
                    # This assumes the last message in the fetched history is the one just added.
                    history_for_llm = []
                    if full_chat_history_from_db:
                        # Check if the last message is the current user's input
                        # We compare by message content and user status for robustness
                        last_message_in_db = full_chat_history_from_db[-1]
                        if isinstance(last_message_in_db, dict) and \
                           last_message_in_db.get("isUser") and \
                           last_message_in_db.get("message") == message.input:
                            history_for_llm = full_chat_history_from_db[:-1]
                            print(f"[CHAT_DEBUG] Sliced history for LLM (excluding current user input). Length: {len(history_for_llm)}")
                        else:
                            # If the last message is not the current user's input, use the full history.
                            # This might happen if there's an async timing issue or if the history
                            # contains other non-user messages at the end.
                            print(f"[WARN] Last message in history does not match current user input for user {user_id}. Passing full history to LLM.")
                            history_for_llm = full_chat_history_from_db
                    
                    print(f"[CHAT_DEBUG] Calling generate_streaming_response with inputs: query='{transformed_input[:50]}...', user_context_present={bool(user_context_str)}, internet_context_present={bool(internet_context_str)}, chat_history_length={len(history_for_llm)}")
                    async for token_chunk in generate_streaming_response(chat_runnable, inputs={"query": transformed_input, "user_context": user_context_str, "internet_context": internet_context_str, "name": username, "chat_history": history_for_llm}, stream=True):
                        if isinstance(token_chunk, str):
                            full_response_text += token_chunk
                            yield json.dumps({"type": "assistantStream", "token": token_chunk, "done": False, "messageId": assistant_msg_base["id"]}) + "\n"
                        await asyncio.sleep(0.01)
                    
                    final_message_content = full_response_text + (("\n\n" + additional_notes) if additional_notes else "")
                    assistant_msg_base["message"] = final_message_content
                    yield json.dumps({"type": "assistantStream", "token": ("\n\n" + additional_notes) if additional_notes else "", "done": True, "memoryUsed": memory_used, "agentsUsed": agents_used, "internetUsed": internet_used, "proUsed": pro_features_used, "messageId": assistant_msg_base["id"]}) + "\n"
                    await add_message_to_db(user_id, active_chat_id, final_message_content, is_user=False, is_visible=True, memoryUsed=memory_used, agentsUsed=agents_used, internetUsed=internet_used)
                    print(f"[CHAT_DEBUG] Streaming response completed and final message saved.")
                except Exception as e:
                    print(f"[ERROR] Error during streaming response generation: {e}")
                    traceback.print_exc()
                    error_msg_user = "Sorry, an error occurred while generating the response."
                    assistant_msg_base["message"] = error_msg_user
                    yield json.dumps({"type": "assistantStream", "token": error_msg_user, "done": True, "error": True, "messageId": assistant_msg_base["id"]}) + "\n"
                    await add_message_to_db(user_id, active_chat_id, error_msg_user, is_user=False, is_visible=True, error=True)
                    print(f"[CHAT_DEBUG] Error message sent and saved.")
        
        return StreamingResponse(response_generator(), media_type="application/x-ndjson")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"[ERROR] /chat {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Chat processing error.")

@app.post("/elaborator", status_code=status.HTTP_200_OK, summary="Elaborate Text", tags=["Utilities"])
async def elaborate(message: ElaboratorMessage, user_id: str = Depends(PermissionChecker(required_permissions=["use:elaborator"]))):
    print(f"[ENDPOINT /elaborator] User {user_id}, input: '{message.input[:50]}...'")
    try:
        elaborator_runnable = get_tool_runnable(elaborator_system_prompt_template, elaborator_user_prompt_template, None, ["query", "purpose"])
        output = elaborator_runnable.invoke({"query": message.input, "purpose": message.purpose})
        return JSONResponse(content={"message": output})
    except Exception as e:
        print(f"[ERROR] /elaborator: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Elaboration failed.")

@app.post("/encrypt", status_code=status.HTTP_200_OK, summary="Encrypt Data", tags=["Utilities"])
async def encrypt_data(request: EncryptionRequest):
    try:
        return JSONResponse(content={"encrypted_data": aes_encrypt(request.data)})
    except Exception as e:
        print(f"[ERROR] /encrypt: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption failed.")

@app.post("/decrypt", status_code=status.HTTP_200_OK, summary="Decrypt Data", tags=["Utilities"])
async def decrypt_data(request: DecryptionRequest):
    try:
        return JSONResponse(content={"decrypted_data": aes_decrypt(request.encrypted_data)})
    except ValueError: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decryption failed: Invalid data or key.")
    except Exception as e:
        print(f"[ERROR] /decrypt: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Decryption failed.")


# Tool Handlers
@register_tool("gmail")
async def gmail_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = tool_call_input.get("input")
    if not user_id:
        return {"status": "failure", "error": "User_id missing for Gmail."}
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
        tool_runnable = get_tool_runnable(gmail_agent_system_prompt_template, gmail_agent_user_prompt_template, gmail_agent_required_format, ["query", "username", "previous_tool_response"])
        tool_call_str_output = tool_runnable.invoke({"query": str(input_val), "username": username, "previous_tool_response": tool_call_input.get("previous_tool_response")})
        
        tool_call_dict: Dict[str, Any]
        if isinstance(tool_call_str_output, dict): 
            tool_call_dict = tool_call_str_output
        elif isinstance(tool_call_str_output, str):
            try:
                tool_call_dict = json.loads(tool_call_str_output)
            except json.JSONDecodeError:
                print(f"[ERROR] Gmail tool LLM output not JSON: {tool_call_str_output}")
                return {"status": "failure", "error": f"LLM output not valid JSON: {tool_call_str_output[:100]}..."}
        else:
            print(f"[ERROR] Gmail tool unexpected LLM output type: {type(tool_call_str_output)}")
            return {"status": "failure", "error": "Unexpected LLM output type for Gmail tool."}

        actual_tool_name = tool_call_dict.get("tool_name")
        if actual_tool_name in ["send_email", "reply_email"]:
            return {"action": "approve", "tool_call": tool_call_dict}
        else:
            tool_result = await parse_and_execute_tool_calls(tool_call_dict) 
            return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] Gmail tool {user_id}: {e}")
        traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gdocs")
async def gdocs_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = str(tool_call_input.get("input",""))
    previous_tool_response = tool_call_input.get("previous_tool_response", {})
    if not user_id: return {"status": "failure", "error": "User_id missing."}
    try:
        tool_runnable = get_tool_runnable(gdocs_agent_system_prompt_template, gdocs_agent_user_prompt_template, gdocs_agent_required_format, ["query", "previous_tool_response"])
        tool_call_output = tool_runnable.invoke({"query": input_val, "previous_tool_response": previous_tool_response})
        tool_call_dict = json.loads(tool_call_output) if isinstance(tool_call_output, str) else tool_call_output
        return await parse_and_execute_tool_calls(tool_call_dict)
    except Exception as e: return {"status": "failure", "error": str(e)}

@register_tool("gcalendar")
async def gcalendar_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = str(tool_call_input.get("input",""))
    previous_tool_response = tool_call_input.get("previous_tool_response", {})
    if not user_id: return {"status": "failure", "error": "User_id missing."}
    try:
        user_profile = await load_user_profile(user_id)
        timezone = user_profile.get("userData", {}).get("personalInfo", {}).get("timezone", "UTC") 
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        tool_runnable = get_tool_runnable(gcalendar_agent_system_prompt_template, gcalendar_agent_user_prompt_template, gcalendar_agent_required_format, ["query", "current_time", "timezone", "previous_tool_response"])
        tool_call_output = tool_runnable.invoke({"query": input_val, "current_time": current_time, "timezone": timezone, "previous_tool_response": previous_tool_response})
        tool_call_dict = json.loads(tool_call_output) if isinstance(tool_call_output, str) else tool_call_output
        return await parse_and_execute_tool_calls(tool_call_dict)
    except Exception as e: return {"status": "failure", "error": str(e)}

@register_tool("gsheets")
async def gsheets_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = str(tool_call_input.get("input",""))
    previous_tool_response = tool_call_input.get("previous_tool_response", {})
    if not user_id: return {"status": "failure", "error": "User_id missing."}
    try:
        tool_runnable = get_tool_runnable(gsheets_agent_system_prompt_template, gsheets_agent_user_prompt_template, gsheets_agent_required_format, ["query", "previous_tool_response"])
        tool_call_output = tool_runnable.invoke({"query": input_val, "previous_tool_response": previous_tool_response})
        tool_call_dict = json.loads(tool_call_output) if isinstance(tool_call_output, str) else tool_call_output
        return await parse_and_execute_tool_calls(tool_call_dict)
    except Exception as e: return {"status": "failure", "error": str(e)}

@register_tool("gslides")
async def gslides_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = str(tool_call_input.get("input",""))
    previous_tool_response = tool_call_input.get("previous_tool_response", {})
    if not user_id: return {"status": "failure", "error": "User_id missing."}
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
        tool_runnable = get_tool_runnable(gslides_agent_system_prompt_template, gslides_agent_user_prompt_template, gslides_agent_required_format, ["query", "user_name", "previous_tool_response"])
        tool_call_output = tool_runnable.invoke({"query": input_val, "user_name": username, "previous_tool_response": previous_tool_response})
        tool_call_dict = json.loads(tool_call_output) if isinstance(tool_call_output, str) else tool_call_output
        return await parse_and_execute_tool_calls(tool_call_dict)
    except Exception as e: return {"status": "failure", "error": str(e)}

@register_tool("gdrive")
async def gdrive_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id")
    input_val = str(tool_call_input.get("input",""))
    previous_tool_response = tool_call_input.get("previous_tool_response", {})
    if not user_id: return {"status": "failure", "error": "User_id missing."}
    try:
        tool_runnable = get_tool_runnable(gdrive_agent_system_prompt_template, gdrive_agent_user_prompt_template, gdrive_agent_required_format, ["query", "previous_tool_response"])
        tool_call_output = tool_runnable.invoke({"query": input_val, "previous_tool_response": previous_tool_response})
        tool_call_dict = json.loads(tool_call_output) if isinstance(tool_call_output, str) else tool_call_output
        return await parse_and_execute_tool_calls(tool_call_dict)
    except Exception as e: return {"status": "failure", "error": str(e)}


# --- Utility Endpoints (Now use Custom Claims or M2M for Management API) ---

@app.post("/get-role", status_code=status.HTTP_200_OK, summary="Get User Role from Token", tags=["User Management"])
async def get_role(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    user_id = payload["user_id"]
    print(f"[ENDPOINT /get-role] Called by user {user_id} (from token claims).")
    user_role = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}role", "free") 
    print(f"User {user_id} role from token claim: {user_role}")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role})

@app.post("/get-referral-code", status_code=status.HTTP_200_OK, summary="Get Referral Code from Token", tags=["User Management"])
async def get_referral_code(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    user_id = payload["user_id"]
    print(f"[ENDPOINT /get-referral-code] Called by user {user_id} (from token claims).")
    referral_code = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referralCode", None)
    if not referral_code:
        print(f"User {user_id} referral code not found in token claims.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": None}) 
    print(f"User {user_id} referral code from token claim found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": referral_code})

@app.post("/get-referrer-status", status_code=status.HTTP_200_OK, summary="Get Referrer Status from Token", tags=["User Management"])
async def get_referrer_status(payload: dict = Depends(auth.get_decoded_payload_with_claims)):
    user_id = payload["user_id"]
    print(f"[ENDPOINT /get-referrer-status] Called by user {user_id} (from token claims).")
    referrer_status = payload.get(f"{CUSTOM_CLAIMS_NAMESPACE}referrerStatus", False) 
    print(f"User {user_id} referrer status from token claim: {referrer_status}")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"referrerStatus": referrer_status})

@app.post("/get-user-and-set-referrer-status", status_code=status.HTTP_200_OK, summary="Set Referrer Status by Code (Admin Action)", tags=["User Management"])
async def get_user_and_set_referrer_status(
    request: SetReferrerRequest,
    user_id_making_request: str = Depends(PermissionChecker(required_permissions=["admin:user_metadata"]))
):
    referral_code_to_find = request.referral_code
    print(f"[ENDPOINT /set-referrer-status] User {user_id_making_request} trying to set referrer for code {referral_code_to_find}.")
    try:
        mgmt_token = get_management_token() 
        if not mgmt_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="M2M token unavailable.")

        headers_search = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        search_url = f"https://{AUTH0_DOMAIN}/api/v2/users"
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

        update_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_to_update_id}"
        update_payload = {"app_metadata": {"referrer": True}}
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
        print(f"[ERROR] /set-referrer-status: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set referrer status.")

# --- Google Authentication Endpoint ---
@app.post("/authenticate-google", status_code=status.HTTP_200_OK, summary="Authenticate Google Services", tags=["Integrations"])
async def authenticate_google(user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"]))):
    print(f"[ENDPOINT /authenticate-google] User {user_id}.")
    token_path = os.path.join(BASE_DIR, "..", "..", "tokens", f"token_{user_id}.pickle") 
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    creds = None
    try:
        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                creds = pickle.load(token_file)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request()) 
            else:
                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google auth required or token expired. Setup flow needed.")
            with open(token_path, "wb") as token_file:
                pickle.dump(creds, token_file)
        return JSONResponse(content={"success": True, "message": "Google auth successful."})
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[ERROR] Google auth for {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Google auth failed: {str(e)}")


# --- Memory and Knowledge Graph Endpoints ---
@app.post("/graphrag", status_code=status.HTTP_200_OK, summary="Query Knowledge Graph (RAG)", tags=["Knowledge Graph"])
async def graphrag(request: GraphRAGRequest, user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /graphrag] User {user_id}, Query: '{request.query[:50]}...'")
    try:
        if not all([graph_driver, embed_model, text_conversion_runnable, query_classification_runnable]):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GraphRAG dependencies unavailable.")
        context = await asyncio.to_thread(query_user_profile, user_id, request.query, graph_driver, embed_model, text_conversion_runnable, query_classification_runnable)
        return JSONResponse(content={"context": context or "No relevant context found."})
    except Exception as e:
        print(f"[ERROR] /graphrag {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GraphRAG query failed.")

@app.post("/initiate-long-term-memories", status_code=status.HTTP_200_OK, summary="Initialize/Reset Knowledge Graph", tags=["Knowledge Graph"])
async def create_graph(request_data: Optional[Dict[str, bool]] = None, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    clear_graph_flag = request_data.get("clear_graph", False) if request_data else False
    action = "Resetting/rebuilding" if clear_graph_flag else "Initiating/Updating"
    print(f"[ENDPOINT /initiate-LTM] {action} KG for user {user_id}.")
    loop = asyncio.get_event_loop()
    input_dir = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs") 
    os.makedirs(input_dir, exist_ok=True)

    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
        if not all([graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable]):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph building dependencies unavailable.")

        def read_files_sync(udir, uname):
            fpath = os.path.join(udir, f"{user_id}_profile_summary.txt") # Use user_id for consistency
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    return [{"text": f.read(), "source": os.path.basename(fpath)}]
            return [{"text": f"Initial data for {uname}. Preferences: Likes Italian food. Works as a software engineer.", "source": "default_sample.txt"}]
        
        extracted_texts = await loop.run_in_executor(None, read_files_sync, input_dir, username)

        if clear_graph_flag:
            print(f"Clearing KG for user: {user_id} (username for scope: {username})...")
            def clear_neo4j_user_graph_sync(driver, uid_scope: str): 
                with driver.session(database="neo4j") as session:
                    query = "MATCH (n {userId: $userId_scope}) DETACH DELETE n" 
                    session.execute_write(lambda tx: tx.run(query, userId_scope=uid_scope))
            await loop.run_in_executor(None, clear_neo4j_user_graph_sync, graph_driver, user_id)
            print(f"Graph cleared for user: {user_id}.")

        if extracted_texts:
            await loop.run_in_executor(None, build_initial_knowledge_graph, user_id, username, extracted_texts, graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable)
            return JSONResponse(content={"message": f"Knowledge Graph {action.lower()} for user {username} completed."})
        else:
            return JSONResponse(content={"message": "No input documents found. Graph not modified."})
    except Exception as e:
        print(f"[ERROR] /initiate-LTM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Knowledge Graph operation failed.")

@app.post("/delete-subgraph", status_code=status.HTTP_200_OK, summary="Delete Subgraph by Source", tags=["Knowledge Graph"])
async def delete_subgraph(request: DeleteSubgraphRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    source_key = request.source.lower().replace(' ', '_') 
    print(f"[ENDPOINT /delete-subgraph] User {user_id}, source key: {source_key}")
    loop = asyncio.get_event_loop()
    try:
        source_identifier_in_graph = f"{user_id}_{source_key}.txt" 

        if not graph_driver:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j driver unavailable.")
        
        await loop.run_in_executor(None, delete_source_subgraph, graph_driver, source_identifier_in_graph, user_id) 

        input_dir_path = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs")
        file_to_delete_on_disk = os.path.join(input_dir_path, source_identifier_in_graph) 
        
        def remove_file_sync(path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    return True, None
                except OSError as e_os:
                    return False, str(e_os)
            return False, "File not found on disk for deletion."
        
        deleted, ferr = await loop.run_in_executor(None, remove_file_sync, file_to_delete_on_disk)
        if not deleted:
            print(f"[WARN] Could not delete source file {file_to_delete_on_disk}: {ferr}")
        
        return JSONResponse(content={"message": f"Subgraph for source '{request.source}' (graph id: {source_identifier_in_graph}) processed for deletion."})
    except Exception as e:
        print(f"[ERROR] /delete-subgraph {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Subgraph deletion failed.")

@app.post("/create-document", status_code=status.HTTP_200_OK, summary="Create Input Documents from Profile", tags=["Knowledge Graph"])
async def create_document(user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[ENDPOINT /create-document] User {user_id}.")
    input_dir = os.path.join(USER_PROFILE_DB_DIR, user_id, "input_docs")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await load_user_profile(user_id)
        db_user_data = user_profile.get("userData", {})
        username = db_user_data.get("personalInfo", {}).get("name", user_id) 
        await loop.run_in_executor(None, os.makedirs, input_dir, True) 

        bg_tasks = []
        created_files_info = []
        
        summary_text = ""
        summary_filename = f"{user_id}_profile_summary.txt"
        await loop.run_in_executor(None, summarize_and_write_sync, user_id, username, summary_text, summary_filename, input_dir)
        created_files_info.append(summary_filename)
        
        return JSONResponse(content={"message": "Input documents processed.", "created_files": created_files_info, "summary_generated_length": len(summary_text)})
    except Exception as e:
        print(f"[ERROR] /create-document {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document creation failed.")

@app.post("/customize-long-term-memories", status_code=status.HTTP_200_OK, summary="Customize KG with Text", tags=["Knowledge Graph"])
async def customize_graph(request: GraphRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /customize-LTM] User {user_id}, Info: '{request.information[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
        required_deps = [graph_driver, embed_model, fact_extraction_runnable, query_classification_runnable, information_extraction_runnable, graph_analysis_runnable, graph_decision_runnable, text_description_runnable]
        if not all(required_deps):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph customization dependencies unavailable.")

        extracted_points_data = await loop.run_in_executor(None, fact_extraction_runnable.invoke, {"paragraph": request.information, "username": username})
        
        extracted_points = []
        if isinstance(extracted_points_data, dict) and "facts" in extracted_points_data and isinstance(extracted_points_data["facts"], list):
            extracted_points = extracted_points_data["facts"]
        elif isinstance(extracted_points_data, list): 
            extracted_points = extracted_points_data
        else:
            print(f"[WARN] Unexpected format from fact_extraction_runnable: {type(extracted_points_data)}")
            
        if not extracted_points:
            return JSONResponse(content={"message": "No facts extracted. Graph not modified."})

        crud_tasks = [loop.run_in_executor(None, crud_graph_operations, user_id, point, graph_driver, embed_model, query_classification_runnable, information_extraction_runnable, graph_analysis_runnable, graph_decision_runnable, text_description_runnable) for point in extracted_points]
        crud_results = await asyncio.gather(*crud_tasks, return_exceptions=True)
        
        processed = sum(1 for r in crud_results if not isinstance(r, Exception))
        errors = [str(r) for r in crud_results if isinstance(r, Exception)]
        msg = f"Knowledge Graph customization processed {processed}/{len(extracted_points)} facts." + (f" Errors: {len(errors)}" if errors else "")
        
        return JSONResponse(status_code=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS, content={"message": msg, "errors": errors})
    except Exception as e:
        print(f"[ERROR] /customize-LTM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Knowledge Graph customization failed.")


# --- Task Queue Endpoints ---
@app.post("/fetch-tasks", status_code=status.HTTP_200_OK, summary="Fetch User Tasks", tags=["Tasks"])
async def get_tasks(user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))):
    print(f"[ENDPOINT /fetch-tasks] User {user_id}.")
    try:
        user_tasks = await task_queue.get_tasks_for_user(user_id)
        s_tasks = []
        for t in user_tasks:
            if isinstance(t.get('created_at'), datetime.datetime): 
                t['created_at'] = t['created_at'].isoformat()
            if isinstance(t.get('completed_at'), datetime.datetime): 
                t['completed_at'] = t['completed_at'].isoformat()
            if isinstance(t.get('processing_started_at'), datetime.datetime):
                t['processing_started_at'] = t['processing_started_at'].isoformat()
            s_tasks.append(t)
        return JSONResponse(content={"tasks": s_tasks})
    except Exception as e:
        print(f"[ERROR] /fetch-tasks {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch tasks.")

@app.post("/add-task", status_code=status.HTTP_201_CREATED, summary="Add New Task", tags=["Tasks"])
async def add_task_endpoint(task_request: CreateTaskRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))):
    print(f"[ENDPOINT /add-task] User {user_id}, Desc: '{task_request.description[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        # Ensure active_chat_id is available. If not, get_chat_history_messages will create one.
        user_profile_for_task = await mongo_manager.get_user_profile(user_id)
        active_chat_id = user_profile_for_task.get("userData", {}).get("active_chat_id", None)
        
        await get_chat_history_messages(user_id, active_chat_id) # This ensures active_chat_id is set in profile
        
        # Re-fetch active_chat_id in case it was just created/updated
        user_profile_after_task_init = await mongo_manager.get_user_profile(user_id)
        active_chat_id = user_profile_after_task_init.get("userData", {}).get("active_chat_id", None)

        if not active_chat_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine active chat ID for task creation.")
        
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
        
        # Fetch chat history for the current request
        current_chat_history_for_task = await get_chat_history_messages(user_id, active_chat_id)
        
        unified_output = await loop.run_in_executor(None, unified_classification_runnable.invoke, {"query": task_request.description, "chat_history": current_chat_history_for_task})
        use_personal_context = unified_output.get("use_personal_context", False)
        internet_needed = unified_output.get("internet", "None")
        
        task_priority = 2
        try:
            priority_response = await loop.run_in_executor(None, priority_runnable.invoke, {"task_description": task_request.description})
            task_priority = priority_response.get("priority", 2)
        except Exception as e_prio:
            print(f"[WARN] Priority determination failed for task '{task_request.description[:30]}...': {e_prio}. Defaulting to low.")
            pass
            
        new_task_id = await task_queue.add_task(user_id=user_id, chat_id=active_chat_id, description=task_request.description, priority=task_priority, username=username, use_personal_context=use_personal_context, internet=internet_needed)
        
        await add_message_to_db(user_id, active_chat_id, task_request.description, is_user=True, is_visible=False)
        confirm_msg = f"Task added: '{task_request.description[:40]}...'"
        await add_message_to_db(user_id, active_chat_id, confirm_msg, is_user=False, is_visible=True, agentsUsed=True, task=task_request.description)
        
        return JSONResponse(content={"task_id": new_task_id, "message": "Task added successfully."}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"[ERROR] /add-task {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add task.")

@app.post("/update-task", status_code=status.HTTP_200_OK, summary="Update Task", tags=["Tasks"])
async def update_task_endpoint(request: UpdateTaskRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))):
    print(f"[ENDPOINT /update-task] User {user_id}, Task: {request.task_id}, Prio: {request.priority}")
    try:
        updated = await task_queue.update_task(user_id, request.task_id, request.description, request.priority)
        if not updated: 
            task = await task_queue.get_task_by_id(user_id, request.task_id)
            if not task:
                 raise ValueError(f"Task with id {request.task_id} for user {user_id} not found.")
            else: 
                 raise ValueError(f"Cannot update task {request.task_id} with status: {task['status']}.")
        return JSONResponse(content={"message": "Task updated successfully."})
    except ValueError as ve:
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /update-task {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update task.")

@app.post("/delete-task", status_code=status.HTTP_200_OK, summary="Delete Task", tags=["Tasks"])
async def delete_task_endpoint(request: DeleteTaskRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))):
    print(f"[ENDPOINT /delete-task] User {user_id}, Task: {request.task_id}")
    try:
        deleted = await task_queue.delete_task(user_id, request.task_id)
        return JSONResponse(content={"message": "Task deleted successfully."})
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /delete-task {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete task.")


# --- Short-Term Memory Endpoints ---
@app.post("/get-short-term-memories", status_code=status.HTTP_200_OK, summary="Get Short-Term Memories", tags=["Short-Term Memory"])
async def get_short_term_memories(request: GetShortTermMemoriesRequest, user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /get-STM] User {user_id}, Cat: {request.category}, Lim: {request.limit}")
    loop = asyncio.get_event_loop()
    try:
        memories = await loop.run_in_executor(None, memory_backend.memory_manager.fetch_memories_by_category, user_id, request.category, request.limit)
        s_mem = []
        for m in memories:
            if isinstance(m.get('created_at'), datetime.datetime): 
                m['created_at'] = m['created_at'].isoformat()
            if isinstance(m.get('expires_at'), datetime.datetime): 
                m['expires_at'] = m['expires_at'].isoformat()
            s_mem.append(m)
        return JSONResponse(content=s_mem)
    except Exception as e:
        print(f"[ERROR] /get-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch short-term memories.")

@app.post("/add-short-term-memory", status_code=status.HTTP_201_CREATED, summary="Add STM", tags=["Short-Term Memory"])
async def add_memory(request: AddMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /add-STM] User {user_id}, Cat: {request.category}")
    loop = asyncio.get_event_loop()
    try:
        mem_id = await loop.run_in_executor(None, memory_backend.memory_manager.store_memory, user_id, request.text, request.retention_days, request.category)
        return JSONResponse(content={"memory_id": mem_id, "message": "Short-term memory added."}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"[ERROR] /add-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add short-term memory.")

@app.post("/update-short-term-memory", status_code=status.HTTP_200_OK, summary="Update STM", tags=["Short-Term Memory"])
async def update_memory(request: UpdateMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /update-STM] User {user_id}, ID: {request.id}")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, memory_backend.memory_manager.update_memory_crud, user_id, request.category, request.id, request.text, request.retention_days)
        return JSONResponse(content={"message": "Short-term memory updated."})
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /update-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update short-term memory.")

@app.post("/delete-short-term-memory", status_code=status.HTTP_200_OK, summary="Delete STM", tags=["Short-Term Memory"])
async def delete_memory(request: DeleteMemoryRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /delete-STM] User {user_id}, ID: {request.id}, Cat: {request.category}")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, memory_backend.memory_manager.delete_memory, user_id, request.category, request.id)
        return JSONResponse(content={"message": "Short-term memory deleted."})
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /delete-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete short-term memory.")

@app.post("/clear-all-short-term-memories", status_code=status.HTTP_200_OK, summary="Clear All STM", tags=["Short-Term Memory"])
async def clear_all_memories(user_id: str = Depends(PermissionChecker(required_permissions=["write:memory"]))):
    print(f"[ENDPOINT /clear-all-STM] User {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, memory_backend.memory_manager.clear_all_memories, user_id)
        return JSONResponse(content={"message": "All short-term memories cleared."})
    except Exception as e:
        print(f"[ERROR] /clear-all-STM {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear all short-term memories.")

@app.post("/get-memory-categories", status_code=status.HTTP_200_OK, summary="Get Memory Categories", tags=["Short-Term Memory"])
async def get_memory_categories(user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /get-memory-categories] User {user_id}.")
    try:
        return JSONResponse(content={"categories": CATEGORIES})
    except Exception as e:
        print(f"[ERROR] /get-memory-categories {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve memory categories.")


# --- User Profile Database Endpoints ---
@app.post("/set-user-data", status_code=status.HTTP_200_OK, summary="Set User Profile Data", tags=["User Profile"])
async def set_db_data(request: UpdateUserDataRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[ENDPOINT /set-user-data] User {user_id}, Data: {str(request.data)[:100]}...")
    try:
        profile = await load_user_profile(user_id) 
        if "userData" not in profile:
            profile["userData"] = {}
        profile["userData"].update(request.data)
        success = await write_user_profile(user_id, profile)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to write user profile to JSON.")

        if "personalInfo" in profile["userData"] and graph_driver:
            personal_info_data = profile["userData"]["personalInfo"]
            if isinstance(personal_info_data, dict): 
                print(f"[NEO4J_INITIATE_PERSONAL_INFO_UPDATE] Initiating Neo4j update for personal info for user {user_id}.")
                await update_neo4j_with_personal_info(user_id, personal_info_data, graph_driver)
            else:
                print(f"[WARN] personalInfo for user {user_id} is not a dictionary. Skipping Neo4j update.")
        
        return JSONResponse(content={"message": "User data stored successfully.", "status": 200})
    except Exception as e:
        print(f"[ERROR] /set-user-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set user data.")

@app.post("/add-db-data", status_code=status.HTTP_200_OK, summary="Add/Merge User Profile Data", tags=["User Profile"])
async def add_db_data(request: AddUserDataRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:profile"]))):
    print(f"[ENDPOINT /add-db-data] User {user_id}, Data: {str(request.data)[:100]}...")
    try:
        profile = await load_user_profile(user_id) 
        existing_udata = profile.get("userData", {})
        
        for key, new_val in request.data.items():
            if key in existing_udata and isinstance(existing_udata[key], list) and isinstance(new_val, list):
                existing_udata[key].extend(item for item in new_val if item not in existing_udata[key])
            elif key in existing_udata and isinstance(existing_udata[key], dict) and isinstance(new_val, dict):
                existing_udata[key].update(new_val) 
            else:
                existing_udata[key] = new_val
        
        profile["userData"] = existing_udata
        success = await write_user_profile(user_id, profile) 
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to write merged user profile.")
        return JSONResponse(content={"message": "User data merged successfully.", "status": 200})
    except Exception as e:
        print(f"[ERROR] /add-db-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to merge user data.")

@app.post("/get-user-data", status_code=status.HTTP_200_OK, summary="Get User Profile Data", tags=["User Profile"])
async def get_db_data(user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))):
    print(f"[ENDPOINT /get-user-data] User {user_id}.")
    try:
        profile = await load_user_profile(user_id) 
        return JSONResponse(content={"data": profile.get("userData", {}), "status": 200})
    except Exception as e:
        print(f"[ERROR] /get-user-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user data.")

# --- Graph Data Endpoint ---
@app.post("/get-graph-data", status_code=status.HTTP_200_OK, summary="Get KG Data (Visualization)", tags=["Knowledge Graph"])
async def get_graph_data_apoc(user_id: str = Depends(PermissionChecker(required_permissions=["read:memory"]))):
    print(f"[ENDPOINT /get-graph-data] User {user_id}.")
    loop = asyncio.get_event_loop()
    if not graph_driver:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j driver unavailable.")
    
    graph_visualization_query = """
    MATCH (u:User {userId: $userId})-[r*0..2]-(n)
    WHERE n.userId = $userId OR (EXISTS(r) AND ALL(rel IN r WHERE startNode(rel).userId = $userId OR endNode(rel).userId = $userId))
    WITH collect(DISTINCT n) as nodes, collect(DISTINCT r) as rels_list
    UNWIND rels_list as rel
    RETURN [node IN nodes | { id: elementId(node), label: coalesce(labels(node)[0], 'Unknown'), properties: properties(node) }] AS nodes_list,
           [rel_item IN rels_list | { id: elementId(rel_item), from: elementId(startNode(rel_item)), to: elementId(endNode(rel_item)), label: type(rel_item), properties: properties(rel_item) }] AS edges_list
    """

    def run_q(driver, query, params):
        with driver.session(database="neo4j") as session: 
            res = session.run(query, params).single() 
            return (res['nodes_list'] if res else [], res['edges_list'] if res else [])
    try:
        nodes, edges = await loop.run_in_executor(None, run_q, graph_driver, graph_visualization_query, {"userId": user_id})
        return JSONResponse(content={"nodes": nodes, "edges": edges})
    except Exception as e:
        print(f"[ERROR] /get-graph-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get graph data.")

# --- Notifications Endpoint ---
@app.post("/get-notifications", status_code=status.HTTP_200_OK, summary="Get User Notifications", tags=["Notifications"])
async def get_notifications_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:notifications"]))):
    print(f"[ENDPOINT /get-notifications] User {user_id}.")
    try:
        notifications = await mongo_manager.get_notifications(user_id)
        # Convert datetime objects to ISO format for JSON serialization
        s_notifications = []
        for n in notifications:
            if isinstance(n.get('timestamp'), datetime.datetime):
                n['timestamp'] = n['timestamp'].isoformat()
            s_notifications.append(n)
        return JSONResponse(content={"notifications": s_notifications})
    except Exception as e:
        print(f"[ERROR] /get-notifications {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get notifications.")

@app.post("/add-notification", status_code=status.HTTP_201_CREATED, summary="Add New Notification", tags=["Notifications"])
async def add_notification_endpoint(notification_data: Dict[str, Any], user_id: str = Depends(PermissionChecker(required_permissions=["write:notifications"]))):
    print(f"[ENDPOINT /add-notification] User {user_id}, Data: {str(notification_data)[:100]}...")
    try:
        success = await mongo_manager.add_notification(user_id, notification_data)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add notification.")
        return JSONResponse(content={"message": "Notification added successfully."}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"[ERROR] /add-notification {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add notification.")

@app.post("/clear-notifications", status_code=status.HTTP_200_OK, summary="Clear All Notifications", tags=["Notifications"])
async def clear_notifications_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:notifications"]))):
    print(f"[ENDPOINT /clear-notifications] User {user_id}.")
    try:
        success = await mongo_manager.clear_notifications(user_id)
        if not success:
            # If no notifications were found to clear, it's still a success from user perspective
            print(f"[WARN] No notifications found to clear for user {user_id}.")
        return JSONResponse(content={"message": "All notifications cleared successfully."})
    except Exception as e:
        print(f"[ERROR] /clear-notifications {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear notifications.")


# --- Task Approval Endpoints ---
@app.post("/approve-task", response_model=ApproveTaskResponse, summary="Approve Pending Task", tags=["Tasks"])
async def approve_task_endpoint(request: TaskIdRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:tasks"]))):
    print(f"[ENDPOINT /approve-task] User {user_id}, Task: {request.task_id}")
    try:
        result_data = await task_queue.approve_task(user_id, request.task_id) 
        task_details = await task_queue.get_task_by_id(user_id, request.task_id) 
        
        if task_details and task_details.get("chat_id"):
            await add_message_to_db(user_id, task_details["chat_id"], str(result_data), is_user=False, is_visible=True, type="tool_result", task=task_details.get("description"), agentsUsed=True)
        
        return ApproveTaskResponse(message="Task approved and completed.", result=result_data)
    except ValueError as ve: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /approve-task {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Task approval failed.")

@app.post("/get-task-approval-data", response_model=TaskApprovalDataResponse, summary="Get Task Approval Data", tags=["Tasks"])
async def get_task_approval_data_endpoint(request: TaskIdRequest, user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"]))):
    print(f"[ENDPOINT /get-task-approval-data] User {user_id}, Task: {request.task_id}")
    try:
        task = await task_queue.get_task_by_id(user_id, request.task_id)
        if task: 
            if task.get("status") == "approval_pending":
                return TaskApprovalDataResponse(approval_data=task.get("approval_data"))
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is not pending approval. Current status: {task.get('status')}")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or access denied.")
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[ERROR] /get-task-approval-data {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get task approval data.")


# --- Data Source Configuration Endpoints ---
@app.post("/get_data_sources", status_code=status.HTTP_200_OK, summary="Get Data Source Statuses", tags=["Configuration"])
async def get_data_sources_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:config"]))):
    print(f"[ENDPOINT /get_data_sources] User {user_id}.")
    try:
        profile = await load_user_profile(user_id)
        settings = profile.get("userData", {})
        statuses = [{"name": src, "enabled": settings.get(f"{src}Enabled", True)} for src in DATA_SOURCES] 
        return JSONResponse(content={"data_sources": statuses})
    except Exception as e:
        print(f"[ERROR] /get_data_sources {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get data source statuses.")

@app.post("/set_data_source_enabled", status_code=status.HTTP_200_OK, summary="Enable/Disable Data Source", tags=["Configuration"])
async def set_data_source_enabled_endpoint(request: SetDataSourceEnabledRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:config"]))):
    print(f"[ENDPOINT /set_data_source_enabled] User {user_id}, Source: {request.source}, Enabled: {request.enabled}")
    if request.source not in DATA_SOURCES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data source: {request.source}")
    try:
        profile = await load_user_profile(user_id)
        if "userData" not in profile:
            profile["userData"] = {}
        profile["userData"][f"{request.source}Enabled"] = request.enabled
        success = await write_user_profile(user_id, profile) 
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save data source status.")
        return JSONResponse(content={"status": "success", "message": f"Data source '{request.source}' status set to {request.enabled}."})
    except Exception as e:
        print(f"[ERROR] /set_data_source_enabled {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set data source status.")


# --- WebSocket Endpoint (Authentication updated) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: Optional[str] = None
    try:
        authenticated_user_id = await auth.ws_authenticate(websocket) 
        if not authenticated_user_id:
            print("[WS /ws] WebSocket authentication failed or connection closed during auth.")
            return 
        
        await manager.connect(websocket, authenticated_user_id)
        while True:
            data = await websocket.receive_text()
            try:
                message_payload = json.loads(data)
                if message_payload.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                print(f"[WS /ws] Received non-JSON message from {authenticated_user_id}. Ignoring.")
                pass 
            except Exception as e_ws_loop:
                print(f"[WS /ws] Error in WebSocket loop for user {authenticated_user_id}: {e_ws_loop}")
    except WebSocketDisconnect:
        print(f"[WS /ws] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e: 
        print(f"[WS /ws] Unexpected WebSocket error (User: {authenticated_user_id or 'unknown'}): {e}")
        traceback.print_exc()
        try:
            # Attempt to close, Starlette's close is usually safe to call
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except RuntimeError as re: # e.g., "Cannot call 'send' once a close message has been sent."
            print(f"[WS /ws] Error during explicit close in exception handler (likely already closing/closed): {re}")
        except Exception as e_close: # Catch any other error during close
            print(f"[WS /ws] Unexpected error during explicit close in exception handler: {e_close}")
    finally:
        manager.disconnect(websocket)
        print(f"[WS /ws] WebSocket connection cleaned up for user: {authenticated_user_id or 'unknown'}")


# --- Voice Endpoint (FastRTC - Authentication still a TODO here) ---
async def handle_audio_conversation(audio: tuple[int, np.ndarray]) -> AsyncGenerator[tuple[int, np.ndarray], None]:
     user_id_for_voice = "PLACEHOLDER_VOICE_USER_ID" 
     print(f"\n--- [VOICE] Audio chunk received (User: {user_id_for_voice}) ---")

     if not stt_model:
         print("[VOICE_ERROR] STT model not available. Cannot process audio.")
         yield (0, np.array([])) 
         return
     
     user_transcribed_text = stt_model.stt(audio)
     if not user_transcribed_text or not user_transcribed_text.strip():
         print("[VOICE] Empty transcription from STT.")
         return 
         
     print(f"[VOICE] User (STT - {user_id_for_voice}): {user_transcribed_text}")
     
     bot_response_text = f"Voice processing is a work in progress for user {user_id_for_voice}. You said: '{user_transcribed_text}'"
     
     if not tts_model:
         print("[VOICE_ERROR] TTS model not available. Cannot generate audio response.")
         yield (0, np.array([]))
         return
         
     tts_options: TTSOptions = {"voice_id": SELECTED_TTS_VOICE} 
     async for sr, chunk in tts_model.stream_tts(bot_response_text, options=tts_options):
          if chunk is not None and chunk.size > 0:
              yield (sr, chunk)
              
     print(f"--- [VOICE] Finished processing audio response for {user_id_for_voice} ---")

voice_stream_handler = Stream(
    ReplyOnPause(
        handle_audio_conversation,
        algo_options=AlgoOptions(), 
        model_options=SileroVadOptions(), 
        can_interrupt=False 
    ),
    mode="send-receive", 
    modality="audio"
)
voice_stream_handler.mount(app, path="/voice") 
print(f"[FASTAPI] {datetime.datetime.now()}: FastRTC voice stream mounted at /voice.")

# --- Main Execution Block ---
if __name__ == "__main__":
    multiprocessing.freeze_support() 

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s [%(name)s] %(message)s" 
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO" 

    print(f"[UVICORN] Starting Uvicorn server on host 0.0.0.0, port 5000...")
    print(f"[UVICORN] API Documentation available at http://localhost:5000/docs")
    
    uvicorn.run(
        "__main__:app", 
        host="0.0.0.0",
        port=5000,
        lifespan="on", 
        reload=False,  
        workers=1,     
        log_config=log_config
    )