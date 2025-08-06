from .base import BaseTTS, TTSOptionsBase
from .elevenlabs import ElevenLabsTTS
from main.config import TTS_PROVIDER

if TTS_PROVIDER == "ORPHEUS":
    from .orpheus import OrpheusTTS
else:
    OrpheusTTS = None