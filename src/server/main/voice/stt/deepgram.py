import logging
import asyncio
from .base import BaseSTT
from main.config import DEEPGRAM_API_KEY

try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        BufferSource,
    )
except ImportError:
    raise ImportError("Deepgram SDK not installed. Please install it with 'pip install deepgram-sdk>=3.0'")

logger = logging.getLogger(__name__)

class DeepgramSTT(BaseSTT):
    """
    Deepgram Speech-to-Text implementation that transcribes audio chunks.
    """
    def __init__(self):
        if not DEEPGRAM_API_KEY:
            logger.error("DEEPGRAM_API_KEY not set. DeepgramSTT cannot be initialized.")
            raise ValueError("DEEPGRAM_API_KEY is required for DeepgramSTT.")
        
        try:
            # Initialize the Deepgram Client
            self.client = DeepgramClient(DEEPGRAM_API_KEY)
            logger.info("DeepgramSTT initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}", exc_info=True)
            raise

    async def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        """
        Transcribes an audio chunk using Deepgram's REST API for pre-recorded audio,
        which is suitable for chunk-by-chunk processing.
        """
        if not self.client:
            logger.error("Deepgram client not initialized.")
            return ""

        try:
            # The audio is raw PCM, 16-bit signed little-endian, mono.
            # We must provide the mimetype to Deepgram.
            source: BufferSource = {
                "buffer": audio_bytes
            }
            
            # Configure Deepgram options for the request for best results
            # Crucially, we must specify the encoding, sample_rate, and channels for raw audio.
            options = PrerecordedOptions(
                model="nova-3",
                smart_format=True,
                punctuate=True,
                utterances=True,
                encoding="linear16",
                sample_rate=sample_rate,
                channels=1
            )

            # Make the API call to transcribe the audio buffer
            response = await self.client.listen.asyncrest.v("1").transcribe_file(
                source, options
            )
            
            # Extract the transcript from the response
            transcript = response.results.channels[0].alternatives[0].transcript
            logger.debug(f"Deepgram STT Transcription: '{transcript}'")
            return transcript.strip()

        except Exception as e:
            logger.error(f"Error during Deepgram STT transcription: {e}", exc_info=True)
            # Return an empty string on error to avoid breaking the voice chat flow
            return ""