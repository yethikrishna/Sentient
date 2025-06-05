# src/server/legacy/voice/gcp_tts.py
import os
from google.cloud import texttospeech_v1 as texttospeech # Use v1 for more control if needed
import logging
import asyncio

logger = logging.getLogger(__name__)

class GCPTTS:
    def __init__(self):
        # Authentication is handled by Application Default Credentials (ADC)
        # Ensure GOOGLE_APPLICATION_CREDENTIALS env var is set or gcloud auth application-default login run
        self.client = texttospeech.TextToSpeechAsyncClient() # Use AsyncClient
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-O", # Example of a Studio voice, usually higher quality
            # ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL # Name implies gender, or use Neural2/Wavenet directly
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000, # Good for voice
            # speaking_rate=1.0, # Default
            # pitch=0.0 # Default
        )
        logger.info("GCP TTS initialized (async).")

    async def stream_tts(self, text: str, options: dict = None): # Made async
        """
        Synthesizes speech from the input text and yields audio chunks asynchronously.
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config
        )
        
        logger.debug(f"GCP TTS synthesizing for text: '{text[:50]}...'")
        try:
            response = await self.client.synthesize_speech(request=request)
            # GCP TTS returns the full audio content. We need to chunk it.
            # A common chunk size for 16kHz 16-bit mono audio is 320 bytes for 10ms.
            # For faster streaming from server to client, smaller, more frequent chunks are better.
            chunk_size = 3200 # 100ms of 16kHz, 16-bit mono audio. (16000 samples/sec * 2 bytes/sample * 0.1 sec)
            
            audio_content = response.audio_content
            total_bytes = len(audio_content)
            # print(f"GCP TTS: Synthesized {total_bytes} bytes. Streaming in chunks of {chunk_size} bytes.")

            for i in range(0, total_bytes, chunk_size):
                chunk = audio_content[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.05) # Slight delay to simulate real streaming and prevent overwhelming client
                                        # This sleep might be adjusted or removed depending on client handling.
                                        # 0.1s of audio takes 0.1s to play. Sending faster is okay.
            
            logger.debug(f"Finished streaming audio from GCP TTS for text: '{text[:50]}...'")
        except Exception as e:
            logger.error(f"Error during GCP TTS synthesis or streaming: {e}")
            # Optionally yield an error marker or raise an exception
            return