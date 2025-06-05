# src/server/legacy/voice/stt.py
import numpy as np
from faster_whisper import WhisperModel
import librosa
import logging # Added logging

logger = logging.getLogger(__name__)

class FasterWhisperSTT:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        """
        Initialize the Faster Whisper STT model.
        """
        try:
            logger.info(f"Loading Whisper model '{model_size}' on {device} ({compute_type})...")
            self.whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            self.whisper_model = None # Ensure it's None on failure

    def stt(self, audio_data: bytes, input_sample_rate: int = 16000) -> str:
        """
        Transcribe audio bytes to text using the Faster Whisper model.
        Assumes input audio is raw PCM.

        Args:
            audio_data (bytes): Raw audio data bytes.
            input_sample_rate (int): Sample rate of the input audio_data.

        Returns:
            str: Transcribed text.
        """
        if self.whisper_model is None:
            logger.error("Whisper model not loaded. Cannot transcribe.")
            return ""

        try:
            # Convert raw bytes to NumPy array (assuming 16-bit PCM, which is common)
            # This might need adjustment if client sends audio in a different format (e.g., float32 bytes)
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # Convert to float32 and normalize
            audio_float32 = audio_np.astype(np.float32) / 32768.0
            
            # Resample to 16000 Hz if necessary for Whisper model
            target_sr = 16000
            if input_sample_rate != target_sr:
                # logger.debug(f"Resampling audio from {input_sample_rate} Hz to {target_sr} Hz.")
                audio_float32 = librosa.resample(y=audio_float32, orig_sr=input_sample_rate, target_sr=target_sr)

            if audio_float32.ndim != 1:
                audio_float32 = audio_float32.flatten()
            
            # logger.debug(f"Transcribing audio with shape {audio_float32.shape}, dtype {audio_float32.dtype}")
            segments, _ = self.whisper_model.transcribe(
                audio_float32,
                language="en", # Make configurable if needed
                task="transcribe"
                # beam_size=5 # Optional: for potentially better accuracy at cost of speed
            )
            transcription = " ".join([seg.text for seg in segments]).strip()
            # logger.debug(f"Transcription: '{transcription}'")
            return transcription
        except Exception as e:
            logger.error(f"Error during STT transcription: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def stt_from_tuple(self, audio_tuple: tuple[int, np.ndarray]) -> str:
        """
        Compatibility method to transcribe audio from a (sample_rate, audio_array) tuple.
        This is kept if other parts of the system still use this format.
        """
        if self.whisper_model is None:
            logger.error("Whisper model not loaded. Cannot transcribe (from tuple).")
            return ""

        sample_rate, audio_array = audio_tuple

        if audio_array.dtype == np.int16:
            audio_float32 = audio_array.astype(np.float32) / 32768.0
        elif audio_array.dtype == np.float32:
            audio_float32 = audio_array # Already float32
        else:
            logger.warning(f"Unsupported audio array dtype: {audio_array.dtype}. Attempting conversion to float32.")
            audio_float32 = audio_array.astype(np.float32) 
            # Normalization might be needed here depending on the original scale.
            # If it was, for example, uint8, simple casting isn't enough.
            # For now, assuming it's reasonably scaled if not int16/float32.

        target_sr = 16000
        if sample_rate != target_sr:
            audio_float32 = librosa.resample(y=audio_float32, orig_sr=sample_rate, target_sr=target_sr)

        if audio_float32.ndim != 1:
            audio_float32 = audio_float32.flatten()
        
        try:
            segments, _ = self.whisper_model.transcribe(
                audio_float32, language="en", task="transcribe"
            )
            transcription = " ".join([seg.text for seg in segments]).strip()
            return transcription
        except Exception as e:
            logger.error(f"Error during STT transcription (from tuple): {e}")
            return ""