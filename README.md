<div align="center">

# SimulTransOverlay

**Real-time screen subtitle translation overlay for Windows**

[![license](https://img.shields.io/badge/license-AGPL%20v3-blue.svg)](LICENSE)
[![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue.svg)]()
[![python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)]()
[![version](https://img.shields.io/badge/version-v1.0.0-green.svg)](CHANGELOG.md)
[![tests](https://img.shields.io/badge/tests-80%20passed%20(99%25)-brightgreen.svg)]()
[![security](https://img.shields.io/badge/security-SBOM%20audited-success.svg)](docs/SBOM.md)

</div>

Real-time system audio capture, local ASR, embedded offline translation, and semi-transparent overlay subtitles -- zero external dependencies, double-click to run.

---

## Features

- **System Audio Capture** -- WASAPI Loopback captures audio from any application (video / live / meeting)
- **Real-time ASR** -- faster-whisper / SenseVoice engines with GPU acceleration or CPU fallback
- **Embedded Offline Translation** -- ctranslate2 + OPUS-MT, no network or Ollama required
- **Semi-transparent Overlay** -- always-on-top, mouse pass-through, draggable, 12 themes
- **Async Pipeline** -- 4-stage thread isolation (audio -> VAD -> ASR -> UI), no UI freezes
- **Memory Safety** -- watermark monitoring + auto GC + hot unload/load models (5 min idle release)
- **Structured Logging** -- crash diagnostics export for troubleshooting
- **Zero-dependency EXE** -- single-directory packaging, auto-downloads models on first run

## Quick Start

### EXE Users (Recommended)

1. Download `SimulTransOverlay-v1.0.zip` from [Releases](https://github.com/luyi14-bits/SimulTransOverlay/releases)
2. Extract to any directory
3. Double-click `SimulTransOverlay.exe`
4. First run auto-downloads ASR model (~1GB, one-time only)
5. Play a foreign-language video -- the overlay shows real-time translated subtitles

> Translation models (OPUS-MT) auto-download on first translation.

### From Source (Developers)

```bash
# 1. Clone the repository
git clone https://github.com/luyi14-bits/SimulTransOverlay.git
cd SimulTransOverlay

# 2. Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell
pip install -r requirements.txt

# 3. Run
python main.py
```

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
| Translation | ctranslate2 + OPUS-MT (offline, embedded) |
| UI Framework | PyQt6 |
| Overlay | Always-on-top, frameless, transparent |

## Architecture

```
System Audio (WASAPI 32ms)
    │  Audio Capture
    ▼
Audio Resampling (48kHz -> 16kHz mono)
    ▼
Silero VAD (Voice Activity Detection + Segmentation)
    ▼
faster-whisper / SenseVoice (ASR Transcription)
    ▼
ctranslate2 + OPUS-MT (Offline Translation)
    ▼
PyQt6 Semi-transparent Overlay (Display Subtitles)
```

## Project Structure

```
SimulTransOverlay/
├── main.py                      # Application entry point
├── src/                         # Core source code
│   ├── __init__.py
│   ├── audio_capture.py         # WASAPI audio loopback capture
│   ├── resample.py              # Audio resampling (48kHz -> 16kHz)
│   ├── vad_processor.py         # Silero VAD voice activity detection
│   ├── asr_engine.py            # ASR engine abstract base class
│   ├── asr_whisper.py           # faster-whisper backend
│   ├── asr_sensevoice.py        # SenseVoice backend
│   ├── translator.py            # Offline translation (ctranslate2 + OPUS-MT)
│   ├── translator_legacy.py    # Ollama/DeepSeek fallback (optional)
│   ├── subtitle_overlay.py      # PyQt6 semi-transparent overlay
│   ├── config_loader.py        # Configuration loading & management
│   ├── model_manager.py        # Model download manager
│   └── pipeline.py             # Async pipeline orchestrator
├── config/
│   └── config.yaml             # Default configuration
├── tests/                       # Automated tests (80 tests, 99% pass)
│   ├── conftest.py
│   ├── test_audio_capture.py
│   ├── test_resample.py
│   ├── test_vad.py
│   ├── test_asr_engine.py
│   ├── test_translator.py
│   ├── test_overlay.py
│   └── test_pipeline.py
├── docs/                        # Documentation
│   └── SBOM.md                 # Software Bill of Materials
├── requirements.txt            # Python dependencies
├── .github/                     # GitHub community templates
├── CHANGELOG.md                 # Release history
├── PIPELINE_KANBAN.md           # Product pipeline kanban
└── LICENSE                      # AGPL v3
```

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| v1.0.0 | Async pipeline + embedded translation + offline observability | Done |
| Future | TTS voice read-aloud | Planned |
| Future | Control panel UI (5 tabs) | Planned |
| Future | Global hotkey (Ctrl+Shift+T) | Planned |
| Future | macOS / Linux port | Planned |

See [PIPELINE_KANBAN.md](PIPELINE_KANBAN.md) for full status.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the [GNU AGPL v3 License](LICENSE) -- see the LICENSE file for details.
