from .base import BaseTTS, TTSOptionsBase
from .elevenlabs import ElevenLabsTTS

from main.config import TTS_PROVIDER

# Conditionally import Orpheus for development to avoid loading heavy dependencies in production.
if TTS_PROVIDER == "ORPHEUS":
    try:
        from .orpheus import OrpheusTTS
    except ImportError:
        print("Could not import OrpheusTTS. Ensure all dependencies are installed.")
        OrpheusTTS = None # type: ignore