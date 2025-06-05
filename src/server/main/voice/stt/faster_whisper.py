# src/server/main/voice/stt_services/faster_whisper_stt.py
import numpy as np
from faster_whisper import WhisperModel
import librosa
import logging
import asyncio # For run_in_executor

from .base_stt import BaseSTT

logger = logging.getLogger(__name__)

class FasterWhisperSTT(BaseSTT):
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        try:
            logger.info(f"Loading FasterWhisper model '{model_size}' on {device} ({compute_type})...")
            self.whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("FasterWhisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading FasterWhisper model: {e}")
            self.whisper_model = None
            raise  # Re-raise exception to signal failure at startup

    def _transcribe_sync(self, audio_float32: np.ndarray) -> str:
        """Synchronous transcription part."""
        if self.whisper_model is None:
            logger.error("FasterWhisper model not loaded. Cannot transcribe.")
            return ""
        segments, _ = self.whisper_model.transcribe(
            audio_float32,
            language="en",
            task="transcribe"
        )
        return " ".join([seg.text for seg in segments]).strip()

    async def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        if self.whisper_model is None:
            return "" # Already logged during init

        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_np.astype(np.float32) / 32768.0
            
            target_sr = 16000 # Whisper native sample rate
            if sample_rate != target_sr:
                audio_float32 = librosa.resample(y=audio_float32, orig_sr=sample_rate, target_sr=target_sr)

            if audio_float32.ndim != 1: # Ensure 1D array
                audio_float32 = audio_float32.flatten()
            
            loop = asyncio.get_running_loop()
            # Run the blocking CTranslate2 model in a thread pool executor
            transcription = await loop.run_in_executor(None, self._transcribe_sync, audio_float32)
            
            logger.debug(f"FasterWhisper Transcription: '{transcription}'")
            return transcription
        except Exception as e:
            logger.error(f"Error during FasterWhisper STT transcription: {e}")
            import traceback
            traceback.print_exc()
            return ""