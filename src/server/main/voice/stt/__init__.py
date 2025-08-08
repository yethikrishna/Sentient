from .base import BaseSTT
from .elevenlabs import ElevenLabsSTT
from .deepgram import DeepgramSTT # New import
from main.config import STT_PROVIDER

if STT_PROVIDER == "FASTER_WHISPER":
    from .faster_whisper import FasterWhisperSTT
else:
    FasterWhisperSTT = None