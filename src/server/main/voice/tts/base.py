# src/server/main/voice/tts_services/base_tts.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Tuple
import numpy as np

class TTSOptionsBase(dict): # Using dict for flexibility, can be Pydantic model
    pass

class BaseTTS(ABC):
    @abstractmethod
    async def stream_tts(self, text: str, options: TTSOptionsBase = None) -> AsyncGenerator[bytes | Tuple[int, np.ndarray], None]:
        """
        Streams synthesized audio for the given text.
        Yields audio chunks. Chunks can be bytes (preferred for direct network sending)
        or a tuple of (sample_rate, numpy_array_of_floats) for some internal TTS like Orpheus.
        The voice WebSocket route will need to handle these types.
        """
        # This is for type hinting; actual implementation will use `yield`
        if False: # pragma: no cover
            yield b"" 