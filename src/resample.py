"""Audio resample module.

Resamples captured audio from 48kHz stereo f32 to 16kHz mono f32,
the format required by Silero VAD and faster-whisper.
"""

import numpy as np


def validate_audio_format(audio: np.ndarray, sample_rate: int) -> None:
    """Validate that the input audio has the expected format.

    Args:
        audio: Input audio array (stereo 2D or mono 1D)
        sample_rate: Sample rate of the input audio

    Raises:
        ValueError: If format is not 48kHz float32
    """
    if sample_rate != 48000:
        raise ValueError(
            f"Expected sample_rate=48000, got {sample_rate}"
        )
    if audio.dtype != np.float32:
        raise ValueError(
            f"Expected dtype=float32, got {audio.dtype}"
        )


def _stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert stereo to mono by averaging channels.

    Args:
        audio: Input audio array (2D: channels x samples, or 1D: already mono)

    Returns:
        Mono audio array (1D)
    """
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2 and audio.shape[0] == 2:
        return np.mean(audio, axis=0, dtype=np.float32)
    raise ValueError(f"Unexpected audio shape: {audio.shape}")


def resample_to_16khz(audio: np.ndarray) -> np.ndarray:
    """Resample 48kHz audio to 16kHz mono.

    Uses linear interpolation for simplicity. For production use,
    consider a proper polyphase filter (e.g., scipy.signal.resample or libsamplerate).

    Args:
        audio: Input audio array (2D: channels x samples @ 48kHz, or 1D mono)

    Returns:
        Mono audio array at 16kHz (1D numpy array of float32)
    """
    if audio.size == 0:
        return np.array([], dtype=np.float32)

    # Convert to mono first
    mono = _stereo_to_mono(audio)

    input_len = len(mono)
    output_len = int(input_len * 16000 / 48000)

    if output_len == 0:
        return np.array([], dtype=np.float32)

    # Linear interpolation
    indices = np.linspace(0, input_len - 1, output_len)
    low_idx = indices.astype(np.int64)
    high_idx = np.clip(low_idx + 1, 0, input_len - 1)
    frac = indices - low_idx

    result = mono[low_idx] * (1 - frac) + mono[high_idx] * frac
    return result.astype(np.float32)
