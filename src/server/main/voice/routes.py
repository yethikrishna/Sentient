# src/server/main/voice/routes.py

import asyncio
import json
import logging
import uuid
import time
from typing import AsyncGenerator, Dict
import re

import numpy as np
from fastapi import APIRouter, Depends
from fastrtc import AlgoOptions, ReplyOnPause, SileroVadOptions, Stream
from fastrtc.utils import audio_to_float32, get_current_context

from main.auth.utils import PermissionChecker
from main.dependencies import mongo_manager
from main.llm import get_qwen_assistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

rtc_token_cache: Dict[str, Dict] = {}
TOKEN_EXPIRATION_SECONDS = 600

@router.post("/initiate", summary="Initiate a voice chat session")
async def initiate_voice_session(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))
):
    """
    Generates a short-lived, single-use token for authenticating a WebRTC/WebSocket voice stream.
    """
    # Clean up expired tokens to prevent the cache from growing indefinitely
    now = time.time()
    expired_tokens = [token for token, data in rtc_token_cache.items() if data["expires_at"] < now]
    for token in expired_tokens:
        del rtc_token_cache[token]

    # Generate a new token
    rtc_token = str(uuid.uuid4())
    expires_at = now + TOKEN_EXPIRATION_SECONDS
    rtc_token_cache[rtc_token] = {"user_id": user_id, "expires_at": expires_at}
    
    logger.info(f"Initiated voice session for user {user_id} with token {rtc_token}")
    return {"rtc_token": rtc_token}


class MyVoiceChatHandler(ReplyOnPause):
    """
    A custom FastRTC handler for managing a real-time voice chat session.
    It orchestrates STT, LLM, and TTS in a fully streaming pipeline.
    """
    def __init__(self):
        # Initialize the parent ReplyOnPause class with VAD settings
        super().__init__(
            fn=self.process_audio_chunk,
            model_options=SileroVadOptions(
                threshold=0.65,
                min_speech_duration_ms=250,
                min_silence_duration_ms=3000,   # wait 3s of silence
                speech_pad_ms=800,              # give extra buffer before and after speech
                max_speech_duration_s=15,
            ),
            algo_options=AlgoOptions(
                audio_chunk_duration=0.5,
                started_talking_threshold=0.1,
                speech_threshold=0.05,          # consider only more solid chunks as pause
            ),
            can_interrupt=True, # Set to False to prevent user interruption while bot is speaking
        )

    def copy(self):
        """Creates a new instance of the handler for each new connection."""
        return MyVoiceChatHandler()

    async def process_audio_chunk(self, audio: tuple[int, np.ndarray]):
        """
        Main callback for FastRTC. Handles STT, LLM, and TTS streaming.
        This function is a generator, yielding audio chunks back to the client.
        """
        from main.app import stt_model_instance, tts_model_instance

        context = get_current_context()
        webrtc_id = context.webrtc_id

        # Authenticate the stream using the webrtc_id as the RTC token
        rtc_token = webrtc_id
        token_info = rtc_token_cache.get(rtc_token, None)

        if not token_info or time.time() > token_info["expires_at"]:
            logger.error(f"Invalid or expired RTC token received: {rtc_token}. Terminating stream.")
            await self.send_message(json.dumps({"type": "error", "message": "Authentication failed. Please refresh."}))
            return

        user_id = token_info["user_id"]
        logger.info(f"WebRTC stream authenticated for user {user_id} via token {rtc_token}")

        try:
            # 1. Speech-to-Text (STT)
            if not stt_model_instance:
                raise Exception("STT model is not initialized.")
            
            await self.send_message(json.dumps({"type": "status", "message": "transcribing"}))
            sample_rate, audio_array = audio
            transcription = await stt_model_instance.transcribe(audio_array.tobytes(), sample_rate=sample_rate)
            
            if not transcription or not transcription.strip():
                logger.info("STT returned empty string, skipping.")
                await self.send_message(json.dumps({"type": "status", "message": "listening"}))
                return

            logger.info(f"STT result for user {user_id}: {transcription}")
            await self.send_message(json.dumps({"type": "stt_result", "text": transcription}))

            # 2. Save user message to DB
            user_message_id = str(uuid.uuid4())
            await mongo_manager.add_message(
                user_id=user_id, role="user", content=transcription, message_id=user_message_id
            )

            # 3. Language Model (LLM) - Get full response
            await self.send_message(json.dumps({"type": "status", "message": "thinking"}))
            
            # --- CORRECTED LOGIC ---
            # Fetch past history, reverse it to chronological order, then add the new user message.
            history = await mongo_manager.get_message_history(user_id, limit=20)
            messages_for_llm = list(reversed(history))
            messages_for_llm.append({"role": "user", "content": transcription})
            
            logger.info(f"LLM processing messages for user {user_id}: {messages_for_llm}")
            # --- END CORRECTION ---

            qwen_assistant = get_qwen_assistant(
                system_message="You are a helpful voice assistant. Keep your responses concise and conversational."
            )

            # Get the full final response from the LLM by iterating through its generator
            full_response_buffer = ""
            for history_chunk in qwen_assistant.run(messages=messages_for_llm):
                if isinstance(history_chunk, list) and history_chunk:
                    last_message = history_chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        full_response_buffer = last_message["content"]
            
            # Clean the response from any agent tags that shouldn't be spoken
            full_response_buffer = re.sub(r'<(think|tool_code|tool_result|answer)>.*?</\1>', '', full_response_buffer, flags=re.DOTALL).strip()

            if not full_response_buffer:
                logger.warning(f"LLM returned an empty response for user {user_id}.")
                await self.send_message(json.dumps({"type": "status", "message": "listening"}))
                return

            # Save the full response to DB
            assistant_message_id = str(uuid.uuid4())
            await self.send_message(json.dumps({"type": "llm_result", "text": full_response_buffer, "messageId": assistant_message_id}))
            await mongo_manager.add_message(
                user_id=user_id, role="assistant", content=full_response_buffer, message_id=assistant_message_id
            )

            # 4. Split response into sentences
            # This regex splits by sentence-ending punctuation while keeping the punctuation with the sentence.
            sentences = re.split(r'(?<=[.?!])\s+', full_response_buffer)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # 5. Text-to-Speech (TTS) per sentence
            if not tts_model_instance:
                raise Exception("TTS model is not initialized.")
            await self.send_message(json.dumps({"type": "status", "message": "speaking"}))

            # 6. Stream audio for each sentence
            for sentence in sentences:
                if not sentence: continue
                logger.info(f"Generating TTS for sentence: '{sentence}'")
                audio_stream = tts_model_instance.stream_tts(sentence)
                
                async for audio_chunk in audio_stream:
                    if isinstance(audio_chunk, tuple) and isinstance(audio_chunk[1], np.ndarray):
                        # This is from Orpheus TTS: (sample_rate, np.ndarray)
                        sample_rate, audio_array = audio_chunk
                        audio_float32 = audio_to_float32(audio_array)
                        yield (sample_rate, audio_float32)
                    elif isinstance(audio_chunk, bytes):
                        # This is from ElevenLabs TTS (PCM bytes)
                        # We need to convert it to the format fastrtc expects: (sample_rate, np.ndarray)
                        # Assuming 16kHz, 16-bit PCM from ElevenLabs
                        sample_rate = 16000 
                        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                        audio_float32 = audio_to_float32(audio_array)
                        yield (sample_rate, audio_float32)

        except Exception as e:
            logger.error(f"Error in voice_chat for user {user_id}: {e}", exc_info=True)
            await self.send_message(json.dumps({"type": "error", "message": str(e)}))
        finally:
            # Use a try-except block for the final message to prevent crashing on disconnect
            try:
                await self.send_message(json.dumps({"type": "status", "message": "listening"}))
            except Exception as final_e:
                logger.warning(f"Could not send final 'listening' status for user {user_id}, connection likely closed: {final_e}")


# --- Instantiate the handler and create the FastRTC Stream ---
stream = Stream(
    handler=MyVoiceChatHandler(),
    modality="audio",
    mode="send-receive",
)

@router.post("/end", summary="End voice chat session")
async def end_voice_session(rtc_token: str):
    if rtc_token in rtc_token_cache:
        del rtc_token_cache[rtc_token]
        return {"status": "terminated"}
    return {"status": "not_found"}