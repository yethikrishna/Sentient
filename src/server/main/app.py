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
    STT_PROVIDER, TTS_PROVIDER, ELEVENLABS_API_KEY, ORPHEUS_MODEL_PATH, ORPHEUS_N_GPU_LAYERS,
    FASTER_WHISPER_MODEL_SIZE, FASTER_WHISPER_DEVICE, FASTER_WHISPER_COMPUTE_TYPE,
    APP_SERVER_PORT
)
# --- Centralized Dependencies ---
# Import shared instances from the dependencies module
from .dependencies import mongo_manager, neo4j_manager, memory_mongo_manager


# --- STT/TTS Service Imports ---
# These imports will be adjusted if class names/files change in voice.stt and voice.tts
from .voice.stt import BaseSTT, FasterWhisperSTT, ElevenLabsSTT
from .voice.tts import BaseTTS, ElevenLabsTTS as ElevenLabsTTSImpl
# OrpheusTTS is imported conditionally inside initialize_tts() to avoid loading heavy dependencies in production.


# --- Routers ---
from .auth.routes import router as auth_router
from .chat.routes import router as chat_router
from .voice.routes import router as voice_router
from .memory.routes import router as memory_router
from .integrations.routes import router as integrations_router
from .misc.routes import router as misc_router # Corrected router import
from .agents.routes import router as agents_router

# --- Other Global Instances ---
http_client: httpx.AsyncClient = httpx.AsyncClient()

stt_model_instance: BaseSTT | None = None
tts_model_instance: BaseTTS | None = None

logging.basicConfig(level=logging.INFO)
from .memory.dependencies import initialize_memory_managers, close_memory_managers
logger = logging.getLogger(__name__) 

def initialize_stt():
    global stt_model_instance
    logger.info("Initializing STT model...")
    if STT_PROVIDER == "FASTER_WHISPER":
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
    elif STT_PROVIDER == "ELEVENLABS":
        try:
            if not ELEVENLABS_API_KEY:
                logger.error("ELEVENLABS_API_KEY not set for Production STT.")
                stt_model_instance = None
            else:
                stt_model_instance = ElevenLabsSTT()
                logger.info("ElevenLabsSTT initialized for Production.")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabsSTT for Production: {e}", exc_info=True)
            stt_model_instance = None
    else:
        logger.warning(f"STT_PROVIDER is set to '{STT_PROVIDER}', which is not a valid option ('FASTER_WHISPER', 'ELEVENLABS'). No STT model loaded.")
        stt_model_instance = None
    logger.info("STT model initialization complete.")

def initialize_tts():
    global tts_model_instance
    logger.info("Initializing TTS model...")
    if TTS_PROVIDER == "ORPHEUS":
        try:
            from .voice.tts import OrpheusTTS # Conditionally import here

            if not ORPHEUS_MODEL_PATH or not os.path.exists(ORPHEUS_MODEL_PATH):
                 logger.warning(f"Orpheus model path not found or not set. TTS might not work. Path: {ORPHEUS_MODEL_PATH}")
                 tts_model_instance = None
            else:
                tts_model_instance = OrpheusTTS(
                    model_path=ORPHEUS_MODEL_PATH, 
                    n_gpu_layers=ORPHEUS_N_GPU_LAYERS,
                    default_voice_id="tara" 
                )
                logger.info("OrpheusTTS initialized for Development.")
        except Exception as e:
            logger.error(f"Failed to initialize OrpheusTTS for Development: {e}", exc_info=True)
            tts_model_instance = None
    elif TTS_PROVIDER == "ELEVENLABS":
        try:
            if not ELEVENLABS_API_KEY:
                logger.error("ELEVENLABS_API_KEY not set for TTS (ElevenLabs).")
                tts_model_instance = None
            else:
                tts_model_instance = ElevenLabsTTSImpl()
                logger.info("ElevenLabsTTS initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabsTTS: {e}", exc_info=True)
            tts_model_instance = None
    elif TTS_PROVIDER == "GCP":
        try:
            # from .voice.tts import GCPTTS # Assuming a GCPTTS class exists
            # tts_model_instance = GCPTTS()
            logger.warning("GCPTTS is mentioned but not implemented in the provided files. Skipping.")
            # logger.info("GCPTTS initialized for Production.")
        except Exception as e:
            logger.error(f"Failed to initialize GCPTTS for Production: {e}", exc_info=True)
            tts_model_instance = None
    else:
        logger.warning(f"TTS_PROVIDER is set to '{TTS_PROVIDER}', which is not a valid option ('ORPHEUS', 'ELEVENLABS', 'GCP'). No TTS model loaded.")
        tts_model_instance = None
    logger.info("TTS model initialization complete.")

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup...")
    await mongo_manager.initialize_db()
    initialize_stt()
    initialize_tts()
    initialize_memory_managers()
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup complete.")
    yield 
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown sequence initiated...")
    await http_client.aclose()
    if mongo_manager and mongo_manager.client:
        close_memory_managers()
        mongo_manager.client.close() 
        print(f"[{datetime.datetime.now()}] [LIFESPAN] MongoManager client closed attempt.")
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown complete.")

app = FastAPI(
    title="Sentient Main Server", 
    description="Core API: Auth, Chat, Voice, Onboarding, Profile, Settings.", 
    version="2.2.0", 
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

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(memory_router)
app.include_router(integrations_router)
app.include_router(misc_router) # Corrected router name
app.include_router(agents_router)

@app.get("/", tags=["General"], summary="Root endpoint for the Main Server")
async def root():
    return {"message": "Sentient Main Server Operational (Qwen Agent Integrated)."}

@app.get("/health", tags=["General"], summary="Health check for the Main Server")
async def health():
    db_status = "connected" if mongo_manager.client else "disconnected"
    stt_status = "loaded" if stt_model_instance else "not_loaded"
    tts_status = "loaded" if tts_model_instance else "not_loaded"
    llm_status = "qwen_agent_on_demand"
    
    return {
        "status": "healthy", 
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": db_status,
            "stt": stt_status,
            "tts": tts_status,
            "llm": llm_status
        }
    }

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

if __name__ == "__main__":
    import uvicorn
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER_ACCESS] %(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER_DEFAULT] %(message)s'
    print(f"[{datetime.datetime.now()}] [MainServer_Service] Attempting to start Main Server on host 0.0.0.0, port {APP_SERVER_PORT}...")
    uvicorn.run(
        "server.main.app:app", 
        host="0.0.0.0",
        port=APP_SERVER_PORT,
        lifespan="on",
        reload=False,
        workers=1, 
        log_config=log_config
    )