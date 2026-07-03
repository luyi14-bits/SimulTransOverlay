# Software Bill of Materials (SBOM) — SimulTransOverlay

> 生成日期：2026-07-04 | 许可证：AGPL v3

## 运行时依赖

| 包名 | 版本 | 许可证 | 兼容 AGPL |
|------|------|--------|-----------|
| PyQt6 | 6.11.0 | GPL v3 | ✅ GPL v3 兼容 AGPL v3 |
| PyQt6-Qt6 | 6.11.1 | GPL v3 / LGPL | ✅ |
| torch | 2.12.1 | BSD | ✅ |
| torchaudio | 2.11.0 | BSD | ✅ |
| faster-whisper | 1.2.1 | MIT | ✅ |
| ctranslate2 | 4.8.1 | MIT | ✅ |
| sentencepiece | 0.2.1 | Apache 2.0 | ✅ |
| numpy | 2.5.0 | BSD | ✅ |
| sounddevice | — | MIT | ✅ |
| soundfile | — | BSD | ✅ |
| httpx | 0.28.1 | BSD | ✅ |
| PyYAML | — | MIT | ✅ |
| psutil | — | BSD | ✅ |
| transformers | 5.13.0 | Apache 2.0 | ✅ |

## 模型资产（首次运行时自动下载）

| 模型 | 来源 | 许可证 | 用途 |
|------|------|--------|------|
| faster-whisper base | HuggingFace | MIT (OpenAI Whisper) | ASR 语音识别 |
| opus-mt-ja-zh | Helsinki-NLP | CC-BY-4.0 | 日→中翻译 |
| opus-mt-ja-en | Helsinki-NLP | CC-BY-4.0 | 日→英翻译 |
| opus-mt-en-zh | Helsinki-NLP | CC-BY-4.0 | 英→中翻译 |
| opus-mt-zh-en | Helsinki-NLP | CC-BY-4.0 | 中→英翻译 |

## 许可证声明

SimulTransOverlay 使用 AGPL v3 协议发布。所有第三方依赖的许可证均兼容 AGPL v3 分发。
PyQt6 使用 GPL v3 协议，与 AGPL v3 兼容。模型资产使用 CC-BY-4.0 协议。
