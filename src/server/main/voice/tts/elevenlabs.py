import os
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings
import logging
from typing import AsyncGenerator, Optional

from .base import BaseTTS, TTSOptionsBase
from ...config import ELEVENLABS_API_KEY 

logger = logging.getLogger(__name__)

class ElevenLabsTTS(BaseTTS):
    def __init__(self, voice_id: Optional[str] = None, model_id: Optional[str] = None):
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY environment variable not set.")
            raise ValueError("ELEVENLABS_API_KEY environment variable not set for ElevenLabsTTS.")
        
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        # Default voice "Rachel" ID: JBFqnCBsd6RMkjVDRZzb
        self.voice_id = voice_id or "JBFqnCBsd6RMkjVDRZzb" 
        self.model_id = model_id or "eleven_multilingual_v2" 
        logger.info(f"ElevenLabs TTS initialized with voice_id: {self.voice_id}, model_id: {self.model_id}")

    async def stream_tts(self, text: str, options: TTSOptionsBase = None) -> AsyncGenerator[bytes, None]:
        voice_id_to_use = self.voice_id
        model_id_to_use = self.model_id
        
        custom_settings_dict = {}
        if options:
            voice_id_to_use = options.get("voice_id", self.voice_id)
            model_id_to_use = options.get("model_id", self.model_id)
            if "stability" in options: custom_settings_dict["stability"] = options["stability"]
            if "similarity_boost" in options: custom_settings_dict["similarity_boost"] = options["similarity_boost"]
            if "style" in options: custom_settings_dict["style"] = options["style"]
            if "use_speaker_boost" in options: custom_settings_dict["use_speaker_boost"] = options["use_speaker_boost"]
        
        effective_settings = VoiceSettings(
            stability=custom_settings_dict.get("stability", 0.71), 
            similarity_boost=custom_settings_dict.get("similarity_boost", 0.5),
            style=custom_settings_dict.get("style", 0.0), 
            use_speaker_boost=custom_settings_dict.get("use_speaker_boost", True)
        )

        logger.debug(f"ElevenLabs streaming TTS for text: '{text[:50]}...' using voice {voice_id_to_use}, model {model_id_to_use}")
        
        try:
            audio_stream = self.client.generate(
                text=text,
                voice=Voice(voice_id=voice_id_to_use, settings=effective_settings),
                model=model_id_to_use,
                stream=True,
                output_format="pcm_16000", 
            )

            if not hasattr(audio_stream, '__iter__') and not hasattr(audio_stream, '__aiter__'):
                logger.error("ElevenLabs client.generate did not return a streamable object.")
                return

            for chunk in audio_stream: # type: ignore
                if chunk:
                    yield chunk 
            logger.debug(f"Finished streaming audio from ElevenLabs TTS for text: '{text[:50]}...'")
        except Exception as e:
            logger.error(f"Error during ElevenLabs TTS streaming: {e}", exc_info=True)
            yield b"" 
            return