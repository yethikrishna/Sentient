import time
import datetime 
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Main application script execution started.")

import os
import asyncio
import traceback
import json
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator # Removed Any, Dict, List, Tuple, Union as they are mostly used in routes now
import uuid

from fastapi import FastAPI, status, Depends # Removed HTTPException, WebSocket, WebSocketDisconnect, Security
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import nest_asyncio
import uvicorn

# --- Core Dependencies from common.dependencies ---
from server.common.dependencies import (
    mongo_manager,
    task_queue, # Keep if Gmail polling uses it to send data to Kafka
    # memory_backend, # Removed, complex memory graph is out
    polling_scheduler_task_handle, # Global handle for the scheduler task
    POLLING_SCHEDULER_INTERVAL_SECONDS, # Used in the scheduler loop itself
    DATA_SOURCES_CONFIG, # For knowing about Gmail
    polling_scheduler_loop, # The main scheduler function
    initialize_kafka_producer_on_startup # Kafka producer init
)

# --- Voice specific (simplified) ---
from server.voice.stt import FasterWhisperSTT
from server.voice.orpheus_tts import OrpheusTTS, TTSOptions, VoiceId # Orpheus for dummy audio

# --- FastRTC for voice endpoint ---
from fastrtc import Stream, ReplyOnPause, AlgoOptions, SileroVadOptions
import numpy as np # For FastRTC audio data

print(f"[{datetime.datetime.now()}] [STARTUP] Basic imports completed.")

# --- Environment Loading ---
print(f"[{datetime.datetime.now()}] [STARTUP] Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env") # Correct path relative to app.py
load_dotenv(dotenv_path=dotenv_path)
print(f"[{datetime.datetime.now()}] [STARTUP] Environment variables loaded.")

IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS").upper() # Only Orpheus relevant for dummy
print(f"[{datetime.datetime.now()}] [STARTUP] IS_DEV_ENVIRONMENT: {IS_DEV_ENVIRONMENT}")
print(f"[{datetime.datetime.now()}] [STARTUP] TTS_PROVIDER (for dummy voice): {TTS_PROVIDER}")

nest_asyncio.apply()
print(f"[{datetime.datetime.now()}] [STARTUP] nest_asyncio applied.")

# --- Global Model Instances (Simplified) ---
stt_model: Optional[FasterWhisperSTT] = None
tts_model: Optional[OrpheusTTS] = None # Only Orpheus for dummy
SELECTED_TTS_VOICE: VoiceId = "tara" # Default dummy voice

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_model, tts_model, polling_scheduler_task_handle
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [FASTAPI_LIFECYCLE] App startup...")

    # Initialize MongoDB (collections and indexes)
    await mongo_manager.initialize_db()
    # Initialize TaskQueue (if used by Gmail->Kafka pipeline)
    # await task_queue.initialize_db() # Assuming TaskQueue also needs init
    
    # Initialize Kafka Producer
    await initialize_kafka_producer_on_startup()

    # Initialize STT for voice input
    print(f"[{datetime.datetime.now()}] [LIFECYCLE] Loading STT model (FasterWhisper)...")
    try:
        stt_model = FasterWhisperSTT(model_size="base", device="cpu", compute_type="int8")
        print(f"[{datetime.datetime.now()}] [LIFECYCLE] STT model loaded.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [LIFECYCLE_ERROR] STT model failed to load. Voice input may not work. Details: {e}")
        stt_model = None
    
    # Initialize simplified TTS for dummy voice responses
    print(f"[{datetime.datetime.now()}] [LIFECYCLE] Loading TTS model (Orpheus for dummy responses)...")
    try:
        if TTS_PROVIDER == "ORPHEUS": # Only Orpheus needed
            tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
            print(f"[{datetime.datetime.now()}] [LIFECYCLE] Orpheus TTS (for dummy voice) loaded.")
        else:
            print(f"[{datetime.datetime.now()}] [LIFECYCLE_WARN] TTS_PROVIDER is '{TTS_PROVIDER}', but only Orpheus is used for dummy voice. Orpheus will be loaded.")
            tts_model = OrpheusTTS(verbose=False, default_voice_id=SELECTED_TTS_VOICE)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [LIFECYCLE_ERROR] Dummy TTS model (Orpheus) failed to load. Dummy voice responses may be silent. Details: {e}")
        tts_model = None

    # Start the central polling scheduler loop
    polling_scheduler_task_handle = asyncio.create_task(polling_scheduler_loop())
    print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE] Central polling scheduler started.")

    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [FASTAPI_LIFECYCLE] App startup complete.")
    yield # Application runs

    # --- Shutdown Logic ---
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [FASTAPI_LIFECYCLE] App shutdown sequence initiated...")
    if polling_scheduler_task_handle and not polling_scheduler_task_handle.done():
        print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE] Cancelling polling scheduler task...")
        polling_scheduler_task_handle.cancel()
        try:
            await polling_scheduler_task_handle
        except asyncio.CancelledError:
            print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE] Polling scheduler task successfully cancelled.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE_ERROR] Error during polling scheduler shutdown: {e}")
    
    # Close Kafka Producer
    await KafkaProducerManager.close_producer()

    if mongo_manager and mongo_manager.client:
        mongo_manager.client.close()
        print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE] MongoManager client closed.")
    # if task_queue and task_queue.client: 
    #     task_queue.client.close()
    #     print(f"[{datetime.datetime.now()}] [FASTAPI_LIFECYCLE] TaskQueue MongoDB client closed.")
    
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [FASTAPI_LIFECYCLE] App shutdown complete.")

# --- FastAPI Application Setup ---
print(f"[{datetime.datetime.now()}] [FASTAPI] Initializing FastAPI app...")
app = FastAPI(
    title="Sentient Server (Revamped)", 
    description="Core API for Sentient application: Onboarding, Dummy Chat, Gmail Polling.", 
    version="1.5.0_revamped", # Indicate revamped version
    docs_url="/docs", 
    redoc_url=None, 
    lifespan=lifespan
)
print(f"[{datetime.datetime.now()}] [FASTAPI] FastAPI app initialized.")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["app://.", "http://localhost:3000", "http://localhost"], # Client URLs
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)
print(f"[{datetime.datetime.now()}] [FASTAPI] CORS middleware added.")

# --- API Routers ---
# Import and include routers for different functionalities
from server.common import routes as common_routes
# from server.utils import routes as utils_routes # If Google Auth callback is here

app.include_router(common_routes.router)
# app.include_router(utils_routes.router, prefix="/utils") # Example

print(f"[{datetime.datetime.now()}] [FASTAPI] Routers included.")

# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="API Root", tags=["General"])
async def main_root():
    return {"message": "Sentient API (Revamped) is running."}

# --- Voice Endpoint (FastRTC for Dummy Voice Chat) ---
async def handle_dummy_voice_conversation(audio: tuple[int, np.ndarray]) -> AsyncGenerator[tuple[int, np.ndarray], None]:
    global stt_model, tts_model, SELECTED_TTS_VOICE
    user_id_for_voice = "voice_user_placeholder" # In a real app, this would come from authenticated session

    print(f"[{datetime.datetime.now()}] [VOICE_DUMMY] Audio chunk received (User: {user_id_for_voice})")

    if stt_model:
        user_transcribed_text = stt_model.stt(audio)
        if user_transcribed_text and user_transcribed_text.strip():
            print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_STT] User ({user_id_for_voice}): {user_transcribed_text}")
        else:
            print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_STT] No valid text transcribed for user {user_id_for_voice}.")
    else:
        print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_WARN] STT model not available. Skipping transcription.")

    # Generate a fixed dummy audio response
    dummy_response_text = "This is a dummy voice response."
    print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_TTS] Generating dummy TTS: '{dummy_response_text}'")

    if tts_model:
        try:
            # Assuming OrpheusTTS is used, which expects TTSOptions
            tts_options: TTSOptions = {"voice_id": SELECTED_TTS_VOICE}
            async for sr, chunk_np in tts_model.stream_tts(dummy_response_text, options=tts_options):
                if chunk_np is not None and chunk_np.size > 0:
                    yield (sr, chunk_np) # FastRTC expects (sample_rate, numpy_array)
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_TTS_ERROR] Error generating dummy audio: {e}")
            traceback.print_exc()
            # Optionally, yield a silent chunk or handle error appropriately
            # yield (24000, np.array([], dtype=np.float32)) 
    else:
        print(f"[{datetime.datetime.now()}] [VOICE_DUMMY_WARN] TTS model not available. Cannot generate dummy audio response.")
        # Yield a short silent audio segment as a fallback if no TTS
        # This ensures the FastRTC stream sends *something* back
        silence_duration_ms = 100
        sample_rate_for_silence = 16000 # A common sample rate
        num_samples = int(sample_rate_for_silence * (silence_duration_ms / 1000.0))
        silent_chunk = np.zeros(num_samples, dtype=np.float32)
        yield (sample_rate_for_silence, silent_chunk)
    
    print(f"[{datetime.datetime.now()}] [VOICE_DUMMY] Finished processing dummy voice response for {user_id_for_voice}.")

# Setup FastRTC Stream for voice
# Using ReplyOnPause implies VAD is active. For a simple dummy response,
# we might not need complex VAD, but keeping it maintains the structure.
voice_stream_handler = Stream(
    ReplyOnPause(
        handle_dummy_voice_conversation,
        algo_options=AlgoOptions( # Simplified VAD or defaults
            audio_chunk_duration=0.2, # Shorter chunks might be okay for dummy
            speech_threshold=0.3
        ), 
        model_options=SileroVadOptions(threshold=0.5), # Default Silero VAD
        can_interrupt=False # Dummy response doesn't need interruption
    ),
    mode="send-receive", # Client sends audio, server sends audio back
    modality="audio"
)

# Mount the FastRTC stream handler.
# The client (e.g., from BackgroundCircleProvider) will connect to this.
# FastRTC internally creates /webrtc/offer and /websocket/offer under this path.
voice_stream_handler.mount(app, path="/voice")
print(f"[{datetime.datetime.now()}] [FASTAPI] FastRTC voice stream for dummy responses mounted at /voice.")
print(f"[{datetime.datetime.now()}] [FASTAPI] Expected Voice WebSocket: ws://<host>:<port>/voice/websocket/offer")
print(f"[{datetime.datetime.now()}] [FASTAPI] Expected Voice WebRTC Offer: http://<host>:<port>/voice/webrtc/offer")


# --- Main Execution Block ---
if __name__ == "__main__":
    multiprocessing.freeze_support() # For PyInstaller compatibility if used

    # Configure Uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    log_config["loggers"]["uvicorn.error"]["level"] = "INFO" # Or "DEBUG" for more verbose startup/error logs

    app_server_port = int(os.getenv("APP_SERVER_PORT", 5000))
    print(f"[{datetime.datetime.now()}] [UVICORN] Starting Uvicorn server on host 0.0.0.0, port {app_server_port}...")
    print(f"[{datetime.datetime.now()}] [UVICORN] API Documentation (Swagger UI) available at http://localhost:{app_server_port}/docs")
    
    uvicorn.run(
        "server.app.app:app", # Path to the FastAPI app instance
        host="0.0.0.0",
        port=app_server_port,
        lifespan="on", # Use the lifespan manager
        reload=IS_DEV_ENVIRONMENT, # Enable auto-reload in development
        workers=1, # Typically 1 for development. Adjust for production.
        log_config=log_config
    )

# Calculate and print total startup time
END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP_COMPLETE] Server script full execution and Uvicorn setup took {END_TIME - START_TIME:.2f} seconds.")