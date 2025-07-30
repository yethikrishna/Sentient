from abc import ABC, abstractmethod

class BaseSTT(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        """
        Transcribes audio bytes to text.
        Implementations should handle format conversion if necessary.
        """
        pass