"""Audio capture module using WASAPI Loopback.

Captures system audio output via Windows WASAPI Loopback API.
Auto-detects the current active output device — no manual config needed.
"""

import logging
from typing import Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# Virtual audio device keywords to prioritize (SteelSeries, Voicemeeter, etc.)
_VIRTUAL_KEYWORDS = [
    "sonar", "steelseries", "vb-cable", "voicemeeter",
    "virtual", "cable", "obs", "audio router",
]


def list_loopback_devices() -> list[dict]:
    """List all WASAPI loopback capture devices.

    WASAPI loopback devices appear as input devices in sounddevice,
    associated with the WASAPI host API. Each captures the audio
    being played through a specific output device.

    Returns:
        List of dicts with keys: name, index, channels, is_default
    """
    devices = []
    try:
        wasapi_hostapi_indices = _get_wasapi_hostapi_indices()

        for i, dev in enumerate(sd.query_devices()):
            # Loopback = WASAPI input device with input channels
            if (
                dev["hostapi"] in wasapi_hostapi_indices
                and dev["max_input_channels"] > 0
            ):
                # Check if this is the default WASAPI loopback device
                is_default = "WASAPI" in dev["name"] and "loopback" in dev["name"].lower()
                devices.append({
                    "name": dev["name"],
                    "index": i,
                    "channels": dev["max_input_channels"],
                    "samplerate": int(dev["default_samplerate"]),
                    "is_default": bool(dev.get("default_samplerate")),
                })
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return []

    devices.sort(key=lambda d: (not d["is_default"], d["name"].lower()))
    return devices


def _get_wasapi_hostapi_indices() -> list[int]:
    """Get indices of WASAPI host APIs."""
    indices = []
    for i in range(sd.query_hostapis().__len__()):
        api = sd.query_hostapis(i)
        if "wasapi" in api["name"].lower():
            indices.append(i)
    return indices


def find_best_device() -> Optional[int]:
    """Auto-detect the best WASAPI loopback device.

    Priority:
    1. Virtual audio devices (SteelSeries Sonar, Voicemeeter, etc.)
    2. Default WASAPI loopback device
    3. Any available WASAPI loopback device

    Returns:
        Device index, or None if nothing suitable found.
    """
    devices = list_loopback_devices()
    if not devices:
        logger.error("No WASAPI loopback devices found!")
        return None

    # Log all available devices
    logger.info("Available WASAPI loopback devices:")
    for dev in devices:
        logger.info(f"  [{dev['index']}] {dev['name']}")

    # Priority 1: virtual audio devices (SteelSeries, Voicemeeter etc.)
    name_lower = ""
    for dev in devices:
        name_lower = dev["name"].lower()
        for kw in _VIRTUAL_KEYWORDS:
            if kw in name_lower:
                logger.info(
                    f"Auto-selected virtual audio device: [{dev['index']}] {dev['name']}"
                )
                return dev["index"]

    # Priority 2: default device or first available
    selected = devices[0]
    logger.info(
        f"Auto-selected default loopback device: [{selected['index']}] {selected['name']}"
    )
    return selected["index"]


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
            logger.info(f"Found device by name: [{dev['index']}] {dev['name']}")
            return dev["index"]

    logger.warning(f"No loopback device matching '{name_substring}' found")
    return None


class AudioCapture:
    """WASAPI Loopback audio capture for Windows system audio.

    Auto-detects the best loopback device (virtual audio preferred).
    Falls back gracefully if no suitable device is found.
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
        self._active_device_name = "unknown"

    @property
    def active_device_name(self) -> str:
        """Human-readable name of the currently active capture device."""
        return self._active_device_name

    def set_callback(self, callback):
        """Set the audio data callback."""
        self._callback = callback

    def start(self):
        """Start audio capture using WASAPI loopback.

        Auto-detects the best device if none specified.
        Logs the selected device name for debugging.
        """
        if self.is_running:
            return

        # Resolve device index
        device_index = None
        if self.device_name and self.device_name.lower() != "auto":
            device_index = find_device_by_name(self.device_name)
            if device_index is None:
                logger.warning(
                    f"Device '{self.device_name}' not found, auto-detecting..."
                )

        if device_index is None:
            device_index = find_best_device()

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

            if device_index is not None:
                dev_info = sd.query_devices(device_index)
                self._active_device_name = dev_info["name"]
                logger.info(
                    f"Audio capture started: [{device_index}] {self._active_device_name}"
                )
            else:
                self._active_device_name = "unknown (no loopback device)"
                logger.warning("Audio capture started with no loopback device")

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
