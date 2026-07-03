"""ASR engine base module.

Defines the abstract base class for ASR engines, factory function,
and transcription result buffer for sentence assembly.
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class BaseASREngine(ABC):
    """Abstract base class for all ASR engines."""

    def __init__(self, language: str = "ja"):
        self.name = "base"
        self.language = language
        self.is_loaded = False

    @abstractmethod
    def load_model(self) -> None:
        """Load the ASR model into memory."""
        ...

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text.

        Args:
            audio: 16kHz mono float32 audio array

        Returns:
            Transcribed text string
        """
        ...

    def unload(self) -> None:
        """Unload the model to free memory."""
        self.is_loaded = False


class TranscriptionBuffer:
    """Buffer for assembling transcription segments into sentences.

    Manages a sliding window of recent transcription results
    and assembles them into coherent sentences.
    """

    def __init__(self, max_segments: int = 5):
        self.max_segments = max_segments
        self._segments = []

    def add_segment(self, text: str) -> Optional[str]:
        """Add a transcription segment and return the assembled sentence.

        Args:
            text: New transcription segment

        Returns:
            Assembled sentence if buffer is ready, None otherwise
        """
        if not text.strip():
            return None

        self._segments.append(text.strip())

        # Keep only the last N segments
        if len(self._segments) > self.max_segments:
            self._segments.pop(0)

        # Assemble into a sentence
        return " ".join(self._segments)

    def clear(self) -> None:
        """Clear the buffer."""
        self._segments = []

    @property
    def current_text(self) -> str:
        """Get the current buffered text."""
        return " ".join(self._segments)


def create_asr_engine(
    engine_name: str = "faster-whisper",
    model_size: str = "small",
    language: str = "ja",
    device: str = "auto",
    compute_type: str = "int8",
) -> BaseASREngine:
    """Factory function to create an ASR engine instance.

    Args:
        engine_name: "faster-whisper" or "sensevoice"
        model_size: Model size (tiny/base/small/medium/large)
        language: Source language code
        device: "auto" | "cuda" | "cpu"
        compute_type: "auto" | "float16" | "int8" | "float32"

    Returns:
        An ASR engine instance

    Raises:
        ValueError: If engine_name is not supported
    """
    if engine_name == "faster-whisper":
        from .asr_whisper import WhisperASREngine
        return WhisperASREngine(
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type,
        )
    elif engine_name == "sensevoice":
        from .asr_sensevoice import SenseVoiceASREngine
        return SenseVoiceASREngine(language=language)
    else:
        raise ValueError(f"Unknown engine: {engine_name}")
