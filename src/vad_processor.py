"""Silero VAD (Voice Activity Detection) processor module.

Detects speech segments in 16kHz mono audio streams using Silero VAD.
Handles real-time segmentation with configurable silence thresholds.
"""

import numpy as np


class SileroVADProcessor:
    """Voice Activity Detection processor using Silero VAD model.

    Processes 16kHz mono audio chunks and detects speech segments.
    Manages speech/silence state for real-time segmentation.
    """

    def __init__(self, silence_threshold: float = 0.5):
        self.sample_rate = 16000
        self.silence_threshold = silence_threshold
        self._is_speech_active = False
        self._silence_duration = 0.0
        self._speech_duration = 0.0
        self._chunk_duration = 0.032  # 32ms per chunk at 16kHz
        self._speech_buffer = []
        self._model = None

    @property
    def is_speech_active(self) -> bool:
        return self._is_speech_active

    @is_speech_active.setter
    def is_speech_active(self, value: bool):
        self._is_speech_active = value

    @property
    def silence_duration(self) -> float:
        return self._silence_duration

    @silence_duration.setter
    def silence_duration(self, value: float):
        self._silence_duration = value

    def load_model(self) -> None:
        """Load the Silero VAD model.

        In production, this uses the silero-vad library.
        """
        try:
            import silero_vad
            self._model = silero_vad.load_silero_vad()
        except ImportError:
            raise ImportError(
                "silero-vad not installed. Run: pip install silero-vad"
            )

    def process_chunk(self, audio_chunk: np.ndarray) -> float:
        """Process a 16kHz mono audio chunk and return speech probability.

        Args:
            audio_chunk: 16kHz mono float32 audio chunk (typically 512 samples / 32ms)

        Returns:
            Speech probability between 0.0 and 1.0

        Raises:
            ValueError: If audio format is invalid
        """
        if audio_chunk.dtype != np.float32:
            raise ValueError(f"Expected float32, got {audio_chunk.dtype}")

        if len(audio_chunk) != 512:
            raise ValueError(
                f"Expected 512 samples (32ms @ 16kHz), got {len(audio_chunk)}"
            )

        # In real implementation, this calls the silero-vad model
        # For now, return a mock probability based on signal energy
        energy = np.mean(audio_chunk ** 2)
        probability = min(1.0, float(energy * 100))

        # Track speech/silence state
        if probability > 0.5:
            self._is_speech_active = True
            self._silence_duration = 0.0
            self._speech_duration += self._chunk_duration
            self._speech_buffer.append(audio_chunk)
        else:
            if self._is_speech_active:
                self._silence_duration += self._chunk_duration
            self._speech_duration = 0.0

        return probability

    def should_segment(self) -> bool:
        """Check if current speech segment should be finalized.

        Returns:
            True if silence duration exceeds threshold
        """
        if self._is_speech_active and self._silence_duration >= self.silence_threshold:
            return True
        return False

    def pop_segment(self) -> np.ndarray:
        """Get the accumulated speech segment and reset buffer.

        Returns:
            Concatenated audio samples for the speech segment
        """
        if not self._speech_buffer:
            return np.array([], dtype=np.float32)

        segment = np.concatenate(self._speech_buffer)
        self._speech_buffer = []
        self._is_speech_active = False
        self._silence_duration = 0.0
        self._speech_duration = 0.0
        return segment
