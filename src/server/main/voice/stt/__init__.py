from .base import BaseSTT
from .elevenlabs import ElevenLabsSTTfrom main.config import STT_PROVIDER

# Conditionally import FasterWhisper to avoid loading heavy dependencies if not used.
if STT_PROVIDER == "FASTER_WHISPER":
    try:
        from .faster_whisper import FasterWhisperSTT
    except ImportError:
        print("Could not import FasterWhisperSTT. Ensure all dependencies are installed.")
        FasterWhisperSTT = None
else:
    FasterWhisperSTT = None
