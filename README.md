# SimulTransOverlay — 屏幕同传翻译（暂时还有bug，勿用）

> 实时捕获系统音频 → 本地 ASR 语音识别 → 内嵌离线翻译 → 半透明叠加层显示译文
> **零外部依赖**：无需安装 Python/Ollama/CUDA，双击即用

## 功能特性

- **系统音频捕获** — WASAPI Loopback 捕获任意应用音频输出（视频/直播/会议）
- **实时语音识别** — faster-whisper 引擎，GPU 加速 / CPU 均可
- **内嵌离线翻译** — 基于 ctranslate2 + OPUS-MT，无需网络、无需 Ollama
- **半透明叠加层** — 始终置顶、鼠标穿透、可拖拽、12 种主题
- **即开即用** — 单文件 exe 打包，双击启动，自动下载语音模型

## 快速开始（exe 用户）

```bash
# 1. 下载 SimulTransOverlay-v1.0.zip
# 2. 解压到任意目录
# 3. 双击 SimulTransOverlay.exe
# 4. 首次运行会自动下载 ASR 模型（~1GB，仅一次）
# 5. 播放外语视频/直播，半透明框显示实时翻译字幕
```

> 翻译模型（OPUS-MT）在首次翻译时自动下载缓存。

## 系统要求

- **OS**: Windows 10 21H2+ / Windows 11
- **GPU** (推荐): NVIDIA（加速语音识别）
- **CPU** (可用): Intel/AMD x86_64
- **RAM**: ≥8GB
- **存储**: ≥5GB（模型文件）

## 项目结构

```
simultrans-overlay/
├── src/                    # 核心源码
│   ├── audio_capture.py    # WASAPI 音频环回捕获
│   ├── resample.py         # 音频重采样（48kHz→16kHz）
│   ├── vad_processor.py    # Silero VAD 语音活动检测
│   ├── asr_engine.py       # ASR 引擎抽象基类
│   ├── asr_whisper.py      # faster-whisper 后端
│   ├── asr_sensevoice.py   # SenseVoice 后端
│   ├── translator.py       # 内嵌离线翻译（ctranslate2+OPUS-MT）
│   ├── translator_legacy.py# Ollama/DeepSeek 回退（可选）
│   ├── subtitle_overlay.py # PyQt6 半透明叠加层
│   ├── control_panel.py    # 设置控制面板
│   └── model_manager.py    # 模型下载管理
├── config/
│   └── config.yaml         # 默认配置
├── tests/
│   ├── test_audio_capture.py
│   ├── test_resample.py
│   └── test_vad.py
├── models/                 # 运行时下载的模型文件
├── docs/                   # 文档
├── main.py                 # 应用入口
└── requirements.txt        # Python 依赖
```

## 技术架构

```
系统音频 (WASAPI 32ms)
    ↓
音频重采样 (48kHz→16kHz mono)
    ↓
Silero VAD (语音活动检测 + 断句)
    ↓
faster-whisper / SenseVoice (ASR 转写)
    ↓
faster-whisper (ASR 转写)
    ↓
内嵌 OPUS-MT / ctranslate2 (离线翻译)
    ↓
PyQt6 半透明叠加层 (显示译文)
```

## 许可证

MIT License
