"""SenseVoice ASR engine backend.

Uses FunASR SenseVoice model for speech recognition.
Excels at Chinese/Japanese/Korean language recognition.
"""

import logging
from typing import Optional

import numpy as np

from .asr_engine import BaseASREngine

logger = logging.getLogger(__name__)


class SenseVoiceASREngine(BaseASREngine):
    """SenseVoice ASR engine via FunASR framework."""

    def __init__(self, language: str = "zh"):
        super().__init__(language=language)
        self.name = "sensevoice"
        self._model = None

    def load_model(self) -> None:
        """Load the SenseVoice model via FunASR.

        Downloads model if not already cached (~1GB for SenseVoice-Small).
        """
        try:
            from funasr import AutoModel

            logger.info("Loading SenseVoice model...")
            self._model = AutoModel(
                model="iic/SenseVoiceSmall",
                vad_model="iic/speech_fsmn_vad_zh-cn_16k-common-pytorch",
                punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
                disable_update=True,
            )
            self.is_loaded = True
            logger.info("SenseVoice model loaded successfully")

        except ImportError:
            raise ImportError(
                "funasr not installed. Run: pip install funasr"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load SenseVoice model: {e}")

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
            result = self._model.generate(input=audio)
            if result and len(result) > 0:
                return result[0].get("text", "")
            return ""
        except Exception as e:
            logger.error(f"SenseVoice transcription failed: {e}")
            return ""
