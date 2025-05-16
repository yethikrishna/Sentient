import time
from datetime import datetime, timezone

# Record script start time for performance monitoring and logging
START_TIME = time.time()
print(f"[STARTUP] {datetime.now()}: Script execution started.")

# --- Core Python and System Imports ---
import os
import json
import asyncio
import pickle
import multiprocessing
import traceback # For detailed error printing

# --- Third-Party Library Imports ---
from tzlocal import get_localzone # Keep if needed elsewhere, but use explicit UTC for DB timestamps
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    status
)
from fastapi.security import OAuth2PasswordBearer, SecurityScopes # For Authentication
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse # For various response types
from fastapi.middleware.cors import CORSMiddleware # For Cross-Origin Resource Sharing
from fastapi.staticfiles import StaticFiles # For serving static files
from pydantic import BaseModel, Field # For data validation and settings management
from typing import Optional, Any, Dict, List, AsyncGenerator, Union # For type hinting

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

print(f"[STARTUP] {datetime.now()}: Basic imports completed.")

# --- Application-Specific Module Imports ---
# Import specific functions, runnables, and helpers from respective server subdirectories
print(f"[STARTUP] {datetime.now()}: Importing model components...")

# Agents: Core logic for decision making and tool usage
from server.agents.runnables import *
from server.agents.functions import *
from server.agents.prompts import *
from server.agents.formats import *
from server.agents.base import *
from server.agents.helpers import *

# Memory: Short-term and long-term memory management
from server.memory.runnables import *
from server.memory.functions import *
from server.memory.prompts import *
from server.memory.constants import *
from server.memory.formats import *
from server.memory.backend import MemoryBackend

# Utils: General utility functions
from server.utils.helpers import *

# Scraper: Web scraping functionalities
from server.scraper.runnables import *
from server.scraper.functions import *
from server.scraper.prompts import *
from server.scraper.formats import *

# Auth: Authentication related helpers (e.g., AES encryption, management tokens)
from server.auth.helpers import * # Contains AES, get_management_token

# Common: Shared components across different modules
from server.common.functions import *
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

# Re-import datetime for clarity, though already imported at the top
from datetime import datetime, timezone

# --- Environment Variable Loading ---
# Load environment variables from .env file located in the 'server' directory
print(f"[STARTUP] {datetime.now()}: Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
print(f"[STARTUP] {datetime.now()}: Environment variables loaded from {dotenv_path}")

# --- Asyncio Configuration ---
# Apply nest_asyncio to allow running asyncio event loops within other event loops.
# This is useful in environments like Jupyter notebooks or when integrating with
# libraries that manage their own event loops.
print(f"[STARTUP] {datetime.now()}: Applying nest_asyncio...")
nest_asyncio.apply()
print(f"[STARTUP] {datetime.now()}: nest_asyncio applied.")

# --- Global Initializations ---
print(f"[INIT] {datetime.now()}: Starting global initializations...")

# List of available data sources for context gathering
DATA_SOURCES = ["gmail", "internet_search", "gcalendar"]

# --- Auth0 Configuration & JWKS (JSON Web Key Set) ---
# Auth0 domain and API audience are crucial for token validation.
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") # This should match the API identifier in Auth0
ALGORITHMS = ["RS256"] # Auth0 typically uses RS256 for signing tokens

# Validate that essential Auth0 configuration is present
if not AUTH0_DOMAIN or not AUTH0_AUDIENCE:
    print("[ERROR] FATAL: AUTH0_DOMAIN or AUTH0_AUDIENCE not set in environment variables!")
    exit(1) # Exit if configuration is missing

# Fetch JWKS keys from Auth0's discovery endpoint.
# These keys are used to verify the signature of JWTs.
jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
try:
    print(f"[INIT] {datetime.now()}: Fetching JWKS from {jwks_url}...")
    jwks_response = requests.get(jwks_url)
    jwks_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
    jwks = jwks_response.json()
    print(f"[INIT] {datetime.now()}: JWKS fetched successfully.")
except requests.exceptions.RequestException as e:
     print(f"[ERROR] FATAL: Could not fetch JWKS from Auth0: {e}")
     exit(1) # Exit if JWKS cannot be fetched
except Exception as e:
     print(f"[ERROR] FATAL: Error processing JWKS: {e}")
     exit(1) # Exit on other JWKS processing errors

# OAuth2 password bearer scheme. The tokenUrl is a dummy here as FastAPI uses it
# primarily to extract the token from the Authorization header. Actual validation
# happens against the fetched JWKS.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- JWT Validation Logic ---
class Auth:
    """
    Handles authentication and authorization using JWTs from Auth0.
    Provides dependencies for FastAPI routes to protect them and methods
    for WebSocket authentication.
    """

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> str:
        """
        FastAPI dependency to validate an incoming JWT token and return the user_id (subject claim).
        This function is typically used in route definitions to protect endpoints.

        Args:
            token: The JWT token extracted from the Authorization header by `oauth2_scheme`.

        Raises:
            HTTPException (401): If the token is invalid, expired, or credentials cannot be validated.
            HTTPException (403): If the token is valid but lacks required permissions (optional).

        Returns:
            str: The user_id (Auth0 'sub' claim) if the token is valid.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        # Example permission exception, can be used if scope checking is implemented
        permission_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

        try:
            # Get the unverified header from the token to find the 'kid' (Key ID)
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            # Find the corresponding public key in the fetched JWKS using the 'kid'
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"], "kid": key["kid"], "use": key["use"],
                        "n": key["n"], "e": key["e"]
                    }
            if not rsa_key:
                print("[AUTH_VALIDATION] Signing key not found in JWKS for kid:", unverified_header["kid"])
                raise credentials_exception

            # Decode and validate the token using the public key
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE, # Verify the token is intended for this API
                issuer=f"https://{AUTH0_DOMAIN}/" # Verify the token issuer
            )

            user_id: str = payload.get("sub") # 'sub' claim usually holds the user ID
            if user_id is None:
                print("[AUTH_VALIDATION] Token payload missing 'sub' (user_id).")
                raise credentials_exception

            # Optional: Check for specific scopes/permissions if needed
            # scopes = payload.get("scope", "").split()
            # if "read:messages" not in scopes: # Example scope check
            #     raise permission_exception

            # print(f"[AUTH_VALIDATION] Token validated successfully for user: {user_id}")
            return user_id # Return the user ID

        except JWTError as e:
            print(f"[AUTH_VALIDATION] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e: # jose specific errors, often related to key issues
             print(f"[AUTH_VALIDATION] JOSE Error (likely key issue): {e}")
             raise credentials_exception
        except Exception as e: # Catch-all for unexpected errors during validation
             print(f"[AUTH_VALIDATION] Unexpected validation error: {e}")
             traceback.print_exc()
             raise credentials_exception

    async def ws_authenticate(self, websocket: WebSocket) -> Optional[str]:
        """
        Authenticates a WebSocket connection.
        Expects the client to send an auth message with a token shortly after connecting.

        Args:
            websocket: The WebSocket connection instance.

        Returns:
            Optional[str]: The user_id if authentication is successful, None otherwise.
                           The WebSocket connection will be closed on failure.
        """
        try:
            # Receive the initial authentication message from the client
            auth_data = await websocket.receive_text()
            message = json.loads(auth_data)

            # Check if the message type is 'auth' and a token is provided
            if message.get("type") != "auth":
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Auth message expected")
                return None

            token = message.get("token")
            if not token:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token missing in auth message")
                return None

            # Validate the token using the helper method
            user_id = await self.get_current_user_from_token(token)

            if user_id:
                 await websocket.send_text(json.dumps({"type": "auth_success", "user_id": user_id}))
                 print(f"[WS_AUTH] WebSocket authenticated for user: {user_id}")
                 return user_id
            else:
                 # This path should ideally not be reached if get_current_user_from_token raises
                 # HTTPException on failure, which it does. Kept as a fallback.
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
                 # Attempt to close the WebSocket gracefully on server error
                 await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
            except:
                pass # Ignore errors during close if already closed or problematic
            return None

    async def get_current_user_from_token(self, token: str) -> Optional[str]:
        """
        Helper method to validate a token string directly.
        This is used by `ws_authenticate` to avoid dependency injection issues.

        Args:
            token: The JWT token string.

        Returns:
            Optional[str]: The user_id ('sub' claim) if the token is valid, None otherwise.

        Raises:
            HTTPException: If the token is invalid.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"], "kid": key["kid"], "use": key["use"],
                        "n": key["n"], "e": key["e"]
                    }
            if not rsa_key:
                raise credentials_exception

            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
            return user_id
        except JWTError as e:
            print(f"[AUTH_HELPER] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e:
            print(f"[AUTH_HELPER] JOSE Error: {e}")
            raise credentials_exception
        except Exception as e:
            print(f"[AUTH_HELPER] Unexpected validation error: {e}")
            raise credentials_exception

# Instantiate the Auth class for use in dependencies
auth = Auth()
print(f"[INIT] {datetime.now()}: Authentication helper initialized.")

# Initialize embedding model
# This model is used for converting text into numerical vectors (embeddings).
print(f"[INIT] {datetime.now()}: Initializing HuggingFace Embedding model ({os.environ.get('EMBEDDING_MODEL_REPO_ID', 'N/A')})...")
try:
    embed_model = HuggingFaceEmbedding(model_name=os.environ["EMBEDDING_MODEL_REPO_ID"])
    print(f"[INIT] {datetime.now()}: HuggingFace Embedding model initialized.")
except KeyError:
    print(f"[ERROR] {datetime.now()}: EMBEDDING_MODEL_REPO_ID not set in environment. Embedding model not initialized.")
    embed_model = None
except Exception as e:
    print(f"[ERROR] {datetime.now()}: Failed to initialize Embedding model: {e}")
    embed_model = None

# Initialize Neo4j driver
# This driver is used to connect to and interact with the Neo4j graph database.
print(f"[INIT] {datetime.now()}: Initializing Neo4j Graph Driver (URI: {os.environ.get('NEO4J_URI', 'N/A')})...")
try:
    graph_driver = GraphDatabase.driver(
        uri=os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    graph_driver.verify_connectivity() # Check if the connection to Neo4j is successful
    print(f"[INIT] {datetime.now()}: Neo4j Graph Driver initialized and connected.")
except KeyError:
    print(f"[ERROR] {datetime.now()}: NEO4J_URI, NEO4J_USERNAME, or NEO4J_PASSWORD not set. Neo4j Driver not initialized.")
    graph_driver = None
except Exception as e:
    print(f"[ERROR] {datetime.now()}: Failed to initialize or connect Neo4j Driver: {e}")
    graph_driver = None

# --- WebSocket Manager ---
class WebSocketManager:
    """
    Manages active WebSocket connections, mapping authenticated user_ids to their sockets.
    Provides methods for sending messages to specific users or broadcasting to all.
    """
    def __init__(self):
        """Initializes the WebSocketManager with an empty dictionary for active connections."""
        # Stores active connections: user_id (str) -> WebSocket object
        self.active_connections: Dict[str, WebSocket] = {}
        print(f"[WS_MANAGER] {datetime.now()}: WebSocketManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Registers an authenticated WebSocket connection.
        If the user already has an active connection, the old one is closed.

        Args:
            websocket: The new WebSocket connection instance.
            user_id: The authenticated user_id associated with this connection.
        """
        # The WebSocket connection is accepted in the endpoint before this method is called.
        if user_id in self.active_connections:
             print(f"[WS_MANAGER] {datetime.now()}: User {user_id} already has an active connection. Closing old one.")
             old_ws = self.active_connections[user_id]
             try:
                 # Close the old WebSocket connection with a policy violation code
                 await old_ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="New connection established")
             except Exception:
                 pass # Ignore errors if the old socket is already closed or problematic

        self.active_connections[user_id] = websocket
        print(f"[WS_MANAGER] {datetime.now()}: WebSocket connected for user: {user_id} ({len(self.active_connections)} total)")

    def disconnect(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the active list.

        Args:
            websocket: The WebSocket connection instance to remove.
        """
        user_id_to_remove = None
        # Find the user_id associated with the disconnecting WebSocket
        for user_id, ws in self.active_connections.items():
            if ws == websocket:
                user_id_to_remove = user_id
                break
        if user_id_to_remove:
             del self.active_connections[user_id_to_remove]
             print(f"[WS_MANAGER] {datetime.now()}: WebSocket disconnected for user: {user_id_to_remove} ({len(self.active_connections)} total)")
        # else:
        #      # This can happen if disconnect is called multiple times or on an unmanaged socket
        #      print(f"[WS_MANAGER] {datetime.now()}: WebSocket disconnect requested, but socket not found in active connections.")

    async def send_personal_message(self, message: str, user_id: str):
        """
        Sends a message to a specific connected user.

        Args:
            message: The string message to send.
            user_id: The user_id of the recipient.
        """
        websocket = self.active_connections.get(user_id)
        if websocket:
             try:
                 await websocket.send_text(message)
             except Exception as e:
                 print(f"[WS_MANAGER] {datetime.now()}: Error sending personal message to user {user_id}: {e}")
                 # If sending fails, assume the connection is broken and disconnect it
                 self.disconnect(websocket)
        # else:
             # print(f"[WS_MANAGER] {datetime.now()}: Could not send personal message: User {user_id} not connected.")

    async def broadcast(self, message: str):
        """
        Sends a message to all currently connected users.

        Args:
            message: The string message to broadcast.
        """
        # Create a copy of connections to iterate over, as the dictionary might change
        # if connections drop during the broadcast.
        connections_to_send = list(self.active_connections.values())
        disconnected_websockets = []

        for connection in connections_to_send:
            try:
                await connection.send_text(message)
            except Exception as e:
                # If sending fails, mark the WebSocket for disconnection
                user_id = "unknown" # Attempt to find user_id for logging
                for uid, ws in self.active_connections.items(): # Check current active connections
                    if ws == connection:
                        user_id = uid
                        break
                print(f"[WS_MANAGER] {datetime.now()}: Error broadcasting to user {user_id}, marking for disconnect: {e}")
                disconnected_websockets.append(connection)

        # Disconnect all WebSockets that failed during the broadcast
        for ws in disconnected_websockets:
            self.disconnect(ws)

    async def broadcast_json(self, data: dict):
        """
        Sends a JSON payload (serialized to string) to all connected users.

        Args:
            data: The dictionary to serialize to JSON and broadcast.
        """
        await self.broadcast(json.dumps(data))

# Instantiate the WebSocketManager
manager = WebSocketManager()
print(f"[INIT] {datetime.now()}: WebSocketManager instance created.")

# Initialize various runnables (LangChain components)
# These are pre-configured chains or agents for specific tasks.
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
chat_history = get_chat_history() # Manages its own state internally; consider user-scoping later
chat_runnable = get_chat_runnable(chat_history)
agent_runnable = get_agent_runnable(chat_history)
unified_classification_runnable = get_unified_classification_runnable(chat_history)
reddit_runnable = get_reddit_runnable()
twitter_runnable = get_twitter_runnable()
internet_query_reframe_runnable = get_internet_query_reframe_runnable()
internet_summary_runnable = get_internet_summary_runnable()
print(f"[INIT] {datetime.now()}: Runnables initialization complete.")


# Tool handlers registry: A dictionary to map tool names to their handler functions.
tool_handlers: Dict[str, callable] = {}
print(f"[INIT] {datetime.now()}: Tool handlers registry initialized.")

# Instantiate the task queue globally
# This queue will manage background tasks, notifying users via WebSockets.
print(f"[INIT] {datetime.now()}: Initializing TaskQueue...")
task_queue = TaskQueue() # Pass WebSocket manager for notifications
print(f"[INIT] {datetime.now()}: TaskQueue initialized.")

# --- Voice Model Initializations ---
# STT (Speech-to-Text) and TTS (Text-to-Speech) models will be loaded during app startup (lifespan event)
# to avoid slow global initialization and allow for potential resource management.
stt_model = None
tts_model = None
SELECTED_TTS_VOICE: VoiceId = "tara" # Default voice for TTS

# --- Database and State Management ---
print(f"[CONFIG] {datetime.now()}: Defining database file paths...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define base directories for user-specific data.
# Using separate directories for profiles, chat histories, and notifications.
USER_PROFILE_DB_DIR = os.path.join(BASE_DIR, "..", "..", "user_databases")
CHAT_DB_DIR = os.path.join(BASE_DIR, "..", "..", "chat_databases")
NOTIFICATIONS_DB_DIR = os.path.join(BASE_DIR, "..", "..", "notification_databases")

# Ensure these directories exist
os.makedirs(USER_PROFILE_DB_DIR, exist_ok=True)
os.makedirs(CHAT_DB_DIR, exist_ok=True)
os.makedirs(NOTIFICATIONS_DB_DIR, exist_ok=True)

# Functions to get user-specific database file paths
def get_user_profile_db_path(user_id: str) -> str:
    """Constructs the path to a user's profile JSON file."""
    # Consider sanitizing user_id if it can contain problematic characters for filenames.
    return os.path.join(USER_PROFILE_DB_DIR, f"{user_id}_profile.json")

def get_user_chat_db_path(user_id: str) -> str:
    """Constructs the path to a user's chat history JSON file."""
    return os.path.join(CHAT_DB_DIR, f"{user_id}_chats.json")

def get_user_notifications_db_path(user_id: str) -> str:
    """Constructs the path to a user's notifications JSON file."""
    return os.path.join(NOTIFICATIONS_DB_DIR, f"{user_id}_notifications.json")

print(f"[CONFIG] {datetime.now()}: User-specific database directories set.")

# Async Locks for file-based database access
# These global locks prevent race conditions when multiple async operations try to
# access the same user's files.
# For higher concurrency, a per-user lock strategy (e.g., a dictionary of locks)
# or a proper database system would be more scalable.
db_lock = asyncio.Lock()  # Global lock for chat database files
notifications_db_lock = asyncio.Lock() # Global lock for notification database files
profile_db_lock = asyncio.Lock() # Global lock for user profile database files
print(f"[INIT] {datetime.now()}: Global database locks initialized (consider per-user locks for scale).")

# Initial structure for a new user's chat database
initial_db = {"chats": [], "active_chat_id": 0, "next_chat_id": 1}
print(f"[CONFIG] {datetime.now()}: Initial chat DB structure defined.")

# Initialize MemoryBackend
# This backend handles operations related to the agent's memory.
print(f"[INIT] {datetime.now()}: Initializing MemoryBackend...")
memory_backend = MemoryBackend() # Pass WebSocket manager for potential notifications
print(f"[INIT] {datetime.now()}: MemoryBackend initialized. Performing cleanup...")
# Cleanup operations for memory might depend on user context, so deferred for now.
# memory_backend.cleanup()
print(f"[INIT] {datetime.now()}: MemoryBackend cleanup deferred.")

# Tool Registration Decorator
def register_tool(name: str):
    """
    A decorator to register tool handler functions.
    Registered handlers are stored in the `tool_handlers` dictionary.

    Args:
        name: The name of the tool to register.

    Returns:
        A decorator function.
    """
    def decorator(func: callable):
        print(f"[TOOL_REGISTRY] {datetime.now()}: Registering tool '{name}' with handler '{func.__name__}'")
        tool_handlers[name] = func
        return func
    return decorator

# --- Google OAuth2 Configuration ---
print(f"[CONFIG] {datetime.now()}: Setting up Google OAuth2 configuration...")

# Define the scopes (permissions) required for Google APIs
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
    "https://mail.google.com/", # Broader mail scope
]
print(f"[CONFIG] {datetime.now()}:   - SCOPES defined: {SCOPES}")

# Construct Google API credentials dictionary from environment variables
# This is used for the OAuth flow.
CREDENTIALS_DICT = {
    "installed": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
        "auth_uri": os.environ.get("GOOGLE_AUTH_URI"),
        "token_uri": os.environ.get("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost"] # Ensure this matches your Google Cloud Console setup
    }
}
print(f"[CONFIG] {datetime.now()}: Google OAuth2 configuration complete.")

# --- Auth0 Management API Configuration ---
# Credentials for accessing the Auth0 Management API (e.g., to manage users, roles).
MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")
print(f"[CONFIG] {datetime.now()}: Auth0 Management API config loaded.")

# --- Helper Functions (User-Specific File Operations) ---

async def load_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Loads profile data for a specific user from their JSON file.

    Args:
        user_id: The ID of the user whose profile is to be loaded.

    Returns:
        A dictionary containing the user's profile data, or a default structure if not found or error.
    """
    profile_path = get_user_profile_db_path(user_id)
    # print(f"[DB_HELPER] Loading profile for {user_id} from {profile_path}")
    try:
        async with profile_db_lock: # Acquire lock for thread-safe file access
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except FileNotFoundError:
        # print(f"[DB_HELPER] Profile not found for {user_id}. Returning default.")
        return {"userData": {}} # Return a default empty profile structure
    except (json.JSONDecodeError, Exception) as e:
        print(f"[ERROR] Error loading profile for {user_id} from {profile_path}: {e}")
        return {"userData": {}} # Return default on error

async def write_user_profile(user_id: str, data: Dict[str, Any]) -> bool:
    """
    Writes profile data for a specific user to their JSON file.

    Args:
        user_id: The ID of the user whose profile is to be written.
        data: The dictionary containing the user's profile data.

    Returns:
        True if writing was successful, False otherwise.
    """
    profile_path = get_user_profile_db_path(user_id)
    # print(f"[DB_HELPER] Writing profile for {user_id} to {profile_path}")
    try:
         async with profile_db_lock: # Acquire lock for thread-safe file access
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4) # Save with pretty printing
            return True
    except Exception as e:
        print(f"[ERROR] Error writing profile for {user_id} to {profile_path}: {e}")
        return False

async def load_notifications_db(user_id: str) -> Dict[str, Any]:
    """
    Loads notifications for a specific user from their JSON file.

    Args:
        user_id: The ID of the user whose notifications are to be loaded.

    Returns:
        A dictionary containing notifications and the next ID, or an initial structure.
    """
    notifications_path = get_user_notifications_db_path(user_id)
    async with notifications_db_lock:
        try:
            with open(notifications_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure basic structure exists
                if "notifications" not in data:
                    data["notifications"] = []
                if "next_notification_id" not in data:
                    data["next_notification_id"] = 1
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize if file not found or JSON is invalid
            return {"notifications": [], "next_notification_id": 1}
        except Exception as e:
            print(f"[ERROR] Error loading notifications for {user_id} from {notifications_path}: {e}")
            return {"notifications": [], "next_notification_id": 1} # Return default on error

async def save_notifications_db(user_id: str, data: Dict[str, Any]):
    """
    Saves notifications for a specific user to their JSON file.

    Args:
        user_id: The ID of the user whose notifications are to be saved.
        data: The dictionary containing notification data.
    """
    notifications_path = get_user_notifications_db_path(user_id)
    async with notifications_db_lock:
        try:
            with open(notifications_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Error saving notifications for {user_id} to {notifications_path}: {e}")

async def load_db(user_id: str) -> Dict[str, Any]:
    """
    Loads the chat database for a specific user from their JSON file.
    Initializes with a default structure if the file doesn't exist or is invalid.

    Args:
        user_id: The ID of the user whose chat database is to be loaded.

    Returns:
        A dictionary representing the user's chat database.
    """
    chat_path = get_user_chat_db_path(user_id)
    async with db_lock: # Use the global chat DB lock
        try:
            with open(chat_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Basic validation and type coercion for critical fields
                if "chats" not in data:
                    data["chats"] = []
                if "active_chat_id" not in data:
                    data["active_chat_id"] = 0
                if "next_chat_id" not in data:
                    data["next_chat_id"] = 1

                try: # Ensure IDs are integers
                    if data.get("active_chat_id") is not None:
                        data["active_chat_id"] = int(data["active_chat_id"])
                    if data.get("next_chat_id") is not None:
                        data["next_chat_id"] = int(data["next_chat_id"])
                except (ValueError, TypeError): # Reset on conversion error
                    data["active_chat_id"] = 0
                    data["next_chat_id"] = 1
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return initial_db.copy() # Return a copy of the initial structure for a new user
        except Exception as e:
            print(f"[ERROR] Error loading chat DB for {user_id} from {chat_path}: {e}")
            return initial_db.copy() # Return default on other errors

async def save_db(user_id: str, data: Dict[str, Any]):
    """
    Saves the chat database for a specific user to their JSON file.
    Ensures critical ID fields are integers before saving.

    Args:
        user_id: The ID of the user whose chat database is to be saved.
        data: The dictionary representing the user's chat database.
    """
    chat_path = get_user_chat_db_path(user_id)
    async with db_lock: # Use the global chat DB lock
        try:
            # Ensure IDs are integers before saving to maintain consistency
            if data.get("active_chat_id") is not None:
                data["active_chat_id"] = int(data["active_chat_id"])
            if data.get("next_chat_id") is not None:
                data["next_chat_id"] = int(data["next_chat_id"])
            for chat in data.get("chats", []):
                if chat.get("id") is not None:
                    chat["id"] = int(chat["id"])

            with open(chat_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Error saving chat DB for {user_id} to {chat_path}: {e}")

async def get_chat_history_messages(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves the message history of the currently active chat for a specific user.
    Handles initial state (no chats), inactivity (creates new chat), and ensures an
    active chat is always selected or created for the user.

    Args:
        user_id: The ID of the user whose chat history is being requested.

    Returns:
        A list of message dictionaries for the active chat, or an empty list if
        the active chat is new or has no visible messages.
    """
    print(f"[CHAT_HISTORY] {datetime.now()}: get_chat_history_messages called for user {user_id}.")
    async with db_lock: # Global lock for chat DB operations; consider per-user locks for scale
        print(f"[CHAT_HISTORY] {datetime.now()}: Acquired chat DB lock for user {user_id}.")
        chatsDb = await load_db(user_id) # Load the specific user's chat database
        active_chat_id = chatsDb.get("active_chat_id", 0)
        next_chat_id = chatsDb.get("next_chat_id", 1)
        current_time = datetime.now(timezone.utc) # Use timezone-aware datetime
        existing_chats = chatsDb.get("chats", [])
        active_chat = None

        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} DB state - active_chat_id: {active_chat_id}, next_chat_id: {next_chat_id}, num_chats: {len(existing_chats)}")

        # --- Logic for handling active_chat_id and inactivity ---
        if active_chat_id == 0: # No active chat ID set
            if not existing_chats: # No chats exist at all for this user
                new_chat_id = next_chat_id
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - No chats exist. Creating first chat ID: {new_chat_id}.")
                new_chat = {"id": new_chat_id, "messages": []}
                chatsDb["chats"] = [new_chat]
                chatsDb["active_chat_id"] = new_chat_id
                chatsDb["next_chat_id"] = new_chat_id + 1
                await save_db(user_id, chatsDb)
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - First chat created and activated. DB saved.")
                return [] # Return empty messages for the newly created chat
            else: # Chats exist, but none is active; activate the latest one
                latest_chat_id = existing_chats[-1]['id']
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Activating latest chat ID: {latest_chat_id}.")
                chatsDb['active_chat_id'] = latest_chat_id
                active_chat_id = latest_chat_id # Update local variable
                await save_db(user_id, chatsDb)
                print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Activated latest chat. DB saved.")

        # Find the active chat object
        active_chat = next((chat for chat in existing_chats if chat.get("id") == active_chat_id), None)

        if not active_chat:
            # This case should be rare if the above logic is correct, but as a safeguard:
            print(f"[ERROR] {datetime.now()}: User {user_id} - Active chat ID '{active_chat_id}' mismatch or chat not found. Resetting active ID to 0.")
            chatsDb["active_chat_id"] = 0 # Reset to force re-evaluation on next call
            await save_db(user_id, chatsDb)
            return [] # Return empty as state is inconsistent

        # Inactivity check: if the active chat has messages and the last one is too old
        if active_chat.get("messages"):
            try:
                last_message = active_chat["messages"][-1]
                timestamp_str = last_message.get("timestamp")
                if timestamp_str:
                    # Ensure timestamp is parsed correctly (ISO format with UTC offset)
                    last_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if (current_time - last_timestamp).total_seconds() > 600: # 10-minute inactivity threshold
                        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Inactivity detected in chat {active_chat_id}. Creating new chat.")
                        new_chat_id = next_chat_id
                        new_chat = {"id": new_chat_id, "messages": []}
                        chatsDb["chats"].append(new_chat)
                        chatsDb["active_chat_id"] = new_chat_id
                        chatsDb["next_chat_id"] = new_chat_id + 1
                        await save_db(user_id, chatsDb)
                        print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - New chat {new_chat_id} created/activated due to inactivity.")
                        return [] # Return empty messages for the new chat
            except Exception as e:
                print(f"[WARN] {datetime.now()}: User {user_id} - Error during inactivity check for chat {active_chat_id}: {e}")
                # Continue with current chat if inactivity check fails

        # Return visible messages from the active chat
        if active_chat and active_chat.get("messages"):
            filtered_messages = [msg for msg in active_chat["messages"] if msg.get("isVisible", True)]
            print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Returning {len(filtered_messages)} visible messages for active chat {active_chat_id}.")
            return filtered_messages
        else:
            print(f"[CHAT_HISTORY] {datetime.now()}: User {user_id} - Active chat {active_chat_id} has no messages. Returning empty list.")
            return []

async def add_message_to_db(
    user_id: str,
    chat_id: Union[int, str],
    message_text: str,
    is_user: bool,
    is_visible: bool = True,
    **kwargs
) -> Optional[str]:
    """
    Adds a message to the specified chat ID for a specific user.

    Args:
        user_id: The ID of the user.
        chat_id: The ID of the chat to add the message to.
        message_text: The content of the message.
        is_user: Boolean indicating if the message is from the user (True) or AI (False).
        is_visible: Boolean indicating if the message should be visible in the UI.
        **kwargs: Additional optional fields for the message (e.g., memoryUsed, type).

    Returns:
        The ID of the newly added message, or None if an error occurred.
    """
    # print(f"[DB_ADD_MSG] User: {user_id}, Chat: {chat_id}, IsUser: {is_user}, Visible: {is_visible}, Text: {message_text[:50]}...")
    try:
        target_chat_id = int(chat_id)
    except (ValueError, TypeError):
        print(f"[ERROR] Invalid chat_id format for add_message_to_db: '{chat_id}'. Message not added.")
        return None

    async with db_lock: # Still using global lock; consider per-user or finer-grained locks
        try:
            chatsDb = await load_db(user_id)
            active_chat = next((chat for chat in chatsDb.get("chats", []) if chat.get("id") == target_chat_id), None)

            if active_chat:
                message_id = str(int(time.time() * 1000)) # Unique message ID based on timestamp
                new_message = {
                    "id": message_id,
                    "message": message_text,
                    "isUser": is_user,
                    "isVisible": is_visible,
                    "timestamp": datetime.now(timezone.utc).isoformat(), # UTC timestamp
                    "memoryUsed": kwargs.get("memoryUsed", False),
                    "agentsUsed": kwargs.get("agentsUsed", False),
                    "internetUsed": kwargs.get("internetUsed", False),
                    "type": kwargs.get("type"), # e.g., 'tool_result', 'error'
                    "task": kwargs.get("task")  # Description of task if related
                }
                # Remove None values for cleaner JSON output
                new_message = {k: v for k, v in new_message.items() if v is not None}

                if "messages" not in active_chat: # Ensure 'messages' list exists
                    active_chat["messages"] = []
                active_chat["messages"].append(new_message)
                await save_db(user_id, chatsDb)
                # print(f"Message added to DB (User: {user_id}, Chat ID: {target_chat_id}, User: {is_user})")
                return message_id
            else:
                print(f"[ERROR] Could not find chat with ID {target_chat_id} for user {user_id} to add message.")
                return None
        except Exception as e:
            print(f"[ERROR] Error adding message to DB for user {user_id}, chat {target_chat_id}: {e}")
            traceback.print_exc()
            return None

# --- Background Task Processors ---
# These run continuously in the background to handle queued operations.
# They need to be adapted if the state they operate on (e.g., task queue items)
# becomes strictly user-specific in storage.

async def cleanup_tasks_periodically():
    """
    Periodically cleans up old, completed tasks from the task queue.
    Currently assumes a global task queue; would need modification for per-user task storage.
    """
    print(f"[TASK_CLEANUP] {datetime.now()}: Starting periodic task cleanup loop.")
    while True:
        cleanup_interval = 3600 # Run every 1 hour
        print(f"[TASK_CLEANUP] {datetime.now()}: Running cleanup task...")
        try:
            # If TaskQueue stores tasks per user, this method would need to iterate
            # through users or be called with user context.
            await task_queue.delete_old_completed_tasks()
            print(f"[TASK_CLEANUP] {datetime.now()}: Cleanup complete.")
        except Exception as e:
             print(f"[ERROR] {datetime.now()}: Error during periodic task cleanup: {e}")
             traceback.print_exc()
        await asyncio.sleep(cleanup_interval)

async def process_queue():
    """
    Continuously processes tasks from the global task queue.
    Each task should contain a `user_id` to allow user-specific execution.
    """
    print(f"[TASK_PROCESSOR] {datetime.now()}: Starting task processing loop.")
    while True:
        task = await task_queue.get_next_task() # Fetches from the global queue
        if task:
            task_id = task.get("task_id", "N/A")
            task_user_id = task.get("user_id", "N/A") # Essential for user-specific processing
            task_desc = task.get("description", "N/A")
            task_chat_id = task.get("chat_id", "N/A")
            print(f"[TASK_PROCESSOR] {datetime.now()}: Processing task ID: {task_id} for User: {task_user_id}, Chat: {task_chat_id}, Desc: {task_desc[:50]}...")

            if task_user_id == "N/A": # Cannot process without user context
                 print(f"[ERROR] {datetime.now()}: Task {task_id} is missing user_id. Cannot process.")
                 await task_queue.complete_task(task_id, error="Task missing user context", status="error")
                 continue

            try:
                # Execute the task, passing the user_id for context
                task_queue.current_task_execution = asyncio.create_task(
                    execute_agent_task(task_user_id, task)
                )
                result = await task_queue.current_task_execution

                if result == APPROVAL_PENDING_SIGNAL:
                    # Task is awaiting user approval; status already set by execute_agent_task
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) pending approval.")
                else:
                    # Task completed normally
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) completed normally. Result len: {len(str(result)) if result else 0}")
                    if task_chat_id != "N/A":
                        # Add results to the specific user's chat
                        # Store the original prompt/description (hidden)
                        await add_message_to_db(task_user_id, task_chat_id, task["description"], is_user=True, is_visible=False)
                        # Store the visible result from the agent/tool
                        await add_message_to_db(task_user_id, task_chat_id, result, is_user=False, is_visible=True, type="tool_result", task=task["description"], agentsUsed=True)
                    else:
                        print(f"[WARN] Task {task_id} (User: {task_user_id}) has no chat_id. Result not added to chat.")
                    await task_queue.complete_task(task_id, result=result) # Mark as complete in queue
                    print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} marked completed in queue.")
                    # WebSocket broadcast of task completion is handled by TaskQueue.complete_task

            except asyncio.CancelledError:
                print(f"[TASK_PROCESSOR] {datetime.now()}: Task {task_id} (User: {task_user_id}) execution cancelled.")
                await task_queue.complete_task(task_id, error="Task cancelled", status="cancelled")
            except Exception as e:
                error_str = str(e)
                print(f"[ERROR] {datetime.now()}: Error processing task {task_id} (User: {task_user_id}): {error_str}")
                traceback.print_exc()
                await task_queue.complete_task(task_id, error=error_str, status="error")
            finally:
                 task_queue.current_task_execution = None # Clear current execution tracking
        else:
            # No task in queue, wait briefly before checking again
            await asyncio.sleep(0.1)

async def process_memory_operations():
    """
    Continuously processes memory operations from the global memory queue.
    Each operation must include a `user_id` for user-specific memory updates.
    """
    print(f"[MEMORY_PROCESSOR] {datetime.now()}: Starting memory operation processing loop.")
    while True:
        operation = await memory_backend.memory_queue.get_next_operation() # Fetches from global queue
        if operation:
            op_id = operation.get("operation_id", "N/A")
            user_id = operation.get("user_id", "N/A") # Essential for user-specific memory
            memory_data = operation.get("memory_data", "N/A") # Data to be processed into memory
            print(f"[MEMORY_PROCESSOR] {datetime.now()}: Processing memory op ID: {op_id} for User: {user_id}...")

            if user_id == "N/A": # Cannot process without user context
                 print(f"[ERROR] {datetime.now()}: Memory operation {op_id} is missing user_id. Cannot process.")
                 await memory_backend.memory_queue.complete_operation(op_id, error="Operation missing user context", status="error")
                 continue

            try:
                # Perform the memory update for the specific user
                await memory_backend.update_memory(user_id, memory_data)
                print(f"[MEMORY_PROCESSOR] {datetime.now()}: Memory update for user {user_id} successful (Op ID: {op_id}).")
                await memory_backend.memory_queue.complete_operation(op_id, result="Success")
                # WebSocket broadcast related to memory update is handled by MemoryBackend

            except Exception as e:
                error_str = str(e)
                print(f"[ERROR] {datetime.now()}: Error processing memory op {op_id} for user {user_id}: {error_str}")
                traceback.print_exc()
                await memory_backend.memory_queue.complete_operation(op_id, error=error_str, status="error")
        else:
            # No operation in queue, wait briefly
            await asyncio.sleep(0.1)

# --- Task Execution Logic ---
async def execute_agent_task(user_id: str, task: dict) -> str:
    """
    Executes an agent task for a specific user.
    This involves gathering context (user profile, internet), invoking an agent runnable,
    processing tool calls (including potential approval flows), and reflecting on results.

    Args:
        user_id: The ID of the user for whom the task is being executed.
        task: A dictionary containing task details (description, use_personal_context, internet).

    Returns:
        A string representing the final result of the task, or APPROVAL_PENDING_SIGNAL
        if the task requires user approval for a tool call.
    """
    task_id = task.get("task_id", "N/A")
    task_desc = task.get("description", "N/A")
    print(f"[AGENT_EXEC] {datetime.now()}: Executing task ID: {task_id} for User: {user_id}, Desc: {task_desc[:50]}...")

    # --- Load User-Specific Context ---
    # Load user profile to get name/personality settings for this specific user.
    # Using synchronous load_user_profile as this function runs in a background task processor,
    # and file I/O is acceptable here. If it were in a main async event loop,
    # it should be run in an executor.
    user_profile = await load_user_profile(user_id) # Changed to await
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
    personality = user_profile.get("userData", {}).get("personality", "Default helpful assistant")

    transformed_input = task.get("description", "") # Use task description as primary input
    use_personal_context = task.get("use_personal_context", False)
    internet_search_needed = task.get("internet", "None") != "None" # Renamed for clarity

    user_context_str = None # Renamed for clarity
    internet_context_str = None # Renamed for clarity

    # --- Compute User Context (from Knowledge Graph / Memory) ---
    if use_personal_context:
        print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) - Querying user profile/memory...")
        try:
            if graph_driver and embed_model and text_conversion_runnable and query_classification_runnable:
                # Run synchronous graph query in a threadpool to avoid blocking the asyncio loop
                user_context_str = await asyncio.to_thread(
                     query_user_profile, # This function performs Neo4j queries
                     user_id,            # Pass user_id for user-specific graph queries
                     transformed_input,
                     graph_driver,
                     embed_model,
                     text_conversion_runnable,
                     query_classification_runnable
                 )
                print(f"[AGENT_EXEC] User context retrieved for task {task_id}. Len: {len(str(user_context_str)) if user_context_str else 0}")
            else:
                print(f"[WARN] Skipping user context query for task {task_id} due to missing dependencies (Neo4j/EmbedModel).")
                user_context_str = "User context is currently unavailable."
        except Exception as e:
            print(f"[ERROR] Error computing user_context for task {task_id} (User: {user_id}): {e}")
            user_context_str = f"Error retrieving user context: {e}"

    # --- Compute Internet Context ---
    if internet_search_needed:
         print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) - Searching internet...")
         try:
              # Reframe query for better search results
              reframed_query = get_reframed_internet_query(internet_query_reframe_runnable, transformed_input)
              # Perform search
              search_results = get_search_results(reframed_query)
              # Summarize search results
              internet_context_str = get_search_summary(internet_summary_runnable, search_results)
              print(f"[AGENT_EXEC] Internet context summary generated for task {task_id}. Len: {len(str(internet_context_str)) if internet_context_str else 0}")
         except Exception as e:
             print(f"[ERROR] Error computing internet_context for task {task_id} (User: {user_id}): {e}")
             internet_context_str = f"Error retrieving internet context: {e}"

    # --- Invoke Agent Runnable ---
    # The agent runnable makes decisions based on the query and provided contexts.
    # TODO: Ensure agent_runnable and its internal chat_history are user-specific if they rely on ongoing conversation state.
    print(f"[AGENT_EXEC] Invoking agent runnable for task {task_id} (User: {user_id})...")
    agent_input = {
        "query": transformed_input,
        "name": username,
        "user_context": user_context_str,
        "internet_context": internet_context_str,
        "personality": personality
    }
    try:
        response = agent_runnable.invoke(agent_input)
        print(f"[AGENT_EXEC] Agent response received for task {task_id}.")
    except Exception as e:
        print(f"[ERROR] Error invoking agent_runnable for task {task_id} (User: {user_id}): {e}")
        return f"Error: Agent failed to process the request: {e}"

    # --- Process Tool Calls from Agent Response ---
    tool_calls = []
    if isinstance(response, dict) and "tool_calls" in response:
        tool_calls = response["tool_calls"]
    elif isinstance(response, list): # If response is directly a list of tool calls
        tool_calls = response
    else:
         if isinstance(response, str): # Direct answer from agent, no tools
             return response
         error_msg = f"Invalid agent response type: {type(response)}. Expected dict with 'tool_calls' or list."
         print(f"[AGENT_EXEC] {error_msg}");
         return error_msg

    all_tool_results = []
    previous_tool_result = None # For chaining tool results if needed
    print(f"[AGENT_EXEC] Processing {len(tool_calls)} tool calls for task {task_id} (User: {user_id}).")

    for i, tool_call_item in enumerate(tool_calls):
         # Validate tool_call structure (expecting a dict with specific keys)
         tool_content = tool_call_item.get("content") if isinstance(tool_call_item, dict) and tool_call_item.get("response_type") == "tool_call" else tool_call_item

         if not isinstance(tool_content, dict):
             print(f"[AGENT_EXEC] Skipping invalid tool content format (item {i+1}) for task {task_id}.")
             all_tool_results.append({"tool_name": "unknown", "tool_result": "Invalid tool call format", "status": "error"})
             continue

         tool_name = tool_content.get("tool_name")
         task_instruction = tool_content.get("task_instruction")

         if not tool_name or not task_instruction:
             print(f"[AGENT_EXEC] Skipping tool call {i+1} (task {task_id}) due to missing tool_name or task_instruction.")
             all_tool_results.append({"tool_name": tool_name or "unknown", "tool_result": "Missing tool name or instruction", "status": "error"})
             continue

         tool_handler = tool_handlers.get(tool_name)
         if not tool_handler:
              error_msg = f"Tool '{tool_name}' not found."
              print(f"[AGENT_EXEC] {error_msg} (Task {task_id})")
              all_tool_results.append({"tool_name": tool_name, "tool_result": error_msg, "status": "error"})
              continue

         # Prepare input for the tool handler, including user_id and previous result
         tool_input = {"input": str(task_instruction), "user_id": user_id}
         if tool_content.get("previous_tool_response", False) and previous_tool_result:
             tool_input["previous_tool_response"] = previous_tool_result

         print(f"[AGENT_EXEC] Invoking tool handler '{tool_name}' for task {task_id} (User: {user_id})...")
         try:
              # Tool handlers are async and must accept `user_id` in their input dictionary.
              tool_result_main = await tool_handler(tool_input)
         except Exception as e:
             error_msg = f"Error executing tool '{tool_name}' for task {task_id} (User: {user_id}): {e}"
             print(f"[ERROR] {error_msg}")
             traceback.print_exc()
             all_tool_results.append({"tool_name": tool_name, "tool_result": error_msg, "status": "error"})
             previous_tool_result = error_msg # Store error as previous result for context
             continue

         # Handle Approval Flow: If tool requires user approval
         if isinstance(tool_result_main, dict) and tool_result_main.get("action") == "approve":
              print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) requires approval for tool '{tool_name}'.")
              approval_data = tool_result_main.get("tool_call", {}) # Data needed for approval
              await task_queue.set_task_approval_pending(task_id, approval_data) # Sets task status and notifies user
              return APPROVAL_PENDING_SIGNAL # Signal to processor that task is paused

         # Store Normal Tool Result
         else:
              # Extract actual result, handling cases where tool_result_main might be a dict wrapper
              tool_result = tool_result_main.get("tool_result", tool_result_main) if isinstance(tool_result_main, dict) else tool_result_main
              print(f"[AGENT_EXEC] Tool '{tool_name}' executed successfully for task {task_id}. Storing result.")
              previous_tool_result = tool_result # Update for next tool in sequence
              all_tool_results.append({"tool_name": tool_name, "tool_result": tool_result, "status": "success"})

    # --- Final Reflection/Summarization on Tool Results ---
    if not all_tool_results:
         print(f"[AGENT_EXEC] No successful tool calls or actions performed for task {task_id} (User: {user_id}).")
         return "No specific actions were taken based on your request."

    print(f"[AGENT_EXEC] Task {task_id} (User: {user_id}) requires final reflection/summarization on tool results...")
    final_result_str = "No final summary generated from tool actions."
    try:
        # Special handling for inbox summarization if it's the only tool used
        if len(all_tool_results) == 1 and all_tool_results[0].get("tool_name") == "search_inbox":
             # Logic for inbox_summarizer_runnable if needed, or handled by reflection
             # For now, assume reflection_runnable handles all cases.
             final_result_str = reflection_runnable.invoke({"tool_results": all_tool_results})

        else: # General reflection for multiple or other tool results
             final_result_str = reflection_runnable.invoke({"tool_results": all_tool_results})
        print(f"[AGENT_EXEC] Reflection/Summarization finished for task {task_id}.")
    except Exception as e:
         final_result_str = f"Error generating final summary of actions: {e}"
         print(f"[ERROR] {final_result_str} (Task {task_id}, User: {user_id})")

    return final_result_str


# --- FastAPI Application Setup ---
print(f"[FASTAPI] {datetime.now()}: Initializing FastAPI app...")
app = FastAPI(
    title="Sentient API",
    description="API for the Sentient application, providing chat, agent, memory, and other functionalities.",
    version="1.0.0",
    docs_url="/docs", # Path for Swagger UI
    redoc_url=None    # Disable ReDoc
)
print(f"[FASTAPI] {datetime.now()}: FastAPI app initialized.")

# CORS (Cross-Origin Resource Sharing) Middleware
# Allows requests from specified origins (e.g., Electron frontend, localhost for dev).
print(f"[FASTAPI] {datetime.now()}: Adding CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["app://.", "http://localhost:3000", "http://localhost"], # Whitelist specific origins
    allow_credentials=True, # Allow cookies and authorization headers
    allow_methods=["*"],    # Allow all HTTP methods
    allow_headers=["*"]     # Allow all headers
)
print(f"[FASTAPI] {datetime.now()}: CORS middleware added.")


# --- FastAPI Startup and Shutdown Events (Lifespan) ---
@app.on_event("startup")
async def startup_event():
    """
    Handles application startup procedures. This includes loading models,
    initializing background tasks, and setting up any necessary resources.
    """
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application startup event triggered.")

    # --- Load STT/TTS Models ---
    # These models are loaded here to ensure they are ready when the app starts,
    # but not during global script initialization which can be slow.
    global stt_model, tts_model # Make them accessible globally within this module

    print("[FASTAPI_LIFECYCLE] Loading STT (Speech-to-Text) model...")
    try:
        stt_model = FasterWhisperSTT(model_size="base", device="cpu", compute_type="int8")
        print("[FASTAPI_LIFECYCLE] STT model loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load STT model during startup: {e}")
        # App can continue without STT if it's optional, or exit if critical.

    print("[FASTAPI_LIFECYCLE] Loading TTS (Text-to-Speech) model...")
    try:
        tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
        print("[FASTAPI_LIFECYCLE] TTS model loaded successfully.")
    except Exception as e:
        print(f"[ERROR] FATAL: Could not load TTS model during startup: {e}")
        exit(1) # Exit if TTS model, considered critical, fails to load.

    # Load pending tasks and memory operations from persistent storage (if any)
    # TODO: Implement user scoping if tasks/operations are stored per user.
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Loading tasks from storage...")
    await task_queue.load_tasks()
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Loading memory operations from storage...")
    await memory_backend.memory_queue.load_operations()

    # Start background processors for task queue, memory operations, and cleanup
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Creating background task processors...")
    asyncio.create_task(process_queue())
    asyncio.create_task(process_memory_operations())
    asyncio.create_task(cleanup_tasks_periodically())

    # Context engines (Gmail, Calendar, Internet) might need user-specific initialization
    # or dynamic handling based on user_id per request. Deferred for now.
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Context engine initialization deferred (needs user context).")
    # TODO: Consider how context engines are managed if they maintain user-specific state or connections.

    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Handles application shutdown procedures. This includes saving any pending data
    and gracefully closing resources.
    """
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Application shutdown event triggered.")
    # Save pending tasks and memory operations to persistent storage
    await task_queue.save_tasks()
    await memory_backend.memory_queue.save_operations()
    print(f"[FASTAPI_LIFECYCLE] {datetime.now()}: Tasks and memory operations saved.")
    # Any other cleanup (e.g., closing database connections if not managed by driver)

# --- Pydantic Models for Request/Response Validation ---
# These models define the expected structure of data for API endpoints.

class Message(BaseModel):
    """Request model for standard chat messages."""
    input: str = Field(..., description="The user's input message.")
    pricing: str = Field(..., description="Current pricing plan of the user (e.g., 'free', 'pro').")
    credits: int = Field(..., description="Number of credits the user has.")

class ElaboratorMessage(BaseModel):
    """Request model for the elaborator endpoint."""
    input: str = Field(..., description="The text to be elaborated.")
    purpose: str = Field(..., description="The purpose or context for elaboration.")

class EncryptionRequest(BaseModel):
    """Request model for data encryption."""
    data: str = Field(..., description="The string data to encrypt.")

class DecryptionRequest(BaseModel):
    """Request model for data decryption."""
    encrypted_data: str = Field(..., description="The encrypted string data to decrypt.")

# Request models where user_id is implicitly obtained from the auth token
class ReferrerStatusRequest(BaseModel):
    """Request model to set referrer status (user_id from token)."""
    referrer_status: bool

class BetaUserStatusRequest(BaseModel):
    """Request model to set beta user status (user_id from token)."""
    beta_user_status: bool

class SetReferrerRequest(BaseModel):
    """Request model to set a user (found by referral_code) as a referrer."""
    referral_code: str

class DeleteSubgraphRequest(BaseModel):
    """Request model to delete a subgraph by source (user_id from token)."""
    source: str = Field(..., description="The source key of the subgraph to delete (e.g., 'linkedin').")

class GraphRequest(BaseModel):
    """Request model for graph customization (user_id from token)."""
    information: str = Field(..., description="Information to be processed into the graph.")

class GraphRAGRequest(BaseModel):
    """Request model for Graph RAG queries (user_id from token)."""
    query: str = Field(..., description="The query to run against the graph using RAG.")

class RedditURL(BaseModel):
    """Request model for scraping Reddit data (user_id from token)."""
    url: str = Field(..., description="The Reddit URL to scrape.")

class TwitterURL(BaseModel):
    """Request model for scraping Twitter data (user_id from token)."""
    url: str = Field(..., description="The Twitter URL to scrape.")

class LinkedInURL(BaseModel):
    """Request model for scraping LinkedIn data (user_id from token)."""
    url: str = Field(..., description="The LinkedIn profile URL to scrape.")

class SetDataSourceEnabledRequest(BaseModel):
    """Request model to enable/disable a data source (user_id from token)."""
    source: str = Field(..., description="The name of the data source (e.g., 'gmail').")
    enabled: bool = Field(..., description="True to enable, False to disable.")

class CreateTaskRequest(BaseModel):
    """Request model for creating a new task (user_id from token)."""
    description: str = Field(..., description="The description of the task.")

class UpdateTaskRequest(BaseModel):
    """Request model for updating an existing task (user_id from token for ownership check)."""
    task_id: str = Field(..., description="The ID of the task to update.")
    description: str = Field(..., description="The new description for the task.")
    priority: int = Field(..., ge=1, le=5, description="The new priority for the task (1-5).")

class DeleteTaskRequest(BaseModel):
    """Request model for deleting a task (user_id from token for ownership check)."""
    task_id: str = Field(..., description="The ID of the task to delete.")

class GetShortTermMemoriesRequest(BaseModel):
    """Request model for fetching short-term memories (user_id from token)."""
    category: str = Field(..., description="The category of memories to fetch.")
    limit: int = Field(10, ge=1, description="The maximum number of memories to return.")

class UpdateUserDataRequest(BaseModel):
    """Request model for setting/overwriting user profile data (user_id from token)."""
    data: Dict[str, Any] = Field(..., description="A dictionary of user data to set.")

class AddUserDataRequest(BaseModel):
    """Request model for adding/merging user profile data (user_id from token)."""
    data: Dict[str, Any] = Field(..., description="A dictionary of user data to add/merge.")

class AddMemoryRequest(BaseModel):
    """Request model for adding a short-term memory (user_id from token)."""
    text: str = Field(..., description="The content of the memory.")
    category: str = Field(..., description="The category for this memory.")
    retention_days: int = Field(..., ge=1, description="Number of days to retain the memory.")

class UpdateMemoryRequest(BaseModel):
    """Request model for updating a short-term memory (user_id from token)."""
    id: int = Field(..., description="The ID of the memory to update.")
    text: str = Field(..., description="The new content for the memory.")
    category: str = Field(..., description="The new category for the memory.")
    retention_days: int = Field(..., ge=1, description="New retention period in days.")

class DeleteMemoryRequest(BaseModel):
    """Request model for deleting a short-term memory (user_id from token)."""
    id: int = Field(..., description="The ID of the memory to delete.")
    category: str = Field(..., description="The category of the memory to delete from.")

class TaskIdRequest(BaseModel):
    """Generic request model for operations requiring a task_id (user_id from token)."""
    task_id: str = Field(..., description="The ID of the task.")

# Response models
class TaskApprovalDataResponse(BaseModel):
    """Response model for task approval data."""
    approval_data: Optional[Dict[str, Any]] = None

class ApproveTaskResponse(BaseModel):
    """Response model for approving a task."""
    message: str
    result: Any


# --- API Endpoints ---

@app.get("/", status_code=status.HTTP_200_OK, summary="API Root", tags=["General"])
async def main_root():
    """
    Root endpoint for the API. Returns a simple welcome message.
    """
    return {"message": "Sentient API is running."}

@app.post("/get-history", status_code=status.HTTP_200_OK, summary="Get Chat History", tags=["Chat"])
async def get_history(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the chat history for the currently authenticated user.
    This includes messages from the active chat session and the active chat ID.
    """
    print(f"[ENDPOINT /get-history] {datetime.now()}: Called by user {user_id}.")
    try:
        messages = await get_chat_history_messages(user_id)
        async with db_lock: # Acquire lock to safely read active_chat_id
            chatsDb = await load_db(user_id)
            current_active_chat_id = chatsDb.get("active_chat_id", 0)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"messages": messages, "activeChatId": current_active_chat_id}
        )
    except Exception as e:
        print(f"[ERROR] /get-history for user {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history."
        )

@app.post("/clear-chat-history", status_code=status.HTTP_200_OK, summary="Clear Chat History", tags=["Chat"])
async def clear_chat_history_endpoint(user_id: str = Depends(auth.get_current_user)): # Renamed to avoid conflict
    """
    Clears all chat history for the authenticated user, resetting it to an initial state.
    """
    print(f"[ENDPOINT /clear-chat-history] {datetime.now()}: Called by user {user_id}.")
    async with db_lock: # Ensure exclusive access to the user's chat DB file
        try:
            chatsDb = initial_db.copy() # Reset to the default initial structure
            await save_db(user_id, chatsDb) # Save the reset structure for this user
            print(f"[ENDPOINT /clear-chat-history] User {user_id} - Chat DB reset and saved.")
            # TODO: If any in-memory chat history components are user-specific, clear them here.
            # e.g., chat_history.clear_for_user(user_id) if such a method exists.
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Chat history cleared successfully.", "activeChatId": 0}
            )
        except Exception as e:
            print(f"[ERROR] /clear-chat-history for user {user_id}: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear chat history."
            )

@app.post("/chat", status_code=status.HTTP_200_OK, summary="Process Chat Message", tags=["Chat"])
async def chat(message: Message, user_id: str = Depends(auth.get_current_user)):
    """
    Handles incoming chat messages from the authenticated user.
    It classifies the input, retrieves context (memory, internet),
    and generates a response, potentially creating agent tasks or updating memory.
    This endpoint returns a streaming response (application/x-ndjson).
    """
    endpoint_start_time = time.time()
    print(f"[ENDPOINT /chat] {datetime.now()}: Called by user {user_id}. Input: '{message.input[:50]}...'")

    # Ensure global runnables and backends are accessible (Python's global scope rules)
    global chat_runnable, agent_runnable, unified_classification_runnable, memory_backend, task_queue
    global priority_runnable, internet_query_reframe_runnable, internet_summary_runnable
    # Other runnables like reflection_runnable are used indirectly.

    try:
        # --- Load User Profile ---
        user_profile_data = await load_user_profile(user_id) # Load this user's profile
        if not user_profile_data or "userData" not in user_profile_data:
            # This indicates an issue with profile storage or initialization for the user
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User profile could not be loaded or is incomplete.")
        username = user_profile_data.get("userData", {}).get("personalInfo", {}).get("name", "User")
        personality_setting = user_profile_data.get("userData", {}).get("personality", "Default helpful assistant")
        print(f"[ENDPOINT /chat] User {user_id} - Profile loaded: Name='{username}'")

        # --- Determine Active Chat ID ---
        # Ensure an active chat exists or is created for the user.
        await get_chat_history_messages(user_id) # This also handles inactivity and creates new chats
        async with db_lock: # Safely read the potentially updated active_chat_id
            chatsDb = await load_db(user_id)
            active_chat_id = chatsDb.get("active_chat_id", 0)
        if active_chat_id == 0: # Should not happen if get_chat_history_messages works correctly
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine or create an active chat for the user.")
        print(f"[ENDPOINT /chat] User {user_id} - Active chat ID: {active_chat_id}")

        # --- Ensure Runnables use Correct History (Currently Global) ---
        # TODO: This is a significant point for multi-user scaling.
        # The `chat_history` object is global. For true multi-tenancy,
        # runnables needing history (chat_runnable, agent_runnable, unified_classification_runnable)
        # would need to be instantiated per request with user-specific history,
        # or designed to accept user_id and fetch history internally.
        # For now, assuming they handle context correctly or the impact is managed.
        # current_chat_history = get_user_specific_chat_history(user_id) # Idealized
        # chat_runnable = get_chat_runnable(current_chat_history)

        # --- Unified Input Classification ---
        print(f"[ENDPOINT /chat] User {user_id} - Classifying input: '{message.input[:50]}...'")
        # Invoke the classification runnable (assumed to be thread-safe or stateless regarding user history here)
        unified_output = unified_classification_runnable.invoke({"query": message.input})
        category = unified_output.get("category", "chat")
        use_personal_context = unified_output.get("use_personal_context", False)
        internet_search_type = unified_output.get("internet", "None") # e.g., "None", "Quick", "Deep"
        transformed_input = unified_output.get("transformed_input", message.input)
        print(f"[ENDPOINT /chat] User {user_id} - Classification result: Category='{category}', PersonalContext='{use_personal_context}', Internet='{internet_search_type}'")

        pricing_plan = message.pricing
        credits = message.credits

        # --- Streaming Response Generator ---
        async def response_generator():
            """
            Asynchronous generator for streaming chat responses.
            Yields JSON objects for different stages of processing and the final AI response.
            """
            stream_start_time = time.time()
            print(f"[STREAM /chat] User {user_id} - Starting stream for chat {active_chat_id}.")
            memory_used, agents_used, internet_used, pro_features_used = False, False, False, False # Renamed for clarity
            user_context_str, internet_context_str, additional_notes = None, None, "" # Renamed

            # 1. Add User Message to DB (Visible)
            user_msg_id = await add_message_to_db(user_id, active_chat_id, message.input, is_user=True, is_visible=True)
            if not user_msg_id:
                print(f"[ERROR] Failed to add user message to DB for user {user_id}, chat {active_chat_id}.")
                yield json.dumps({"type":"error", "message":"Failed to save your message."})+"\n"
                return

            # 2. Yield User Message Confirmation (for UI update)
            user_msg_timestamp = datetime.now(timezone.utc).isoformat()
            yield json.dumps({"type": "userMessage", "id": user_msg_id, "message": message.input, "timestamp": user_msg_timestamp}) + "\n"
            await asyncio.sleep(0.01) # Small delay to ensure message is processed by client

            # 3. Prepare Assistant Message Structure (for later population)
            assistant_msg_id_ts = str(int(time.time() * 1000)) # Timestamp-based ID for assistant message
            assistant_msg_base = { # Renamed for clarity
                "id": assistant_msg_id_ts, "message": "", "isUser": False,
                "memoryUsed": False, "agentsUsed": False, "internetUsed": False,
                "timestamp": datetime.now(timezone.utc).isoformat(), "isVisible": True
            }

            # --- Handle "Agent" Category (Task Creation) ---
            if category == "agent":
                agents_used = True
                assistant_msg_base["agentsUsed"] = True
                print(f"[STREAM /chat] User {user_id} - Input classified as 'agent' task for: '{transformed_input[:50]}...'")

                # Determine task priority
                priority_response = priority_runnable.invoke({"task_description": transformed_input})
                priority = priority_response.get("priority", 3) # Default priority
                print(f"[STREAM /chat] User {user_id} - Adding agent task with priority: {priority}...")

                # Add task to the queue (passes all necessary context including user_id)
                await task_queue.add_task(
                    user_id=user_id,
                    chat_id=active_chat_id,
                    description=transformed_input,
                    priority=priority,
                    username=username,
                    personality=personality_setting,
                    use_personal_context=use_personal_context,
                    internet=internet_search_type
                )
                print(f"[STREAM /chat] User {user_id} - Agent task added to queue.")

                # Confirmation message for the user
                assistant_msg_base["message"] = "Okay, I'll get right on that for you."
                # Store the hidden user prompt that triggered the agent
                await add_message_to_db(user_id, active_chat_id, transformed_input, is_user=True, is_visible=False)
                # Store the AI's confirmation message (visible)
                await add_message_to_db(
                    user_id, active_chat_id, assistant_msg_base["message"], is_user=False, is_visible=True,
                    agentsUsed=True, task=transformed_input
                )

                # Yield final message directly for agent task creation
                yield json.dumps({
                    "type": "assistantMessage", "messageId": assistant_msg_base["id"],
                    "message": assistant_msg_base["message"], "memoryUsed": False,
                    "agentsUsed": True, "internetUsed": False, "done": True, "proUsed": False
                }) + "\n"
                return # End stream for agent task creation

            # --- Handle Memory/Context Retrieval (for "chat" or "memory" categories if personal context needed) ---
            if category == "memory" or use_personal_context:
                memory_used = True
                assistant_msg_base["memoryUsed"] = True
                yield json.dumps({"type": "intermediary", "message": "Checking your context...", "id": assistant_msg_id_ts}) + "\n"
                print(f"[STREAM /chat] User {user_id} - Retrieving memory context for: '{transformed_input[:50]}...'")
                try:
                    # Retrieve relevant memories for the user based on the input
                    user_context_str = await memory_backend.retrieve_memory(user_id, transformed_input)
                    if user_context_str:
                        print(f"[STREAM /chat] User {user_id} - Retrieved user context, length: {len(str(user_context_str))}")
                    else:
                        print(f"[STREAM /chat] User {user_id} - No relevant memories found for this input.")
                except Exception as e:
                    print(f"[ERROR] Memory retrieval error for user {user_id}: {e}")
                    user_context_str = f"Error retrieving your context: {e}" # Inform user in response potentially

                # If category is explicitly "memory", queue an operation to update memory
                if category == "memory":
                    if pricing_plan == "free" and credits <= 0:
                        additional_notes += " (Memory update skipped: Pro features or credits needed)"
                        print(f"[STREAM /chat] User {user_id} - Free plan/credits exhausted. Skipping memory update.")
                    else:
                        pro_features_used = True # Updating memory is a pro feature
                        print(f"[STREAM /chat] User {user_id} - Queueing memory update operation...")
                        # Add operation to memory queue (processed in background)
                        asyncio.create_task(memory_backend.add_operation(user_id, transformed_input))

            # --- Handle Internet Search ---
            if internet_search_type and internet_search_type != "None":
                internet_used = True
                assistant_msg_base["internetUsed"] = True
                if pricing_plan == "free" and credits <= 0:
                    additional_notes += " (Internet search skipped: Pro features or credits needed)"
                    print(f"[STREAM /chat] User {user_id} - Free plan/credits exhausted. Skipping internet search.")
                else:
                    pro_features_used = True # Internet search is a pro feature
                    yield json.dumps({"type": "intermediary", "message": "Searching the internet...", "id": assistant_msg_id_ts}) + "\n"
                    print(f"[STREAM /chat] User {user_id} - Performing internet search for: '{transformed_input[:50]}...'")
                    try:
                        reframed_query = get_reframed_internet_query(internet_query_reframe_runnable, transformed_input)
                        search_results = get_search_results(reframed_query)
                        internet_context_str = get_search_summary(internet_summary_runnable, search_results)
                        if internet_context_str:
                            print(f"[STREAM /chat] User {user_id} - Internet search summary length: {len(str(internet_context_str))}")
                        else:
                            print(f"[STREAM /chat] User {user_id} - No summary generated from internet search.")
                    except Exception as e:
                        print(f"[ERROR] Internet search error for user {user_id}: {e}")
                        internet_context_str = f"Error during internet search: {e}"

            # --- Generate Chat/Memory Response (for "chat" or "memory" categories) ---
            if category in ["chat", "memory"]:
                yield json.dumps({"type": "intermediary", "message": "Thinking...", "id": assistant_msg_id_ts}) + "\n"
                full_response_text = "" # Accumulate streamed tokens
                try:
                    # Generate response using the chat runnable, streaming tokens
                    # TODO: Ensure chat_runnable uses user-specific history
                    async for token in generate_streaming_response(
                        chat_runnable,
                        inputs={
                            "query": transformed_input,
                            "user_context": user_context_str,
                            "internet_context": internet_context_str,
                            "name": username,
                            "personality": personality_setting
                        },
                        stream=True
                    ):
                        if isinstance(token, str):
                             full_response_text += token
                             # Yield each token as it's generated
                             yield json.dumps({"type": "assistantStream", "token": token, "done": False, "messageId": assistant_msg_base["id"]}) + "\n"
                        await asyncio.sleep(0.01) # Small delay between tokens for smoother streaming

                    # Final stream packet with completion status and metadata
                    final_message_content = full_response_text + (("\n\n" + additional_notes) if additional_notes else "")
                    assistant_msg_base["message"] = final_message_content
                    yield json.dumps({
                        "type": "assistantStream",
                        "token": ("\n\n" + additional_notes) if additional_notes else "", # Send notes as part of final packet if any
                        "done": True,
                        "memoryUsed": memory_used,
                        "agentsUsed": agents_used, # Will be False here, handled above
                        "internetUsed": internet_used,
                        "proUsed": pro_features_used,
                        "messageId": assistant_msg_base["id"]
                    }) + "\n"

                    # Save final assistant message to DB
                    await add_message_to_db(
                        user_id, active_chat_id, final_message_content, is_user=False, is_visible=True,
                        memoryUsed=memory_used, agentsUsed=agents_used, internetUsed=internet_used
                    )

                except Exception as e:
                     print(f"[ERROR] Chat generation error for user {user_id}: {e}")
                     traceback.print_exc()
                     error_message_for_user = "Sorry, I encountered an error while generating that response."
                     assistant_msg_base["message"] = error_message_for_user
                     # Send error indication in stream
                     yield json.dumps({"type": "assistantStream", "token": error_message_for_user, "done": True, "error": True, "messageId": assistant_msg_base["id"]}) + "\n"
                     # Save error message to DB
                     await add_message_to_db(user_id, active_chat_id, error_message_for_user, is_user=False, is_visible=True, error=True) # Added error flag

            stream_duration = time.time() - stream_start_time
            print(f"[STREAM /chat] User {user_id} - Stream finished for chat {active_chat_id}. Duration: {stream_duration:.2f}s")

        # Return the streaming response
        print(f"[ENDPOINT /chat] User {user_id} - Returning StreamingResponse.")
        return StreamingResponse(response_generator(), media_type="application/x-ndjson")

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (e.g., from auth, validation, or explicit raises)
        raise http_exc
    except Exception as e:
        print(f"[ERROR] Unexpected error in /chat endpoint for user {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during chat processing."
        )
    finally:
        endpoint_duration = time.time() - endpoint_start_time
        print(f"[ENDPOINT /chat] User {user_id} - Request processing finished. Duration: {endpoint_duration:.2f}s")


@app.post("/elaborator", status_code=status.HTTP_200_OK, summary="Elaborate Text", tags=["Utilities"])
async def elaborate(message: ElaboratorMessage): # Consider adding Depends(auth.get_current_user) if sensitive
    """
    Elaborates on the input text based on the provided purpose.
    Uses a specific LangChain runnable for this task.
    """
    print(f"[ENDPOINT /elaborator] {datetime.now()}: Called with input: '{message.input[:50]}...', purpose: '{message.purpose}'")
    try:
         # Get a tool runnable configured for elaboration
         elaborator_runnable = get_tool_runnable(
             elaborator_system_prompt_template,
             elaborator_user_prompt_template,
             None, # No specific required format for output
             ["query", "purpose"] # Expected input keys
         )
         output = elaborator_runnable.invoke({"query": message.input, "purpose": message.purpose})
         return JSONResponse(status_code=status.HTTP_200_OK, content={"message": output})
    except Exception as e:
        print(f"[ERROR] /elaborator: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text elaboration failed."
        )


# --- Tool Handlers (Registered Callbacks for Agent Actions) ---
# These functions are called when an agent decides to use a specific tool.
# They now accept `tool_call_input` which includes `user_id`.

@register_tool("gmail")
async def gmail_tool(tool_call_input: dict) -> Dict[str, Any]:
    """
    Handles Gmail-related tasks invoked by the agent for a specific user.
    It can send emails, reply, search, etc., potentially requiring user approval for actions.

    Args:
        tool_call_input: A dictionary containing 'input' (task instruction) and 'user_id'.
                         May also contain 'previous_tool_response'.

    Returns:
        A dictionary with 'tool_result' or an 'action':'approve' structure.
    """
    user_id = tool_call_input.get("user_id")
    if not user_id:
        return {"status": "failure", "error": "User context (user_id) missing in tool call for Gmail."}
    print(f"[TOOL HANDLER gmail] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")

    try:
         user_profile = await load_user_profile(user_id) # Load profile for username, etc.
         username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")

         # Get a runnable configured for Gmail agent tasks
         tool_runnable = get_tool_runnable(
             gmail_agent_system_prompt_template,
             gmail_agent_user_prompt_template,
             gmail_agent_required_format, # Expected JSON format from LLM
             ["query", "username", "previous_tool_response"]
         )
         # Invoke the LLM to determine the specific Gmail action and parameters
         tool_call_str_output = tool_runnable.invoke({
             "query": str(tool_call_input["input"]),
             "username": username,
             "previous_tool_response": tool_call_input.get("previous_tool_response")
         })

         # Robust JSON parsing of LLM output
         try:
             tool_call_dict = json.loads(tool_call_str_output)
         except json.JSONDecodeError:
             error_msg = f"Invalid JSON response from Gmail LLM: {tool_call_str_output}"
             print(f"[ERROR] Gmail Tool for {user_id}: {error_msg}")
             tool_call_dict = {"tool_name": "error_parsing_llm_output", "task_instruction": error_msg}


         actual_tool_name = tool_call_dict.get("tool_name")
         print(f"[TOOL HANDLER gmail] User {user_id} - LLM proposed Gmail action: {actual_tool_name}")

         # If action requires approval (e.g., sending/replying), return approval request
         if actual_tool_name in ["send_email", "reply_email"]:
              return {"action": "approve", "tool_call": tool_call_dict}
         else:
              # Execute other Gmail actions directly (e.g., search, read)
              # `parse_and_execute_tool_calls` needs user_id for Google auth context
              tool_result = await parse_and_execute_tool_calls(user_id, json.dumps(tool_call_dict))
              return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] Gmail Tool execution failed for user {user_id}: {e}")
        traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gdrive")
async def drive_tool(tool_call_input: dict) -> Dict[str, Any]:
    """Handles Google Drive related tasks for the user (e.g., search files)."""
    user_id = tool_call_input.get("user_id")
    if not user_id: return {"status": "failure", "error": "User context missing for GDrive."}
    print(f"[TOOL HANDLER gdrive] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")
    try:
         tool_runnable = get_tool_runnable(
             gdrive_agent_system_prompt_template,
             gdrive_agent_user_prompt_template,
             gdrive_agent_required_format,
             ["query", "previous_tool_response"]
         )
         tool_call_str = tool_runnable.invoke({
             "query": str(tool_call_input["input"]),
             "previous_tool_response": tool_call_input.get("previous_tool_response")
         })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Needs user_id
         return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] GDrive Tool for user {user_id}: {e}"); traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gdocs")
async def gdoc_tool(tool_call_input: dict) -> Dict[str, Any]:
    """Handles Google Docs related tasks for the user."""
    user_id = tool_call_input.get("user_id")
    if not user_id: return {"status": "failure", "error": "User context missing for GDocs."}
    print(f"[TOOL HANDLER gdocs] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")
    try:
         tool_runnable = get_tool_runnable(
             gdocs_agent_system_prompt_template,
             gdocs_agent_user_prompt_template,
             gdocs_agent_required_format,
             ["query", "previous_tool_response"]
         )
         tool_call_str = tool_runnable.invoke({
             "query": str(tool_call_input["input"]),
             "previous_tool_response": tool_call_input.get("previous_tool_response")
         })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Needs user_id
         return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] GDocs Tool for user {user_id}: {e}"); traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gsheets")
async def gsheet_tool(tool_call_input: dict) -> Dict[str, Any]:
    """Handles Google Sheets related tasks for the user."""
    user_id = tool_call_input.get("user_id")
    if not user_id: return {"status": "failure", "error": "User context missing for GSheets."}
    print(f"[TOOL HANDLER gsheets] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")
    try:
         tool_runnable = get_tool_runnable(
             gsheets_agent_system_prompt_template,
             gsheets_agent_user_prompt_template,
             gsheets_agent_required_format,
             ["query", "previous_tool_response"]
         )
         tool_call_str = tool_runnable.invoke({
             "query": str(tool_call_input["input"]),
             "previous_tool_response": tool_call_input.get("previous_tool_response")
         })
         tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Needs user_id
         return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] GSheets Tool for user {user_id}: {e}"); traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gslides")
async def gslides_tool(tool_call_input: dict) -> Dict[str, Any]:
    """Handles Google Slides related tasks for the user."""
    user_id = tool_call_input.get("user_id")
    if not user_id: return {"status": "failure", "error": "User context missing for GSlides."}
    print(f"[TOOL HANDLER gslides] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User")
        tool_runnable = get_tool_runnable(
            gslides_agent_system_prompt_template,
            gslides_agent_user_prompt_template,
            gslides_agent_required_format,
            ["query", "user_name", "previous_tool_response"]
        )
        tool_call_str = tool_runnable.invoke({
            "query": str(tool_call_input["input"]),
            "user_name": username,
            "previous_tool_response": tool_call_input.get("previous_tool_response")
        })
        tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Needs user_id
        return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] GSlides Tool for user {user_id}: {e}"); traceback.print_exc()
        return {"status": "failure", "error": str(e)}

@register_tool("gcalendar")
async def gcalendar_tool(tool_call_input: dict) -> Dict[str, Any]:
    """Handles Google Calendar related tasks for the user (e.g., list events, create event)."""
    user_id = tool_call_input.get("user_id")
    if not user_id: return {"status": "failure", "error": "User context missing for GCalendar."}
    print(f"[TOOL HANDLER gcalendar] Called for user {user_id} with input: '{str(tool_call_input.get('input'))[:50]}...'")
    try:
        current_time_iso = datetime.now(timezone.utc).isoformat()
        try:
            local_timezone_key = str(get_localzone()) # Attempt to get local timezone
        except Exception:
            local_timezone_key = "UTC" # Default to UTC if local cannot be determined
            print(f"[WARN] GCalendar Tool for user {user_id}: Could not determine local timezone, defaulting to UTC.")

        tool_runnable = get_tool_runnable(
            gcalendar_agent_system_prompt_template,
            gcalendar_agent_user_prompt_template,
            gcalendar_agent_required_format,
            ["query", "current_time", "timezone", "previous_tool_response"]
        )
        tool_call_str = tool_runnable.invoke({
            "query": str(tool_call_input["input"]),
            "current_time": current_time_iso,
            "timezone": local_timezone_key,
            "previous_tool_response": tool_call_input.get("previous_tool_response")
        })
        tool_result = await parse_and_execute_tool_calls(user_id, tool_call_str) # Needs user_id
        return {"tool_result": tool_result}
    except Exception as e:
        print(f"[ERROR] GCalendar Tool for user {user_id}: {e}"); traceback.print_exc()
        return {"status": "failure", "error": str(e)}


# --- Utility Endpoints (Protected by Auth) ---

@app.post("/get-role", status_code=status.HTTP_200_OK, summary="Get User Role", tags=["User Management"])
async def get_role(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the role(s) assigned to the authenticated user from Auth0.
    Requires Auth0 Management API access.
    """
    print(f"[ENDPOINT /get-role] Called by user {user_id}.")
    try:
        mgmt_token = get_management_token() # Helper to get Auth0 Management API token
        if not mgmt_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth0 Management API token unavailable.")

        roles_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles"
        headers = {"Authorization": f"Bearer {mgmt_token}"}
        async with httpx.AsyncClient() as client:
            roles_response = await client.get(roles_url, headers=headers)

        if roles_response.status_code != 200:
            raise HTTPException(
                status_code=roles_response.status_code,
                detail=f"Auth0 API Error fetching roles: {roles_response.text}"
            )
        roles_data = roles_response.json()
        # Assuming a user primarily has one relevant role for this app's logic
        user_role_name = roles_data[0]['name'].lower() if roles_data and roles_data[0].get('name') else "free"
        print(f"User {user_id} role determined as: {user_role_name}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"role": user_role_name})
    except Exception as e:
        print(f"[ERROR] /get-role for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user role."
        )

@app.post("/get-beta-user-status", status_code=status.HTTP_200_OK, summary="Get Beta User Status", tags=["User Management"])
async def get_beta_user_status(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the 'betaUser' status from the authenticated user's app_metadata in Auth0.
    """
    print(f"[ENDPOINT /get-beta-user-status] Called by user {user_id}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Management token unavailable.")

        user_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(user_url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(response.status_code, f"Auth0 API Error getting user: {response.text}")

        user_data = response.json()
        status_val = user_data.get("app_metadata", {}).get("betaUser")
        # Ensure consistent boolean conversion
        status_bool = str(status_val).lower() == 'true' if status_val is not None else False
        print(f"User {user_id} beta status: {status_bool}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"betaUserStatus": status_bool})
    except Exception as e:
        print(f"[ERROR] /get-beta-user-status for {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed beta status retrieval.")

@app.post("/get-referral-code", status_code=status.HTTP_200_OK, summary="Get Referral Code", tags=["User Management"])
async def get_referral_code(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the 'referralCode' from the authenticated user's app_metadata in Auth0.
    """
    print(f"[ENDPOINT /get-referral-code] Called by user {user_id}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Management token unavailable.")

        url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(response.status_code, f"Auth0 API Error: {response.text}")

        user_data = response.json()
        referral_code = user_data.get("app_metadata", {}).get("referralCode")
        if not referral_code:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Referral code not found for this user.")
        print(f"User {user_id} referral code found.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"referralCode": referral_code})
    except Exception as e:
        print(f"[ERROR] /get-referral-code for {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed referral code retrieval.")

@app.post("/get-referrer-status", status_code=status.HTTP_200_OK, summary="Get Referrer Status", tags=["User Management"])
async def get_referrer_status(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the 'referrer' status from the authenticated user's app_metadata in Auth0.
    Indicates if this user has successfully referred someone.
    """
    print(f"[ENDPOINT /get-referrer-status] Called by user {user_id}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Management token unavailable.")

        url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(response.status_code, f"Auth0 API Error: {response.text}")

        user_data = response.json()
        status_val = user_data.get("app_metadata", {}).get("referrer")
        status_bool = str(status_val).lower() == 'true' if status_val is not None else False
        print(f"User {user_id} referrer status: {status_bool}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"referrerStatus": status_bool})
    except Exception as e:
        print(f"[ERROR] /get-referrer-status for {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed referrer status retrieval.")

@app.post("/get-user-and-set-referrer-status", status_code=status.HTTP_200_OK, summary="Set Referrer Status by Code", tags=["User Management"])
async def get_user_and_set_referrer_status(request: SetReferrerRequest, user_id_making_request: str = Depends(auth.get_current_user)):
    """
    Finds a user by their referral_code and sets their 'referrer' app_metadata flag to True.
    The request is made by an authenticated user (user_id_making_request).
    """
    referral_code = request.referral_code
    print(f"[ENDPOINT /get-user-and-set-referrer-status] User {user_id_making_request} is setting referrer status for code {referral_code}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Management token unavailable.")

        headers = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}

        # Search for the user who owns the referral_code
        search_query = f'app_metadata.referralCode:"{referral_code}"'
        search_url = f"https://{AUTH0_DOMAIN}/api/v2/users"
        params = {'q': search_query, 'search_engine': 'v3'} # Use Auth0 search engine v3
        async with httpx.AsyncClient() as client:
            search_response = await client.get(search_url, headers=headers, params=params)

        if search_response.status_code != 200:
            raise HTTPException(search_response.status_code, f"Auth0 User Search Error: {search_response.text}")

        users_found = search_response.json()
        if not users_found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No user found with referral code: {referral_code}")

        user_to_set_id = users_found[0].get("user_id")
        if not user_to_set_id:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Found user matching referral code, but their user_id is missing.")
        print(f"Found user {user_to_set_id} matching referral code {referral_code}.")

        # Set 'referrer' status to True for the found user
        update_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_to_set_id}"
        update_headers = {"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
        update_payload = {"app_metadata": {"referrer": True}}
        async with httpx.AsyncClient() as client:
            set_status_response = await client.patch(update_url, headers=update_headers, json=update_payload)

        if set_status_response.status_code != 200:
            raise HTTPException(set_status_response.status_code, f"Auth0 User Update Error: {set_status_response.text}")

        print(f"Referrer status successfully set to True for user {user_to_set_id}.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Referrer status updated successfully for the referred user."})
    except Exception as e:
        print(f"[ERROR] /get-user-and-set-referrer-status for referral code {referral_code}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to set referrer status.")

@app.post("/get-user-and-invert-beta-user-status", status_code=status.HTTP_200_OK, summary="Invert Beta User Status", tags=["User Management"])
async def get_user_and_invert_beta_user_status(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the current 'betaUser' status for the authenticated user from Auth0,
    inverts it (True -> False, False -> True), and updates it in Auth0.
    """
    print(f"[ENDPOINT /get-user-and-invert-beta-user-status] Called by user {user_id}.")
    try:
        mgmt_token = get_management_token()
        if not mgmt_token: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Management token unavailable.")

        # Step 1: Get current betaUser status
        get_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}"
        get_headers = {"Authorization": f"Bearer {mgmt_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            get_response = await client.get(get_url, headers=get_headers)

        if get_response.status_code != 200:
            raise HTTPException(get_response.status_code, f"Auth0 Get User Error: {get_response.text}")

        user_data = get_response.json()
        current_status_val = user_data.get("app_metadata", {}).get("betaUser")
        current_bool_status = str(current_status_val).lower() == 'true' if current_status_val is not None else False
        inverted_status = not current_bool_status
        print(f"User {user_id} current beta status: {current_bool_status}. Will be set to: {inverted_status}")

        # Step 2: Set the inverted betaUser status
        set_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}" # Same URL for update
        set_headers = {"Authorization": f"Bearer {mgmt_token}", "Content-Type": "application/json"}
        set_payload = {"app_metadata": {"betaUser": inverted_status}}
        async with httpx.AsyncClient() as client:
            set_response = await client.patch(set_url, headers=set_headers, json=set_payload)

        if set_response.status_code != 200:
            raise HTTPException(set_response.status_code, f"Auth0 Set User Metadata Error: {set_response.text}")

        print(f"Beta user status successfully inverted to {inverted_status} for user {user_id}.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Beta user status inverted successfully."})
    except Exception as e:
        print(f"[ERROR] /get-user-and-invert-beta-user-status for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to invert beta user status.")

# Encryption/Decryption endpoints (Consider if these need auth or are public utilities)
@app.post("/encrypt", status_code=status.HTTP_200_OK, summary="Encrypt Data", tags=["Utilities"])
async def encrypt_data(request: EncryptionRequest):
    """
    Encrypts the provided string data using AES encryption.
    """
    try:
        encrypted_data = aes_encrypt(request.data)
        return JSONResponse(content={"encrypted_data": encrypted_data})
    except Exception as e:
        print(f"[ERROR] /encrypt: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Encryption failed.")

@app.post("/decrypt", status_code=status.HTTP_200_OK, summary="Decrypt Data", tags=["Utilities"])
async def decrypt_data(request: DecryptionRequest):
    """
    Decrypts the provided AES encrypted string data.
    """
    try:
        decrypted_data = aes_decrypt(request.encrypted_data)
        return JSONResponse(content={"decrypted_data": decrypted_data})
    except ValueError: # aes_decrypt might raise ValueError for bad padding/key
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Decryption failed: Invalid data or key.")
    except Exception as e:
        print(f"[ERROR] /decrypt: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Decryption failed.")


# --- Scraper Endpoints (Protected by Auth) ---
@app.post("/scrape-linkedin", status_code=status.HTTP_200_OK, summary="Scrape LinkedIn Profile", tags=["Scraping"])
async def scrape_linkedin(profile: LinkedInURL, user_id: str = Depends(auth.get_current_user)):
    """
    Scrapes a LinkedIn profile given its URL.
    The actual scraping logic runs in a thread pool to avoid blocking.
    """
    print(f"[ENDPOINT /scrape-linkedin] Called by user {user_id} for URL: {profile.url}")
    try:
        # `scrape_linkedin_profile` is a synchronous function, run it in executor
        linkedin_profile_data = await asyncio.to_thread(scrape_linkedin_profile, profile.url)
        return JSONResponse(content={"profile": linkedin_profile_data})
    except Exception as e:
        print(f"[ERROR] /scrape-linkedin for user {user_id}, URL {profile.url}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "LinkedIn profile scraping failed.")

@app.post("/scrape-reddit", status_code=status.HTTP_200_OK, summary="Scrape and Analyze Reddit Data", tags=["Scraping"])
async def scrape_reddit(reddit_url: RedditURL, user_id: str = Depends(auth.get_current_user)):
    """
    Scrapes data from a Reddit URL and then analyzes it to extract topics.
    Both scraping and analysis run in a thread pool.
    """
    print(f"[ENDPOINT /scrape-reddit] Called by user {user_id} for URL: {reddit_url.url}")
    try:
        subreddits_data = await asyncio.to_thread(reddit_scraper, reddit_url.url)
        if not subreddits_data:
            return JSONResponse(content={"topics": []}) # Return empty if no data scraped

        # Analyze the scraped data using the reddit_runnable
        analysis_response = await asyncio.to_thread(reddit_runnable.invoke, {"subreddits": subreddits_data})
        # Ensure consistent output format for topics
        topics = []
        if isinstance(analysis_response, list):
            topics = analysis_response
        elif isinstance(analysis_response, dict) and 'topics' in analysis_response:
            topics = analysis_response.get('topics', [])
        return JSONResponse(content={"topics": topics})
    except Exception as e:
        print(f"[ERROR] /scrape-reddit for user {user_id}, URL {reddit_url.url}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Reddit scraping or analysis failed.")

@app.post("/scrape-twitter", status_code=status.HTTP_200_OK, summary="Scrape and Analyze Twitter Data", tags=["Scraping"])
async def scrape_twitter(twitter_url: TwitterURL, user_id: str = Depends(auth.get_current_user)):
    """
    Scrapes recent tweets from a Twitter URL and analyzes them to extract topics.
    """
    print(f"[ENDPOINT /scrape-twitter] Called by user {user_id} for URL: {twitter_url.url}")
    try:
        tweets_data = await asyncio.to_thread(scrape_twitter_data, twitter_url.url, 20) # Scrape up to 20 tweets
        if not tweets_data:
            return JSONResponse(content={"topics": []})

        analysis_response = await asyncio.to_thread(twitter_runnable.invoke, {"tweets": tweets_data})
        topics = []
        if isinstance(analysis_response, list):
            topics = analysis_response
        elif isinstance(analysis_response, dict) and 'topics' in analysis_response:
            topics = analysis_response.get('topics', [])
        return JSONResponse(content={"topics": topics})
    except Exception as e:
        print(f"[ERROR] /scrape-twitter for user {user_id}, URL {twitter_url.url}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Twitter scraping or analysis failed.")

# --- Google Authentication Endpoint ---
@app.post("/authenticate-google", status_code=status.HTTP_200_OK, summary="Authenticate Google Services", tags=["Authentication"])
async def authenticate_google(user_id: str = Depends(auth.get_current_user)):
    """
    Checks for existing Google API credentials for the authenticated user.
    If credentials exist and are valid, returns success.
    If expired and refreshable, attempts to refresh them.
    If no valid credentials, indicates that authentication is required (currently implies server-side flow issue).
    Stores credentials in a user-specific pickle file.
    """
    print(f"[ENDPOINT /authenticate-google] Called by user {user_id}.")
    # User-specific path for storing Google OAuth tokens
    token_path = os.path.join(BASE_DIR, f"token_{user_id}.pickle") # Store in server/ not server/server
    creds = None
    try:
        # Load existing credentials if available
        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                creds = pickle.load(token_file)

        # Check if credentials are valid or need refresh
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                 print(f"Refreshing Google token for user {user_id}...")
                 creds.refresh(Request()) # Attempt to refresh the token
                 print(f"Google token refreshed for user {user_id}.")
            else:
                 # This branch means no valid token and no refresh token, or first-time auth.
                 # The `InstalledAppFlow`'s `run_local_server` is for CLI apps and won't work directly
                 # in a backend server context for multiple users without a more complex OAuth dance.
                 # For a web server, a web flow (Authorization Code Flow) is typically used, where the
                 # user is redirected to Google, authorizes, and Google redirects back with a code.
                 print(f"[WARN] Google token invalid/missing for user {user_id}. Interactive flow would be needed for initial auth.")
                 # flow = InstalledAppFlow.from_client_config(CREDENTIALS_DICT, SCOPES)
                 # creds = flow.run_local_server(port=0) # This line is problematic on a server.
                 raise HTTPException(
                     status_code=status.HTTP_401_UNAUTHORIZED,
                     detail=f"Google authentication required for user {user_id}. Please ensure credentials are set up via an appropriate OAuth flow."
                 )
            # Save the (newly obtained or refreshed) credentials
            with open(token_path, "wb") as token_file:
                pickle.dump(creds, token_file)
            print(f"Google token saved/updated for user {user_id} at {token_path}.")
        else:
             print(f"Valid Google token found for user {user_id} at {token_path}.")
        return JSONResponse(content={"success": True, "message": "Google authentication successful."})
    except HTTPException as http_exc:
        raise http_exc # Re-raise specific HTTP exceptions
    except Exception as e:
        print(f"[ERROR] Google authentication process for user {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )


# --- Memory and Knowledge Graph Endpoints (Protected by Auth) ---
@app.post("/graphrag", status_code=status.HTTP_200_OK, summary="Query Knowledge Graph (RAG)", tags=["Knowledge Graph"])
async def graphrag(request: GraphRAGRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Performs a Retrieval-Augmented Generation (RAG) query against the user's
    knowledge graph. This involves embedding the query, finding relevant nodes/relationships,
    and using that context to generate an answer.
    """
    print(f"[ENDPOINT /graphrag] Called by user {user_id} for query: '{request.query[:50]}...'")
    try:
        # Check for essential dependencies for graph operations
        if not all([graph_driver, embed_model, text_conversion_runnable, query_classification_runnable]):
             raise HTTPException(
                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                 detail="GraphRAG dependencies (Neo4j, EmbedModel, Runnables) are not available."
             )
        # The `query_user_profile` function performs synchronous Neo4j operations.
        # Run it in a thread pool executor to avoid blocking the main asyncio event loop.
        # Pass user_id for user-scoped graph queries.
        context = await asyncio.to_thread(
             query_user_profile,
             user_id,
             request.query,
             graph_driver,
             embed_model,
             text_conversion_runnable,
             query_classification_runnable
        )
        return JSONResponse(content={"context": context or "No relevant context found in the knowledge graph."})
    except Exception as e:
        print(f"[ERROR] /graphrag for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "GraphRAG query failed.")

@app.post("/initiate-long-term-memories", status_code=status.HTTP_200_OK, summary="Initialize/Reset Knowledge Graph", tags=["Knowledge Graph"])
async def create_graph(request_data: Optional[Dict[str, bool]] = None, user_id: str = Depends(auth.get_current_user)):
    """
    Initializes or resets the long-term knowledge graph for the authenticated user.
    If `clear_graph` is true in the request body, the existing graph for the user is cleared
    before building new structures from input files (currently global, needs user-specific input).

    Args:
        request_data: Optional dictionary, may contain `{"clear_graph": true}`.
        user_id: Authenticated user ID.
    """
    clear_graph_flag = request_data.get("clear_graph", False) if request_data else False
    action_being_performed = "Resetting and rebuilding" if clear_graph_flag else "Initiating/Updating"
    print(f"[ENDPOINT /initiate-long-term-memories] {action_being_performed} knowledge graph for user {user_id}.")

    input_dir = os.path.join(BASE_DIR, "input") # TODO: Input directory might need to be user-specific.
    loop = asyncio.get_event_loop()

    try:
        user_profile = await load_user_profile(user_id)
        # Username is used as a scope/identifier within the graph building process.
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)

        if not all([graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable]):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Graph building dependencies are unavailable.")

        # Synchronous file reading logic
        def read_files_sync_for_user(user_input_dir: str, uname: str):
            # This is a simplified example. Real implementation would read user-specific files.
            # For now, it implies global input files but tags them with username.
            # Example: find files in user_input_dir related to uname.
            sample_file_path = os.path.join(user_input_dir, f"{uname}_sample_document.txt")
            if os.path.exists(sample_file_path):
                with open(sample_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return [{"text": content, "source": os.path.basename(sample_file_path)}]
            return [{"text": f"Sample content for user {uname} from default.", "source": "default_sample.txt"}]

        extracted_texts = await loop.run_in_executor(None, read_files_sync_for_user, input_dir, username)

        # Clear user's portion of the graph if requested
        if clear_graph_flag:
             print(f"Clearing existing graph data for user {user_id} (scoped by username: {username})...")
             try:
                 # Neo4j operations are synchronous, run in executor
                 def clear_neo4j_user_graph_sync(driver, uid_scope: str):
                      with driver.session(database="neo4j") as session:
                           # IMPORTANT: Modify query for proper user-scoping.
                           # Example: MATCH (n {userId: $uid_scope}) DETACH DELETE n
                           # The current query clears the ENTIRE graph if not scoped properly.
                           # For safety in a shared environment, this needs careful review.
                           # As a placeholder, assuming nodes have a 'username' property for scoping.
                           # query = "MATCH (n {username: $username}) DETACH DELETE n"
                           # For full graph reset (as per original logic, use with caution):
                           query = "MATCH (n) DETACH DELETE n" # This clears everything!
                           session.execute_write(lambda tx: tx.run(query, username=uid_scope)) # Pass username if query uses it
                 await loop.run_in_executor(None, clear_neo4j_user_graph_sync, graph_driver, username)
                 print(f"Graph cleared for user scope: {username}.")
             except Exception as clear_e:
                 raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to clear graph: {clear_e}")

        # Build/Update graph with extracted texts
        if extracted_texts:
             print(f"Building/Updating graph for user {username} from {len(extracted_texts)} document(s)...")
             # `build_initial_knowledge_graph` is synchronous
             await loop.run_in_executor(
                 None, build_initial_knowledge_graph, username, extracted_texts,
                 graph_driver, embed_model, text_dissection_runnable, information_extraction_runnable
             )
             print(f"Graph build process completed for user {username}.")
             return JSONResponse(content={"message": f"Knowledge graph {action_being_performed.lower()} for user {username}."})
        else:
             return JSONResponse(content={"message": "No input documents found. Graph not modified."})

    except Exception as e:
        print(f"[ERROR] /initiate-long-term-memories for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Knowledge graph operation failed.")

@app.post("/delete-subgraph", status_code=status.HTTP_200_OK, summary="Delete Subgraph by Source", tags=["Knowledge Graph"])
async def delete_subgraph(request: DeleteSubgraphRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Deletes a subgraph associated with a specific source (e.g., 'linkedin', 'reddit')
    for the authenticated user. This involves removing nodes/relationships from Neo4j
    and deleting the corresponding source file from the input directory.
    """
    source_key = request.source.lower() # Normalize source key
    print(f"[ENDPOINT /delete-subgraph] Called by user {user_id} for source: {source_key}")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id).lower()

        # Define mappings from source keys to expected filenames (username-scoped)
        # These filenames are conventions used when creating documents.
        SOURCE_FILENAME_MAPPINGS = {
            "linkedin": f"{username}_linkedin_profile.txt",
            "reddit": f"{username}_reddit_profile.txt",
            "twitter": f"{username}_twitter_profile.txt",
            "extroversion": f"{username}_extroversion.txt",
            "introversion": f"{username}_introversion.txt",
            "sensing": f"{username}_sensing.txt",
            "intuition": f"{username}_intuition.txt",
            "thinking": f"{username}_thinking.txt",
            "feeling": f"{username}_feeling.txt",
            "judging": f"{username}_judging.txt",
            "perceiving": f"{username}_perceiving.txt",
            # "personality_summary": f"{username}_personality_summary.txt", # If a unified personality file exists
        }
        file_name_to_delete = SOURCE_FILENAME_MAPPINGS.get(source_key)
        if not file_name_to_delete:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid or unsupported source key: {request.source}")

        if not graph_driver:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Neo4j driver is unavailable.")

        # Delete from Neo4j graph (synchronous, run in executor)
        # The `delete_source_subgraph` function needs to correctly use the file_name (which acts as a source identifier)
        # and potentially the username/user_id for scoping the deletion within Neo4j.
        print(f"Deleting subgraph for user {user_id} (username: {username}), source file identifier: '{file_name_to_delete}'...")
        await loop.run_in_executor(None, delete_source_subgraph, graph_driver, file_name_to_delete) # Pass user_id/username if query needs it for scoping

        # Delete the corresponding source file from the input directory
        # TODO: Input directory should be user-specific if files are not globally managed.
        input_dir_path = os.path.join(BASE_DIR, "input") # Current global input dir
        file_path_to_delete_on_disk = os.path.join(input_dir_path, file_name_to_delete)

        def remove_file_sync(path_to_remove: str):
             if os.path.exists(path_to_remove):
                 try:
                    os.remove(path_to_remove)
                    return True, None
                 except OSError as e_os:
                    return False, str(e_os)
             else:
                return False, "File not found on disk." # File might have been already deleted or never existed

        deleted_on_disk, file_error = await loop.run_in_executor(None, remove_file_sync, file_path_to_delete_on_disk)
        if deleted_on_disk:
            print(f"Successfully deleted input file: {file_path_to_delete_on_disk}")
        else:
            print(f"[WARN] Could not delete input file {file_path_to_delete_on_disk}: {file_error}")

        return JSONResponse(content={"message": f"Subgraph and source file for '{request.source}' (identified by '{file_name_to_delete}') processed for deletion."})
    except Exception as e:
        print(f"[ERROR] /delete-subgraph for user {user_id}, source {request.source}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Subgraph deletion process failed.")


@app.post("/create-document", status_code=status.HTTP_200_OK, summary="Create Input Documents from Profile", tags=["Knowledge Graph"])
async def create_document(user_id: str = Depends(auth.get_current_user)):
    """
    Creates text documents in the 'server/input' directory based on the authenticated
    user's profile data (personality, social media links, etc.).
    These documents can then be used to build the knowledge graph.
    Documents are named using the user's lowercase username.
    """
    print(f"[ENDPOINT /create-document] Called by user {user_id}.")
    input_dir_path = os.path.join(BASE_DIR, "input") # TODO: Consider user-specific input directories
    loop = asyncio.get_event_loop()
    try:
        user_profile_data = await load_user_profile(user_id) # Load profile asynchronously
        db_user_data = user_profile_data.get("userData", {})
        # Use lowercase username for filenames to ensure consistency
        username = db_user_data.get("personalInfo", {}).get("name", user_id).lower()

        personality_type_list = db_user_data.get("personalityType", [])
        structured_linkedin_profile_data = db_user_data.get("linkedInProfile", {})
        reddit_profile_topics = db_user_data.get("redditProfile", [])
        twitter_profile_topics = db_user_data.get("twitterProfile", [])

        await loop.run_in_executor(None, os.makedirs, input_dir_path, True) # Ensure input directory exists

        background_tasks = []
        trait_descriptions_for_summary = []

        # --- Process Personality Traits ---
        if isinstance(personality_type_list, list):
             for trait in personality_type_list:
                 trait_lower = trait.lower()
                 if trait_lower in PERSONALITY_DESCRIPTIONS: # Predefined descriptions for traits
                      desc_content = f"{trait.capitalize()}: {PERSONALITY_DESCRIPTIONS[trait_lower]}"
                      trait_descriptions_for_summary.append(desc_content)
                      filename = f"{username}_{trait_lower}.txt"
                      # Summarize and write each trait description in a separate file (in thread pool)
                      background_tasks.append(loop.run_in_executor(
                          None, summarize_and_write_sync, username, desc_content, filename, input_dir_path
                      ))

        # --- Process LinkedIn Profile ---
        if structured_linkedin_profile_data:
             li_text_content = json.dumps(structured_linkedin_profile_data, indent=2) if isinstance(structured_linkedin_profile_data, dict) else str(structured_linkedin_profile_data)
             li_filename = f"{username}_linkedin_profile.txt"
             background_tasks.append(loop.run_in_executor(
                 None, summarize_and_write_sync, username, li_text_content, li_filename, input_dir_path
             ))

        # --- Process Reddit Profile Topics ---
        if reddit_profile_topics:
            rd_text_content = "User's Reddit Interests: " + ", ".join(
                reddit_profile_topics if isinstance(reddit_profile_topics, list) else [str(reddit_profile_topics)]
            )
            rd_filename = f"{username}_reddit_profile.txt"
            background_tasks.append(loop.run_in_executor(
                None, summarize_and_write_sync, username, rd_text_content, rd_filename, input_dir_path
            ))

        # --- Process Twitter Profile Topics ---
        if twitter_profile_topics:
            tw_text_content = "User's Twitter Interests: " + ", ".join(
                twitter_profile_topics if isinstance(twitter_profile_topics, list) else [str(twitter_profile_topics)]
            )
            tw_filename = f"{username}_twitter_profile.txt"
            background_tasks.append(loop.run_in_executor(
                None, summarize_and_write_sync, username, tw_text_content, tw_filename, input_dir_path
            ))

        # Execute all file writing tasks concurrently and gather results
        results = await asyncio.gather(*background_tasks, return_exceptions=True)
        created_files_list = [fname for success, fname in results if success and fname and not isinstance(fname, Exception)] # Check type of fname
        failed_files_list = [fname for success, fname in results if not success or isinstance(fname, Exception) or not isinstance(fname, str)] # check type


        unified_personality_summary = "\n".join(trait_descriptions_for_summary)
        print(f"Document creation process finished for user {user_id} (username: {username}). Created: {len(created_files_list)}, Failed: {len(failed_files_list)}")
        return JSONResponse(content={
            "message": "Input documents processed based on user profile.",
            "created_files": created_files_list,
            "failed_files": failed_files_list,
            "personality_summary_generated": unified_personality_summary # This is the combined text, not a file
        })

    except Exception as e:
        print(f"[ERROR] /create-document for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Document creation from profile failed.")

# Helper function for `create_document` to run synchronous summarization and file writing in a thread pool.
def summarize_and_write_sync(username_for_context: str, text_content: str, output_filename: str, output_dir: str) -> tuple[bool, Optional[str]]:
    """
    Summarizes text content and writes it to a file. Designed for use in an executor.

    Args:
        username_for_context: Username, passed to summarizer for context.
        text_content: The text to summarize and write.
        output_filename: The name of the file to create.
        output_dir: The directory to save the file in.

    Returns:
        A tuple (success_flag, filename_or_error_message).
    """
    if not text_content:
        return False, output_filename # Indicate failure if no content
    try:
        # Ensure runnables are thread-safe if used here. LLM calls are typically network-bound.
        # `text_summarizer_runnable` is assumed to be safe for concurrent calls.
        summarized_content = text_summarizer_runnable.invoke({"user_name": username_for_context, "text": text_content})
        file_path = os.path.join(output_dir, output_filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summarized_content)
        print(f"[SUMMARIZE_WRITE_SYNC] Successfully wrote summarized content to: {file_path}")
        return True, output_filename
    except Exception as e:
        print(f"[ERROR] Summarize/Write sync failed for {output_filename} in {output_dir}: {e}")
        return False, output_filename # Return filename to indicate which one failed


@app.post("/customize-long-term-memories", status_code=status.HTTP_200_OK, summary="Customize Knowledge Graph with Text", tags=["Knowledge Graph"])
async def customize_graph(request: GraphRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Customizes the user's knowledge graph by extracting facts from the provided text
    and applying CRUD (Create, Read, Update, Delete) operations to the graph.
    """
    print(f"[ENDPOINT /customize-long-term-memories] Called by user {user_id} with text: '{request.information[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)

        # Check for necessary graph operation dependencies
        required_deps = [
            graph_driver, embed_model, fact_extraction_runnable,
            query_classification_runnable, information_extraction_runnable,
            graph_analysis_runnable, graph_decision_runnable, text_description_runnable
        ]
        if not all(required_deps):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Graph customization dependencies are not available.")

        # Extract facts from the input information (synchronous, run in executor)
        # `fact_extraction_runnable` needs `username` for context.
        extracted_points = await loop.run_in_executor(
            None, fact_extraction_runnable.invoke, {"paragraph": request.information, "username": username}
        )
        if not isinstance(extracted_points, list): extracted_points = [] # Ensure it's a list
        if not extracted_points:
            return JSONResponse(content={"message": "No relevant facts extracted from the provided information. Graph not modified."})

        # Apply CRUD operations for each extracted fact (concurrently in executor)
        crud_tasks = []
        print(f"Applying CRUD operations for {len(extracted_points)} extracted facts for user {user_id} (username: {username})...")
        for point in extracted_points:
             crud_tasks.append(loop.run_in_executor(
                 None, crud_graph_operations, user_id, point, graph_driver, embed_model, # Pass user_id for graph ops
                 query_classification_runnable, information_extraction_runnable,
                 graph_analysis_runnable, graph_decision_runnable, text_description_runnable
             ))
        crud_results = await asyncio.gather(*crud_tasks, return_exceptions=True)

        processed_count = sum(1 for r in crud_results if not isinstance(r, Exception))
        errors_encountered = [str(r) for r in crud_results if isinstance(r, Exception)]
        message = f"Knowledge graph customization processed for {processed_count}/{len(extracted_points)} facts."
        if errors_encountered:
            message += f" Encountered {len(errors_encountered)} errors."
            print(f"[ERROR] /customize-long-term-memories for user {user_id}: Errors occurred: {errors_encountered}")

        return JSONResponse(
            status_code=status.HTTP_200_OK if not errors_encountered else status.HTTP_207_MULTI_STATUS, # 207 if partial success
            content={"message": message, "errors": errors_encountered}
        )

    except Exception as e:
        print(f"[ERROR] /customize-long-term-memories for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Knowledge graph customization failed.")


# --- Task Queue Endpoints (Protected by Auth) ---
@app.post("/fetch-tasks", status_code=status.HTTP_200_OK, summary="Fetch User Tasks", tags=["Tasks"])
async def get_tasks(user_id: str = Depends(auth.get_current_user)):
    """
    Fetches all tasks associated with the authenticated user from the task queue.
    """
    print(f"[ENDPOINT /fetch-tasks] Called by user {user_id}.")
    try:
        # TaskQueue's `get_tasks_for_user` filters tasks by the provided user_id.
        user_tasks = await task_queue.get_tasks_for_user(user_id)
        serializable_tasks_list = []
        for task_item in user_tasks: # Ensure datetime objects are ISO formatted for JSON
             if isinstance(task_item.get('created_at'), datetime):
                 task_item['created_at'] = task_item['created_at'].isoformat()
             if isinstance(task_item.get('completed_at'), datetime):
                 task_item['completed_at'] = task_item['completed_at'].isoformat()
             serializable_tasks_list.append(task_item)
        return JSONResponse(content={"tasks": serializable_tasks_list})
    except Exception as e:
        print(f"[ERROR] /fetch-tasks for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch user tasks.")

@app.post("/add-task", status_code=status.HTTP_201_CREATED, summary="Add New Task", tags=["Tasks"])
async def add_task_endpoint(task_request: CreateTaskRequest, user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Adds a new task to the queue for the authenticated user.
    The task's priority and context needs (personal, internet) are determined automatically.
    """
    print(f"[ENDPOINT /add-task] Called by user {user_id} with description: '{task_request.description[:50]}...'")
    loop = asyncio.get_event_loop()
    try:
        # Determine Active Chat ID for this user (to associate task with a chat)
        await get_chat_history_messages(user_id) # Ensures active chat is set
        async with db_lock:
            chatsDb = await load_db(user_id)
            active_chat_id = chatsDb.get("active_chat_id", 0)
        if active_chat_id == 0:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not determine active chat to associate task with.")

        # Load user profile for name and personality (used by agent executing the task)
        user_profile = await load_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id)
        personality = user_profile.get("userData", {}).get("personality", "Default helpful assistant")

        # Classify task needs (personal context, internet) and determine priority (in thread pool)
        unified_output = await loop.run_in_executor(
            None, unified_classification_runnable.invoke, {"query": task_request.description}
        )
        use_personal_context = unified_output.get("use_personal_context", False)
        internet_needed = unified_output.get("internet", "None")

        try:
            priority_response = await loop.run_in_executor(
                None, priority_runnable.invoke, {"task_description": task_request.description}
            )
            task_priority = priority_response.get("priority", 3) # Default priority
        except Exception as e_priority:
            print(f"[WARN] Priority check failed for new task (user {user_id}): {e_priority}. Defaulting to priority 3.")
            task_priority = 3

        # Add Task to Queue (TaskQueue handles user_id association)
        new_task_id = await task_queue.add_task(
            user_id=user_id, chat_id=active_chat_id, description=task_request.description,
            priority=task_priority, username=username, personality=personality,
            use_personal_context=use_personal_context, internet=internet_needed
        )

        # Add messages to the user's chat DB to reflect task creation
        # Hidden user prompt that triggered the task
        await add_message_to_db(user_id, active_chat_id, task_request.description, is_user=True, is_visible=False)
        # Visible AI confirmation message
        confirmation_message = f"Okay, I've added the task: '{task_request.description[:40]}...'"
        await add_message_to_db(
            user_id, active_chat_id, confirmation_message, is_user=False, is_visible=True,
            agentsUsed=True, task=task_request.description # Mark as agent-related
        )
        # WebSocket broadcast of new task is handled by TaskQueue.add_task

        return JSONResponse(content={"task_id": new_task_id, "message": "Task added successfully."}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"[ERROR] /add-task for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add task.")

@app.post("/update-task", status_code=status.HTTP_200_OK, summary="Update Existing Task", tags=["Tasks"])
async def update_task_endpoint(update_request: UpdateTaskRequest, user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Updates an existing task's description or priority for the authenticated user.
    The TaskQueue verifies ownership before updating.
    """
    task_id_to_update = update_request.task_id
    new_description = update_request.description
    new_priority_val = update_request.priority
    print(f"[ENDPOINT /update-task] User {user_id} updating task {task_id_to_update} with new priority {new_priority_val}.")
    try:
        # TaskQueue's `update_task` must verify that `user_id` owns `task_id_to_update`.
        updated_task_details = await task_queue.update_task(user_id, task_id_to_update, new_description, new_priority_val)
        if not updated_task_details:
            # This implies task not found or user doesn't have permission (handled by TaskQueue)
            raise ValueError("Task not found or update not authorized for this user.")
        # WebSocket broadcast of task update is handled by TaskQueue.update_task
        return JSONResponse(content={"message": "Task updated successfully."})
    except ValueError as ve: # Specific error for not found / unauthorized
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /update-task for user {user_id}, task {task_id_to_update}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update task.")

@app.post("/delete-task", status_code=status.HTTP_200_OK, summary="Delete Task", tags=["Tasks"])
async def delete_task_endpoint(delete_request: DeleteTaskRequest, user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Deletes a task from the queue for the authenticated user.
    The TaskQueue verifies ownership before deletion.
    """
    task_id_to_delete = delete_request.task_id
    print(f"[ENDPOINT /delete-task] User {user_id} deleting task {task_id_to_delete}.")
    try:
        # TaskQueue's `delete_task` must verify that `user_id` owns `task_id_to_delete`.
        was_deleted = await task_queue.delete_task(user_id, task_id_to_delete)
        if not was_deleted:
            raise ValueError("Task not found or deletion not authorized for this user.")
        # WebSocket broadcast of task deletion is handled by TaskQueue.delete_task
        return JSONResponse(content={"message": "Task deleted successfully."})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /delete-task for user {user_id}, task {task_id_to_delete}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete task.")


# --- Short-Term Memory Endpoints (Protected by Auth) ---
@app.post("/get-short-term-memories", status_code=status.HTTP_200_OK, summary="Get Short-Term Memories", tags=["Short-Term Memory"])
async def get_short_term_memories(request: GetShortTermMemoriesRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves short-term memories for the authenticated user, filtered by category and limit.
    """
    category_filter = request.category
    limit_count = request.limit
    print(f"[ENDPOINT /get-short-term-memories] User {user_id} fetching memories. Category: {category_filter}, Limit: {limit_count}")
    loop = asyncio.get_event_loop()
    try:
        # `fetch_memories_by_category` is synchronous, run in executor. It needs user_id.
        memories_list = await loop.run_in_executor(
            None, memory_backend.memory_manager.fetch_memories_by_category, user_id, category_filter, limit_count
        )
        # Serialize datetime objects to ISO format string for JSON compatibility
        serializable_memories = []
        for mem in memories_list:
            if isinstance(mem.get('created_at'), datetime):
                mem['created_at'] = mem['created_at'].isoformat()
            if isinstance(mem.get('expires_at'), datetime):
                mem['expires_at'] = mem['expires_at'].isoformat()
            serializable_memories.append(mem)
        return JSONResponse(content=serializable_memories) # Returns a list directly
    except Exception as e:
        print(f"[ERROR] /get-short-term-memories for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch short-term memories.")

@app.post("/add-short-term-memory", status_code=status.HTTP_201_CREATED, summary="Add Short-Term Memory", tags=["Short-Term Memory"])
async def add_memory(request: AddMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Adds a new short-term memory for the authenticated user.
    """
    text_content = request.text
    category_name = request.category
    retention_period_days = request.retention_days
    print(f"[ENDPOINT /add-short-term-memory] User {user_id} adding memory. Category: {category_name}, Retention: {retention_period_days} days.")
    loop = asyncio.get_event_loop()
    try:
        # `store_memory` is synchronous, needs user_id.
        new_memory_id = await loop.run_in_executor(
            None, memory_backend.memory_manager.store_memory, user_id, text_content, retention_period_days, category_name
        )
        return JSONResponse(
            content={"memory_id": new_memory_id, "message": "Short-term memory added successfully."},
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"[ERROR] /add-short-term-memory for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add short-term memory.")

@app.post("/update-short-term-memory", status_code=status.HTTP_200_OK, summary="Update Short-Term Memory", tags=["Short-Term Memory"])
async def update_memory(request: UpdateMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Updates an existing short-term memory for the authenticated user.
    """
    memory_id_to_update = request.id
    new_text = request.text
    new_category = request.category
    new_retention_days = request.retention_days
    print(f"[ENDPOINT /update-short-term-memory] User {user_id} updating memory ID: {memory_id_to_update}.")
    loop = asyncio.get_event_loop()
    try:
        # `update_memory_crud` is synchronous, needs user_id.
        await loop.run_in_executor(
            None, memory_backend.memory_manager.update_memory_crud,
            user_id, new_category, memory_id_to_update, new_text, new_retention_days
        )
        return JSONResponse(content={"message": "Short-term memory updated successfully."})
    except ValueError as ve: # Raised by memory_manager if memory not found for user/category
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /update-short-term-memory for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update short-term memory.")

@app.post("/delete-short-term-memory", status_code=status.HTTP_200_OK, summary="Delete Short-Term Memory", tags=["Short-Term Memory"])
async def delete_memory(request: DeleteMemoryRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Deletes a specific short-term memory for the authenticated user.
    """
    memory_id_to_delete = request.id
    category_of_memory = request.category
    print(f"[ENDPOINT /delete-short-term-memory] User {user_id} deleting memory ID: {memory_id_to_delete} from category: {category_of_memory}.")
    loop = asyncio.get_event_loop()
    try:
        # `delete_memory` is synchronous, needs user_id.
        await loop.run_in_executor(
            None, memory_backend.memory_manager.delete_memory, user_id, category_of_memory, memory_id_to_delete
        )
        return JSONResponse(content={"message": "Short-term memory deleted successfully."})
    except ValueError as ve: # Raised if memory not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /delete-short-term-memory for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete short-term memory.")

@app.post("/clear-all-short-term-memories", status_code=status.HTTP_200_OK, summary="Clear All Short-Term Memories", tags=["Short-Term Memory"])
async def clear_all_memories(user_id: str = Depends(auth.get_current_user)):
    """
    Clears all short-term memories for the authenticated user.
    """
    print(f"[ENDPOINT /clear-all-short-term-memories] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        # `clear_all_memories` is synchronous, needs user_id.
        await loop.run_in_executor(None, memory_backend.memory_manager.clear_all_memories, user_id)
        return JSONResponse(content={"message": "All short-term memories cleared successfully for the user."})
    except Exception as e:
        print(f"[ERROR] /clear-all-short-term-memories for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to clear all short-term memories.")


# --- User Profile Database Endpoints (Protected by Auth) ---
# These endpoints interact with the user's profile JSON file.

@app.post("/set-user-data", status_code=status.HTTP_200_OK, summary="Set User Profile Data", tags=["User Profile"])
async def set_db_data(request: UpdateUserDataRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Sets or overwrites data in the authenticated user's profile.
    The request body `data` dictionary is merged into the existing `userData` field,
    with new values overwriting existing keys at the top level.
    """
    print(f"[ENDPOINT /set-user-data] Called by user {user_id} with data: {str(request.data)[:100]}...")
    loop = asyncio.get_event_loop()
    try:
        # Load existing profile (synchronous, run in executor)
        current_profile_data = await loop.run_in_executor(None, load_user_profile, user_id)
        if "userData" not in current_profile_data:
            current_profile_data["userData"] = {}
        current_profile_data["userData"].update(request.data) # Shallow merge/overwrite at top level

        # Write updated profile back (synchronous, run in executor)
        write_successful = await loop.run_in_executor(None, write_user_profile, user_id, current_profile_data)
        if not write_successful:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to write updated user profile to storage.")

        return JSONResponse(content={"message": "User data stored successfully.", "status": 200})
    except Exception as e:
        print(f"[ERROR] /set-user-data for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to set user data.")

@app.post("/add-db-data", status_code=status.HTTP_200_OK, summary="Add/Merge User Profile Data", tags=["User Profile"])
async def add_db_data(request: AddUserDataRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Adds or merges data into the authenticated user's profile.
    This performs a deeper merge than `/set-user-data`:
    - Lists are extended with unique items.
    - Dictionaries are updated (merged).
    - Other values are overwritten.
    """
    print(f"[ENDPOINT /add-db-data] Called by user {user_id} with data: {str(request.data)[:100]}...")
    loop = asyncio.get_event_loop()
    try:
        current_profile_data = await loop.run_in_executor(None, load_user_profile, user_id)
        existing_user_data = current_profile_data.get("userData", {})

        # Deep merge logic
        for key, new_value in request.data.items():
             if key in existing_user_data and isinstance(existing_user_data[key], list) and isinstance(new_value, list):
                 # Extend list with unique items (handles dicts within list by serializing)
                 existing_items_set = set(map(lambda x: json.dumps(x, sort_keys=True), existing_user_data[key]))
                 for item in new_value:
                      item_json = json.dumps(item, sort_keys=True)
                      if item_json not in existing_items_set:
                          existing_user_data[key].append(item)
                          existing_items_set.add(item_json)
             elif key in existing_user_data and isinstance(existing_user_data[key], dict) and isinstance(new_value, dict):
                 existing_user_data[key].update(new_value) # Merge dictionaries
             else:
                 existing_user_data[key] = new_value # Overwrite or add new key

        current_profile_data["userData"] = existing_user_data # Update the main profile structure
        write_successful = await loop.run_in_executor(None, write_user_profile, user_id, current_profile_data)
        if not write_successful:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to write merged user profile to storage.")

        return JSONResponse(content={"message": "User data added/merged successfully.", "status": 200})
    except Exception as e:
        print(f"[ERROR] /add-db-data for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add/merge user data.")

@app.post("/get-user-data", status_code=status.HTTP_200_OK, summary="Get User Profile Data", tags=["User Profile"])
async def get_db_data(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the `userData` portion of the authenticated user's profile.
    """
    print(f"[ENDPOINT /get-user-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        profile_data = await loop.run_in_executor(None, load_user_profile, user_id)
        user_specific_data = profile_data.get("userData", {}) # Return empty dict if no userData
        return JSONResponse(content={"data": user_specific_data, "status": 200})
    except Exception as e:
        print(f"[ERROR] /get-user-data for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch user data.")

# --- Graph Data Endpoint (Protected by Auth) ---
@app.post("/get-graph-data", status_code=status.HTTP_200_OK, summary="Get Knowledge Graph Data (for Visualization)", tags=["Knowledge Graph"])
async def get_graph_data_apoc(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves data from the Neo4j knowledge graph for visualization.
    The query aims to fetch nodes and relationships, potentially scoped to the user.
    IMPORTANT: The current query is simplified and might fetch global data if not properly
    scoped by `userId` or a similar property in Neo4j.
    """
    print(f"[ENDPOINT /get-graph-data] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    if not graph_driver:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Neo4j graph driver is not available.")

    # Query to fetch nodes and relationships.
    # For user-specific graphs, nodes/rels should be filtered by user_id.
    # Example of a user-scoped query (if nodes have a 'userId' property):
    # """
    # MATCH (n {userId: $userId})
    # WITH collect(DISTINCT n) as nodes
    # OPTIONAL MATCH (s)-[r]->(t) WHERE s IN nodes AND t IN nodes AND s.userId = $userId AND t.userId = $userId
    # WITH nodes, collect(DISTINCT r) as rels
    # RETURN
    #     [node IN nodes | { id: elementId(node), label: coalesce(labels(node)[0], 'Unknown'), properties: properties(node) }] AS nodes_list,
    #     [rel IN rels | { id: elementId(rel), from: elementId(startNode(rel)), to: elementId(endNode(rel)), label: type(rel), properties: properties(rel) }] AS edges_list
    # """
    # Current simplified query (fetches all data - use with caution in multi-user environments without proper scoping):
    graph_visualization_query = """
    MATCH (n)
    WITH collect(DISTINCT n) as nodes
    OPTIONAL MATCH (s)-[r]->(t) WHERE s IN nodes AND t IN nodes
    WITH nodes, collect(DISTINCT r) as rels
    RETURN
        [node IN nodes | { id: elementId(node), label: coalesce(labels(node)[0], 'Unknown'), properties: properties(node) }] AS nodes_list,
        [rel IN rels | { id: elementId(rel), from: elementId(startNode(rel)), to: elementId(endNode(rel)), label: type(rel), properties: properties(rel) }] AS edges_list
    """
    print(f"Executing graph visualization query for user {user_id}...")

    def run_neo4j_query_sync(driver_instance, query_str: str, query_params: dict):
         """Synchronous helper to run Neo4j queries."""
         try:
             with driver_instance.session(database="neo4j") as session: # Specify database if not default
                 result = session.run(query_str, query_params).single() # Assuming query returns a single row with nodes_list and edges_list
                 # Ensure lists are returned even if result is None or keys are missing
                 nodes_data = result['nodes_list'] if result and 'nodes_list' in result else []
                 edges_data = result['edges_list'] if result and 'edges_list' in result else []
                 return (nodes_data, edges_data)
         except Exception as e_neo:
             print(f"Neo4j query error during graph data fetch: {e_neo}")
             raise # Re-raise to be caught by the main try-except

    try:
        # Pass user_id as a parameter if the query is user-scoped
        nodes_result, edges_result = await loop.run_in_executor(
            None, run_neo4j_query_sync, graph_driver, graph_visualization_query, {"userId": user_id}
        )
        print(f"Graph data query successful for user {user_id}. Nodes fetched: {len(nodes_result)}, Edges fetched: {len(edges_result)}")
        return JSONResponse(content={"nodes": nodes_result, "edges": edges_result})
    except Exception as e:
        print(f"[ERROR] /get-graph-data for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch graph data for visualization.")

# --- Notifications Endpoint (Protected by Auth) ---
@app.post("/get-notifications", status_code=status.HTTP_200_OK, summary="Get User Notifications", tags=["Notifications"])
async def get_notifications_endpoint(user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Retrieves all notifications for the authenticated user.
    """
    print(f"[ENDPOINT /get-notifications] Called by user {user_id}.")
    try:
        notifications_db_data = await load_notifications_db(user_id) # Load user's specific notifications file
        user_notifications = notifications_db_data.get("notifications", [])
        # Serialize datetime objects if they exist in notification items
        for notification_item in user_notifications:
             if isinstance(notification_item.get('timestamp'), datetime):
                 notification_item['timestamp'] = notification_item['timestamp'].isoformat()
        return JSONResponse(content={"notifications": user_notifications})
    except Exception as e:
        print(f"[ERROR] /get-notifications for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch user notifications.")


# --- Task Approval Endpoints (Protected by Auth) ---
@app.post("/approve-task", response_model=ApproveTaskResponse, summary="Approve a Pending Task", tags=["Tasks"])
async def approve_task_endpoint(request: TaskIdRequest, user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Approves a task that is pending user approval.
    The TaskQueue handles executing the approved action and updating the task status.
    Ownership of the task by the user is verified by the TaskQueue.
    """
    task_id_to_approve = request.task_id
    print(f"[ENDPOINT /approve-task] User {user_id} is approving task {task_id_to_approve}.")
    try:
        # TaskQueue's `approve_task` verifies user ownership and executes the pending action.
        # It returns the result of the executed action.
        execution_result_data = await task_queue.approve_task(user_id, task_id_to_approve)
        print(f"Task {task_id_to_approve} (User: {user_id}) approved and underlying action executed.")

        # Add the result of the approved action to the user's chat DB
        task_details = await task_queue.get_task_by_id(task_id_to_approve) # Re-fetch task details for chat_id
        if task_details and task_details.get("user_id") == user_id and task_details.get("chat_id"):
            await add_message_to_db(
                user_id,
                task_details["chat_id"],
                str(execution_result_data), # Convert result to string for message
                is_user=False,
                is_visible=True,
                type="tool_result", # Mark as a tool/agent result
                task=task_details.get("description"),
                agentsUsed=True
            )
        else:
            print(f"[WARN] Could not add approved task result to chat for task {task_id_to_approve} (User: {user_id}). Task details or chat_id missing.")

        # WebSocket broadcast about task completion is handled by TaskQueue.
        return ApproveTaskResponse(message="Task approved and completed successfully.", result=execution_result_data)
    except ValueError as ve: # Raised by TaskQueue for invalid state, not found, or unauthorized
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        print(f"[ERROR] /approve-task for user {user_id}, task {task_id_to_approve}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Task approval process failed.")

@app.post("/get-task-approval-data", response_model=TaskApprovalDataResponse, summary="Get Data for Task Approval", tags=["Tasks"])
async def get_task_approval_data_endpoint(request: TaskIdRequest, user_id: str = Depends(auth.get_current_user)): # Renamed
    """
    Retrieves the specific data associated with a task that is pending approval.
    This data is typically what the user needs to review before approving (e.g., email content).
    """
    task_id_for_data = request.task_id
    print(f"[ENDPOINT /get-task-approval-data] User {user_id} requesting approval data for task {task_id_for_data}.")
    try:
        # TaskQueue's `get_task_by_id` should ideally handle user ownership check or return enough info to do so.
        task_item = await task_queue.get_task_by_id(task_id_for_data)

        if task_item and task_item.get("user_id") == user_id:
            if task_item.get("status") == "approval_pending":
                return TaskApprovalDataResponse(approval_data=task_item.get("approval_data"))
            else:
                 raise HTTPException(
                     status_code=status.HTTP_400_BAD_REQUEST,
                     detail=f"Task '{task_id_for_data}' is not pending approval. Current status: {task_item.get('status')}."
                 )
        else: # Task not found or does not belong to the user
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail=f"Task '{task_id_for_data}' not found or access is denied for this user."
             )
    except HTTPException as http_exc: # Re-raise known HTTP exceptions
        raise http_exc
    except Exception as e:
        print(f"[ERROR] /get-task-approval-data for user {user_id}, task {task_id_for_data}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch task approval data.")


# --- Data Source Configuration Endpoints (Protected by Auth) ---
@app.post("/get_data_sources", status_code=status.HTTP_200_OK, summary="Get Data Source Statuses", tags=["Configuration"])
async def get_data_sources_endpoint(user_id: str = Depends(auth.get_current_user)):
    """
    Retrieves the enabled/disabled status for all available data sources
    (e.g., 'gmail', 'internet_search') for the authenticated user from their profile.
    """
    print(f"[ENDPOINT /get_data_sources] Called by user {user_id}.")
    loop = asyncio.get_event_loop()
    try:
        user_profile = await loop.run_in_executor(None, load_user_profile, user_id)
        user_settings = user_profile.get("userData", {})
        # Construct status list, defaulting to True (enabled) if not explicitly set.
        data_sources_status = [
            {"name": source_name, "enabled": user_settings.get(f"{source_name}Enabled", True)}
            for source_name in DATA_SOURCES
        ]
        return JSONResponse(content={"data_sources": data_sources_status})
    except Exception as e:
        print(f"[ERROR] /get_data_sources for user {user_id}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to fetch data source statuses.")

@app.post("/set_data_source_enabled", status_code=status.HTTP_200_OK, summary="Enable/Disable Data Source", tags=["Configuration"])
async def set_data_source_enabled_endpoint(request: SetDataSourceEnabledRequest, user_id: str = Depends(auth.get_current_user)):
    """
    Sets the enabled/disabled status for a specific data source for the authenticated user.
    This status is stored in the user's profile.
    """
    source_to_configure = request.source
    is_enabled = request.enabled
    print(f"[ENDPOINT /set_data_source_enabled] User {user_id} setting source: {source_to_configure} to enabled: {is_enabled}")

    if source_to_configure not in DATA_SOURCES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid data source name: {source_to_configure}")

    loop = asyncio.get_event_loop()
    try:
        current_profile = await loop.run_in_executor(None, load_user_profile, user_id)
        if "userData" not in current_profile:
            current_profile["userData"] = {}
        current_profile["userData"][f"{source_to_configure}Enabled"] = is_enabled # Update the specific flag

        write_success = await loop.run_in_executor(None, write_user_profile, user_id, current_profile)
        if not write_success:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save updated data source status to user profile.")

        # TODO: If context engines (Gmail, Calendar, etc.) are stateful per user,
        # this is where a signal might be sent to reload/reinitialize the engine for this user and source.
        print(f"[ACTION_NEEDED] Context engine for '{source_to_configure}' (user {user_id}) may need to be reloaded or its state updated due to status change.")

        return JSONResponse(content={"status": "success", "message": f"Data source '{source_to_configure}' status set to '{'enabled' if is_enabled else 'disabled'}'."})
    except Exception as e:
        print(f"[ERROR] /set_data_source_enabled for user {user_id}, source {source_to_configure}: {e}"); traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to set data source status.")


# --- WebSocket Endpoint (With Authentication) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections.
    Requires authentication via a token sent as the first message from the client.
    Manages connection lifecycle and can receive pings.
    """
    await websocket.accept() # Accept the WebSocket handshake
    authenticated_user_id: Optional[str] = None # Store user_id upon successful auth
    try:
        # Step 1: Authenticate the WebSocket connection
        # The `ws_authenticate` method expects an auth message with a token.
        authenticated_user_id = await auth.ws_authenticate(websocket)
        if not authenticated_user_id:
             # ws_authenticate already closes the WebSocket on failure.
             print("[WS /ws] WebSocket authentication failed or connection closed during auth.")
             return # Exit if authentication was not successful

        # Step 2: Add the successfully authenticated connection to the manager
        await manager.connect(websocket, authenticated_user_id)

        # Step 3: Keep connection alive and handle incoming messages (e.g., pings)
        while True:
            data = await websocket.receive_text() # Wait for messages from the client
            # print(f"Received WS message from user {authenticated_user_id}: {data[:100]}") # Log received data (optional)
            try:
                 # Handle control messages like pings from the client
                 message_payload = json.loads(data)
                 if message_payload.get("type") == "ping":
                     await websocket.send_text(json.dumps({"type": "pong"})) # Respond to ping
            except json.JSONDecodeError:
                 # Ignore non-JSON messages if not expecting other formats
                 pass
            except Exception as e_ws_loop:
                 print(f"[WS /ws] Error in WebSocket receive loop for user {authenticated_user_id}: {e_ws_loop}")
                 # Depending on error, might break or continue

    except WebSocketDisconnect:
        print(f"[WS /ws] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        # Catch any other unexpected errors during WebSocket handling
        print(f"[WS /ws] Unexpected WebSocket error (User: {authenticated_user_id or 'unknown'}): {e}")
        traceback.print_exc()
    finally:
        # Ensure the connection is removed from the manager upon disconnection or error
        # `manager.disconnect` is idempotent and handles cases where the socket might already be removed.
        manager.disconnect(websocket)
        print(f"[WS /ws] WebSocket connection closed and cleaned up for user: {authenticated_user_id or 'unknown'}")


# --- Voice Endpoint (FastRTC - Real-Time Communication) ---
# TODO: Current FastRTC stream setup does not explicitly handle authentication per stream.
# Authentication for voice streams would likely require modifying FastRTC's connection
# handshake or passing an auth token in the initial messages, similar to the general WebSocket endpoint.
# The `handle_audio_conversation` function needs `user_id` to be truly functional.

async def handle_audio_conversation(audio: tuple[int, np.ndarray]) -> AsyncGenerator[tuple[int, np.ndarray], None]:
     """
     Handles a segment of audio from a FastRTC stream.
     It transcribes the audio to text (STT), then (ideally) processes this text
     through the chat/agent logic for a specific user, and finally synthesizes
     the response back to audio (TTS) to be streamed to the client.

     Args:
         audio: A tuple containing (sample_rate, audio_data_as_numpy_array).

     Yields:
         Tuples of (sample_rate, audio_chunk_as_numpy_array) for the TTS response.

     --- MAJOR TODO ---
     This function currently lacks user context (`user_id`). For it to work correctly in a
     multi-user environment, `user_id` must be obtained (e.g., from stream metadata if
     FastRTC supports it, or via an initial auth message over the stream) and used for:
     - Loading the correct user profile.
     - Accessing the user's active chat and chat history.
     - Adding messages to the user's database.
     - Invoking runnables (chat, agent, memory) with user-specific context.
     - Potentially selecting user-preferred TTS voice.
     """
     # Placeholder for user_id - THIS IS A CRITICAL MISSING PIECE FOR MULTI-USER VOICE
     user_id_for_voice = "PLACEHOLDER_VOICE_USER"
     print(f"\n--- [VOICE] Received audio chunk for processing (User: {user_id_for_voice}) ---")

     # --- 1. Speech-to-Text (STT) ---
     if not stt_model:
         print("[VOICE_ERROR] STT model not loaded. Cannot process audio.")
         yield 0, np.array([]) # Yield empty audio to signify error or end
         return
     print("[VOICE] Transcribing audio...")
     user_transcribed_text = stt_model.stt(audio)
     if not user_transcribed_text or not user_transcribed_text.strip():
         print("[VOICE] No text transcribed from audio or empty transcription.")
         return # Nothing to process

     print(f"[VOICE] User (STT - {user_id_for_voice}): {user_transcribed_text}")

     # --- 2. Process Transcribed Text (Chat/Agent Logic - NEEDS USER_ID) ---
     # This section is a placeholder and requires full implementation with user_id.
     # - Load user profile (name, personality) for user_id_for_voice.
     # - Get active chat_id for user_id_for_voice.
     # - Add user_transcribed_text to the user's chat DB.
     # - Classify input, retrieve context (memory, internet) for user_id_for_voice.
     # - Invoke chat_runnable or agent_runnable with user-specific history and context.
     # - The result `bot_response_text` would come from this processing step.

     # Example placeholder response since full logic isn't implemented here:
     bot_response_text = f"Voice interaction for user '{user_id_for_voice}' is a work in progress. You said: '{user_transcribed_text}'"
     print(f"[VOICE] Generating placeholder TTS response: {bot_response_text}")

     # --- 3. Text-to-Speech (TTS) ---
     if not tts_model:
         print("[VOICE_ERROR] TTS model not loaded. Cannot synthesize response.")
         yield 0, np.array([])
         return

     tts_options: TTSOptions = {"voice_id": SELECTED_TTS_VOICE} # Use default or user-preferred voice
     async for sample_rate, audio_chunk in tts_model.stream_tts(bot_response_text, options=tts_options):
          if audio_chunk is not None and audio_chunk.size > 0:
              yield (sample_rate, audio_chunk)
     print(f"--- [VOICE] Finished processing audio for user {user_id_for_voice} ---")

# FastRTC Stream Setup
# Configures the real-time audio stream using `handle_audio_conversation` as the processor.
# `ReplyOnPause` means processing happens when the user pauses speaking (VAD-based).
# `can_interrupt=False` means TTS won't be interrupted by new user speech during synthesis.
voice_stream_handler = Stream(
    ReplyOnPause(
        handle_audio_conversation,
        algo_options=AlgoOptions(), # Default VAD algorithm options
        model_options=SileroVadOptions(), # Default Silero VAD model options
        can_interrupt=False
    ),
    mode="send-receive", # Bidirectional audio
    modality="audio"
)
# Mounts the FastRTC stream at the "/voice" path on the FastAPI app.
voice_stream_handler.mount(app, path="/voice")
print(f"[FASTAPI] {datetime.now()}: FastRTC voice stream mounted at /voice (Authentication TODO).")


# --- Main Execution Block ---
if __name__ == "__main__":
    # Enable support for multiprocessing, especially important on Windows
    # if the application or its dependencies use multiprocessing.
    multiprocessing.freeze_support()

    # Configure Uvicorn logging for better readability and detail
    log_config = uvicorn.config.LOGGING_CONFIG
    # Customize access log format
    log_config["formatters"]["access"]["fmt"] = \
        "%(asctime)s %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    # Customize default log format to include logger name (e.g., uvicorn.error)
    log_config["formatters"]["default"]["fmt"] = \
        "%(asctime)s %(levelprefix)s [%(name)s] %(message)s" # Added %(name)s
    # Set log level for Uvicorn's error logger (can be DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO"
    # Ensure access logs use the 'access' handler defined in Uvicorn's default config
    log_config["loggers"]["uvicorn.access"]["handlers"] = ["access"]

    print(f"[UVICORN] {datetime.now()}: Starting Uvicorn server on host 0.0.0.0, port 5000...")
    print(f"[UVICORN] {datetime.now()}: Access API documentation at http://localhost:5000/docs")
    uvicorn.run(
        "__main__:app",       # Path to the FastAPI app instance (filename:variable_name)
        host="0.0.0.0",       # Listen on all available network interfaces
        port=5000,            # Port to listen on
        lifespan="on",        # Enable lifespan events (startup/shutdown)
        reload=False,         # Disable auto-reload for production (set to True for dev)
        workers=1,            # Number of worker processes (adjust based on CPU cores and load)
        log_config=log_config # Apply custom logging configuration
    )