import time
import datetime
from datetime import timezone
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Main Server application script execution started.")

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import logging
import httpx 

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    STT_PROVIDER, TTS_PROVIDER, ELEVENLABS_API_KEY,
    FASTER_WHISPER_MODEL_SIZE, FASTER_WHISPER_DEVICE, FASTER_WHISPER_COMPUTE_TYPE,
    APP_SERVER_PORT
)
from .dependencies import mongo_manager
from .voice.stt import BaseSTT, FasterWhisperSTT, ElevenLabsSTT
from .voice.tts import BaseTTS, ElevenLabsTTS as ElevenLabsTTSImpl
from .auth.routes import router as auth_router
from .chat.routes import router as chat_router
from .notifications.routes import router as notifications_router
from .voice.routes import router as voice_router
from .memory.routes import router as memory_router
from .integrations.routes import router as integrations_router
from .misc.routes import router as misc_router
from .agents.routes import router as agents_router
from .memory.dependencies import initialize_memory_managers, close_memory_managers

http_client: httpx.AsyncClient = httpx.AsyncClient()
stt_model_instance: Optional[BaseSTT] = None
tts_model_instance: Optional[BaseTTS] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

def initialize_stt():
    global stt_model_instance
    logger.info(f"Initializing STT model provider: {STT_PROVIDER}")
    if STT_PROVIDER == "FASTER_WHISPER":
        try:
            stt_model_instance = FasterWhisperSTT(
                model_size=FASTER_WHISPER_MODEL_SIZE, device=FASTER_WHISPER_DEVICE,
                compute_type=FASTER_WHISPER_COMPUTE_TYPE
            )
        except Exception as e:
            logger.error(f"Failed to initialize FasterWhisper STT: {e}", exc_info=True)
    elif STT_PROVIDER == "ELEVENLABS":
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not set for STT.")
        else:
            stt_model_instance = ElevenLabsSTT()
    else:
        logger.warning(f"Invalid STT_PROVIDER: '{STT_PROVIDER}'. No STT model loaded.")

def initialize_tts():
    global tts_model_instance
    logger.info(f"Initializing TTS model provider: {TTS_PROVIDER}")
    if TTS_PROVIDER == "ORPHEUS":
        try:
            from .voice.tts import OrpheusTTS
            tts_model_instance = OrpheusTTS()
        except ImportError:
             logger.error("OrpheusTTS could not be imported. Check dependencies or TTS_PROVIDER setting.")
        except Exception as e:
            logger.error(f"Failed to initialize OrpheusTTS: {e}", exc_info=True)
    elif TTS_PROVIDER == "ELEVENLABS":
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not set for TTS.")
        else:
            tts_model_instance = ElevenLabsTTSImpl()
    else:
        logger.warning(f"Invalid TTS_PROVIDER: '{TTS_PROVIDER}'. No TTS model loaded.")

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
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown complete.")

app = FastAPI(title="Sentient Main Server", version="2.2.0", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)

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
app.include_router(notifications_router)
app.include_router(integrations_router)
app.include_router(misc_router)
app.include_router(agents_router)

@app.get("/", tags=["General"])
async def root():
    return {"message": "Sentient Main Server Operational (Qwen Agent Integrated)."}

@app.get("/health", tags=["General"])
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "connected" if mongo_manager.client else "disconnected",
            "stt": "loaded" if stt_model_instance else "not_loaded",
            "tts": "loaded" if tts_model_instance else "not_loaded",
            "llm": "qwen_agent_on_demand"
        }
    }

END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [APP_PY_LOADED] Main Server app.py loaded in {END_TIME - START_TIME:.2f} seconds.")

if __name__ == "__main__":
    import uvicorn
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER_ACCESS] %(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER_DEFAULT] %(message)s'
    uvicorn.run("server.main.app:app", host="0.0.0.0", port=APP_SERVER_PORT, lifespan="on", reload=False, workers=1, log_config=log_config)