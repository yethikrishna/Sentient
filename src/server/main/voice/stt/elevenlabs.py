import logging
import httpx
import wave
import io
from .base import BaseSTT
from ...config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)

def pcm_to_wav(pcm_data: bytes, sample_rate: int, num_channels: int = 1, sample_width: int = 2) -> bytes:
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        return wav_io.getvalue()

class ElevenLabsSTT(BaseSTT):
    def __init__(self):
        if not ELEVENLABS_API_KEY:
            logger.error("ELEVENLABS_API_KEY not set. ElevenLabsSTT cannot be initialized.")
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabsSTT.")
        
        self.client = httpx.AsyncClient()
        self.stt_api_url = "https://api.elevenlabs.io/v1/speech-to-text"
        logger.info(f"ElevenLabsSTT initialized (targetting endpoint: {self.stt_api_url}).")


    async def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        try:
            wav_data = pcm_to_wav(audio_bytes, sample_rate)
            files = {'audio': ('audio.wav', wav_data, 'audio/wav')}
            headers = {"xi-api-key": ELEVENLABS_API_KEY}
            
            response = await self.client.post(
                self.stt_api_url,
                files=files,
                headers=headers,
                timeout=30.0 
            )
            response.raise_for_status()
            result = response.json()
            transcription = result.get("transcription", result.get("text","")) 
            logger.debug(f"ElevenLabs STT Transcription: '{transcription}'")
            return transcription
        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs STT API error: {e.response.status_code} - {e.response.text}")
            return f"ElevenLabs STT Error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"Error during ElevenLabs STT transcription: {e}", exc_info=True)
            return "Error in STT processing."