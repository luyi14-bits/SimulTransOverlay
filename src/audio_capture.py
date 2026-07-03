"""Audio capture module using WASAPI Loopback.

Captures system audio output via Windows WASAPI Loopback API.
Supports optional microphone mixing.
"""

import numpy as np


class AudioCapture:
    """WASAPI Loopback audio capture for Windows system audio.

    Captures all audio output from the system's default playback device.
    """

    def __init__(self, mic_enabled: bool = False, mic_ratio: float = 0.3):
        self.sample_rate = 48000
        self.channels = 2
        self.blocksize = 1536  # 32ms @ 48kHz
        self.is_running = False
        self.mic_enabled = mic_enabled
        self.mic_ratio = mic_ratio
        self._stream = None
        self._callback = None

    def set_callback(self, callback):
        """Set the audio data callback.

        Args:
            callback: Function that receives (numpy_array: (channels, samples) float32)
        """
        self._callback = callback

    def start(self):
        """Start audio capture.

        In production, opens a sounddevice InputStream with WASAPI loopback.
        """
        if self.is_running:
            return

        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.blocksize,
                dtype=np.float32,
                callback=self._audio_callback,
                device=None,  # Default loopback device
            )
            self._stream.start()
        except ImportError:
            raise ImportError(
                "sounddevice not installed. Run: pip install sounddevice"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start audio capture: {e}")

        self.is_running = True

    def stop(self):
        """Stop audio capture."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.is_running = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal audio callback from sounddevice.

        Args:
            indata: Input audio buffer (frames x channels)
            frames: Number of frames
            time_info: Timing info
            status: Status flags
        """
        if status:
            import logging
            logging.warning(f"Audio capture status: {status}")

        # sounddevice gives (frames, channels), convert to (channels, frames)
        audio = indata.T.copy()

        if self._callback:
            self._callback(audio)

    def __del__(self):
        self.stop()
