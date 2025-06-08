# src/server/main/voice/tts/__init__.py
from .base import BaseTTS, TTSOptionsBase
from .elevenlabs import ElevenLabsTTS

from ...config import TTS_PROVIDER

# Conditionally import Orpheus for development to avoid loading heavy dependencies in production.
if TTS_PROVIDER == "ORPHEUS":
    from .orpheus import OrpheusTTS, TTSOptions as OrpheusTTSOptions, VoiceId as OrpheusVoiceId, AVAILABLE_VOICES as ORPHEUS_VOICES