# src/server/main/voice/tts/__init__.py
from .base_tts import BaseTTS, TTSOptionsBase
from .orpheus_tts import OrpheusTTS, TTSOptions as OrpheusTTSOptions, VoiceId as OrpheusVoiceId, AVAILABLE_VOICES as ORPHEUS_VOICES
from .eleven_labs_tts import ElevenLabsTTS