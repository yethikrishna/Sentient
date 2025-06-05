# src/server/main/voice/tts_services/eleven_labs_tts.py
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings
import logging
from typing import AsyncGenerator

from .base_tts import BaseTTS, TTSOptionsBase
from ...config import ELEVENLABS_API_KEY # Import API key from main config

logger = logging.getLogger(__name__)

class ElevenLabsTTS(BaseTTS):
    def __init__(self):
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY environment variable not set.")
            raise ValueError("ELEVENLABS_API_KEY environment variable not set for ElevenLabsTTS.")
        
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        self.voice_id = "JBFqnCBsd6RMkjVDRZzb"  # Example: "Rachel"
        self.model_id = "eleven_multilingual_v2" 
        logger.info(f"ElevenLabs TTS initialized with voice_id: {self.voice_id}, model_id: {self.model_id}")

    async def stream_tts(self, text: str, options: TTSOptionsBase = None) -> AsyncGenerator[bytes, None]:
        voice_id_to_use = self.voice_id
        # Options could allow overriding voice_id, stability, similarity_boost etc.
        custom_settings = {}
        if options:
            voice_id_to_use = options.get("voice_id", self.voice_id)
            if "stability" in options: custom_settings["stability"] = options["stability"]
            if "similarity_boost" in options: custom_settings["similarity_boost"] = options["similarity_boost"]
        
        effective_settings = VoiceSettings(
            stability=custom_settings.get("stability", 0.7), # Default stability
            similarity_boost=custom_settings.get("similarity_boost", 0.8) # Default similarity boost
        )

        logger.debug(f"ElevenLabs streaming TTS for text: '{text[:50]}...' using voice {voice_id_to_use}")
        
        try:
            audio_stream = self.client.generate(
                text=text,
                voice=Voice(voice_id=voice_id_to_use, settings=effective_settings),
                model=self.model_id,
                stream=True,
                output_format="pcm_16000", # Raw PCM at 16kHz
            )

            for chunk in audio_stream:
                if chunk:
                    yield chunk 
            logger.debug(f"Finished streaming audio from ElevenLabs TTS for text: '{text[:50]}...'")
        except Exception as e:
            logger.error(f"Error during ElevenLabs TTS streaming: {e}")
            return