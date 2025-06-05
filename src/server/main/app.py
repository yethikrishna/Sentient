# src/server/main/app.py
import time
import datetime
from datetime import timezone
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Main Server application script execution started.")

import os
import asyncio
from contextlib import asynccontextmanager
import traceback
import logging # For general logging
import httpx 

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --- Core Components ---
from .config import (
    IS_DEV_ENVIRONMENT, TTS_PROVIDER, ELEVENLABS_API_KEY, ORPHEUS_MODEL_PATH, ORPHEUS_N_GPU_LAYERS,
    FASTER_WHISPER_MODEL_SIZE, FASTER_WHISPER_DEVICE, FASTER_WHISPER_COMPUTE_TYPE,
    OLLAMA_MODEL_NAME, OPENROUTER_MODEL_NAME, OLLAMA_BASE_URL, OPENROUTER_API_KEY, APP_SERVER_PORT
)
from .db import MongoManager
from .ws_manager import MainWebSocketManager
from .auth.utils import AuthHelper # AuthHelper is central
# from .runnables import OllamaRunnable, OpenRouterRunnable # If LLMs are initialized globally

# --- STT/TTS Service Imports ---
from .voice.stt_services import BaseSTT, FasterWhisperSTT, ElevenLabsSTT
from .voice.tts_services import BaseTTS, OrpheusTTS, ElevenLabsTTS as ElevenLabsTTSImpl, GCPTTS

# --- Routers ---
from .auth.routes import router as auth_router
from .chat.routes import router as chat_router
from .voice.routes import router as voice_router
from .api.routes import router as api_router # Miscellaneous API routes

# --- Global Instances ---
# These will be initialized in the lifespan manager or directly if appropriate.
mongo_manager_instance = MongoManager()
auth_helper = AuthHelper() # Global AuthHelper instance
main_websocket_manager = MainWebSocketManager()
http_client: httpx.AsyncClient = httpx.AsyncClient()

stt_model_instance: BaseSTT | None = None
tts_model_instance: BaseTTS | None = None
is_dev_env: bool = IS_DEV_ENVIRONMENT # Make it easily importable by routers

# LLM Runnable Instances (Optional: initialize globally if shared)
# ollama_llm: OllamaRunnable | None = None
# openrouter_llm: OpenRouterRunnable | None = None


# --- Logging Setup ---
# You can customize logging further here if needed, e.g., using logging.config.dictConfig
logging.basicConfig(level=logging.INFO if not IS_DEV_ENVIRONMENT else logging.DEBUG)
logger = logging.getLogger(__name__) # Logger for app.py

def initialize_stt():
    global stt_model_instance
    logger.info("Initializing STT model...")
    if IS_DEV_ENVIRONMENT:
        try:
            stt_model_instance = FasterWhisperSTT(
                model_size=FASTER_WHISPER_MODEL_SIZE,
                device=FASTER_WHISPER_DEVICE,
                compute_type=FASTER_WHISPER_COMPUTE_TYPE
            )
            logger.info("FasterWhisper STT initialized for Development.")
        except Exception as e:
            logger.error(f"Failed to initialize FasterWhisper STT: {e}", exc_info=True)
            stt_model_instance = None
    else: # Production
        try:
            if not ELEVENLABS_API_KEY:
                logger.error("ELEVENLABS_API_KEY not set for Production STT.")
                stt_model_instance = None
            else:
                # This is a placeholder. Replace with actual ElevenLabs STT initialization.
                stt_model_instance = ElevenLabsSTT()
                logger.info("ElevenLabsSTT initialized for Production (Placeholder).")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabsSTT for Production: {e}", exc_info=True)
            stt_model_instance = None
    logger.info("STT model initialization complete.")

def initialize_tts():
    global tts_model_instance
    logger.info("Initializing TTS model...")
    if IS_DEV_ENVIRONMENT:
        try:
            if not ORPHEUS_MODEL_PATH or not os.path.exists(ORPHEUS_MODEL_PATH):
                 logger.warning(f"Orpheus model path not found or not set. TTS might not work. Path: {ORPHEUS_MODEL_PATH}")
                 tts_model_instance = None
            else:
                tts_model_instance = OrpheusTTS(
                    model_path=ORPHEUS_MODEL_PATH, 
                    n_gpu_layers=ORPHEUS_N_GPU_LAYERS,
                    default_voice_id="tara" # Example default
                )
                logger.info("OrpheusTTS initialized for Development.")
        except Exception as e:
            logger.error(f"Failed to initialize OrpheusTTS for Development: {e}", exc_info=True)
            tts_model_instance = None
    else: # Production
        if TTS_PROVIDER == "ELEVENLABS":
            try:
                if not ELEVENLABS_API_KEY:
                    logger.error("ELEVENLABS_API_KEY not set for Production TTS (ElevenLabs).")
                    tts_model_instance = None
                else:
                    tts_model_instance = ElevenLabsTTSImpl() # Note: Renamed to avoid conflict
                    logger.info("ElevenLabsTTS initialized for Production.")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabsTTS for Production: {e}", exc_info=True)
                tts_model_instance = None
        elif TTS_PROVIDER == "GCP":
            try:
                tts_model_instance = GCPTTS()
                logger.info("GCPTTS initialized for Production.")
            except Exception as e:
                logger.error(f"Failed to initialize GCPTTS for Production: {e}", exc_info=True)
                tts_model_instance = None
        else:
            logger.warning(f"TTS_PROVIDER is '{TTS_PROVIDER}'. No specific production TTS loaded.")
            tts_model_instance = None
    logger.info("TTS model initialization complete.")

# def initialize_llms():
#     global ollama_llm, openrouter_llm
#     logger.info("Initializing LLM Runnable instances...")
#     if IS_DEV_ENVIRONMENT:
#         ollama_llm = OllamaRunnable(model_name=OLLAMA_MODEL_NAME, model_url=f"{OLLAMA_BASE_URL}/api/chat") # Adjusted URL
#         logger.info(f"Ollama LLM Runnable initialized for Dev: {OLLAMA_MODEL_NAME}")
#     else:
#         if OPENROUTER_API_KEY:
#             openrouter_llm = OpenRouterRunnable(model_name=OPENROUTER_MODEL_NAME, api_key=OPENROUTER_API_KEY)
#             logger.info(f"OpenRouter LLM Runnable initialized for Prod: {OPENROUTER_MODEL_NAME}")
#         else:
#             logger.warning("OPENROUTER_API_KEY not set. Production LLM (OpenRouter) not initialized.")
#     logger.info("LLM Runnable initialization complete.")


# --- FastAPI Lifespan Manager ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup...")
    await mongo_manager_instance.initialize_db()
    initialize_stt()
    initialize_tts()
    # initialize_llms() # If using global LLM runnables
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup complete.")
    yield 
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown sequence initiated...")
    await http_client.aclose()
    if mongo_manager_instance and mongo_manager_instance.client:
        # motor client does not have a close() method to be called directly in async.
        # It's typically managed by the event loop or when the client object is garbage collected.
        # Explicitly closing here if it were a sync client or if motor had a specific async close.
        # For motor, client.close() is synchronous and should not be awaited.
        # It's usually not necessary to call client.close() in modern motor versions as it handles connections.
        # However, if there's a specific reason:
        mongo_manager_instance.client.close() # Synchronous close
        print(f"[{datetime.datetime.now()}] [LIFESPAN] MongoManager client closed attempt.")
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown complete.")


# --- FastAPI Application Instance ---
app = FastAPI(
    title="Sentient Main Server", 
    description="Core API: Auth, Chat, Voice, Onboarding, Profile, Settings.", 
    version="2.1.0", # Version bump for refactor
    docs_url="/docs", 
    redoc_url="/redoc", 
    lifespan=lifespan
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["app://.", "http://localhost:3000", "http://localhost"], # Adjust as needed
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# --- Include Routers ---
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(api_router) # For all other miscellaneous routes

# --- General App Information Endpoints ---
@app.get("/", tags=["General"], summary="Root endpoint for the Main Server")
async def root():
    return {"message": "Sentient Main Server Operational (Refactored)."}

@app.get("/health", tags=["General"], summary="Health check for the Main Server")
async def health():
    # Extended health check can verify DB connection, STT/TTS models, etc.
    db_status = "connected" if mongo_manager_instance.client else "disconnected"
    stt_status = "loaded" if stt_model_instance else "not_loaded"
    tts_status = "loaded" if tts_model_instance else "not_loaded"
    
    return {
        "status": "healthy", 
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db_status,
            "stt": stt_status,
            "tts": tts_status
        }
    }

# --- Dependency for AuthHelper (if needed by PermissionChecker directly) ---
# This allows Depends(get_auth_helper_instance) in PermissionChecker,
# but it's simpler if PermissionChecker imports the global `auth_helper` instance.
# async def get_auth_helper_instance() -> AuthHelper:
#     return auth_helper

# --- Nest Asyncio (if still needed, usually for notebooks/specific environments) ---
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


END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [APP_PY_LOADED] Main Server app.py loaded in {END_TIME - START_TIME:.2f} seconds.")

# --- Main Server Entrypoint ---
if __name__ == "__main__":
    import uvicorn
    from .config import APP_SERVER_PORT
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    # Customize log formats if needed
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER_ACCESS] %(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER_DEFAULT] %(message)s'
    print(f"[{datetime.datetime.now()}] [MainServer_Service] Attempting to start Main Server on host 0.0.0.0, port {APP_SERVER_PORT}...")
    print(f"[{datetime.datetime.now()}] [MainServer_Service] Development Mode: {IS_DEV_ENVIRONMENT}")
    uvicorn.run(
        "server.main.app:app", # Point to the app instance in app.py
        host="0.0.0.0",
        port=APP_SERVER_PORT,
        lifespan="on",
        reload=IS_DEV_ENVIRONMENT,
        workers=1, # Consider increasing for production behind a reverse proxy
        log_config=log_config
    )

