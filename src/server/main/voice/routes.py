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
TOKEN_EXPIRATION_SECONDS = 30

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


async def text_chunk_aggregator(llm_text_generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """
    Consumes a stream of text chunks from an LLM, filters out non-spoken agent tags,
    and yields complete sentences or clauses for a natural speech flow.
    """
    buffer = ""
    # Split on common sentence and clause delimiters for more natural pauses.
    delimiters = re.compile(r'([.?!,\n])')

    async for text_chunk in llm_text_generator:
        buffer += text_chunk
        
        # **FIX:** Remove non-spoken agent tags like <think>...</think> before processing.
        buffer = re.sub(r'<think>.*?</think>', '', buffer, flags=re.DOTALL)
        # Also remove other potential non-spoken tags for robustness
        buffer = re.sub(r'<(tool_code|tool_result|answer)>.*?</\1>', '', buffer, flags=re.DOTALL)


        # Split the buffer by delimiters, keeping the delimiters
        parts = delimiters.split(buffer)
        
        # The last part is an incomplete fragment, so we keep it in the buffer.
        # All other parts are complete clauses/sentences.
        if len(parts) > 1:
            # Re-join pairs of (text, delimiter)
            complete_chunks = ["".join(parts[i:i+2]) for i in range(0, len(parts) - 1, 2)]
            buffer = parts[-1]  # The last part is the new buffer
            
            for chunk in complete_chunks:
                if chunk.strip():
                    yield chunk.strip()

    # After the LLM stream is finished, yield any remaining text in the buffer
    if buffer.strip():
        yield buffer.strip()


class MyVoiceChatHandler(ReplyOnPause):
    """
    A custom FastRTC handler for managing a real-time voice chat session.
    It orchestrates STT, LLM, and TTS in a fully streaming pipeline.
    """
    def __init__(self):
        # Initialize the parent ReplyOnPause class with VAD settings
        super().__init__(
            fn=self.process_audio_chunk,
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
            can_interrupt=False, # Set to False to prevent user interruption while bot is speaking
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
        token_info = rtc_token_cache.pop(rtc_token, None)

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

            # 3. Language Model (LLM)
            await self.send_message(json.dumps({"type": "status", "message": "thinking"}))
            history = await mongo_manager.get_message_history(user_id, limit=20)
            messages_for_llm = [msg for msg in reversed(history)]
            qwen_assistant = get_qwen_assistant(
                system_message="You are a helpful voice assistant. Keep your responses concise and conversational."
            )

            # 4. Define an async generator for the LLM text stream
            async def llm_text_generator():
                full_response_buffer = ""
                for history_chunk in qwen_assistant.run(messages=messages_for_llm):
                    if isinstance(history_chunk, list) and history_chunk:
                        last_message = history_chunk[-1]
                        if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                            new_content = last_message["content"][len(full_response_buffer):]
                            if new_content:
                                yield new_content
                                full_response_buffer += new_content
                
                if full_response_buffer.strip():
                    assistant_message_id = str(uuid.uuid4())
                    await self.send_message(json.dumps({"type": "llm_result", "text": full_response_buffer, "messageId": assistant_message_id}))
                    await mongo_manager.add_message(
                        user_id=user_id, role="assistant", content=full_response_buffer, message_id=assistant_message_id
                    )

            # 5. Text-to-Speech (TTS)
            if not tts_model_instance:
                raise Exception("TTS model is not initialized.")
            await self.send_message(json.dumps({"type": "status", "message": "speaking"}))

            # 6. Create the sentence aggregator and stream audio back to the client
            sentence_generator = text_chunk_aggregator(llm_text_generator())
            async for sentence in sentence_generator:
                logger.info(f"Generating TTS for sentence: '{sentence}'")
                audio_stream = tts_model_instance.stream_tts(sentence)
                
                # Buffer all audio chunks for the current sentence
                sentence_audio_chunks = []
                sample_rate = None
                async for audio_chunk in audio_stream:
                    logger.info(f"Received TTS audio chunk {audio_chunk}")
                    if isinstance(audio_chunk, tuple) and isinstance(audio_chunk[1], np.ndarray):
                        if sample_rate is None:
                            sample_rate = audio_chunk[0]
                        sentence_audio_chunks.append(audio_chunk[1])
                
                # If we have audio chunks, concatenate and yield them as a single block
                if sentence_audio_chunks and sample_rate is not None:
                    full_sentence_audio = np.concatenate(sentence_audio_chunks)
                    audio_float32 = audio_to_float32(full_sentence_audio)
                    logger.info(f"Yielding full sentence audio of length {len(audio_float32)} samples.")
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