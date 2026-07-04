"""Audio capture module using WASAPI Loopback.

Captures system audio output via Windows WASAPI Loopback API.
Supports specifying a custom output device by name (e.g. "SteelSeries Sonar").
"""

import logging
from typing import Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


def list_loopback_devices() -> list[dict]:
    """List all WASAPI loopback-capable audio devices.

    Returns:
        List of dicts with keys: name, index, channels, samplerate
        Sorted by name. Empty list if no loopback devices found.
    """
    devices = []
    try:
        for i, dev in enumerate(sd.query_devices()):
            # WASAPI loopback devices have max_output_channels > 0
            if dev["max_output_channels"] > 0:
                devices.append({
                    "name": dev["name"],
                    "index": i,
                    "channels": dev["max_output_channels"],
                    "samplerate": int(dev["default_samplerate"]),
                })
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return []

    devices.sort(key=lambda d: d["name"].lower())
    return devices


def find_device_by_name(name_substring: str) -> Optional[int]:
    """Find a WASAPI loopback device index by partial name match.

    Args:
        name_substring: Partial device name to search for (case-insensitive).

    Returns:
        Device index if found, None otherwise.
    """
    name_lower = name_substring.lower()
    for dev in list_loopback_devices():
        if name_lower in dev["name"].lower():
            logger.info(f"Found device '{dev['name']}' (index {dev['index']})")
            return dev["index"]

    logger.warning(f"No loopback device matching '{name_substring}' found")
    return None


class AudioCapture:
    """WASAPI Loopback audio capture for Windows system audio.

    Captures audio output from the specified device (or default if None).
    """

    def __init__(
        self,
        device_name: Optional[str] = None,
        mic_enabled: bool = False,
        mic_ratio: float = 0.3,
    ):
        self.sample_rate = 48000
        self.channels = 2
        self.blocksize = 1536  # 32ms @ 48kHz
        self.is_running = False
        self.mic_enabled = mic_enabled
        self.mic_ratio = mic_ratio
        self.device_name = device_name
        self._stream = None
        self._callback = None

    def set_callback(self, callback):
        """Set the audio data callback.

        Args:
            callback: Function that receives (numpy_array: (channels, samples) float32)
        """
        self._callback = callback

    def start(self):
        """Start audio capture using WASAPI loopback."""
        if self.is_running:
            return

        # Resolve device index from name
        device_index = None
        if self.device_name:
            device_index = find_device_by_name(self.device_name)
            if device_index is None:
                logger.warning(
                    f"Device '{self.device_name}' not found, falling back to default"
                )

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.blocksize,
                dtype=np.float32,
                callback=self._audio_callback,
                device=device_index,
            )
            self._stream.start()
            dev_info = sd.query_devices(device_index)
            logger.info(
                f"Audio capture started on device: {dev_info['name']} "
                f"(index={device_index})"
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
        """Internal audio callback from sounddevice."""
        if status:
            logger.warning(f"Audio capture status: {status}")

        # sounddevice gives (frames, channels), convert to (channels, frames)
        audio = indata.T.copy()

        if self._callback:
            self._callback(audio)

    def __del__(self):
        self.stop()
