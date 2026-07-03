# Changelog

## [v1.0.0] — 2026-07-04
### Added
- 零外部依赖发行版：双击即用，无需 Python/Ollama/CUDA
- 异步管线架构：4 级线程隔离（音频→VAD→ASR→UI），杜绝界面假死
- 内存水位线监控 + 自动 GC 触发（`MemoryMonitor`）
- 模型热卸载/热加载（`ModelLifecycleManager`，空闲 5 分钟自动释放显存）
- 内嵌离线翻译引擎（`BuiltinTranslator`，基于 ctranslate2 + OPUS-MT）
- 结构化日志系统 + 崩溃诊断导出
- SBOM 合规审查（`docs/SBOM.md`）

### Changed
- 许可证从 MIT 切换为 AGPL v3
- 翻译引擎从 Ollama（外部服务）替换为内嵌 ctranslate2（零外部依赖）
- 打包策略从 `--onefile`（3GB 失败）改为 `--onedir`（52MB 核心包 + 模型按需下载）
- config.yaml 默认引擎改为 `builtin`

### Fixed
- 音频回调被 ASR 推理阻塞导致丢帧（队列解耦）
- PyInstaller `sys._MEIPASS` 路径兼容性
- 翻译引擎语言代码大小写解析

## [Unreleased]
### Added
- Initial MVP: system audio capture → VAD → ASR → translation → overlay
- WASAPI loopback audio capture (Windows 10/11)
- Silero VAD real-time speech segmentation
- faster-whisper ASR engine (GPU/CPU, INT8 quantization)
- PyQt6 transparent overlay window (12 themes, click-through, always-on-top)
- System tray icon with show/hide/quit menu
- 79 automated tests
