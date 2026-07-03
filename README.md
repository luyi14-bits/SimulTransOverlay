<div align="center">

# SimulTransOverlay

**Real-time screen subtitle translation overlay for Windows**

[![license](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue.svg)]()
[![python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)]()
[![status](https://img.shields.io/badge/status-beta-orange.svg)]()

[中文文档](#功能特性) | [English](#quick-start)

Real-time system audio capture, local ASR, embedded offline translation, and semi-transparent overlay subtitles -- zero external dependencies, double-click to run.

</div>

---

## Features

- **System Audio Capture** -- WASAPI Loopback captures audio from any application (video/live/meeting)
- **Real-time ASR** -- faster-whisper engine with GPU acceleration or CPU fallback
- **Embedded Offline Translation** -- ctranslate2 + OPUS-MT, no network or Ollama required
- **Semi-transparent Overlay** -- always-on-top, mouse pass-through, draggable, 12 themes
- **Zero-dependency EXE** -- single-file packaging, auto-downloads ASR models on first run

## Quick Start

### EXE Users (Recommended)

1. Download SimulTransOverlay-v1.0.zip from Releases
2. Extract to any directory
3. Double-click SimulTransOverlay.exe
4. First run auto-downloads ASR model (~1GB, one-time only)
5. Play a foreign-language video -- the overlay shows real-time translated subtitles

> Translation models (OPUS-MT) auto-download on first translation.

### From Source (Developers)

`ash
# 1. Clone the repository
git clone https://github.com/luyi14-bits/SimulTransOverlay.git
cd SimulTransOverlay

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
`

## Screenshots

> Screenshots will be added after the project exits beta.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 21H2+ | Windows 11 |
| **GPU** | -- | NVIDIA (CUDA) |
| **CPU** | Intel/AMD x86_64 | Intel i5+ / AMD Ryzen 5+ |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 5 GB (model files) | SSD recommended |

## Tech Stack

| Category | Technology |
|----------|------------|
| Audio Capture | WASAPI Loopback (pycaw + sounddevice) |
| Voice Activity Detection | Silero VAD |
| ASR Engine | faster-whisper / SenseVoice |
| Translation | ctranslate2 + OPUS-MT (offline) |
| UI Framework | PyQt6 |
| Overlay | Always-on-top, frameless, transparent |

## Architecture

`
System Audio (WASAPI 32ms)
    |  Audio Capture
    v
Audio Resampling (48kHz -> 16kHz mono)
    v
Silero VAD (Voice Activity Detection + Segmentation)
    v
faster-whisper / SenseVoice (ASR Transcription)
    v
ctranslate2 + OPUS-MT (Offline Translation)
    v
PyQt6 Semi-transparent Overlay (Display Subtitles)
`

## Project Structure

`
simultrans-overlay/
  src/                       # Core source code
    audio_capture.py         # WASAPI audio loopback capture
    resample.py              # Audio resampling (48kHz -> 16kHz)
    vad_processor.py          # Silero VAD voice activity detection
    asr_engine.py             # ASR engine abstract base class
    asr_whisper.py            # faster-whisper backend
    asr_sensevoice.py         # SenseVoice backend
    translator.py             # Offline translation (ctranslate2 + OPUS-MT)
    translator_legacy.py     # Ollama/DeepSeek fallback (optional)
    subtitle_overlay.py      # PyQt6 semi-transparent overlay
    control_panel.py         # Settings control panel
    model_manager.py         # Model download manager
  config/
    config.yaml              # Default configuration
  tests/
    test_audio_capture.py
    test_resample.py
    test_vad.py
  models/                    # Runtime-downloaded model files
  docs/                      # Documentation
  main.py                    # Application entry point
  requirements.txt           # Python dependencies
`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'feat: add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.