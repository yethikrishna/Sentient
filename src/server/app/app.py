import time
from datetime import datetime, timezone
START_TIME = time.time()
print(f"[STARTUP] {datetime.now()}: Script execution started.")

import os
import json
import asyncio
import pickle
import multiprocessing
from tzlocal import get_localzone # Keep if needed elsewhere, but use explicit UTC for DB timestamps
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status # Added Depends, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes # Added for Auth
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse # Added HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Added StaticFiles
from pydantic import BaseModel, Field # Added Field
from typing import Optional, Any, Dict, List, AsyncGenerator, Union # Added Union

# --- Auth ---
import requests # For fetching JWKS
from jose import jwt, JWTError # For JWT validation
from jose.exceptions import JOSEError

# --- Other imports ---
from neo4j import GraphDatabase
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import nest_asyncio
import uvicorn
import traceback # For detailed error printing
import numpy as np
import gradio as gr # Still needed for FastRTC internals
from fastrtc import Stream, ReplyOnPause, AlgoOptions, SileroVadOptions
import httpx

print(f"[STARTUP] {datetime.now()}: Basic imports completed.")

# Import specific functions, runnables, and helpers from respective folders
print(f"[STARTUP] {datetime.now()}: Importing model components...")
from server.agents.runnables import *
from server.agents.functions import *
from server.agents.prompts import *
from server.agents.formats import *
from server.agents.base import *
from server.agents.helpers import *

from server.memory.runnables import *
from server.memory.functions import *
from server.memory.prompts import *
from server.memory.constants import *
from server.memory.formats import *
from server.memory.backend import MemoryBackend

from server.utils.helpers import *

from server.scraper.runnables import *
from server.scraper.functions import *
from server.scraper.prompts import *
from server.scraper.formats import *

from server.auth.helpers import * # Contains AES, get_management_token

from server.common.functions import *
from server.common.runnables import *
from server.common.prompts import *
from server.common.formats import *

from server.chat.runnables import *
from server.chat.prompts import *
from server.chat.functions import *

from server.context.gmail import GmailContextEngine
from server.context.internet import InternetSearchContextEngine
from server.context.gcalendar import GCalendarContextEngine

from server.voice.stt import FasterWhisperSTT
from server.voice.orpheus_tts import OrpheusTTS, TTSOptions, VoiceId, AVAILABLE_VOICES

from datetime import datetime, timezone

# Load environment variables from .env file relative to this file's location
print(f"[STARTUP] {datetime.now()}: Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

from datetime import datetime, timezone

print(f"[STARTUP] {datetime.now()}: Environment variables loaded from {dotenv_path}")

# Apply nest_asyncio
print(f"[STARTUP] {datetime.now()}: Applying nest_asyncio...")
nest_asyncio.apply()
print(f"[STARTUP] {datetime.now()}: nest_asyncio applied.")

# --- Global Initializations ---
print(f"[INIT] {datetime.now()}: Starting global initializations...")

DATA_SOURCES = ["gmail", "internet_search", "gcalendar"]

# --- Auth0 Configuration & JWKS ---
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
# Audience should match the API identifier in Auth0
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") # e.g., your API identifier
ALGORITHMS = ["RS256"] # Auth0 uses RS256

if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    print("[ERROR] FATAL: AUTH0_DOMAIN or AUTH0_AUDIENCE not set in environment variables!")
    exit(1)

# Fetch JWKS keys from Auth0 discovery endpoint
jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
try:
    print(f"[INIT] {datetime.now()}: Fetching JWKS from {jwks_url}...")
    jwks_response = requests.get(jwks_url)
    jwks_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    jwks = jwks_response.json()
    print(f"[INIT] {datetime.now()}: JWKS fetched successfully.")
except requests.exceptions.RequestException as e:
     print(f"[ERROR] FATAL: Could not fetch JWKS from Auth0: {e}")
     exit(1)
except Exception as e:
     print(f"[ERROR] FATAL: Error processing JWKS: {e}")
     exit(1)

# OAuth2 scheme (doesn't validate, just extracts token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is dummy here

# --- JWT Validation Logic ---
class Auth:
    """Authentication and authorization helper class."""

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> str:
        """
        Dependency to validate JWT token and return user_id (sub).
        Raises HTTPException for invalid tokens.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        permission_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

        try:
            # Get the signing key from JWKS
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"], "kid": key["kid"], "use": key["use"],
                        "n": key["n"], "e": key["e"]
                    }
            if not rsa_key:
                print("[AUTH_VALIDATION] Signing key not found in JWKS for kid:", unverified_header["kid"])
                raise credentials_exception

            # Decode and validate the token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/"
            )

            user_id: str = payload.get("sub")
            if user_id is None:
                print("[AUTH_VALIDATION] Token payload missing 'sub' (user_id).")
                raise credentials_exception

            # Optional: Check for specific scopes/permissions if needed
            # scopes = payload.get("scope", "").split()
            # if "read:messages" not in scopes: # Example scope check
            #     raise permission_exception

            # print(f"[AUTH_VALIDATION] Token validated successfully for user: {user_id}")
            return user_id # Return the user ID ('sub' claim)

        except JWTError as e:
            print(f"[AUTH_VALIDATION] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e:
             print(f"[AUTH_VALIDATION] JOSE Error (likely key issue): {e}")
             raise credentials_exception
        except Exception as e:
             print(f"[AUTH_VALIDATION] Unexpected validation error: {e}")
             traceback.print_exc()
             raise credentials_exception

    async def ws_authenticate(self, websocket: WebSocket) -> Optional[str]:
        """Authenticates a WebSocket connection using a token sent by the client."""
        try:
            auth_data = await websocket.receive_text()
            message = json.loads(auth_data)
            if message.get("type") != "auth":
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Auth message expected")
                return None

            token = message.get("token")
            if not token:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token missing in auth message")
                return None

            # Validate token using the same logic as the HTTP dependency
            user_id = await self.get_current_user_from_token(token) # Reuse validation logic

            if user_id:
                 await websocket.send_text(json.dumps({"type": "auth_success", "user_id": user_id}))
                 print(f"[WS_AUTH] WebSocket authenticated for user: {user_id}")
                 return user_id
            else:
                 # get_current_user_from_token already raised exception if invalid
                 # This part might not be reached, but as fallback:
                 await websocket.send_text(json.dumps({"type": "auth_failure", "message": "Invalid token"}))
                 await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                 return None

        except WebSocketDisconnect:
            print("[WS_AUTH] Client disconnected during authentication.")
            return None
        except json.JSONDecodeError:
            print("[WS_AUTH] Received non-JSON auth message.")
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Invalid JSON format")
            return None
        except HTTPException as e: # Catch validation errors from get_current_user_from_token
             print(f"[WS_AUTH] Authentication failed: {e.detail}")
             await websocket.send_text(json.dumps({"type": "auth_failure", "message": e.detail}))
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
             return None
        except Exception as e:
            print(f"[WS_AUTH] Unexpected error during WebSocket authentication: {e}")
            traceback.print_exc()
            try:
                 await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
            except: pass # Ignore errors during close
            return None

    async def get_current_user_from_token(self, token: str) -> Optional[str]:
        """ Helper to validate token string directly (used by ws_authenticate) """
        # This replicates the logic from get_current_user but takes token string directly
        credentials_exception = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials" )
        try:
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = { "kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"] }
            if not rsa_key: raise credentials_exception
            payload = jwt.decode( token, rsa_key, algorithms=ALGORITHMS, audience=AUTH0_AUDIENCE, issuer=f"https://{AUTH0_DOMAIN}/" )
            user_id: str = payload.get("sub")
            if user_id is None: raise credentials_exception
            return user_id
        except JWTError as e: print(f"[AUTH_HELPER] JWT Error: {e}"); raise credentials_exception
        except JOSEError as e: print(f"[AUTH_HELPER] JOSE Error: {e}"); raise credentials_exception
        except Exception as e: print(f"[AUTH_HELPER] Unexpected validation error: {e}"); raise credentials_exception

# Instantiate Auth class
auth = Auth()
print(f"[INIT] {datetime.now()}: Authentication helper initialized.")


# Initialize embedding model
print(f"[INIT] {datetime.now()}: Initializing HuggingFace Embedding model ({os.environ.get('EMBEDDING_MODEL_REPO_ID', 'N/A')})...")
try:
    embed_model = HuggingFaceEmbedding(model_name=os.environ["EMBEDDING_MODEL_REPO_ID"])
    print(f"[INIT] {datetime.now()}: HuggingFace Embedding model initialized.")
except Exception as e:
    print(f"[ERROR] {datetime.now()}: Failed to initialize Embedding model: {e}")
    embed_model = None

# Initialize Neo4j driver
print(f"[INIT] {datetime.now()}: Initializing Neo4j Graph Driver (URI: {os.environ.get('NEO4J_URI', 'N/A')})...")
try:
    graph_driver = GraphDatabase.driver(
        uri=os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    graph_driver.verify_connectivity()
    print(f"[INIT] {datetime.now()}: Neo4j Graph Driver initialized and connected.")
except Exception as e:
    print(f"[ERROR] {datetime.now()}: Failed to initialize or connect Neo4j Driver: {e}")
    graph_driver = None

# --- WebSocket Manager --- (Modified for Authentication)
class WebSocketManager:
    def __init__(self):
        # Store active connections mapped to their authenticated user_id
        self.active_connections: Dict[str, WebSocket] = {} # user_id -> WebSocket
        print(f"[WS_MANAGER] {datetime.now()}: WebSocketManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: str):
        # Connection accepted *before* connect is called (in endpoint)
        # Check if user already has an active connection, potentially close old one
        if user_id in self.active_connections:
             print(f"[WS_MANAGER] {datetime.now()}: User {user_id} already has an active connection. Closing old one.")
             old_ws = self.active_connections[user_id]
             try:
                 await old_ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="New connection established")
             except Exception: pass # Ignore errors closing old socket
        self.active_connections[user_id] = websocket
        print(f"[WS_MANAGER] {datetime.now()}: WebSocket connected for user: {user_id} ({len(self.active_connections)} total)")

    def disconnect(self, websocket: WebSocket):
        user_id_to_remove = None
        for user_id, ws in self.active_connections.items():
            if ws == websocket:
                user_id_to_remove = user_id
                break
        if user_id_to_remove:
             del self.active_connections[user_id_to_remove]
             print(f"[WS_MANAGER] {datetime.now()}: WebSocket disconnected for user: {user_id_to_remove} ({len(self.active_connections)} total)")
        # else:
        #      print(f"[WS_MANAGER] {datetime.now()}: WebSocket disconnect requested, but socket not found in active connections.")


    async def send_personal_message(self, message: str, user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
             try:
                 await websocket.send_text(message)
             except Exception as e:
                 print(f"[WS_MANAGER] {datetime.now()}: Error sending personal message to user {user_id}: {e}")
                 self.disconnect(websocket) # Disconnect on send error
        # else:
             # print(f"[WS_MANAGER] {datetime.now()}: Could not send personal message: User {user_id} not connected.")


    async def broadcast(self, message: str):
        # Create a copy of connections to iterate over safely
        connections_to_send = list(self.active_connections.values())
        disconnected_websockets = []
        for connection in connections_to_send:
            try:
                await connection.send_text(message)
            except Exception as e:
                # Find user ID for logging, though it might be gone if disconnect already happened
                user_id = "unknown"
                for uid, ws in self.active_connections.items():
                    if ws == connection: user_id = uid; break
                print(f"[WS_MANAGER] {datetime.now()}: Error broadcasting to user {user_id}, marking for disconnect: {e}")
                disconnected_websockets.append(connection)

        for ws in disconnected_websockets:
            self.disconnect(ws)

    async def broadcast_json(self, data: dict):
        await self.broadcast(json.dumps(data))

manager = WebSocketManager()
print(f"[INIT] {datetime.now()}: WebSocketManager instance created.")

# Initialize runnables (No changes needed here)
print(f"[INIT] {datetime.now()}: Initializing agent/memory/chat/scraper runnables...")
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
chat_history = get_chat_history() # Manages its own state internally
chat_runnable = get_chat_runnable(chat_history)
agent_runnable = get_agent_runnable(chat_history)
unified_classification_runnable = get_unified_classification_runnable(chat_history)
reddit_runnable = get_reddit_runnable()
twitter_runnable = get_twitter_runnable()
internet_query_reframe_runnable = get_internet_query_reframe_runnable()
internet_summary_runnable = get_internet_summary_runnable()
print(f"[INIT] {datetime.now()}: Runnables initialization complete.")


# Tool handlers registry
tool_handlers: Dict[str, callable] = {}
print(f"[INIT] {datetime.now()}: Tool handlers registry initialized.")

# Instantiate the task queue globally
print(f"[INIT] {datetime.now()}: Initializing TaskQueue...")
task_queue = TaskQueue(manager) # Pass WebSocket manager for notifications
print(f"[INIT] {datetime.now()}: TaskQueue initialized.")

# --- Voice Model Initializations --- (Moved to lifespan)
stt_model = None
tts_model = None
SELECTED_TTS_VOICE: VoiceId = "tara" # Default voice
# ... (Voice config constants remain same) ...

# --- Database and State Management ---
print(f"[CONFIG] {datetime.now()}: Defining database file paths...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# User-specific DBs might be needed later, for now keep global paths
USER_PROFILE_DB_DIR = os.path.join(BASE_DIR, "..", "..", "user_databases") # Directory for user profiles
CHAT_DB_DIR = os.path.join(BASE_DIR, "..", "..", "chat_databases")       # Directory for chat histories
NOTIFICATIONS_DB_DIR = os.path.join(BASE_DIR, "..", "..", "notification_databases") # Directory for notifications

os.makedirs(USER_PROFILE_DB_DIR, exist_ok=True)
os.makedirs(CHAT_DB_DIR, exist_ok=True)
os.makedirs(NOTIFICATIONS_DB_DIR, exist_ok=True)

# Functions to get user-specific paths
def get_user_profile_db_path(user_id: str) -> str:
    # Sanitize user_id for filesystem? For now, assume it's safe enough.
    return os.path.join(USER_PROFILE_DB_DIR, f"{user_id}_profile.json")

def get_user_chat_db_path(user_id: str) -> str:
    return os.path.join(CHAT_DB_DIR, f"{user_id}_chats.json")

def get_user_notifications_db_path(user_id: str) -> str:
    return os.path.join(NOTIFICATIONS_DB_DIR, f"{user_id}_notifications.json")

print(f"[CONFIG] {datetime.now()}: User-specific database directories set.")

# Locks - Need per-user locks or a more sophisticated strategy if high concurrency
# For now, use global locks, implying potential contention if multiple users act simultaneously.
# Consider replacing with per-user locks stored in a dictionary if needed.
db_lock = asyncio.Lock()  # Global chat DB lock (potential bottleneck)
notifications_db_lock = asyncio.Lock() # Global notification DB lock
profile_db_lock = asyncio.Lock() # Global profile DB lock

print(f"[INIT] {datetime.now()}: Global database locks initialized (consider per-user locks for scale).")

# Initial DB Structure (remains same)
initial_db = {"chats": [], "active_chat_id": 0, "next_chat_id": 1}
print(f"[CONFIG] {datetime.now()}: Initial chat DB structure defined.")

# Initialize MemoryBackend (modified to handle user_id)
print(f"[INIT] {datetime.now()}: Initializing MemoryBackend...")
memory_backend = MemoryBackend(manager) # Pass WS manager
print(f"[INIT] {datetime.now()}: MemoryBackend initialized. Performing cleanup...")
# memory_backend.cleanup() # Cleanup might need user context? Defer for now.
print(f"[INIT] {datetime.now()}: MemoryBackend cleanup deferred.")

# Tool Registration Decorator (remains same)
def register_tool(name: str):
    def decorator(func: callable):
        print(f"[TOOL_REGISTRY] {datetime.now()}: Registering tool '{name}' with handler '{func.__name__}'")
        tool_handlers[name] = func
        return func
    return decorator

# Google OAuth2 configuration (remains same)
print(f"[CONFIG] {datetime.now()}: Setting up Google OAuth2 configuration...")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
    "https://mail.google.com/",
]
print(f"[CONFIG] {datetime.now()}:   - SCOPES defined: {SCOPES}")

CREDENTIALS_DICT = {
    "installed": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
        "auth_uri": os.environ.get("GOOGLE_AUTH_URI"),
        "token_uri": os.environ.get("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost"] # Make sure this matches your setup
    }
}

print(f"[CONFIG] {datetime.now()}: Google OAuth2 configuration complete.")

# Auth0 Management API configuration (remains same)
MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")
print(f"[CONFIG] {datetime.now()}: Auth0 Management API config loaded.")

# --- Helper Functions (Modified for User-Specific Files) ---

async def load_user_profile(user_id: str):
    """Load profile data for a specific user."""
    profile_path = get_user_profile_db_path(user_id)
    # print(f"[DB_HELPER] Loading profile for {user_id} from {profile_path}")
    try:
        async with profile_db_lock: # Use lock for file access
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except FileNotFoundError:
        # print(f"[DB_HELPER] Profile not found for {user_id}. Returning default.")
        return {"userData": {}} # Default structure
    except (json.JSONDecodeError, Exception) as e:
        print(f"[ERROR] Error loading profile for {user_id}: {e}")
        return {"userData": {}}

async def write_user_profile(user_id: str, data: dict):
    """Write profile data for a specific user."""
    profile_path = get_user_profile_db_path(user_id)
    # print(f"[DB_HELPER] Writing profile for {user_id} to {profile_path}")
    try:
         async with profile_db_lock:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
    except Exception as e:
        print(f"[ERROR] Error writing profile for {user_id}: {e}")
        return False

async def load_notifications_db(user_id: str):
    """Load notifications for a specific user."""
    notifications_path = get_user_notifications_db_path(user_id)
    async with notifications_db_lock:
        try:
            with open(notifications_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "notifications" not in data: data["notifications"] = []
                if "next_notification_id" not in data: data["next_notification_id"] = 1
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {"notifications": [], "next_notification_id": 1} # Initialize
        except Exception as e:
            print(f"[ERROR] Error loading notifications for {user_id}: {e}")
            return {"notifications": [], "next_notification_id": 1}

async def save_notifications_db(user_id: str, data):
    """Save notifications for a specific user."""
    notifications_path = get_user_notifications_db_path(user_id)
    async with notifications_db_lock:
        try:
            with open(notifications_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Error saving notifications for {user_id}: {e}")


async def load_db(user_id: str):
    """Load chat database for a specific user."""
    chat_path = get_user_chat_db_path(user_id)
    async with db_lock:
        try:
            with open(chat_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Basic validation
                if "chats" not in data: data["chats"] = []
                if "active_chat_id" not in data: data["active_chat_id"] = 0
                if "next_chat_id" not in data: data["next_chat_id"] = 1
                try: # Ensure IDs are int
                    if data.get("active_chat_id") is not None: data["active_chat_id"] = int(data["active_chat_id"])
                    if data.get("next_chat_id") is not None: data["next_chat_id"] = int(data["next_chat_id"])
                except: data["active_chat_id"] = 0; data["next_chat_id"] = 1
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return initial_db.copy() # Initialize for this user
        except Exception as e:
            print(f"[ERROR] Error loading chat DB for {user_id}: {e}")
            return initial_db.copy()

async def save_db(user_id: str, data):
    """Save chat database for a specific user."""
    chat_path = get_user_chat_db_path(user_id)
    async with db_lock:
        try:
            # Ensure IDs are int before saving
            if data.get("active_chat_id") is not None: data["active_chat_id"] = int(data["active_chat_id"])
            if data.get("next_chat_id") is not None: data["next_chat_id"] = int(data["next_chat_id"])
            for chat in data.get("chats", []):
                if chat.get("id") is not None: chat["id"] = int(chat["id"])

            with open(chat_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Error saving chat DB for {user_id}: {e}")


async def get_chat_history_messages(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves the chat history of the currently active chat for a specific user.
    Handles initial state, inactivity, and creates new chats as needed for that user.
    """
    print(f"[CHAT_HISTORY] {datetime.now()}: get_chat_history_messages called for user {user_id}.")
    async with db_lock: # Still global lock, consider per-user
        print(f"[CHAT_HISTORY] {datetime.now()}: Acquired chat DB lock for user {user_id}.")
        chatsDb = await load_db(user_id) # Load user's chat DB
        active_chat_id = chatsDb.get("active_chat_id", 0)
        next_chat_id = chatsDb.get("next_chat_id", 1)
        current_time = datetime.now(timezone.utc)
        existing_chats = chatsDb.get("chats", [])
        active_chat = None

        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} DB state - active_chat_id: {active_chat_id}, next_chat_id: {next_chat_id}, num_chats: {len(existing_chats)}")

        # --- Logic for handling active_chat_id and inactivity ---
        # (Remains largely the same, but operates on the user-specific chatsDb)
        if active_chat_id == 0:
            if not existing_chats:
                new_chat_id = next_chat_id
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - No chats exist. Creating first chat ID: {new_chat_id}.")
                new_chat = {"id": new_chat_id, "messages": []}
                chatsDb["chats"] = [new_chat]
                chatsDb["active_chat_id"] = new_chat_id
                chatsDb["next_chat_id"] = new_chat_id + 1
                await save_db(user_id, chatsDb)
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - First chat created and activated. DB saved.")
                return []
            else:
                latest_chat_id = existing_chats[-1]['id']
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Activating latest chat ID: {latest_chat_id}.")
                chatsDb['active_chat_id'] = latest_chat_id
                active_chat_id = latest_chat_id
                await save_db(user_id, chatsDb)
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Activated latest chat. DB saved.")

        active_chat = next((chat for chat in existing_chats if chat.get("id") == active_chat_id), None)

        if not active_chat:
            print(f"[ERROR] {datetime.now()}: User {user_id} - Active chat ID '{active_chat_id}' mismatch. Resetting active ID to 0.")
            chatsDb["active_chat_id"] = 0
            await save_db(user_id, chatsDb)
            return []

        # Inactivity check (if messages exist)
        if active_chat.get("messages"):
            try:
                last_message = active_chat["messages"][-1]
                timestamp_str = last_message.get("timestamp")
                if timestamp_str:
                    # Simple timestamp parsing (adjust if needed)
                    last_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if (current_time - last_timestamp).total_seconds() > 600: # 10 min threshold
                        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Inactivity detected in chat {active_chat_id}. Creating new chat.")
                        new_chat_id = next_chat_id
                        new_chat = {"id": new_chat_id, "messages": []}
                        chatsDb["chats"].append(new_chat)
                        chatsDb["active_chat_id"] = new_chat_id
                        chatsDb["next_chat_id"] = new_chat_id + 1
                        await save_db(user_id, chatsDb)
                        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - New chat {new_chat_id} created/activated due to inactivity.")
                        return [] # Return empty messages for new chat
            except Exception as e:
                print(f"[WARN] {datetime.now()}: User {user_id} - Error during inactivity check for chat {active_chat_id}: {e}")

        # Return visible messages
        if active_chat and active_chat.get("messages"):
            filtered_messages = [msg for msg in active_chat["messages"] if msg.get("isVisible", True)]
            print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Returning {len(filtered_messages)} visible messages for active chat {active_chat_id}.")
            return filtered_messages
        else:
            print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Active chat {active_chat_id} has no messages. Returning empty list.")
            return []


async def add_message_to_db(user_id: str, chat_id: Union[int, str], message_text: str, is_user: bool, is_visible: bool = True, **kwargs):
    """Adds a message to the specified chat ID for the specific user."""
    # print(f"[DB_ADD_MSG] User: {user_id}, Chat: {chat_id}, IsUser: {is_user}, Visible: {is_visible}, Text: {message_text[:50]}...")
    try: target_chat_id = int(chat_id)
    except: print(f"[ERROR] Invalid chat_id format for add_message_to_db: '{chat_id}'."); return None

    async with db_lock: # Still global lock
        try:
            chatsDb = await load_db(user_id)
            active_chat = next((chat for chat in chatsDb.get("chats", []) if chat.get("id") == target_chat_id), None)

            if active_chat:
                message_id = str(int(time.time() * 1000))
                new_message = {
                    "id": message_id, "message": message_text, "isUser": is_user, "isVisible": is_visible,
                    "timestamp": datetime.now(timezone.utc).isoformat(), # No 'Z' needed with offset
                    "memoryUsed": kwargs.get("memoryUsed", False), "agentsUsed": kwargs.get("agentsUsed", False),
                    "internetUsed": kwargs.get("internetUsed", False),
                    "type": kwargs.get("type"), "task": kwargs.get("task") # Include optional fields
                }
                # Remove None values for cleaner JSON
                new_message = {k: v for k, v in new_message.items() if v is not None}

                if "messages" not in active_chat: active_chat["messages"] = []
                active_chat["messages"].append(new_message)
                await save_db(user_id, chatsDb)
                # print(f"Message added to DB (User: {user_id}, Chat ID: {target_chat_id}, User: {is_user})")
                return message_id
            else:
                print(f"[ERROR] Could not find chat with ID {target_chat_id} for user {user_id} to add message.")
                return None
        except Exception as e:
            print(f"[ERROR] Error adding message to DB for user {user_id}: {e}")
            traceback.print_exc()
            return None

# Background task processors (need modification if state becomes user-specific)
# For now, they process global queues, but execution should use user_id from the task/operation data.

async def cleanup_tasks_periodically():
    """Periodically clean up old completed tasks (across all users for now)."""
    print(f"[TASK_CLEANUP] {datetime.now()}: Starting periodic task cleanup loop.")
    while True:
        cleanup_interval = 3600 # 1 hour
        print(f"[TASK_CLEANUP] {datetime.now()}: Running cleanup task...")
        try:
            # TODO: TaskQueue needs modification to handle user-specific tasks if stored per-user
            await task_queue.delete_old_completed_tasks()
            print(f"[TASK_CLEANUP] {datetime.now()}: Cleanup complete.")
        except Exception as e:
             print(f"[ERROR] {datetime.now()}: Error during periodic task cleanup: {e}")
        await asyncio.sleep(cleanup_interval)

async def process_queue():
    """Continuously process tasks from the global queue."""
    print(f"[TASK_PROCESSOR] {datetime.now()}: Starting task processing loop.")
    while True:
        task = await task_queue.get_next_task()
        if task:
            task_id = task.get("task_id", "N/A")
            task_user_id = task.get("user_id", "N/A") # Get user_id associated with the task
            task_desc = task.get("description", "N/A")
            task_chat_id = task.get("chat_id", "N/A")
            print(f"[TASK_PROCESSOR] {datetime.now()}: Processing task ID: {task_id} for User: {task_user_id}, Chat: {task_chat_id}, Desc: {task_desc}...")

            if task_user_id == "N/A":
                 print(f"[ERROR] {datetime.now()}: Task {task_id} is missing user_id. Cannot process.")
                 await task_queue.complete_task(task_id, error="Task missing user context", status="error")
                 continue

            try:
                # Execute task, passing user_id
                task_queue.current_task_execution = asyncio.create_task(execute_agent_task(task_user_id, task))
                result = await task_queue.current_task_execution

                if result == APPROVAL_PENDING_SIGNAL:
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) pending approval.")
                    # Status already set by execute_agent_task
                else:
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) completed normally. Result len: {len(str(result))}")
                    if task_chat_id != "N/A":
                        # Add results to the specific user's chat
                        await add_message_to_db(task_user_id, task_chat_id, task["description"], is_user=True, is_visible=False) # Hidden prompt
                        await add_message_to_db(task_user_id, task_chat_id, result, is_user=False, is_visible=True, type="tool_result", task=task["description"], agentsUsed=True) # Visible result
                    else:
                        print(f"[WARN] Task {task_id} (User: {task_user_id}) has no chat_id. Result not added to chat.")
                    await task_queue.complete_task(task_id, result=result) # Mark complete
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} marked completed in queue.")
                    # WS broadcast handled by TaskQueue.complete_task

            except asyncio.CancelledError:
                print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) execution cancelled.")
                await task_queue.complete_task(task_id, error="Task cancelled", status="cancelled")
                # WS broadcast handled by TaskQueue.complete_task
            except Exception as e:
                error_str = str(e)
                print(f"[ERROR] {datetime.now()}: Error processing task {task_id} (User: {task_user_id}): {error_str}")
                traceback.print_exc()
                await task_queue.complete_task(task_id, error=error_str, status="error")
                # WS broadcast handled by TaskQueue.complete_task
            finally:
                 task_queue.current_task_execution = None
        else:
            await asyncio.sleep(0.1)

async def process_memory_operations():
    """Continuously process memory operations from the global queue."""
    print(f"[MEMORY_PROCESSOR] {datetime.now()}: Starting memory operation processing loop.")
    while True:
        operation = await memory_backend.memory_queue.get_next_operation()
        if operation:
            op_id = operation.get("operation_id", "N/A")
            user_id = operation.get("user_id", "N/A") # Operation must have user_id
            memory_data = operation.get("memory_data", "N/A")
            print(f"[MEMORY_PROCESSOR] {datetime.now()}: Processing memory op ID: {op_id} for User: {user_id}...")

            if user_id == "N/A":
                 print(f"[ERROR] {datetime.now()}: Memory operation {op_id} is missing user_id. Cannot process.")
                 await memory_backend.memory_queue.complete_operation(op_id, error="Operation missing user context", status="error")
                 continue

            try:
                # Perform the memory update for the specific user
                await memory_backend.update_memory(user_id, memory_data)
                print(f"[MEMORY_PROCESSOR] {datetime.now()}: Memory update for user {user_id} successful (Op ID: {op_id}).")
                await memory_backend.memory_queue.complete_operation(op_id, result="Success")
                # WS broadcast handled by MemoryBackend

            except Exception as e:
                error_str = str(e)
                print(f"[ERROR] {datetime.now()}: Error processing memory op {op_id} for user {user_id}: {error_str}")
                traceback.print_exc()
                await memory_backend.memory_queue.complete_operation(op_id, error=error_str, status="error")
                # WS broadcast handled by MemoryBackend

        else:
            await asyncio.sleep(0.1)

# --- Task Execution Logic (Modified to accept user_id) ---
async def execute_agent_task(user_id: str, task: dict) -> str:
    """
    Execute the agent task for a specific user.
    """
    task_id = task.get("task_id", "N/A")
    task_desc = task.get("description", "N/A")
    print(f"[AGENT_EXEC] {datetime.now()}: Executing task ID: {task_id} for User: {user_id}, Desc: {task_desc}...")

    # --- Get User-Specific Context ---
    # Load user profile to get name/personality (avoid global state)
    user_profile = load_user_profile(user_id) # Load sync is okay here as background task
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
    personality = user_profile.get("userData", {}).get("personality", "Default helpful assistant")

    transformed_input = task["description"] # Use task description
    use_personal_context = task["use_personal_context"]
    internet = task["internet"]

    user_context = None
    internet_context = None

    # Compute User Context (Memory)
    if use_personal_context:
        print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) querying user profile/memory...")
        try:
            if graph_driver and embed_model and text_conversion_runnable and query_classification_runnable:
                 # Run sync graph query in threadpool to avoid blocking asyncio loop
                user_context = await asyncio.to_thread(
                     query_user_profile, # This function needs to be thread-safe
                     user_id, # Pass user_id to graph query
                     transformed_input, graph_driver, embed_model,
                     text_conversion_runnable, query_classification_runnable
                 )
                print(f"[AGENT_EXEC] User context retrieved for task {task_id}. Len: {len(str(user_context)) if user_context else 0}")
            else: print(f"[WARN] Skipping user context query for task {task_id} due to missing deps."); user_context = "Context unavailable."
        except Exception as e: print(f"[ERROR] Error computing user_context for task {task_id}: {e}"); user_context = f"Error: {e}"

    # Compute Internet Context (No user needed here directly)
    if internet and internet != "None":
         print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) searching internet...")
         # ... (internet search logic remains same) ...
         try:
              reframed_query = get_reframed_internet_query(internet_query_reframe_runnable, transformed_input)
              search_results = get_search_results(reframed_query)
              internet_context = get_search_summary(internet_summary_runnable, search_results)
              print(f"[AGENT_EXEC] Internet context summary generated for task {task_id}. Len: {len(str(internet_context)) if internet_context else 0}")
         except Exception as e: print(f"[ERROR] Error computing internet_context for task {task_id}: {e}"); internet_context = f"Error: {e}"

    # Invoke Agent Runnable
    print(f"[AGENT_EXEC] Invoking agent runnable for task {task_id} (User: {user_id})...")
    agent_input = {
        "query": transformed_input, "name": username, "user_context": user_context,
        "internet_context": internet_context, "personality": personality
    }
    try:
        # Assuming agent_runnable uses chat_history which is global for now
        # TODO: Chat history needs to be user-specific if agent uses it
        response = agent_runnable.invoke(agent_input)
        print(f"[AGENT_EXEC] Agent response received for task {task_id}.")
    except Exception as e: print(f"[ERROR] Error invoking agent_runnable for task {task_id}: {e}"); return f"Error: {e}"

    # Process Tool Calls (Approval logic remains same, handlers need user_id)
    tool_calls = []
    if isinstance(response, dict) and "tool_calls" in response: tool_calls = response["tool_calls"]
    elif isinstance(response, list): tool_calls = response
    else:
         if isinstance(response, str): return response # Direct answer
         error_msg = f"Invalid agent response type: {type(response)}"; print(f"[AGENT_EXEC] {error_msg}"); return error_msg

    all_tool_results = []
    previous_tool_result = None
    print(f"[AGENT_EXEC] Processing {len(tool_calls)} tool calls for task {task_id} (User: {user_id}).")

    for i, tool_call in enumerate(tool_calls):
         # ... (Validation of tool_call structure) ...
         tool_content = tool_call.get("content") if isinstance(tool_call, dict) and tool_call.get("response_type") == "tool_call" else tool_call
         if not isinstance(tool_content, dict): print(f"Skipping invalid tool content {i+1}"); continue
         tool_name = tool_content.get("tool_name"); task_instruction = tool_content.get("task_instruction")
         if not tool_name or not task_instruction: print(f"Skipping tool {i+1} missing name/instruction"); continue

         tool_handler = tool_handlers.get(tool_name)
         if not tool_handler:
              error_msg = f"Tool '{tool_name}' not found."; print(error_msg); all_tool_results.append({"tool_name": tool_name, "tool_result": error_msg, "status": "error"}); continue

         # Prepare input, passing user_id
         tool_input = {"input": str(task_instruction), "user_id": user_id} # Pass user_id to handler
         if tool_content.get("previous_tool_response", False): tool_input["previous_tool_response"] = previous_tool_result

         print(f"[AGENT_EXEC] Invoking tool handler '{tool_name}' for task {task_id} (User: {user_id})...")
         try:
              # Tool handlers MUST now accept user_id
              tool_result_main = await tool_handler(tool_input)
         except Exception as e: error_msg = f"Error executing '{tool_name}': {e}"; print(f"[ERROR] {error_msg}"); all_tool_results.append({"tool_name": tool_name, "tool_result": error_msg, "status": "error"}); previous_tool_result = error_msg; continue

         # Handle Approval Flow
         if isinstance(tool_result_main, dict) and tool_result_main.get("action") == "approve":
              print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) requires approval for tool '{tool_name}'.")
              approval_data = tool_result_main.get("tool_call", {})
              await task_queue.set_task_approval_pending(task_id, approval_data) # WS broadcast handled by queue
              return APPROVAL_PENDING_SIGNAL

         # Store Normal Result
         else:
              tool_result = tool_result_main.get("tool_result", tool_result_main) if isinstance(tool_result_main, dict) else tool_result_main
              print(f"[AGENT_EXEC] Tool '{tool_name}' executed. Storing result for task {task_id}.")
              previous_tool_result = tool_result
              all_tool_results.append({"tool_name": tool_name, "tool_result": tool_result, "status": "success"})

    # Final Reflection/Summarization (Remains same, uses results)
    if not all_tool_results:
         print(f"[AGENT_EXEC] No successful tool calls for task {task_id}."); return "No specific actions taken."
    print(f"[AGENT_EXEC] Task {task_id} requires reflection/summarization...")
    final_result_str = "No final result generated."
    try:
        # Handle inbox summarization... (remains same)
        # Handle general reflection... (remains same)
        if len(all_tool_results) == 1 and all_tool_results[0].get("tool_name") == "search_inbox":
             # Inbox summarizer logic...
             pass # Replace with actual logic if needed
        else:
             final_result_str = reflection_runnable.invoke({"tool_results": all_tool_results})
        print(f"[AGENT_EXEC] Reflection/Summarization finished for task {task_id}.")
    except Exception as e: final_result_str = f"Error generating final result: {e}"; print(f"[ERROR] {final_result_str}")

    return final_result_str


# --- FastAPI Application Setup ---
print(f"[FASTAPI] {datetime.now()}: Initializing FastAPI app...")
app = FastAPI( title="Sentient API", docs_url="/docs", redoc_url=None )
print(f"[FASTAPI] {datetime.now()}: FastAPI app initialized.")

# CORS Middleware (Allow Electron frontend)
print(f"[FASTAPI] {datetime.now()}: Adding CORS middleware...")
app.add_middleware(
    CORSMiddleware, allow_origins=["app://.", "http://localhost:3000", "http://localhost"], # Specific origins
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
print(f"[FASTAPI] {datetime.now()}: CORS middleware added.")


# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    """Handles application startup procedures."""
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application startup event triggered.")

    # --- Load STT/TTS Models --- (Moved here from global scope)
    global stt_model, tts_model
    print("[FASTAPI_LIFECYCLE] Loading STT model...")
    try:
        stt_model = FasterWhisperSTT(model_size="base", device="cpu", compute_type="int8")
        print("[FASTAPI_LIFECYCLE] STT model loaded.")
    except Exception as e: print(f"[ERROR] Failed to load STT model: {e}")

    print("[FASTAPI_LIFECYCLE] Loading TTS model...")
    try:
        tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
        print("[FASTAPI_LIFECYCLE] TTS model loaded.")
    except Exception as e: print(f"[ERROR] FATAL: Could not load TTS model: {e}"); exit(1) # Exit if TTS fails

    # Load tasks and memory operations (assuming global storage for now)
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Loading tasks from storage...")
    await task_queue.load_tasks() # TODO: Needs user scoping if tasks stored per user
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Loading memory operations from storage...")
    await memory_backend.memory_queue.load_operations() # TODO: Needs user scoping

    # Start background processors
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Creating background task processors...")
    asyncio.create_task(process_queue())
    asyncio.create_task(process_memory_operations())
    asyncio.create_task(cleanup_tasks_periodically())

    # Initialize context engines (needs user context now)
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Context engine initialization deferred (needs user context).")
    # TODO: Context engines need to be initialized per-user or handle requests dynamically based on user_id

    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application shutdown event triggered.")
    # Save tasks and memory operations (global queues for now)
    await task_queue.save_tasks()
    await memory_backend.memory_queue.save_operations()
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Tasks and memory operations saved.")


# --- Pydantic Models (user_id removed where applicable) ---
class Message(BaseModel):
    input: str
    pricing: str
    credits: int

class ElaboratorMessage(BaseModel):
    input: str
    purpose: str

class EncryptionRequest(BaseModel): data: str
class DecryptionRequest(BaseModel): encrypted_data: str

# Requests needing user_id implicitly via token
class ReferrerStatusRequest(BaseModel): referrer_status: bool # user_id from token
class BetaUserStatusRequest(BaseModel): beta_user_status: bool # user_id from token
class SetReferrerRequest(BaseModel): referral_code: str # user_id from token
class DeleteSubgraphRequest(BaseModel): source: str # user_id from token
class GraphRequest(BaseModel): information: str # user_id from token
class GraphRAGRequest(BaseModel): query: str # user_id from token
class RedditURL(BaseModel): url: str # user_id from token (for potential user-specific scraping config/limits)
class TwitterURL(BaseModel): url: str # user_id from token
class LinkedInURL(BaseModel): url: str # user_id from token
class SetDataSourceEnabledRequest(BaseModel): source: str; enabled: bool # user_id from token
class CreateTaskRequest(BaseModel): description: str # user_id from token
class UpdateTaskRequest(BaseModel): task_id: str; description: str; priority: int # user_id from token
class DeleteTaskRequest(BaseModel): task_id: str # user_id from token
class GetShortTermMemoriesRequest(BaseModel): category: str; limit: int # user_id from token
class UpdateUserDataRequest(BaseModel): data: Dict[str, Any] # user_id from token
class AddUserDataRequest(BaseModel): data: Dict[str, Any] # user_id from token
class AddMemoryRequest(BaseModel): text: str; category: str; retention_days: int # user_id from token
class UpdateMemoryRequest(BaseModel): id: int; text: str; category: str; retention_days: int # user_id from token
class DeleteMemoryRequest(BaseModel): id: int; category: str # user_id from token
class TaskIdRequest(BaseModel): task_id: str # user_id needed for action endpoints

# Responses remain the same
class TaskApprovalDataResponse(BaseModel): approval_data: Optional[Dict[str, Any]] = None
class ApproveTaskResponse(BaseModel): message: str; result: Any


# --- API Endpoints (Protected with Auth Dependency) ---

@app.get("/", status_code=200)
async def main_root(): # Renamed to avoid conflict with app instance
    return {"message": "Sentient API"}

# Changed to POST, protected
@app.post("/get-history", status_code=200)
async def get_history(user_id: str = Depends(auth.get_current_user)):
    """Retrieves chat history for the authenticated user."""
    print(f"[ENDPOINT /get-history] {datetime.now()}: Called by user {user_id}.")
    try:
        messages = await get_chat_history_messages(user_id)
        async with db_lock: # Get active chat ID for this user
            chatsDb = await load_db(user_id)
            current_active_chat_id = chatsDb.get("active_chat_id", 0)
        return JSONResponse(status_code=200, content={"messages": messages, "activeChatId": current_active_chat_id})
    except Exception as e: print(f"[ERROR] /get-history for {user_id}: {e}"); raise HTTPException(500, "Failed history retrieval.")

# Protected
@app.post("/clear-chat-history", status_code=200)
async def clear_chat_history(user_id: str = Depends(auth.get_current_user)):
    """Clears chat history for the authenticated user."""
    print(f"[ENDPOINT /clear-chat-history] {datetime.now()}: Called by user {user_id}.")
    async with db_lock:
        try:
            chatsDb = initial_db.copy() # Reset to initial state
            await save_db(user_id, chatsDb) # Save for the specific user
            print(f"[ENDPOINT /clear-chat-history] User {user_id} - Chat DB reset and saved.")
            # TODO: Clear user-specific in-memory history components if they exist
            return JSONResponse(status_code=200, content={"message": "Chat history cleared", "activeChatId": 0})
        except Exception as e: print(f"[ERROR] /clear-chat-history for {user_id}: {e}"); raise HTTPException(500, "Failed clearing history.")

# Protected
@app.post("/chat", status_code=200)
async def chat(message: Message, user_id: str = Depends(auth.get_current_user)):
    """Handles incoming chat messages for the authenticated user."""
    endpoint_start_time = time.time()
    print(f"[ENDPOINT /chat] {datetime.now()}: Called by user {user_id}. Input: '{message.input[:50]}...'")

    # Ensure global variables are accessible (runnables, models)
    global chat_runnable, agent_runnable, unified_classification_runnable, memory_backend, task_queue
    global priority_runnable, internet_query_reframe_runnable, internet_summary_runnable
    # Other runnables used indirectly...

    try:
        # --- Load User Profile ---
        user_profile_data = load_user_profile(user_id) # Load user's profile
        if not user_profile_data or "userData" not in user_profile_data:
            raise HTTPException(status_code=500, detail="User profile could not be loaded.")
        username = user_profile_data.get("userData", {}).get("personalInfo", {}).get("name", "User")
        personality_setting = user_profile_data.get("userData", {}).get("personality", "Default helpful assistant")
        print(f"[ENDPOINT /chat] User {user_id} - Profile loaded: Name='{username}'")

        # --- Determine Active Chat ID ---
        await get_chat_history_messages(user_id) # Ensure active chat exists for user
        async with db_lock: chatsDb = await load_db(user_id); active_chat_id = chatsDb.get("active_chat_id", 0)
        if active_chat_id == 0: raise HTTPException(status_code=500, detail="Could not determine active chat.")
        print(f"[ENDPOINT /chat] User {user_id} - Active chat ID: {active_chat_id}")

        # --- Ensure Runnables use Correct History (Still global, needs user-specific history) ---
        # TODO: This is a major limitation. History needs to be scoped per user.
        # For now, it uses the shared global history object.
        current_chat_history = get_chat_history()
        # chat_runnable = get_chat_runnable(current_chat_history) # Assuming these handle context internally for now
        # agent_runnable = get_agent_runnable(current_chat_history)
        # unified_classification_runnable = get_unified_classification_runnable(current_chat_history)

        # --- Unified Classification ---
        print(f"[ENDPOINT /chat] User {user_id} - Classifying input...")
        unified_output = unified_classification_runnable.invoke({"query": message.input})
        category = unified_output.get("category", "chat"); use_personal_context = unified_output.get("use_personal_context", False)
        internet = unified_output.get("internet", "None"); transformed_input = unified_output.get("transformed_input", message.input)
        print(f"Classification: Cat='{category}', Personal='{use_personal_context}', Internet='{internet}'")

        pricing_plan = message.pricing; credits = message.credits

        # --- Streaming Response Generator ---
        async def response_generator():
            stream_start_time = time.time()
            print(f"[STREAM /chat] User {user_id} - Starting stream for chat {active_chat_id}.")
            memory_used, agents_used, internet_used, pro_used = False, False, False, False
            user_context, internet_context, note = None, None, ""

            # 1. Add User Message to DB (Visible)
            user_msg_id = await add_message_to_db(user_id, active_chat_id, message.input, is_user=True, is_visible=True)
            if not user_msg_id: print(f"[ERROR] Failed to add user message for {user_id}, chat {active_chat_id}"); yield json.dumps({"type":"error", "message":"Save failed"})+"\n"; return

            # 2. Yield User Message Confirmation
            user_msg_timestamp = datetime.now(timezone.utc).isoformat()
            yield json.dumps({"type": "userMessage", "id": user_msg_id, "message": message.input, "timestamp": user_msg_timestamp}) + "\n"; await asyncio.sleep(0.01)

            # 3. Prepare Assistant Message Structure
            assistant_msg_id_ts = str(int(time.time() * 1000))
            assistant_msg = {"id": assistant_msg_id_ts, "message": "", "isUser": False, "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "timestamp": datetime.now(timezone.utc).isoformat(), "isVisible": True }

            # --- Handle Agent Category (Task Creation) ---
            if category == "agent":
                agents_used = True
                assistant_msg["agentsUsed"] = True
                print(f"[STREAM /chat] User {user_id} - Input classified as agent task.")
                priority_response = priority_runnable.invoke({"task_description": transformed_input})
                priority = priority_response.get("priority", 3)
                print(f"Adding agent task for user {user_id} (Priority: {priority})...")
                await task_queue.add_task( # Task queue needs user_id
                    user_id=user_id, # Pass user_id
                    chat_id=active_chat_id, description=transformed_input, priority=priority,
                    username=username, personality=personality_setting,
                    use_personal_context=use_personal_context, internet=internet
                )
                print("Agent task added.")
                assistant_msg["message"] = "Okay, I'll get right on that."
                await add_message_to_db(user_id, active_chat_id, transformed_input, is_user=True, is_visible=False) # Hidden user prompt
                await add_message_to_db(user_id, active_chat_id, assistant_msg["message"], is_user=False, is_visible=True, agentsUsed=True, task=transformed_input) # Visible confirmation
                # Yield final message directly
                yield json.dumps({ "type": "assistantMessage", "messageId": assistant_msg["id"], "message": assistant_msg["message"], "memoryUsed": False, "agentsUsed": True, "internetUsed": False, "done": True, "proUsed": False }) + "\n"
                return # End stream for agent task

            # --- Handle Memory/Context Retrieval ---
            if category == "memory" or use_personal_context:
                memory_used = True; assistant_msg["memoryUsed"] = True
                yield json.dumps({"type": "intermediary", "message": "Checking context...", "id": assistant_msg_id_ts}) + "\n"
                print(f"[STREAM /chat] User {user_id} - Retrieving memory context...")
                try:
                    # Pass user_id to memory backend
                    user_context = await memory_backend.retrieve_memory(user_id, transformed_input)
                    if user_context: print(f"Retrieved user context len: {len(str(user_context))}")
                    else: print("No relevant memories found.")
                except Exception as e: print(f"[ERROR] Memory retrieval error for {user_id}: {e}"); user_context = f"Error: {e}"

                if category == "memory": # Queue update only if explicitly memory category
                    if pricing_plan == "free" and credits <= 0:
                        note += " (Memory update skipped: Pro/Credits needed)"
                        print(f"[STREAM /chat] User {user_id} - Free plan credits exhausted. Skipping memory update.")
                    else:
                        pro_used = True # Memory update is pro use
                        print(f"[STREAM /chat] User {user_id} - Queueing memory update operation...")
                        # Run in background
                        asyncio.create_task(memory_backend.add_operation(user_id, transformed_input))

            # --- Handle Internet Search ---
            if internet and internet != "None":
                internet_used = True; assistant_msg["internetUsed"] = True
                if pricing_plan == "free" and credits <= 0:
                    note += " (Internet search skipped: Pro/Credits needed)"
                    print(f"[STREAM /chat] User {user_id} - Free plan credits exhausted. Skipping internet search.")
                else:
                    pro_used = True # Internet search is pro use
                    yield json.dumps({"type": "intermediary", "message": "Searching internet...", "id": assistant_msg_id_ts}) + "\n"
                    print(f"[STREAM /chat] User {user_id} - Performing internet search...")
                    try:
                        # ... (internet search logic remains same) ...
                        reframed_query = get_reframed_internet_query(internet_query_reframe_runnable, transformed_input)
                        search_results = get_search_results(reframed_query)
                        internet_context = get_search_summary(internet_summary_runnable, search_results)
                        print(f"Internet search summary len: {len(str(internet_context)) if internet_context else 0}")
                    except Exception as e: print(f"[ERROR] Internet search error for {user_id}: {e}"); internet_context = f"Error: {e}"


            # --- Generate Chat/Memory Response ---
            if category in ["chat", "memory"]:
                yield json.dumps({"type": "intermediary", "message": "Thinking...", "id": assistant_msg_id_ts}) + "\n"
                full_response = ""
                try:
                    async for token in generate_streaming_response(
                        chat_runnable, # Still global runnable
                        inputs={ "query": transformed_input, "user_context": user_context, "internet_context": internet_context, "name": username, "personality": personality_setting },
                        stream=True
                    ):
                        if isinstance(token, str):
                             full_response += token
                             yield json.dumps({"type": "assistantStream", "token": token, "done": False, "messageId": assistant_msg["id"]}) + "\n"
                        await asyncio.sleep(0.01) # Small delay between tokens

                    # Final stream packet
                    final_message = full_response + ("\n\n" + note if note else "")
                    assistant_msg["message"] = final_message
                    yield json.dumps({
                        "type": "assistantStream", "token": "\n\n" + note if note else "", "done": True,
                        "memoryUsed": memory_used, "agentsUsed": agents_used, "internetUsed": internet_used,
                        "proUsed": pro_used, "messageId": assistant_msg["id"]
                    }) + "\n"
                    # Save final message to DB
                    await add_message_to_db(user_id, active_chat_id, final_message, is_user=False, is_visible=True,
                                            memoryUsed=memory_used, agentsUsed=agents_used, internetUsed=internet_used)


                except Exception as e:
                     print(f"[ERROR] Chat generation error for {user_id}: {e}")
                     traceback.print_exc()
                     error_message = "Sorry, I encountered an error generating the response."
                     assistant_msg["message"] = error_message
                     yield json.dumps({"type": "assistantStream", "token": error_message, "done": True, "error": True, "messageId": assistant_msg["id"]}) + "\n"
                     await add_message_to_db(user_id, active_chat_id, error_message, is_user=False, is_visible=True, error=True)


            stream_duration = time.time() - stream_start_time
            print(f"[STREAM /chat] User {user_id} - Stream finished. Duration: {stream_duration:.2f}s")

        # Return the streaming response
        print(f"[ENDPOINT /chat] User {user_id} - Returning StreamingResponse.")
        return StreamingResponse(response_generator(), media_type="application/x-ndjson")

    except HTTPException as http_exc: raise http_exc # Re-raise validation/auth errors
    except Exception as e: print(f"[ERROR] Unexpected error in /chat for user {user_id}: {e}"); traceback.print_exc(); raise HTTPException(500, "Internal server error during chat processing.")
    finally: print(f"[ENDPOINT /chat] User {user_id} - Finished. Duration: {time.time() - endpoint_start_time:.2f}s")


# Elaborator endpoint (simple, maybe doesn't need strict auth?)
@app.post("/elaborator", status_code=200)
async def elaborate(message: ElaboratorMessage): # Consider adding Depends(auth.get_current_user) if needed
    # ... (elaboration logic remains same) ...
    print(f"[ENDPOINT /elaborator] {datetime.now()}: Called.")
    try:
         elaborator_runnable = get_tool_runnable( elaborator_system_prompt_template, elaborator_user_prompt_template, None, ["query", "purpose"] )
         output = elaborator_runnable.invoke({"query": message.input, "purpose": message.purpose})
         return JSONResponse(status_code=200, content={"message": output})
    except Exception as e: print(f"[ERROR] /elaborator: {e}"); raise HTTPException(500,"Elaboration failed")


# --- Tool Handlers (Updated to accept user_id) ---
@register_tool("gmail")
async def gmail_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id") # Get user_id passed from execute_agent_task
    if not user_id: return {"status": "failure", "error": "User context missing in tool call"}
    print(f"[TOOL HANDLER gmail] Called for user {user_id}")
    # ... (rest of gmail logic, using user_id if needed for context/auth) ...
    try:
         user_profile = load_user_profile(user_id)
         username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
         tool_runnable = get_tool_runnable(gmail_agent_system_prompt_template, gmail_agent_user_prompt_template, gmail_agent_required_format, ["query", "username", "previous_tool_response"])
         tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "username": username, "previous_tool_response": tool_call_input.get("previous_tool_response") })
         # Add robust JSON parsing
         try: tool_call_dict = json.loads(tool_call_str)
         except json.JSONDecodeError: tool_call_dict = {"tool_name": "error", "task_instruction": f"Invalid JSON from LLM: {tool_call_str}"}
         actual_tool_name = tool_call_dict.get("tool_name")
         print(f"Gmail action: {actual_tool_name}")
         if actual_tool_name in ["send_email", "reply_email"]:
              return {"action": "approve", "tool_call": tool_call_dict}
         else:
              # Execute directly, passing user_id if needed by parse_and_execute...
              tool_result = await parse_and_execute_tool_calls(user_id, json.dumps(tool_call_dict)) # Pass user_id
              return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] Gmail Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}

@register_tool("gdrive")
async def drive_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id"); # ... (Check user_id) ...
    print(f"[TOOL HANDLER gdrive] Called for user {user_id}")
    # ... (GDrive logic) ...
    try:
         tool_runnable = get_tool_runnable( gdrive_agent_system_prompt_template, gdrive_agent_user_prompt_template, gdrive_agent_required_format, ["query", "previous_tool_response"] )
         tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "previous_tool_response": tool_call_input.get("previous_tool_response") })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Pass user_id
         return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] GDrive Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}

@register_tool("gdocs")
async def gdoc_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id"); # ... (Check user_id) ...
    print(f"[TOOL HANDLER gdocs] Called for user {user_id}")
    # ... (GDocs logic) ...
    try:
         tool_runnable = get_tool_runnable( gdocs_agent_system_prompt_template, gdocs_agent_user_prompt_template, gdocs_agent_required_format, ["query", "previous_tool_response"], )
         tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "previous_tool_response": tool_call_input.get("previous_tool_response"), })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Pass user_id
         return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] GDocs Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}

@register_tool("gsheets")
async def gsheet_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id"); # ... (Check user_id) ...
    print(f"[TOOL HANDLER gsheets] Called for user {user_id}")
    # ... (GSheets logic) ...
    try:
         tool_runnable = get_tool_runnable( gsheets_agent_system_prompt_template, gsheets_agent_user_prompt_template, gsheets_agent_required_format, ["query", "previous_tool_response"], )
         tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "previous_tool_response": tool_call_input.get("previous_tool_response"), })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Pass user_id
         return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] GSheets Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}

@register_tool("gslides")
async def gslides_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id"); # ... (Check user_id) ...
    print(f"[TOOL HANDLER gslides] Called for user {user_id}")
    # ... (GSlides logic) ...
    try:
        user_profile = load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
        tool_runnable = get_tool_runnable( gslides_agent_system_prompt_template, gslides_agent_user_prompt_template, gslides_agent_required_format, ["query", "user_name", "previous_tool_response"], )
        tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "user_name": username, "previous_tool_response": tool_call_input.get("previous_tool_response"), })
        tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Pass user_id
        return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] GSlides Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}


@register_tool("gcalendar")
async def gcalendar_tool(tool_call_input: dict) -> Dict[str, Any]:
    user_id = tool_call_input.get("user_id"); # ... (Check user_id) ...
    print(f"[TOOL HANDLER gcalendar] Called for user {user_id}")
    # ... (GCalendar logic) ...
    try:
        current_time_iso = datetime.now(timezone.utc).isoformat()
        try: local_timezone_key = str(get_localzone())
        except: local_timezone_key = "UTC"
        tool_runnable = get_tool_runnable( gcalendar_agent_system_prompt_template, gcalendar_agent_user_prompt_template, gcalendar_agent_required_format, ["query", "current_time", "timezone", "previous_tool_response"], )
        tool_call_str = tool_runnable.invoke({ "query": str(tool_call_input["input"]), "current_time": current_time_iso, "timezone": local_timezone_key, "previous_tool_response": tool_call_input.get("previous_tool_response"), })
        tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Pass user_id
        return {"tool_result": tool_result}
    except Exception as e: print(f"[ERROR] GCalendar Tool for {user_id}: {e}"); return {"status": "failure", "error": str(e)}


# --- Utils Endpoints (Protected, user_id from token) ---

@app.post("/get-role") # Keep POST as it modifies state implicitly (updates checkin)
async def get_role(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-role] Called by user {user_id}.")
    try:
        token = get_management_token(); # This helper likely doesn't need user_id
        if not token: raise HTTPException(500, "Management token unavailable.")
        roles_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client: roles_response = await client.get(roles_url, headers=headers)
        if roles_response.status_code != 200: raise HTTPException(roles_response.status_code, f"Auth0 API Error: {roles_response.text}")
        roles = roles_response.json()
        user_role = roles[0]['name'].lower() if roles else "free" # Default to free
        print(f"User {user_id} role: {user_role}")
        return JSONResponse(status_code=200, content={"role": user_role})
    except Exception as e: print(f"[ERROR] /get-role for {user_id}: {e}"); raise HTTPException(500, "Failed role retrieval.")

@app.post("/get-beta-user-status") # Keep POST
async def get_beta_user_status(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-beta-user-status] Called by user {user_id}.")
    try:
        token = get_management_token(); # ... (check token) ...
        user_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client: response = await client.get(user_url, headers=headers)
        if response.status_code != 200: raise HTTPException(response.status_code, f"Auth0 API Error: {response.text}")
        user_data = response.json()
        status_val = user_data.get("app_metadata", {}).get("betaUser")
        status_bool = str(status_val).lower() == 'true' if status_val is not None else False
        print(f"User {user_id} beta status: {status_bool}")
        return JSONResponse(status_code=200, content={"betaUserStatus": status_bool})
    except Exception as e: print(f"[ERROR] /get-beta-user-status for {user_id}: {e}"); raise HTTPException(500, "Failed status retrieval.")


@app.post("/get-referral-code") # Keep POST
async def get_referral_code(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-referral-code] Called by user {user_id}.")
    try:
        token = get_management_token(); # ... (check token) ...
        url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client: response = await client.get(url, headers=headers)
        if response.status_code != 200: raise HTTPException(response.status_code, f"Auth0 API Error: {response.text}")
        user_data = response.json()
        referral_code = user_data.get("app_metadata", {}).get("referralCode")
        if not referral_code: raise HTTPException(404, "Referral code not found.")
        print(f"User {user_id} referral code found.")
        return JSONResponse(status_code=200, content={"referralCode": referral_code})
    except Exception as e: print(f"[ERROR] /get-referral-code for {user_id}: {e}"); raise HTTPException(500, "Failed code retrieval.")

@app.post("/get-referrer-status") # Keep POST
async def get_referrer_status(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-referrer-status] Called by user {user_id}.")
    try:
        token = get_management_token(); # ... (check token) ...
        url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client: response = await client.get(url, headers=headers)
        if response.status_code != 200: raise HTTPException(response.status_code, f"Auth0 API Error: {response.text}")
        user_data = response.json()
        status_val = user_data.get("app_metadata", {}).get("referrer")
        status_bool = str(status_val).lower() == 'true' if status_val is not None else False
        print(f"User {user_id} referrer status: {status_bool}")
        return JSONResponse(status_code=200, content={"referrerStatus": status_bool})
    except Exception as e: print(f"[ERROR] /get-referrer-status for {user_id}: {e}"); raise HTTPException(500, "Failed status retrieval.")

@app.post("/get-user-and-set-referrer-status")
async def get_user_and_set_referrer_status(request: SetReferrerRequest, user_id_making_request: str = Depends(auth.get_current_user)):
    """Sets the user found by referral code as a referrer."""
    referral_code = request.referral_code
    print(f"[ENDPOINT /get-user-and-set-referrer-status] Called by user {user_id_making_request} with code {referral_code}.")
    try:
        token = get_management_token(); # ... (check token) ...
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        # Search for user by code
        search_query = f'app_metadata.referralCode:"{referral_code}"'
        search_url = f"https://{AUTH0_DOMAIN}/api/v2/users"
        params = {'q': search_query, 'search_engine': 'v3'}
        async with httpx.AsyncClient() as client: search_response = await client.get(search_url, headers=headers, params=params)
        if search_response.status_code != 200: raise HTTPException(search_response.status_code, f"Auth0 Search Error: {search_response.text}")
        users = search_response.json()
        if not users: raise HTTPException(404, f"No user found with referral code: {referral_code}")
        user_to_set_id = users[0].get("user_id");
        if not user_to_set_id: raise HTTPException(500, "Found user but ID missing.")
        print(f"Found user {user_to_set_id} matching code {referral_code}.")

        # Set referrer status for found user
        update_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_to_set_id}"
        update_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        update_payload = {"app_metadata": {"referrer": True}}
        async with httpx.AsyncClient() as client: set_status_response = await client.patch(update_url, headers=update_headers, json=update_payload)
        if set_status_response.status_code != 200: raise HTTPException(set_status_response.status_code, f"Auth0 Update Error: {set_status_response.text}")
        print(f"Referrer status set for user {user_to_set_id}.")
        return JSONResponse(status_code=200, content={"message": "Referrer status updated successfully."})
    except Exception as e: print(f"[ERROR] /get-user-and-set-referrer-status: {e}"); raise HTTPException(500, "Failed setting referrer.")

@app.post("/get-user-and-invert-beta-user-status")
async def get_user_and_invert_beta_user_status(user_id: str = Depends(auth.get_current_user)):
    """Gets current beta status for authenticated user and inverts it."""
    print(f"[ENDPOINT /get-user-and-invert-beta-user-status] Called by user {user_id}.")
    try:
        token = get_management_token(); # ... (check token) ...
        # Get current status
        get_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        get_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client: get_response = await client.get(get_url, headers=get_headers)
        if get_response.status_code != 200: raise HTTPException(get_response.status_code, f"Auth0 Get Error: {get_response.text}")
        user_data = get_response.json()
        current_status_val = user_data.get("app_metadata", {}).get("betaUser")
        current_bool = str(current_status_val).lower() == 'true' if current_status_val is not None else False
        inverted_status = not current_bool
        print(f"User {user_id} current beta: {current_bool}. Setting to: {inverted_status}")
        # Set inverted status
        set_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        set_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        set_payload = {"app_metadata": {"betaUser": inverted_status}}
        async with httpx.AsyncClient() as client: set_response = await client.patch(set_url, headers=set_headers, json=set_payload)
        if set_response.status_code != 200: raise HTTPException(set_response.status_code, f"Auth0 Set Error: {set_response.text}")
        print(f"Beta status inverted successfully for user {user_id}.")
        return JSONResponse(status_code=200, content={"message": "Beta user status inverted successfully."})
    except Exception as e: print(f"[ERROR] /get-user-and-invert-beta-user-status for {user_id}: {e}"); raise HTTPException(500, "Failed inverting status.")

# Encryption/Decryption endpoints (Likely public or use different auth)
@app.post("/encrypt")
async def encrypt_data(request: EncryptionRequest):
    # ... (encryption logic) ...
    try: encrypted_data = aes_encrypt(request.data); return JSONResponse({"encrypted_data": encrypted_data})
    except Exception as e: print(f"[ERROR] /encrypt: {e}"); raise HTTPException(500, "Encryption failed")

@app.post("/decrypt")
async def decrypt_data(request: DecryptionRequest):
    # ... (decryption logic) ...
    try: decrypted_data = aes_decrypt(request.encrypted_data); return JSONResponse({"decrypted_data": decrypted_data})
    except ValueError: raise HTTPException(400, "Decryption failed: Invalid data/key")
    except Exception as e: print(f"[ERROR] /decrypt: {e}"); raise HTTPException(500, "Decryption failed")


# --- Scraper Endpoints (Protected) ---
@app.post("/scrape-linkedin")
async def scrape_linkedin(profile: LinkedInURL, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /scrape-linkedin] Called by user {user_id} for URL: {profile.url}")
    try:
        # Assuming scrape_linkedin_profile doesn't need user_id directly, but auth protects the endpoint
        linkedin_profile = await asyncio.to_thread(scrape_linkedin_profile, profile.url)
        return JSONResponse({"profile": linkedin_profile})
    except Exception as e: print(f"[ERROR] /scrape-linkedin for {user_id}: {e}"); raise HTTPException(500, "Scraping failed")

@app.post("/scrape-reddit")
async def scrape_reddit(reddit_url: RedditURL, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /scrape-reddit] Called by user {user_id} for URL: {reddit_url.url}")
    try:
        subreddits = await asyncio.to_thread(reddit_scraper, reddit_url.url)
        if not subreddits: return JSONResponse({"topics": []})
        response = await asyncio.to_thread(reddit_runnable.invoke, {"subreddits": subreddits})
        topics = response if isinstance(response, list) else response.get('topics', []) if isinstance(response, dict) else [] # Basic parsing
        return JSONResponse({"topics": topics})
    except Exception as e: print(f"[ERROR] /scrape-reddit for {user_id}: {e}"); raise HTTPException(500, "Scraping/analysis failed")

@app.post("/scrape-twitter")
async def scrape_twitter(twitter_url: TwitterURL, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /scrape-twitter] Called by user {user_id} for URL: {twitter_url.url}")
    try:
        tweets = await asyncio.to_thread(scrape_twitter_data, twitter_url.url, 20)
        if not tweets: return JSONResponse({"topics": []})
        response = await asyncio.to_thread(twitter_runnable.invoke, {"tweets": tweets})
        topics = response if isinstance(response, list) else response.get('topics', []) if isinstance(response, dict) else []
        return JSONResponse({"topics": topics})
    except Exception as e: print(f"[ERROR] /scrape-twitter for {user_id}: {e}"); raise HTTPException(500, "Scraping/analysis failed")

# --- Auth Endpoint ---
@app.post("/authenticate-google") # Keep POST
async def authenticate_google(user_id: str = Depends(auth.get_current_user)):
    """Checks/refreshes Google credentials for the authenticated user."""
    print(f"[ENDPOINT /authenticate-google] Called by user {user_id}.")
    # TODO: Implement user-specific token storage (e.g., using user_id in filename or DB)
    token_path = f"server/token_{user_id}.pickle" # Example user-specific path
    creds = None
    try:
        if os.path.exists(token_path):
            with open(token_path, "rb") as token: creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                 print(f"Refreshing Google token for user {user_id}...")
                 creds.refresh(Request())
            else:
                 # This needs modification for non-interactive flow on server
                 print(f"[WARN] Google token invalid/missing for user {user_id}, and interactive flow needed.")
                 # flow = InstalledAppFlow.from_client_config(CREDENTIALS_DICT, SCOPES)
                 # creds = flow.run_local_server(port=0) # This won't work on server
                 raise HTTPException(status_code=401, detail=f"Google authentication required for user {user_id}.")
            with open(token_path, "wb") as token: pickle.dump(creds, token)
            print(f"Google token refreshed/saved for user {user_id}.")
        else:
             print(f"Valid Google token found for user {user_id}.")
        return JSONResponse({"success": True})
    except HTTPException as http_exc: raise http_exc
    except Exception as e: print(f"[ERROR] Google auth for {user_id}: {e}"); raise HTTPException(500, f"Google auth failed: {e}")


# --- Memory Endpoints (Protected) ---
@app.post("/graphrag")
async def graphrag(request: GraphRAGRequest, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /graphrag] Called by user {user_id} for query: '{request.query[:50]}...'")
    try:
        if not all([graph_driver, embed_model, text_conversion_runnable, query_classification_runnable]):
             raise HTTPException(503, "GraphRAG dependencies unavailable.")
        # Run sync query in threadpool, passing user_id
        context = await asyncio.to_thread(
             query_user_profile, user_id, request.query, graph_driver, embed_model, # Pass user_id
             text_conversion_runnable, query_classification_runnable
        )
        return JSONResponse({"context": context or "No relevant context found."})
    except Exception as e: print(f"[ERROR] /graphrag for {user_id}: {e}"); raise HTTPException(500, "GraphRAG failed")

@app.post("/initiate-long-term-memories")
async def create_graph(request_data: Optional[Dict] = None, user_id: str = Depends(auth.get_current_user)): # Accept optional body
    """Creates/resets knowledge graph for the authenticated user."""
    clear_graph_flag = request_data.get("clear_graph", False) if request_data else False
    action = "Resetting" if clear_graph_flag else "Initiating"
    print(f"[ENDPOINT /initiate-long-term-memories] {action} graph for user {user_id}.")
    input_dir = "server/input" # TODO: Input dir might need to be user-specific?
    loop = asyncio.get_event_loop()
    try:
        user_profile = load_user_profile(user_id); username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id) # Use user_id if name missing

        if not all([graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable]):
            raise HTTPException(503, "Graph dependencies unavailable.")

        # Read user-specific input files (adjust read_files logic)
        # For now, assume global input dir, but graph build uses username scope
        def read_files_sync(): # Simplified for example
            # TODO: Implement user-specific file reading if needed
             return [{"text": "Sample content for user "+username, "source": "sample.txt"}]
        extracted_texts = await loop.run_in_executor(None, read_files_sync)

        # Clear graph if requested (use user_id scope if possible in query)
        if clear_graph_flag:
             print(f"Clearing graph for user {user_id}...")
             try:
                 def clear_neo4j_user_graph(driver, uid): # Modify query if graph is user-scoped
                      with driver.session(database="neo4j") as session:
                           # Example: MATCH (n {userId: $uid}) DETACH DELETE n
                           session.execute_write(lambda tx: tx.run("MATCH (n) DETACH DELETE n")) # Simplified: Clears whole graph
                 await loop.run_in_executor(None, clear_neo4j_user_graph, graph_driver, user_id)
             except Exception as clear_e: raise HTTPException(500, f"Failed to clear graph: {clear_e}")

        # Build Graph (pass username which acts as user scope here)
        if extracted_texts:
             print(f"Building graph for user {username} from {len(extracted_texts)} document(s)...")
             await loop.run_in_executor( None, build_initial_knowledge_graph, username, extracted_texts, graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable )
             print(f"Graph build process completed for user {username}.")
             return JSONResponse({"message": f"Graph created/updated for user {username}."})
        else:
             return JSONResponse({"message": "No input documents found. Graph not modified."})

    except Exception as e: print(f"[ERROR] /initiate-long-term-memories for {user_id}: {e}"); raise HTTPException(500, "Graph operation failed")


@app.post("/delete-subgraph")
async def delete_subgraph(request: DeleteSubgraphRequest, user_id: str = Depends(auth.get_current_user)):
    source_key = request.source
    print(f"[ENDPOINT /delete-subgraph] Called by user {user_id} for source: {source_key}")
    loop = asyncio.get_event_loop()
    try:
        user_profile = load_user_profile(user_id); username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id).lower()
        # Map source key to filename (potentially user-specific)
        SOURCES = {
            "linkedin": f"{username}_linkedin_profile.txt",
            "reddit": f"{username}_reddit_profile.txt",
            "twitter": f"{username}_twitter_profile.txt",
            # Add mappings for personality traits if they were saved as separate files
            "extroversion": f"{username}_extroversion.txt",
            "introversion": f"{username}_introversion.txt",
            "sensing": f"{username}_sensing.txt",
            "intuition": f"{username}_intuition.txt",
            "thinking": f"{username}_thinking.txt",
            "feeling": f"{username}_feeling.txt",
            "judging": f"{username}_judging.txt",
            "perceiving": f"{username}_perceiving.txt",
            # "personality_summary": f"{username}_personality_summary.txt", # If unified file exists
        }
        file_name = SOURCES.get(source_key.lower())
        if not file_name: raise HTTPException(400, f"Invalid source key: {source_key}")
        if not graph_driver: raise HTTPException(503, "Neo4j driver unavailable.")

        # Delete from Neo4j (query might need user scope)
        print(f"Deleting subgraph for user {user_id}, source file '{file_name}'...")
        await loop.run_in_executor(None, delete_source_subgraph, graph_driver, file_name) # Pass user_id if query needs it

        # Delete corresponding file (user-specific path?)
        # input_dir = f"server/input/{user_id}" # Example user-specific dir
        input_dir = "server/input" # Still global for now
        file_path_to_delete = os.path.join(input_dir, file_name)
        def remove_file_sync(path): # Sync file removal
             if os.path.exists(path): 
                 try: 
                    os.remove(path)
                    return True, None 
                 except OSError as e: 
                    return False, str(e)
             else: 
                return False, "File not found"
            
        deleted, error = await loop.run_in_executor(None, remove_file_sync, file_path_to_delete)
        if deleted: print(f"Deleted input file: {file_path_to_delete}")
        else: print(f"[WARN] Could not delete file {file_path_to_delete}: {error}")

        return JSONResponse({"message": f"Subgraph for source '{source_key}' deleted."})
    except Exception as e: print(f"[ERROR] /delete-subgraph for {user_id}: {e}"); raise HTTPException(500, "Subgraph deletion failed")


@app.post("/create-document")
async def create_document(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /create-document] Called by user {user_id}.")
    input_dir = "server/input" # TODO: User-specific?
    loop = asyncio.get_event_loop()
    try:
        db = load_user_profile(user_id).get("userData", {})
        username = db.get("personalInfo", {}).get("name", user_id).lower() # Use lowercase username for files
        # ... (load other profile parts: personality_type, linkedin, reddit, twitter) ...
        personality_type = db.get("personalityType", []) # Load user's data
        structured_linkedin_profile = db.get("linkedInProfile", {})
        reddit_profile = db.get("redditProfile", [])
        twitter_profile = db.get("twitterProfile", [])

        await loop.run_in_executor(None, os.makedirs, input_dir, True) # Ensure dir exists

        tasks = []
        trait_descriptions = []
        # --- Process Personality ---
        if isinstance(personality_type, list): # Check if it's a list
             for trait in personality_type:
                 trait_lower = trait.lower()
                 if trait_lower in PERSONALITY_DESCRIPTIONS:
                      desc = f"{trait}: {PERSONALITY_DESCRIPTIONS[trait_lower]}"; trait_descriptions.append(desc)
                      fname = f"{username}_{trait_lower}.txt"
                      tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, desc, fname, input_dir)) # Use sync helper

        # --- Process Social/LinkedIn ---
        if structured_linkedin_profile:
             li_text = json.dumps(structured_linkedin_profile, indent=2) if isinstance(structured_linkedin_profile, dict) else str(structured_linkedin_profile)
             li_fname = f"{username}_linkedin_profile.txt"
             tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, li_text, li_fname, input_dir))
        # ... (process reddit, twitter similarly) ...
        if reddit_profile:
            rd_text = "User's Reddit Interests: " + ", ".join(reddit_profile if isinstance(reddit_profile, list) else [reddit_profile])
            rd_fname = f"{username}_reddit_profile.txt"
            tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, rd_text, rd_fname, input_dir))
        if twitter_profile:
            tw_text = "User's Twitter Interests: " + ", ".join(twitter_profile if isinstance(twitter_profile, list) else [twitter_profile])
            tw_fname = f"{username}_twitter_profile.txt"
            tasks.append(loop.run_in_executor(None, summarize_and_write_sync, username, tw_text, tw_fname, input_dir))


        results = await asyncio.gather(*tasks, return_exceptions=True)
        created_files = [fname for success, fname in results if success and fname and not isinstance(results, Exception)]
        failed_files = [fname for success, fname in results if not success or isinstance(results, Exception)]

        unified_personality = "\n".join(trait_descriptions)
        print(f"Document creation finished for {user_id}. Created: {len(created_files)}, Failed: {len(failed_files)}")
        return JSONResponse({"message": "Documents processed.", "created_files": created_files, "failed_files": failed_files, "personality": unified_personality})

    except Exception as e: print(f"[ERROR] /create-document for {user_id}: {e}"); raise HTTPException(500, "Document creation failed")

# Helper for create_document threadpool
def summarize_and_write_sync(user, text, filename, input_dir):
    if not text: return False, filename
    try:
        # NOTE: Runnables might not be thread-safe depending on underlying models.
        # Consider using multiprocessing or ensuring thread-safety if issues arise.
        summarized = text_summarizer_runnable.invoke({"user_name": user, "text": text})
        file_path = os.path.join(input_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f: f.write(summarized)
        return True, filename
    except Exception as e: print(f"[ERROR] Summarize/Write sync for {filename}: {e}"); return False, filename


@app.post("/customize-long-term-memories")
async def customize_graph(request: GraphRequest, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /customize-long-term-memories] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        user_profile = load_user_profile(user_id); username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
        if not all([...]): raise HTTPException(503, "Graph dependencies unavailable.") # Check deps

        # Extract facts (needs username)
        points = await loop.run_in_executor(None, fact_extraction_runnable.invoke, {"paragraph": request.information, "username": username})
        if not isinstance(points, list): points = []
        if not points: return JSONResponse({"message": "No facts extracted."})

        # Apply CRUD (needs user_id scope if graph is user-specific)
        tasks = []
        print(f"Applying CRUD for {len(points)} facts for user {user_id}...")
        for point in points:
             tasks.append(loop.run_in_executor(
                 None, crud_graph_operations, user_id, point, graph_driver, embed_model, # Pass user_id
                 query_classification_runnable, information_extraction_runnable,
                 graph_analysis_runnable, graph_decision_runnable, text_description_runnable
             ))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # ... (Process results, count errors) ...
        processed_count = sum(1 for r in results if not isinstance(r, Exception))
        errors = [str(r) for r in results if isinstance(r, Exception)]
        message = f"Graph customized for {processed_count}/{len(points)} facts." + (f" Errors: {len(errors)}" if errors else "")
        return JSONResponse(status_code=200 if not errors else 207, content={"message": message, "errors": errors})

    except Exception as e: print(f"[ERROR] /customize-long-term-memories for {user_id}: {e}"); raise HTTPException(500, "Graph customization failed")


# --- Task Queue Endpoints (Protected) ---
@app.post("/fetch-tasks") # Changed to POST
async def get_tasks(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /fetch-tasks] Called by user {user_id}.")
    try:
        # TODO: Modify TaskQueue to filter tasks by user_id
        tasks = await task_queue.get_tasks_for_user(user_id) # Assumes this method exists
        serializable_tasks = []
        for task in tasks: # Serialize datetime objects
             if isinstance(task.get('created_at'), datetime): task['created_at'] = task['created_at'].isoformat()
             if isinstance(task.get('completed_at'), datetime): task['completed_at'] = task['completed_at'].isoformat()
             serializable_tasks.append(task)
        return JSONResponse({"tasks": serializable_tasks})
    except Exception as e: print(f"[ERROR] /fetch-tasks for {user_id}: {e}"); raise HTTPException(500, "Failed fetching tasks.")

@app.post("/add-task", status_code=201)
async def add_task(task_request: CreateTaskRequest, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /add-task] Called by user {user_id} with desc: '{task_request.description[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        # Determine Active Chat ID for this user
        await get_chat_history_messages(user_id)
        async with db_lock: chatsDb = await load_db(user_id)
        active_chat_id = chatsDb.get("active_chat_id", 0)
        if active_chat_id == 0: 
            raise HTTPException(500, "Could not determine active chat.")

        # Load profile info
        user_profile = load_user_profile(user_id); username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id); personality = user_profile.get("userData", {}).get("personality", "Default")

        # Classify Task Needs & Priority (in threadpool)
        unified_output = await loop.run_in_executor( None, unified_classification_runnable.invoke, {"query": task_request.description} )
        use_personal_context = unified_output.get("use_personal_context", False); internet = unified_output.get("internet", "None")
        try: priority_response = await loop.run_in_executor( None, priority_runnable.invoke, {"task_description": task_request.description} ); priority = priority_response.get("priority", 3)
        except Exception as e: print(f"[WARN] Priority check failed for {user_id}: {e}"); priority = 3

        # Add Task to Queue (passing user_id)
        task_id = await task_queue.add_task( user_id=user_id, chat_id=active_chat_id, description=task_request.description, priority=priority, username=username, personality=personality, use_personal_context=use_personal_context, internet=internet )

        # Add messages to user's chat DB
        await add_message_to_db(user_id, active_chat_id, task_request.description, is_user=True, is_visible=False) # Hidden user prompt
        conf_msg = f"Task added: '{task_request.description[:40]}...'"; await add_message_to_db(user_id, active_chat_id, conf_msg, is_user=False, is_visible=True, agentsUsed=True, task=task_request.description) # Visible confirmation

        # WS broadcast handled by TaskQueue.add_task

        return JSONResponse({"task_id": task_id, "message": "Task added"})
    except Exception as e: print(f"[ERROR] /add-task for {user_id}: {e}"); raise HTTPException(500, "Failed adding task.")

@app.post("/update-task")
async def update_task(update_request: UpdateTaskRequest, user_id: str = Depends(auth.get_current_user)):
    task_id = update_request.task_id; new_desc = update_request.description; new_priority = update_request.priority
    print(f"[ENDPOINT /update-task] Called by user {user_id} for task {task_id}.")
    try:
        # TODO: TaskQueue needs to verify user_id owns the task before updating
        updated_task = await task_queue.update_task(user_id, task_id, new_desc, new_priority) # Pass user_id
        if not updated_task: raise ValueError("Task not found or update unauthorized.")
        # WS broadcast handled by TaskQueue.update_task
        return JSONResponse({"message": "Task updated"})
    except ValueError as e: raise HTTPException(404, str(e)) # 404 if not found/unauthorized
    except Exception as e: print(f"[ERROR] /update-task for {user_id}, task {task_id}: {e}"); raise HTTPException(500, "Failed updating task.")

@app.post("/delete-task")
async def delete_task(delete_request: DeleteTaskRequest, user_id: str = Depends(auth.get_current_user)):
    task_id = delete_request.task_id
    print(f"[ENDPOINT /delete-task] Called by user {user_id} for task {task_id}.")
    try:
        # TODO: TaskQueue needs to verify user_id owns the task before deleting
        deleted = await task_queue.delete_task(user_id, task_id) # Pass user_id
        if not deleted: raise ValueError("Task not found or deletion unauthorized.")
        # WS broadcast handled by TaskQueue.delete_task
        return JSONResponse({"message": "Task deleted"})
    except ValueError as e: raise HTTPException(404, str(e)) # 404 if not found/unauthorized
    except Exception as e: print(f"[ERROR] /delete-task for {user_id}, task {task_id}: {e}"); raise HTTPException(500, "Failed deleting task.")


# --- Short-Term Memory Endpoints (Protected) ---
@app.post("/get-short-term-memories")
async def get_short_term_memories(request: GetShortTermMemoriesRequest, user_id: str = Depends(auth.get_current_user)):
    category = request.category; limit = request.limit
    print(f"[ENDPOINT /get-short-term-memories] Called by user {user_id} for Cat: {category}, Lim: {limit}")
    loop = asyncio.get_event_loop()
    try:
        # Pass user_id to backend method
        memories = await loop.run_in_executor( None, memory_backend.memory_manager.fetch_memories_by_category, user_id, category, limit )
        # Serialize datetime if needed
        serializable = [{**m, 'created_at': m['created_at'].isoformat(), 'expires_at': m['expires_at'].isoformat()} for m in memories if isinstance(m.get('created_at'), datetime) and isinstance(m.get('expires_at'), datetime)]
        return JSONResponse(serializable)
    except Exception as e: print(f"[ERROR] /get-short-term-memories for {user_id}: {e}"); raise HTTPException(500, "Failed fetching memories")

@app.post("/add-short-term-memory")
async def add_memory(request: AddMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    text = request.text; category = request.category; retention = request.retention_days
    print(f"[ENDPOINT /add-short-term-memory] Called by user {user_id} for Cat: {category}")
    loop = asyncio.get_event_loop()
    try:
        memory_id = await loop.run_in_executor( None, memory_backend.memory_manager.store_memory, user_id, text, retention, category )
        return JSONResponse({"memory_id": memory_id, "message": "Memory added"}, status_code=201)
    except Exception as e: print(f"[ERROR] /add-short-term-memory for {user_id}: {e}"); raise HTTPException(500, "Failed adding memory")

@app.post("/update-short-term-memory")
async def update_memory(request: UpdateMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    mem_id = request.id; text = request.text; category = request.category; retention = request.retention_days
    print(f"[ENDPOINT /update-short-term-memory] Called by user {user_id} for ID: {mem_id}")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor( None, memory_backend.memory_manager.update_memory_crud, user_id, category, mem_id, text, retention )
        return JSONResponse({"message": "Memory updated"})
    except ValueError as e: raise HTTPException(404, str(e)) # Not found
    except Exception as e: print(f"[ERROR] /update-short-term-memory for {user_id}: {e}"); raise HTTPException(500, "Failed updating memory")

@app.post("/delete-short-term-memory")
async def delete_memory(request: DeleteMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    mem_id = request.id; category = request.category
    print(f"[ENDPOINT /delete-short-term-memory] Called by user {user_id} for ID: {mem_id}, Cat: {category}")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor( None, memory_backend.memory_manager.delete_memory, user_id, category, mem_id )
        return JSONResponse({"message": "Memory deleted"})
    except ValueError as e: raise HTTPException(404, str(e)) # Not found
    except Exception as e: print(f"[ERROR] /delete-short-term-memory for {user_id}: {e}"); raise HTTPException(500, "Failed deleting memory")

@app.post("/clear-all-short-term-memories")
async def clear_all_memories(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /clear-all-short-term-memories] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor( None, memory_backend.memory_manager.clear_all_memories, user_id )
        return JSONResponse({"message": "All memories cleared"})
    except Exception as e: print(f"[ERROR] /clear-all-short-term-memories for {user_id}: {e}"); raise HTTPException(500, "Failed clearing memories")


# --- User Profile DB Endpoints (Protected) ---
@app.post("/set-user-data")
async def set_db_data(request: UpdateUserDataRequest, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /set-user-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        db_data = await loop.run_in_executor(None, load_user_profile, user_id)
        if "userData" not in db_data: db_data["userData"] = {}
        db_data["userData"].update(request.data) # Shallow merge/overwrite
        success = await loop.run_in_executor(None, write_user_profile, user_id, db_data)
        if not success: raise HTTPException(500, "Failed to write user profile.")
        return JSONResponse({"message": "Data stored", "status": 200})
    except Exception as e: print(f"[ERROR] /set-user-data for {user_id}: {e}"); raise HTTPException(500, "Failed setting data")

@app.post("/add-db-data")
async def add_db_data(request: AddUserDataRequest, user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /add-db-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        db_data = await loop.run_in_executor(None, load_user_profile, user_id)
        existing_data = db_data.get("userData", {})
        # ... (Deep merge logic remains same, operating on existing_data) ...
        for key, value in request.data.items():
             if key in existing_data and isinstance(existing_data[key], list) and isinstance(value, list):
                 existing_items = set(map(json.dumps, existing_data[key])) # Handle dicts in list
                 for item in value:
                      item_json = json.dumps(item)
                      if item_json not in existing_items: existing_data[key].append(item); existing_items.add(item_json)
             elif key in existing_data and isinstance(existing_data[key], dict) and isinstance(value, dict): existing_data[key].update(value)
             else: existing_data[key] = value
        db_data["userData"] = existing_data
        success = await loop.run_in_executor(None, write_user_profile, user_id, db_data)
        if not success: raise HTTPException(500, "Failed to write user profile.")
        return JSONResponse({"message": "Data added/merged", "status": 200})
    except Exception as e: print(f"[ERROR] /add-db-data for {user_id}: {e}"); raise HTTPException(500, "Failed adding data")

@app.post("/get-user-data") # Keep POST as it requires auth
async def get_db_data(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-user-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        db_data = await loop.run_in_executor(None, load_user_profile, user_id)
        return JSONResponse({"data": db_data.get("userData", {}), "status": 200})
    except Exception as e: print(f"[ERROR] /get-user-data for {user_id}: {e}"); raise HTTPException(500, "Failed fetching data")

# --- Graph Data Endpoint (Protected) ---
@app.post("/get-graph-data") # Changed to POST
async def get_graph_data_apoc(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-graph-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    if not graph_driver: raise HTTPException(503, "Neo4j driver unavailable")
    # TODO: Modify query if graph is scoped by user_id
    apoc_query = """ MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN collect(n) AS nodes, collect(r) AS edges """ # Simplified query
    # Correct APOC query:
    # apoc_query = """
    # CALL apoc.export.json.all(null,{stream:true, useTypes:true})
    # YIELD data
    # RETURN data
    # """
    # Using manual export approach for broader compatibility:
    apoc_query = """
    MATCH (n) // Potential user scope: MATCH (n {userId: $userId})
    WITH collect(DISTINCT n) as nodes
    OPTIONAL MATCH (s)-[r]->(t) WHERE s IN nodes AND t IN nodes // Potential user scope on r?
    WITH nodes, collect(DISTINCT r) as rels
    RETURN
        [node IN nodes | { id: elementId(node), label: coalesce(labels(node)[0], 'Unknown'), properties: properties(node) }] AS nodes_list,
        [rel IN rels | { id: elementId(rel), from: elementId(startNode(rel)), to: elementId(endNode(rel)), label: type(rel), properties: properties(rel) }] AS edges_list
    """
    print(f"Executing graph query for user {user_id}...")
    def run_neo4j_query_sync(driver, query, params):
         try:
             with driver.session(database="neo4j") as session:
                 result = session.run(query, params).single()
                 return (result['nodes_list'] if result else [], result['edges_list'] if result else [])
         except Exception as e: print(f"Neo4j query error: {e}"); raise # Re-raise
    try:
        nodes, edges = await loop.run_in_executor(None, run_neo4j_query_sync, graph_driver, apoc_query, {"userId": user_id}) # Pass userId if query uses it
        print(f"Graph query successful for user {user_id}. Nodes: {len(nodes)}, Edges: {len(edges)}")
        return JSONResponse({"nodes": nodes, "edges": edges})
    except Exception as e: print(f"[ERROR] /get-graph-data for {user_id}: {e}"); raise HTTPException(500, "Failed fetching graph data.")

# --- Notifications Endpoint (Protected) ---
@app.post("/get-notifications") # Changed to POST
async def get_notifications(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get-notifications] Called by user {user_id}.")
    try:
        notifications_db = await load_notifications_db(user_id) # Load user's notifications
        notifications = notifications_db.get("notifications", [])
        # Serialize datetime if needed
        for n in notifications:
             if isinstance(n.get('timestamp'), datetime): n['timestamp'] = n['timestamp'].isoformat()
        return JSONResponse({"notifications": notifications})
    except Exception as e: print(f"[ERROR] /get-notifications for {user_id}: {e}"); raise HTTPException(500, "Failed fetching notifications.")


# --- Task Approval Endpoints (Protected) ---
@app.post("/approve-task", response_model=ApproveTaskResponse)
async def approve_task(request: TaskIdRequest, user_id: str = Depends(auth.get_current_user)):
    task_id = request.task_id
    print(f"[ENDPOINT /approve-task] Called by user {user_id} for task {task_id}.")
    try:
        # TODO: TaskQueue needs to verify user_id owns the task
        result_data = await task_queue.approve_task(user_id, task_id) # Pass user_id
        print(f"Task {task_id} (User: {user_id}) approved and executed.")
        # Add result to user's chat DB
        task_details = await task_queue.get_task_by_id(task_id) # Should include user_id check
        if task_details and task_details.get("chat_id"):
            await add_message_to_db(user_id, task_details["chat_id"], result_data, is_user=False, is_visible=True, type="tool_result", task=task_details.get("description"), agentsUsed=True)
        else: print(f"[WARN] Could not add approved result to chat for task {task_id}.")
        # WS broadcast handled by TaskQueue
        return ApproveTaskResponse(message="Task approved and completed", result=result_data)
    except ValueError as e: raise HTTPException(400, str(e)) # Bad request (wrong state, not found, unauthorized)
    except Exception as e: print(f"[ERROR] /approve-task for {user_id}, task {task_id}: {e}"); raise HTTPException(500, "Approval failed.")

@app.post("/get-task-approval-data", response_model=TaskApprovalDataResponse)
async def get_task_approval_data(request: TaskIdRequest, user_id: str = Depends(auth.get_current_user)):
    task_id = request.task_id
    print(f"[ENDPOINT /get-task-approval-data] Called by user {user_id} for task {task_id}.")
    try:
        # TODO: TaskQueue needs user_id check
        task = await task_queue.get_task_by_id(task_id) # Assumes this checks user ownership implicitly or explicitly
        if task and task.get("user_id") == user_id and task.get("status") == "approval_pending":
            return TaskApprovalDataResponse(approval_data=task.get("approval_data"))
        elif task and task.get("user_id") == user_id:
             raise HTTPException(400, f"Task '{task_id}' not pending approval (status: {task.get('status')}).")
        else: # Task not found or doesn't belong to user
             raise HTTPException(404, f"Task '{task_id}' not found or access denied.")
    except HTTPException as e: raise e
    except Exception as e: print(f"[ERROR] /get-task-approval-data for {user_id}, task {task_id}: {e}"); raise HTTPException(500, "Failed fetching approval data.")


# --- Data Source Config Endpoints (Protected) ---
@app.post("/get_data_sources") # Changed to POST
async def get_data_sources_endpoint(user_id: str = Depends(auth.get_current_user)):
    print(f"[ENDPOINT /get_data_sources] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await loop.run_in_executor(None, load_user_profile, user_id)
        user_data = user_profile.get("userData", {})
        status_list = [{"name": src, "enabled": user_data.get(f"{src}Enabled", True)} for src in DATA_SOURCES]
        return JSONResponse({"data_sources": status_list})
    except Exception as e: print(f"[ERROR] /get_data_sources for {user_id}: {e}"); raise HTTPException(500, "Failed fetching source status.")

@app.post("/set_data_source_enabled")
async def set_data_source_enabled_endpoint(request: SetDataSourceEnabledRequest, user_id: str = Depends(auth.get_current_user)):
    source, enabled = request.source, request.enabled
    print(f"[ENDPOINT /set_data_source_enabled] Called by user {user_id}. Source: {source}, Enabled: {enabled}")
    if source not in DATA_SOURCES: raise HTTPException(400, f"Invalid source: {source}")
    loop = asyncio.get_event_loop()
    try:
        db_data = await loop.run_in_executor(None, load_user_profile, user_id)
        if "userData" not in db_data: db_data["userData"] = {}
        db_data["userData"][f"{source}Enabled"] = enabled
        success = await loop.run_in_executor(None, write_user_profile, user_id, db_data)
        if not success: raise HTTPException(500, "Failed to save profile.")
        # TODO: Trigger context engine restart/reload for this user and source
        print(f"[ACTION_NEEDED] Context engine for '{source}' (user {user_id}) may need restart.")
        return JSONResponse({"status": "success", "message": f"'{source}' status set to {enabled}."})
    except Exception as e: print(f"[ERROR] /set_data_source_enabled for {user_id}: {e}"); raise HTTPException(500, "Failed setting source status.")


# --- WebSocket Endpoint (With Auth) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = None
    try:
        # Authenticate connection
        user_id = await auth.ws_authenticate(websocket) # Handles auth message and validation
        if not user_id:
             print("[WS /ws] Authentication failed or closed during auth.")
             return # Connection already closed by ws_authenticate

        # Add authenticated connection to manager
        await manager.connect(websocket, user_id)

        # Keep connection alive (handle pings, etc.)
        while True:
            data = await websocket.receive_text()
            # print(f"Received WS message from user {user_id}: {data}")
            try: # Handle potential control messages (like ping)
                 msg = json.loads(data)
                 if msg.get("type") == "ping": await websocket.send_text(json.dumps({"type": "pong"}))
            except: pass # Ignore non-JSON or non-control messages

    except WebSocketDisconnect:
        print(f"[WS /ws] Client disconnected (User: {user_id or 'unknown'}).")
    except Exception as e:
        print(f"[WS /ws] Unexpected WebSocket error (User: {user_id or 'unknown'}): {e}")
    finally:
        # Ensure disconnect is called if connection was ever added
        manager.disconnect(websocket)


# --- Voice Endpoint (FastRTC - Needs Auth Adaptation) ---
# TODO: Adapt FastRTC stream to handle authentication, likely by passing
# the token in the initial connection or first message, similar to /ws.
# This requires modifying the FastRTC library or using a wrapper.
# For now, it remains implicitly unauthenticated.

# ... (handle_audio_conversation remains same for now, but needs user_id context) ...
async def handle_audio_conversation(audio: tuple[int, np.ndarray]) -> AsyncGenerator[tuple[int, np.ndarray], None]:
     # Placeholder: Needs user_id to function correctly
     user_id = "PLACEHOLDER_VOICE_USER" # How to get this for a voice connection?
     print(f"\n--- Received audio chunk for processing (User: {user_id}) ---")
     # ... (rest of the logic needs user_id for DB ops, profile load, memory, tasks) ...
     print("Transcribing..."); # STT
     user_text = stt_model.stt(audio)
     if not user_text or not user_text.strip(): print("No text transcribed."); return
     print(f"User (STT): {user_text}")

     # --- Major TODO: All subsequent logic needs user_id ---
     # - Load user profile for user_id
     # - Determine active chat for user_id
     # - Add messages to user_id's chat DB
     # - Classify input (runnable might need user context)
     # - Add tasks for user_id
     # - Retrieve memory for user_id
     # - Queue memory ops for user_id
     # - Invoke chat runnable (needs user-specific history/context)
     # - Synthesize TTS

     # Example placeholder response
     bot_response_text = f"Voice processing for user {user_id} is not fully implemented yet."
     print(f"Synthesizing placeholder: {bot_response_text}")
     tts_options: TTSOptions = {}
     async for sample_rate, audio_chunk in tts_model.stream_tts(bot_response_text, options=tts_options):
          if audio_chunk is not None and audio_chunk.size > 0: yield (sample_rate, audio_chunk)

# FastRTC Stream Setup (remains same, but handler needs fix)
stream = Stream( ReplyOnPause(handle_audio_conversation, algo_options=AlgoOptions(), model_options=SileroVadOptions(), can_interrupt=False), mode="send-receive", modality="audio" )
stream.mount(app, path="/voice")
print("FastRTC stream mounted at /voice (Authentication TODO).")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s [%(name)s] %(message)s" # Added logger name
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO"
    log_config["loggers"]["uvicorn.access"]["handlers"] = ["access"]

    print(f"[UVICORN] {datetime.now()}: Starting Uvicorn server on 0.0.0.0:5000...")
    uvicorn.run( "__main__:app", host="0.0.0.0", port=5000, lifespan="on", reload=False, workers=1, log_config=log_config )