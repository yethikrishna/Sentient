import asyncio
import logging
import re
import uuid

import numpy as np
from fastrtc import (
    ReplyOnPause,
    Stream,
    WebRTCData,
    audio_to_int16,
    AdditionalOutputs,
)
from ..chat.utils import generate_chat_llm_stream

logger = logging.getLogger(__name__)

stt_model_instance = None
tts_model_instance = None
mongo_manager_instance = None

def set_dependencies(stt_model, tts_model, mongo_manager):
    """Sets dependencies from the main app to avoid circular imports."""
    global stt_model_instance, tts_model_instance, mongo_manager_instance
    stt_model_instance = stt_model
    tts_model_instance = tts_model
    mongo_manager_instance = mongo_manager
    logger.info("STT, TTS, and MongoManager dependencies set for voice stream handler.")

# A simple in-memory cache to hold user context during the WebRTC handshake.
# In a multi-worker setup, a shared cache like Redis would be necessary.
user_context_cache = {}

async def voice_chat_handler(audio: tuple[int, np.ndarray], webrtc_data: WebRTCData):
    webrtc_id = webrtc_data.webrtc_id
    context = user_context_cache.get(webrtc_id, {})
    user_id = context.get("user_id")
    chat_id = context.get("chat_id")

    if not user_id or not chat_id:
        logger.error(f"User context not found for webrtc_id: {webrtc_id}")
        yield AdditionalOutputs({"type": "error", "message": "Authentication context not found. Please reconnect."})
        return

    try:
        # 1. Transcribe the user's audio
        yield AdditionalOutputs({"type": "status", "message": "transcribing"})
        pcm_s16le_bytes = audio_to_int16(audio[1]).tobytes()
        transcribed_text = await stt_model_instance.transcribe(pcm_s16le_bytes, sample_rate=audio[0])
        logger.info(f"STT Result for user {user_id}: '{transcribed_text}'")
        yield AdditionalOutputs({"type": "stt_result", "text": transcribed_text})

        if not transcribed_text or not transcribed_text.strip():
            return

        # 2. Get LLM response from the existing chat agent logic
        yield AdditionalOutputs({"type": "status", "message": "thinking"})
        user_profile = await mongo_manager_instance.get_user_profile(user_id)
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"

        llm_stream = generate_chat_llm_stream(
            user_id, chat_id, transcribed_text, username, mongo_manager_instance,
            enable_internet=True, enable_weather=True, enable_news=True,
            enable_maps=True, enable_shopping=True
        )

        full_llm_response_for_ui = ""
        sentence_buffer = ""
        assistant_message_id = None

        async for event in llm_stream:
            if event.get("type") == "chat_created":
                yield AdditionalOutputs(event)
                chat_id = event.get("chatId")
                if webrtc_id in user_context_cache:
                    user_context_cache[webrtc_id]['chat_id'] = chat_id

            elif event.get("type") == "assistantStream" and not event.get("done"):
                if not assistant_message_id: assistant_message_id = event.get("messageId")

                token = event.get("token", "")
                full_llm_response_for_ui += token
                sentence_buffer += token

                sentences = re.split(r'(?<=[.?!])\s*', sentence_buffer)
                if len(sentences) > 1:
                    complete_sentences = sentences[:-1]
                    sentence_buffer = sentences[-1]

                    for sentence in complete_sentences:
                        sentence_for_tts = re.sub(r"<think>.*?</think>", "", sentence, flags=re.DOTALL).strip()
                        if sentence_for_tts:
                            yield AdditionalOutputs({"type": "status", "message": "speaking"})
                            async for audio_chunk in tts_model_instance.stream_tts(sentence_for_tts):
                                audio_array = np.frombuffer(audio_chunk, dtype=np.int16).reshape(1, -1)
                                yield 16000, audio_array

        # Send the final full text to the UI for display
        cleaned_response = re.sub(r"<think>.*?</think>", "", full_llm_response_for_ui, flags=re.DOTALL).strip()
        yield AdditionalOutputs({"type": "llm_result", "text": cleaned_response, "messageId": assistant_message_id})
        # Process leftover buffer from the LLM stream
        if sentence_buffer.strip():
            sentence_for_tts = re.sub(r"<think>.*?</think>", "", sentence_buffer, flags=re.DOTALL).strip()
            if sentence_for_tts:
                yield AdditionalOutputs({"type": "status", "message": "speaking"})
                async for audio_chunk in tts_model_instance.stream_tts(sentence_for_tts):
                    audio_array = np.frombuffer(audio_chunk, dtype=np.int16).reshape(1, -1)
                    yield 16000, audio_array

    except Exception as e:
        logger.error(f"Error in voice chat handler for user {user_id}: {e}", exc_info=True)
        yield AdditionalOutputs({"type": "error", "message": str(e)})
    finally:
        yield AdditionalOutputs({"type": "status", "message": "listening"})
        user_context_cache.pop(webrtc_id, None)

stream = Stream(
    handler=ReplyOnPause(voice_chat_handler, can_interrupt=False),
    modality="audio",
)