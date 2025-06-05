# src/server/legacy/voice/elevenlabs_tts.py
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings, PlaybackOptions
import logging

logger = logging.getLogger(__name__)

class ElevenLabsTTS:
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            logger.error("ELEVENLABS_API_KEY environment variable not set.")
            raise ValueError("ELEVENLABS_API_KEY environment variable not set.")
        
        self.client = ElevenLabs(api_key=api_key)
        # Default voice, can be overridden in stream_tts if needed
        self.voice_id = "JBFqnCBsd6RMkjVDRZzb"  # Example: A versatile voice like "Rachel"
        self.model_id = "eleven_multilingual_v2" 
        logger.info(f"ElevenLabs TTS initialized with voice_id: {self.voice_id}, model_id: {self.model_id}")

    async def stream_tts(self, text: str, options: dict = None): # Made async
        """
        Synthesizes speech from the input text and yields audio chunks asynchronously.
        """
        voice_id_to_use = self.voice_id
        if options and options.get("voice_id"): # Allow overriding voice via options if needed
            voice_id_to_use = options["voice_id"]
            logger.debug(f"Using voice_id from options: {voice_id_to_use}")
        
        logger.debug(f"ElevenLabs streaming TTS for text: '{text[:50]}...' using voice {voice_id_to_use}")
        
        try:
            # Corrected call structure based on elevenlabs client usage for streaming
            # The `convert` method might not be directly streamable in an async context like this
            # or might return a generator that needs careful handling.
            # The standard way to stream is often client.generate(text=..., stream=True, ...)
            
            # Using generate with stream=True
            # The output format pcm_16000 ensures it's raw PCM at 16kHz, suitable for WebRTC/voice.
            audio_stream = self.client.generate(
                text=text,
                voice=Voice(voice_id=voice_id_to_use, settings=VoiceSettings(stability=0.7, similarity_boost=0.8)),
                model=self.model_id,
                stream=True, # Enable streaming
                output_format="pcm_16000", # For compatibility with voice applications
                # latency is a parameter for generate, not PlaybackOptions here for raw PCM.
                # latency=1 # (1-4, 1 is fastest) - this might be specific to certain models or output formats
            )

            # The audio_stream is an iterator of bytes.
            # Yield chunks directly from the stream.
            for chunk in audio_stream:
                if chunk: # Ensure chunk is not None or empty
                    yield chunk # Yield bytes directly
            logger.debug(f"Finished streaming audio from ElevenLabs TTS for text: '{text[:50]}...'")
        except Exception as e:
            logger.error(f"Error during ElevenLabs TTS streaming: {e}")
            # Optionally yield a specific error marker or raise an exception that can be caught upstream
            # For now, just logging and stopping the generator.
            return