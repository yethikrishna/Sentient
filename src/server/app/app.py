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
from server.context.base import BaseContextEngine
from server.context.gmail import GmailContextEngine
from server.context.gcalendar import GCalendarContextEngine
from server.context.internet import InternetSearchContextEngine
from datetime import timezone, timedelta # For scheduling

# --- MongoDB Manager Import ---
from server.common.dependencies import (
    auth, PermissionChecker, task_queue, mongo_manager, manager, memory_backend,
    active_context_engines, polling_scheduler_task_handle, POLLING_SCHEDULER_INTERVAL_SECONDS,
    DATA_SOURCES_CONFIG, load_user_profile, write_user_profile, get_chat_history_messages,
    add_message_to_db, polling_scheduler_loop, start_user_context_engines
)
from server.common.dependencies import graph_driver, embed_model # Import from dependencies
# --- Third-Party Library Imports ---
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket, # Keep for WebSocketManager type hint if needed, endpoint moved
    WebSocketDisconnect, # Keep for WebSocketManager type hint
    Depends,
    status,
    Security 
)
from fastapi.security import OAuth2PasswordBearer # SecurityScopes removed as PermissionChecker handles it
from fastapi.responses import JSONResponse # HTMLResponse and StreamingResponse moved to routers
from fastapi.middleware.cors import CORSMiddleware
# StaticFiles might not be needed if served by Gradio or other means
# from fastapi.staticfiles import StaticFiles 
# Pydantic models moved to respective routers
from contextlib import asynccontextmanager # For lifespan
from typing import Optional, Any, Dict, List, Tuple # AsyncGenerator removed, Union added for add_message_to_db

# --- Authentication Specific Imports ---

# --- Machine Learning and NLP Imports ---
from neo4j import GraphDatabase
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# --- Google API Imports ---
# from google_auth_oauthlib.flow import InstalledAppFlow # Moved to utils/routes.py
# from google.auth.transport.requests import Request # Moved to utils/routes.py

# --- Environment and Configuration Imports ---
from dotenv import load_dotenv
import nest_asyncio
import uvicorn

# --- Utility and Other Imports ---
import numpy as np
import gradio as gr # Still needed for FastRTC internals
from fastrtc import Stream, ReplyOnPause, AlgoOptions, SileroVadOptions # For FastRTC components
# import httpx # httpx moved to routers where external calls are made

print(f"[STARTUP] {datetime.datetime.now()}: Basic imports completed.")

# --- Application-Specific Module Imports ---
print(f"[STARTUP] {datetime.datetime.now()}: Importing model components...")

# Specific imports for runnables from their correct locations
from server.memory.runnables import (
    get_graph_analysis_runnable,
    get_text_dissection_runnable,
    get_text_conversion_runnable,
    get_query_classification_runnable, # Used by AgentTaskProcessor & MemoryBackend
    get_fact_extraction_runnable,
    get_text_summarizer_runnable,
    get_text_description_runnable,
    get_graph_decision_runnable,
    get_information_extraction_runnable
)
from server.agents.runnables import (
    get_reflection_runnable,      # For AgentTaskProcessor
    get_inbox_summarizer_runnable, # For AgentTaskProcessor
    get_agent_runnable            # For AgentTaskProcessor
)
# The main chat_runnable for the /chat endpoint
from server.chat.runnables import get_chat_runnable

from server.agents.functions import * # Contains Google API auth and functions (tool implementations)
from server.agents.prompts import *
from server.agents.formats import *
from server.agents.base import TaskQueue
from server.agents.helpers import * # Contains parse_and_execute_tool_calls
from server.agents.background import AgentTaskProcessor # APPROVAL_PENDING_SIGNAL not needed here

from server.memory.runnables import *
from server.memory.functions import *
from server.memory.prompts import *
from server.memory.constants import *
from server.memory.formats import *
from server.memory.backend import MemoryBackend

from server.utils.helpers import aes_encrypt, aes_decrypt, get_management_token # Specific utils

from server.auth.helpers import * # Contains AES, get_management_token

from server.common.functions import get_reframed_internet_query, get_search_results, get_search_summary, update_neo4j_with_onboarding_data, update_neo4j_with_personal_info, query_user_profile, get_unified_classification_runnable, get_priority_runnable
from server.common.runnables import get_internet_query_reframe_runnable, get_internet_summary_runnable
from server.common.prompts import *
from server.common.formats import *

from server.chat.runnables import *
from server.chat.prompts import *
from server.chat.functions import * # get_chat_history, generate_streaming_response

# Context Engines are used by background tasks, not directly by app.py routes now
# from server.context.gmail import GmailContextEngine
# from server.context.internet import InternetSearchContextEngine
# from server.context.gcalendar import GCalendarContextEngine

from server.voice.stt import FasterWhisperSTT
from server.voice.orpheus_tts import OrpheusTTS, TTSOptions, VoiceId, AVAILABLE_VOICES
from server.voice.gcp_tts import GCPTTS
from server.voice.elevenlabs_tts import ElevenLabsTTS
import uuid # For new chat_id in helper functions

print(f"[STARTUP] {datetime.datetime.now()}: Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)
print(f"[STARTUP] {datetime.datetime.now()}: Environment variables loaded from {dotenv_path}")

IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS").upper()
print(f"[STARTUP] {datetime.datetime.now()}: Development environment flag set to {IS_DEV_ENVIRONMENT}")
print(f"[STARTUP] {datetime.datetime.now()}: TTS Provider set to {TTS_PROVIDER}")

print(f"[STARTUP] {datetime.datetime.now()}: Applying nest_asyncio...")
nest_asyncio.apply()
print(f"[STARTUP] {datetime.datetime.now()}: nest_asyncio applied.")

print(f"[INIT] {datetime.datetime.now()}: Starting global initializations...")
DATA_SOURCES = ["gmail", "internet_search", "gcalendar"]



print(f"[INIT] {datetime.datetime.now()}: Initializing runnables...")
reflection_runnable = get_reflection_runnable()
inbox_summarizer_runnable = get_inbox_summarizer_runnable()
graph_decision_runnable = get_graph_decision_runnable()
information_extraction_runnable = get_information_extraction_runnable()
graph_analysis_runnable = get_graph_analysis_runnable()
text_dissection_runnable = get_text_dissection_runnable()
text_conversion_runnable = get_text_conversion_runnable()
query_classification_runnable = get_query_classification_runnable()
fact_extraction_runnable = get_fact_extraction_runnable()
text_summarizer_runnable = get_text_summarizer_runnable()
text_description_runnable = get_text_description_runnable()
chat_runnable = get_chat_runnable()
agent_runnable = get_agent_runnable()
internet_query_reframe_runnable = get_internet_query_reframe_runnable()
internet_summary_runnable = get_internet_summary_runnable()
print(f"[INIT] {datetime.datetime.now()}: Runnables initialization complete.")

tool_handlers: Dict[str, callable] = {} # Keep tool_handlers global for registration
print(f"[INIT] {datetime.datetime.now()}: Tool handlers registry initialized.")


print(f"[INIT] {datetime.datetime.now()}: Initializing AgentTaskProcessor...")
agent_task_processor = AgentTaskProcessor(
    task_queue=task_queue,
    tool_handlers=tool_handlers,
    load_user_profile_func=load_user_profile,
    add_message_to_db_func=add_message_to_db,
    graph_driver_instance=graph_driver,
    embed_model_instance=embed_model,
    reflection_runnable_instance=reflection_runnable,
    agent_runnable_instance=agent_runnable,
    internet_query_reframe_runnable_instance=internet_query_reframe_runnable,
    internet_summary_runnable_instance=internet_summary_runnable,
    query_user_profile_func=query_user_profile,
    text_conversion_runnable_instance=text_conversion_runnable,
    query_classification_runnable_instance=query_classification_runnable,
    get_reframed_internet_query_func=get_reframed_internet_query,
    get_search_results_func=get_search_results,
    get_search_summary_func=get_search_summary
)
print(f"[INIT] {datetime.datetime.now()}: AgentTaskProcessor initialized.")

stt_model = None
tts_model = None
SELECTED_TTS_VOICE: VoiceId = "tara" # Default, can be changed



def register_tool(name: str): # This must remain in app.py or be passed to AgentTaskProcessor
    def decorator(func: callable):
        print(f"[TOOL_REGISTRY] Registering tool '{name}'")
        tool_handlers[name] = func
        return func
    return decorator

# Tool function imports for registration need to happen AFTER register_tool is defined
# and tool_handlers is initialized.
# The actual tool functions are in server.agents.functions.
# Registration happens when server.agents.functions is imported IF the decorator is applied there.
# For this refactor, assuming tool registration happens in app.py by calling functions from agents.functions
# OR the decorator is applied directly in agents.functions.py.
# Let's assume registration is handled. The current structure suggests registration would
# happen when the `gmail_tool` etc. functions are defined with `@register_tool`.
# Since tool functions are moved to agents.functions, they should be decorated there.
# Or, if we keep register_tool here, then we'd call it here.
# For now, I'll keep the `@register_tool` and tool function definitions here
# and plan to move them with the `agents/routes.py` or into `agents/tools.py` in a later step if needed.
# The current request is about endpoint separation primarily.

# Re-defining tool handlers as they were in the original app.py
# These will be called by AgentTaskProcessor. They are not FastAPI endpoints.
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
        if actual_tool_name in ["send_email", "reply_email"]: # Example approval tools
            return {"action": "approve", "tool_call": tool_call_dict}
        else:
            # parse_and_execute_tool_calls is in server.agents.helpers
            tool_result = await parse_and_execute_tool_calls(tool_call_dict) 
            return {"tool_result": tool_result} # Ensure this structure is what AgentTaskProcessor expects
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
        tool_result = await parse_and_execute_tool_calls(tool_call_dict)
        return {"tool_result": tool_result}
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
        tool_result = await parse_and_execute_tool_calls(tool_call_dict)
        return {"tool_result": tool_result}
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
        tool_result = await parse_and_execute_tool_calls(tool_call_dict)
        return {"tool_result": tool_result}
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
        tool_result = await parse_and_execute_tool_calls(tool_call_dict)
        return {"tool_result": tool_result}
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
        tool_result = await parse_and_execute_tool_calls(tool_call_dict)
        return {"tool_result": tool_result}
    except Exception as e: return {"status": "failure", "error": str(e)}


print(f"[CONFIG] {datetime.datetime.now()}: Setting up Google OAuth2 configuration...")
SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.compose", "https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive", "https://mail.google.com/"]
CREDENTIALS_DICT = {"installed": {"client_id": os.environ.get("GOOGLE_CLIENT_ID"), "project_id": os.environ.get("GOOGLE_PROJECT_ID"), "auth_uri": os.environ.get("GOOGLE_AUTH_URI"), "token_uri": os.environ.get("GOOGLE_TOKEN_URI"), "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"), "redirect_uris": ["http://localhost"]}} # Keep for utils/routes.py
print(f"[CONFIG] {datetime.datetime.now()}: Google OAuth2 config complete.")
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Keep BASE_DIR if utils/routes.py still needs it for token_path

agent_task_processor_instance: Optional[AgentTaskProcessor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[FASTAPI_LIFECYCLE] App startup at {datetime.datetime.now(timezone.utc).isoformat()}")
    global agent_task_processor_instance, polling_scheduler_task_handle, mongo_manager, task_queue, memory_backend, manager
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
                tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
                print(f"[WARN] Unknown TTS_PROVIDER '{TTS_PROVIDER}'. Defaulting to Orpheus TTS.")
    except Exception as e:
        print(f"[ERROR] TTS model failed to load. Voice features will be unavailable. Details: {e}")
        tts_model = None

    await mongo_manager.initialize_db()
    await task_queue.initialize_db()
    await memory_backend.initialize() # Initialize memory_backend including its queue and manager


    agent_task_processor_instance = agent_task_processor 

    if agent_task_processor_instance:
        asyncio.create_task(agent_task_processor_instance.process_queue())
        asyncio.create_task(agent_task_processor_instance.cleanup_tasks_periodically())
    else:
        print("[ERROR] AgentTaskProcessor not initialized. Task processing will not start.")
        
    asyncio.create_task(memory_backend.process_memory_operations())
    
    global polling_scheduler_task_handle
    polling_scheduler_task_handle = asyncio.create_task(polling_scheduler_loop())
    print(f"[FASTAPI_LIFECYCLE] Central polling scheduler started.")

    print(f"[FASTAPI_LIFECYCLE] App startup complete at {datetime.datetime.now(timezone.utc).isoformat()}")

    yield # The application runs while in this yield block

    if polling_scheduler_task_handle and not polling_scheduler_task_handle.done():
        print("[FASTAPI_LIFECYCLE] Cancelling polling scheduler task...")
        polling_scheduler_task_handle.cancel()
        try:
            await polling_scheduler_task_handle
        except asyncio.CancelledError:
            print("[FASTAPI_LIFECYCLE] Polling scheduler task cancelled.")
        except Exception as e:
            print(f"[FASTAPI_LIFECYCLE_ERROR] Error during polling scheduler shutdown: {e}")
    # ... (rest of your shutdown) ...
    print(f"[FASTAPI_LIFECYCLE] App shutdown.")
    if mongo_manager.client:
        mongo_manager.client.close()
        print("[FASTAPI_LIFECYCLE] MongoManager client closed.")
    if task_queue.client: 
        task_queue.client.close()
        print("[FASTAPI_LIFECYCLE] TaskQueue MongoDB client closed.")
    if memory_backend.memory_queue.client: 
        memory_backend.memory_queue.client.close()
        print("[FASTAPI_LIFECYCLE] MemoryQueue MongoDB client closed.")
    print(f"[FASTAPI_LIFECYCLE] All MongoDB clients known to app.py closed.")

# --- FastAPI Application Setup ---
print(f"[FASTAPI] {datetime.datetime.now()}: Initializing FastAPI app...")
app = FastAPI(title="Sentient API", description="API for Sentient application.", version="1.0.0", docs_url="/docs", redoc_url=None, lifespan=lifespan)
print(f"[FASTAPI] {datetime.datetime.now()}: FastAPI app initialized.")
app.add_middleware(CORSMiddleware, allow_origins=["app://.", "http://localhost:3000", "http://localhost"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
print(f"[FASTAPI] {datetime.datetime.now()}: CORS middleware added.")


# --- API Endpoints ---
# Import and include routers
from server.agents import routes as agent_routes
from server.memory import routes as memory_routes
from server.common import routes as common_routes
from server.utils import routes as util_routes

app.include_router(agent_routes.router)
app.include_router(memory_routes.router)
app.include_router(common_routes.router)
app.include_router(util_routes.router)

# The root endpoint can stay in app.py or be moved to utils/routes.py
@app.get("/", status_code=status.HTTP_200_OK, summary="API Root", tags=["General"])
async def main_root():
    return {"message": "Sentient API is running."}

# --- Voice Endpoint (FastRTC - remains in app.py due to specific mounting) ---
async def handle_audio_conversation(audio: tuple[int, np.ndarray]) -> AsyncGenerator[tuple[int, np.ndarray], None]:
     user_id_for_voice = "PLACEHOLDER_VOICE_USER_ID" # Needs actual user_id integration
     print(f"\n--- [VOICE] Audio chunk received (User: {user_id_for_voice}) ---")

     if not stt_model:
         print("[VOICE_ERROR] STT model not available. Cannot process audio.")
         yield (0, np.array([], dtype=np.float32)) # Ensure correct dtype for empty array
         return
     
     user_transcribed_text = stt_model.stt(audio)
     if not user_transcribed_text or not user_transcribed_text.strip():
         print("[VOICE] Empty transcription from STT.")
         return 
         
     print(f"[VOICE] User (STT - {user_id_for_voice}): {user_transcribed_text}")
     
     # Placeholder for getting a response (e.g., from Ollama or another LLM)
     bot_response_text = f"Voice processing is a work in progress for user {user_id_for_voice}. You said: '{user_transcribed_text}'"
     # In a real scenario, you would call your chat logic here:
     # bot_response_text = await get_chat_response(user_id_for_voice, user_transcribed_text)
     
     if not tts_model:
         print("[VOICE_ERROR] TTS model not available. Cannot generate audio response.")
         yield (0, np.array([], dtype=np.float32))
         return
         
     tts_options: TTSOptions = {"voice_id": SELECTED_TTS_VOICE} 
     async for sr, chunk in tts_model.stream_tts(bot_response_text, options=tts_options): # OrpheusTTS.stream_tts is async
          if chunk is not None and chunk.size > 0: # Ensure chunk is not None and has data
              # Convert chunk to bytes if it's not already (FastRTC expects bytes)
              # OrpheusTTS yields (sr, np.ndarray[np.float32])
              # FastRTC expects (sr, np.ndarray[np.int16]) or bytes
              # Let's assume FastRTC can handle float32 or it needs conversion here.
              # For now, assuming FastRTC can handle it.
              # If not, convert: audio_bytes = (chunk * 32767).astype(np.int16).tobytes()
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
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s %(levelname)s %(client_addr)s - \"%(request_line)s\" %(status_code)s" # Corrected format
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s %(levelname)s [%(name)s] %(message)s" # Corrected format
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO"

    print(f"[UVICORN] Starting Uvicorn server on host 0.0.0.0, port 5000...")
    print(f"[UVICORN] API Documentation available at http://localhost:5000/docs")
    
    uvicorn.run(
        "server.app.app:app", # Updated to point to the app instance within the refactored app.py
        host="0.0.0.0",
        port=5000,
        lifespan="on",
        reload=IS_DEV_ENVIRONMENT, # Enable reload only in dev
        workers=1, # For simplicity in dev; adjust for prod
        log_config=log_config
    )