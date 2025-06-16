import asyncio
import logging
import re
import uuid

import numpy as np
from fastrtc import (
    AudioPTime,
    ReplyOnPause,
    Stream,
    WebRTCData,
    audio_to_int16,
    create_message,
)

from ..app import stt_model_instance, tts_model_instance
from ..chat.utils import process_voice_command
from ..dependencies import mongo_manager

logger = logging.getLogger(__name__)

# A simple in-memory cache to hold user context during the WebRTC handshake.
# In a multi-worker setup, a shared cache like Redis would be necessary.
user_context_cache = {}

async def voice_chat_handler(audio: tuple[int, np.ndarray], webrtc_data: WebRTCData):
    """
    This is the main handler for the fastRTC audio stream.
    It gets triggered by ReplyOnPause when the user stops speaking.
    """
    webrtc_id = webrtc_data.webrtc_id
    context = user_context_cache.pop(webrtc_id, {})
    user_id = context.get("user_id")
    chat_id = context.get("chat_id")

    if not user_id or not chat_id:
        logger.error(f"User context not found for webrtc_id: {webrtc_id}")
        yield create_message("error", "Authentication context not found. Please reconnect.")
        return

    is_new_chat = False
    if not await mongo_manager.get_chat_history(user_id, chat_id):
        is_new_chat = True

    try:
        # 1. Transcribe the user's audio
        yield create_message("status", {"message": "transcribing"})
        pcm_s16le_bytes = audio_to_int16(audio[1]).tobytes()
        transcribed_text = await stt_model_instance.transcribe(pcm_s16le_bytes, sample_rate=audio[0])
        logger.info(f"STT Result for user {user_id}: '{transcribed_text}'")
        yield create_message("stt_result", {"text": transcribed_text})

        if not transcribed_text or not transcribed_text.strip():
            return

        if is_new_chat:
            title = ' '.join(transcribed_text.split()[:3])
            await mongo_manager.create_new_chat_session(user_id, chat_id, title)
            yield create_message("chat_created", {"chatId": chat_id, "title": title})

        # 2. Get LLM response from the existing chat agent logic
        yield create_message("status", {"message": "thinking"})
        user_profile = await mongo_manager.get_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"

        llm_response_text, assistant_message_id = await process_voice_command(
            user_id, chat_id, transcribed_text, username, mongo_manager
        )
        logger.info(f"LLM Result for user {user_id}: '{llm_response_text}'")
        yield create_message("llm_result", {"text": llm_response_text, "messageId": assistant_message_id})

        # 3. Strip <think> tags for TTS
        response_for_tts = re.sub(r"<think>.*?</think>", "", llm_response_text, flags=re.DOTALL).strip()

        if not response_for_tts:
            logger.info("No text to speak after stripping think tags.")
            return

        # 4. Stream the TTS audio back to the client
        yield create_message("status", {"message": "speaking"})
        async for audio_chunk in tts_model_instance.stream_tts(response_for_tts):
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16).reshape(1, -1)
            yield 16000, audio_array

    except Exception as e:
        logger.error(f"Error in voice chat handler for user {user_id}: {e}", exc_info=True)
        yield create_message("error", str(e))


stream = Stream(
    handler=ReplyOnPause(voice_chat_handler, can_interrupt=False),
    modality="audio",
)
