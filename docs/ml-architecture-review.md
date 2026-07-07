# ML 架构评审 — v1.0.0

> 评审日期：2026-07-04

## Sebastian Raschka — ASR 引擎架构
- **faster-whisper** (CTranslate2)：推荐为主引擎。int8 量化 + GPU 加速适合实时场景
- **SenseVoice**：中文场景备选。需要下载 FunASR 框架，目前测试覆盖率 26%
- **模型建议**：默认 `base` 模型（~300MB），允许用户切 `tiny`（~150MB 快速）或 `small`（~500MB 精度）

## Andrej Karpathy — 模型管理 + VAD
- **model_manager.py**: 缓存策略合理，但 ModelScope/HuggingFace 双源可简化优先 HuggingFace
- **VAD 参数**: `silence_threshold=0.5s` 合理。建议增加自适应模式：背景噪音 > -30dB 时自动调整为 0.8s

## Dmitry Lyalin — 产品化评估
- **ctranslate2 + OPUS-MT**：产品化可行。模型首次下载 ~50MB，后续完全离线
- **优化方向**：(1) 缓存预下载 (2) 多语言对扩展
