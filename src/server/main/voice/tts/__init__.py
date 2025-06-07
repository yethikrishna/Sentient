# src/server/main/voice/tts/__init__.py
from .base import BaseTTS, TTSOptionsBase
from .elevenlabs import ElevenLabsTTS

from ...config import IS_DEV_ENVIRONMENT

# Conditionally import Orpheus for development to avoid loading heavy dependencies in production.
if IS_DEV_ENVIRONMENT:
    from .orpheus import OrpheusTTS, TTSOptions as OrpheusTTSOptions, VoiceId as OrpheusVoiceId, AVAILABLE_VOICES as ORPHEUS_VOICES