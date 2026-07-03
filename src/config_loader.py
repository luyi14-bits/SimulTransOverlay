"""Configuration loader for SimulTransOverlay.

Loads and validates settings from config.yaml with sensible defaults.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _get_default_config_path() -> Path:
    """Get the default config path, compatible with PyInstaller.

    When packaged as a frozen exe (PyInstaller), config is extracted
    alongside the executable. When running from source, config is
    relative to the project root.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller temp extraction directory
        return Path(sys._MEIPASS) / "config" / "config.yaml"
    else:
        # Development: src/config_loader.py -> project root / config/config.yaml
        return Path(__file__).resolve().parent.parent / "config" / "config.yaml"


# Default config path
DEFAULT_CONFIG_PATH = _get_default_config_path()


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml.

    Returns:
        Configuration dictionary with all settings.

    Raises:
        FileNotFoundError: If config file doesn't exist at the given path.
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Validate required sections
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """Validate that required config sections exist.

    Args:
        config: Parsed configuration dictionary.

    Raises:
        ValueError: If required sections are missing.
    """
    required_sections = ["audio", "vad", "asr", "translation", "overlay"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")


def get_audio_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get audio capture settings with defaults."""
    return config.get("audio", {
        "sample_rate": 48000,
        "channels": 2,
        "blocksize": 1536,
        "mic_enabled": False,
        "mic_ratio": 0.3,
    })


def get_vad_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get VAD settings with defaults."""
    return config.get("vad", {
        "sample_rate": 16000,
        "silence_threshold": 0.5,
        "chunk_size": 512,
    })


def get_asr_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get ASR engine settings with defaults."""
    return config.get("asr", {
        "engine": "faster-whisper",
        "model": "base",
        "language": "ja",
        "device": "auto",
        "compute_type": "auto",
    })


def get_translation_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get translation settings with defaults."""
    return config.get("translation", {
        "engine": "ollama",
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:3b",
            "context_window": 5,
        },
        "deepseek": {
            "api_base": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
            "stream": True,
        },
        "target_language": "zh-CN",
    })


def get_overlay_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get overlay window settings with defaults."""
    return config.get("overlay", {
        "theme": "dark",
        "font_size": 24,
        "font_color": "#FFFFFF",
        "background_color": "#000000",
        "background_opacity": 0.5,
        "history_lines": 2,
        "window_width": 600,
        "window_height": 100,
    })
