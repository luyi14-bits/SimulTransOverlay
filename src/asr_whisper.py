"""faster-whisper ASR engine backend.

Uses CTranslate2-accelerated Whisper model for fast local speech recognition.
Supports GPU (CUDA) and CPU inference with INT8/FP16 quantization.
"""

import logging
from typing import Optional

import numpy as np

from .asr_engine import BaseASREngine

logger = logging.getLogger(__name__)


class WhisperASREngine(BaseASREngine):
    """faster-whisper ASR engine with CTranslate2 acceleration."""

    def __init__(
        self,
        model_size: str = "small",
        language: str = "ja",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        super().__init__(language=language)
        self.name = "faster-whisper"
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def load_model(self) -> None:
        """Load the faster-whisper model.

        Downloads the model if not already cached.
        """
        try:
            from faster_whisper import WhisperModel

            # Resolve device and compute type
            device, compute_type = self._resolve_device()

            logger.info(
                f"Loading faster-whisper {self.model_size} model "
                f"(device={device}, compute_type={compute_type})"
            )
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,  # Use default cache directory
            )
            self.is_loaded = True
            logger.info("faster-whisper model loaded successfully")

        except ImportError:
            raise ImportError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load faster-whisper model: {e}")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe 16kHz mono audio to text.

        Args:
            audio: 16kHz mono float32 audio array

        Returns:
            Transcribed text string
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if audio.size == 0:
            return ""

        try:
            segments, info = self._model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                vad_filter=False,  # VAD already done upstream
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            return " ".join(text_parts)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def _resolve_device(self):
        """Resolve the best available device and compute type.

        Returns:
            Tuple of (device, compute_type)
        """
        if self.device == "auto":
            import torch
            if torch.cuda.is_available():
                return "cuda", self.compute_type or "float16"
            return "cpu", self.compute_type or "int8"
        return self.device, self.compute_type or "int8"

    def unload(self) -> None:
        """Unload model and free GPU memory."""
        self._model = None
        self.is_loaded = False

        import gc
        gc.collect()

        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
