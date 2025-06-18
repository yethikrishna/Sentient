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
from fastapi import Depends

from fastrtc import ReplyOnPause, Stream, AlgoOptions, SileroVadOptions
from fastrtc.utils import audio_to_bytes, audio_to_float32, AdditionalOutputs
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    STT_PROVIDER, TTS_PROVIDER, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    FASTER_WHISPER_MODEL_SIZE, FASTER_WHISPER_DEVICE, FASTER_WHISPER_COMPUTE_TYPE, APP_SERVER_PORT
)
from .dependencies import mongo_manager
from .auth.routes import router as auth_router
from .chat.routes import router as chat_router
from .notifications.routes import router as notifications_router
from .integrations.routes import router as integrations_router
from .misc.routes import router as misc_router, OnboardingRequest, GoogleAuthSettings, SupermemorySettings
from .auth.utils import PermissionChecker
from .agents.routes import router as agents_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup...")
    await mongo_manager.initialize_db()
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App startup complete.")
    yield 
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown sequence initiated...")    
    if mongo_manager and mongo_manager.client:
        mongo_manager.client.close()
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [LIFESPAN] App shutdown complete.")

app = FastAPI(title="Sentient Main Server", version="2.2.0", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], # More permissive for development
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

app.include_router(auth_router)
app.include_router(chat_router)
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
            "llm": "qwen_agent_on_demand"
        }
    }

END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [APP_PY_LOADED] Main Server app.py loaded in {END_TIME - START_TIME:.2f} seconds.")


# VOICE LOGIC
# --- ElevenLabs Client ---
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- Qwen Agent Text Streaming Logic (from previous script) ---
def qwen_text_stream_for_echo(bot: Assistant, current_messages: list):
    """
    Streams text from a Qwen Agent for the echo function,
    filters out <think> blocks and tool calls, and yields complete, speakable sentences.
    """
    buffer = ""
    processed_lengths = {}
    sentence_terminators = {'.', '?', '!', '\n'}

    # bot.run() yields the *entire* list of messages at each step
    # We pass a copy of current_messages to avoid modification by bot.run internals if any
    for responses_list in bot.run(messages=list(current_messages)):
        for i, response_item in enumerate(responses_list):
            if response_item.get('role') == 'assistant' and 'content' in response_item and response_item['content']:
                last_len = processed_lengths.get(i, 0)
                current_content = response_item['content']
                if len(current_content) > last_len:
                    new_chunk = current_content[last_len:]
                    buffer += new_chunk
                    processed_lengths[i] = len(current_content)

        while '<think>' in buffer and '</think>' in buffer:
            start_idx = buffer.find('<think>')
            end_idx = buffer.find('</think>') + len('</think>')
            if start_idx < end_idx: buffer = buffer[:start_idx] + buffer[end_idx:]
            else: buffer = buffer.replace('</think>', '', 1)

        safe_to_process = buffer
        if '<think>' in buffer:
            safe_to_process = buffer[:buffer.find('<think>')]
        
        last_terminator_pos = -1
        positions = [safe_to_process.rfind(t) for t in sentence_terminators]
        if safe_to_process.rfind('...') > -1: positions.append(safe_to_process.rfind('...'))
        if positions: last_terminator_pos = max(positions)

        if last_terminator_pos != -1:
            terminator_len = 3 if safe_to_process.startswith('...', last_terminator_pos) else 1
            to_yield_part = safe_to_process[:last_terminator_pos + terminator_len]
            buffer = safe_to_process[last_terminator_pos + terminator_len:] + buffer[len(safe_to_process):]
            sentences = to_yield_part.replace('...', '...|').replace('.', '.|').replace('?', '?|').replace('!', '!|').replace('\n', '\n|').split('|')
            for sentence in sentences:
                if sentence.strip(): yield sentence.strip()

    if buffer.strip():
        final_part = buffer
        if '<think>' in final_part: final_part = final_part[:final_part.find('<think>')]
        if final_part.strip(): yield final_part.strip()


# --- FastRTC Echo Function ---
def echo(audio):
    global messages # Use the global messages list

    stt_time = time.time()
    logging.info("Performing STT")
    try:
        transcription = elevenlabs_client.speech_to_text.convert(
            file=audio_to_bytes(audio),
            model_id="scribe_v1",
            tag_audio_events=False,
            language_code="eng",
            diarize=False,
        )
        prompt = transcription.text # Assuming `transcription` has a `text` attribute
    except Exception as e:
        logging.error(f"STT Error: {e}")
        return

    if not prompt.strip(): # Check if prompt is empty or just whitespace
        logging.info("STT returned empty string or whitespace")
        return
    logging.info(f"STT response: '{prompt}'")
    messages.append({"role": "user", "content": prompt})
    logging.info(f"STT took {time.time() - stt_time:.2f} seconds")

    llm_time = time.time()
    full_spoken_response = ""

    # Use the Qwen agent stream
    for sentence in qwen_text_stream_for_echo(qwen_bot, messages):
        if not sentence.strip(): # Skip empty sentences
            continue
        
        logging.info(f"Sending to TTS: '{sentence}'")
        full_spoken_response += sentence + " "
        try:
            audio_stream = elevenlabs_client.text_to_speech.stream(
                text=sentence,
                voice_id="JBFqnCBsd6RMkjVDRZzb", # Example voice ID
                model_id="eleven_multilingual_v2",
                output_format="pcm_24000",
                voice_settings=VoiceSettings(
                    similarity_boost=0.75, stability=0.5, style=0.4, speed =1 # Example settings
                ),
            )
            for audio_chunk in audio_stream:
                if audio_chunk: # Ensure there's data in the chunk
                    audio_array = audio_to_float32(np.frombuffer(audio_chunk, dtype=np.int16))
                    yield (24000, audio_array) # Yield sample rate and audio data
        except Exception as e:
            logging.error(f"TTS Error for sentence '{sentence}': {e}")
            continue # Try to continue with the next sentence

    if full_spoken_response.strip():
        messages.append({"role": "assistant", "content": full_spoken_response.strip()})
        logging.info(f"LLM final spoken response: '{full_spoken_response.strip()}'")
    else:
        logging.info("LLM did not produce any speakable output.")
        
    logging.info(f"LLM processing took {time.time() - llm_time:.2f} seconds")


# --- FastRTC Stream Setup ---
stream = Stream(
    ReplyOnPause(
        echo,
        algo_options=AlgoOptions(
            audio_chunk_duration=0.5,
            started_talking_threshold=0.1,
            speech_threshold=0.03,
        ),
        model_options=SileroVadOptions(
            threshold=0.75, # VAD sensitivity
            min_speech_duration_ms=250,
            min_silence_duration_ms=1000, # Shorter silence for quicker replies
            speech_pad_ms=300, # Padding around detected speech
            max_speech_duration_s=15,
        ),
    ),
    modality="audio",
    mode="send-receive",
)


if __name__ == "__main__":
    import uvicorn
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER_ACCESS] %(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER_DEFAULT] %(message)s'
    uvicorn.run("server.main.app:app", host="0.0.0.0", port=APP_SERVER_PORT, lifespan="on", reload=False, workers=1, log_config=log_config)