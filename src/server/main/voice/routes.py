import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Optional

import numpy as np
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastrtc import AlgoOptions, ReplyOnPause, SileroVadOptions, Stream, get_cloudflare_turn_credentials_async
from fastrtc.utils import audio_to_float32

from main.auth.utils import AuthHelper, PermissionChecker
from main.dependencies import auth_helper, mongo_manager
from main.llm import get_qwen_assistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

# A simple in-memory cache for temporary WebRTC tokens.
# In a multi-worker production environment, this should be replaced with Redis.
# Format: { "rtc_token": {"user_id": "...", "expires_at": ...} }
rtc_token_cache: Dict[str, Dict] = {}
TOKEN_EXPIRATION_SECONDS = 30

@router.post("/initiate", summary="Initiate a voice chat session")
async def initiate_voice_session(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))
):
    """
    1. Authenticates the user.
    2. Generates a secure, single-use token (rtc_token).
    3. Caches the token with the user_id and a short expiration.
    4. Returns the token to the client.
    The client will then use this token as the 'webrtc_id' to connect.
    """
    rtc_token = str(uuid.uuid4())
    expires_at = time.time() + TOKEN_EXPIRATION_SECONDS
    rtc_token_cache[rtc_token] = {"user_id": user_id, "expires_at": expires_at}
    
    logger.info(f"Initiated voice session for user {user_id} with token {rtc_token}")
    return {"rtc_token": rtc_token}

def voice_chat(audio, ctx):
    """
    Main callback for FastRTC. Handles STT, LLM, and TTS streaming.
    This function is a generator, yielding audio chunks back to the client.
    """
    logger.info("Starting voice chat session with ctx: %s", ctx)
    from main.app import stt_model_instance, tts_model_instance

    # Authenticate the stream using the webrtc_id as a temporary token
    rtc_token = ctx.webrtc_id
    token_info = rtc_token_cache.pop(rtc_token, None) # Pop to make it single-use

    if not token_info or time.time() > token_info["expires_at"]:
        logger.error(f"Invalid or expired RTC token received: {rtc_token}. Terminating stream.")
        return

    user_id = token_info["user_id"]
    logger.info(f"WebRTC stream authenticated for user {user_id} via token {rtc_token}")

    loop = asyncio.get_event_loop()

    try:
        # 1. Speech-to-Text (STT)
        if not stt_model_instance:
            raise Exception("STT model is not initialized.")
        
        ctx.send(json.dumps({"type": "status", "message": "transcribing"}))
        transcription = stt_model_instance.transcribe_audio(audio)
        if not transcription or not transcription.strip():
            logger.info("STT returned empty string, skipping.")
            ctx.send(json.dumps({"type": "status", "message": "listening"}))
            return

        logger.info(f"STT result for user {user_id}: {transcription}")
        ctx.send(json.dumps({"type": "stt_result", "text": transcription}))

        # 2. Save user message to DB
        user_message_id = str(uuid.uuid4())
        loop.run_until_complete(
            mongo_manager.add_message(
                user_id=user_id,
                role="user",
                content=transcription,
                message_id=user_message_id,
            )
        )

        # 3. Language Model (LLM)
        ctx.send(json.dumps({"type": "status", "message": "thinking"}))
        history = loop.run_until_complete(
            mongo_manager.get_message_history(user_id, limit=20)
        )
        
        messages_for_llm = [msg for msg in reversed(history)]

        qwen_assistant = get_qwen_assistant(
            system_message="You are a helpful voice assistant. Keep your responses concise and conversational."
        )

        def text_stream_generator():
            full_response = ""
            for chunk in qwen_assistant.run(messages=messages_for_llm):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(
                        last_message.get("content"), str
                    ):
                        new_content = last_message["content"][len(full_response):]
                        if new_content:
                            full_response += new_content
                            yield new_content
            
            assistant_message_id = str(uuid.uuid4())
            ctx.send(json.dumps({"type": "llm_result", "text": full_response, "messageId": assistant_message_id}))
            loop.run_until_complete(
                mongo_manager.add_message(
                    user_id=user_id,
                    role="assistant",
                    content=full_response,
                    message_id=assistant_message_id,
                )
            )

        # 5. Text-to-Speech (TTS)
        if not tts_model_instance:
            raise Exception("TTS model is not initialized.")

        ctx.send(json.dumps({"type": "status", "message": "speaking"}))
        audio_stream = tts_model_instance.generate_audio_stream(text_stream_generator())

        # 6. Stream audio back to client
        for audio_chunk in audio_stream:
            if isinstance(audio_chunk, bytes):
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float32 = audio_to_float32(audio_array)
            elif isinstance(audio_chunk, np.ndarray):
                audio_float32 = audio_to_float32(audio_chunk)
            else:
                continue
            
            yield (tts_model_instance.sample_rate, audio_float32)

    except Exception as e:
        logger.error(f"Error in voice_chat for user {user_id}: {e}", exc_info=True)
        ctx.send(json.dumps({"type": "error", "message": str(e)}))
    finally:
        ctx.send(json.dumps({"type": "status", "message": "listening"}))

# Configure and create the FastRTC stream
# Using a TURN server is necessary for cloud deployments to handle firewalls and NATs.
stream = Stream(
    ReplyOnPause(
        voice_chat,
        algo_options=AlgoOptions(
            audio_chunk_duration=0.5,
            started_talking_threshold=0.1,
            speech_threshold=0.03,
        ),
        model_options=SileroVadOptions(
            threshold=0.75,
            min_speech_duration_ms=250,
            min_silence_duration_ms=1500,
            speech_pad_ms=400,
            max_speech_duration_s=15,
        ),
    ),
    modality="audio",
    mode="send-receive",
    # Use Cloudflare's TURN service via the helper function.
    # This requires the HF_TOKEN environment variable to be set.
)