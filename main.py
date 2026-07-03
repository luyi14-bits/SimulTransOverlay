"""SimulTransOverlay — 屏幕同传翻译半透明框

Main entry point. Queue-based async pipeline:
Audio Capture Thread → VAD Worker Thread → ASR Worker Thread → UI Main Thread
"""

import logging
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

# Ensure src is on path (only needed when running from source)
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.audio_capture import AudioCapture
from src.resample import resample_to_16khz
from src.vad_processor import SileroVADProcessor
from src.asr_engine import create_asr_engine, TranscriptionBuffer
from src.translator import create_translator, TranslationContext
from src.subtitle_overlay import SubtitleOverlay, OverlayApp
from src.config_loader import load_config, get_audio_config, get_vad_config, get_asr_config, get_translation_config
from src.pipeline import PipelineWorker, MemoryMonitor, ModelLifecycleManager, PipelineMetrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("simultrans")

CHUNK_SIZE_16KHZ = 512  # 32ms @ 16kHz


class SimulTransPipeline:
    """Queue-based async pipeline with thread isolation.

    4-stage pipeline:
    [Audio Capture Thread] → audio_queue → [VAD Worker] → segment_queue
      → [ASR Worker] → text_queue → [Translation Worker] → translate_queue
      → [UI main thread updates overlay]
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.running = False
        self.metrics = PipelineMetrics()
        self.memory_monitor = MemoryMonitor(threshold_percent=80.0)
        self._memory_check_timer: Optional[threading.Thread] = None

        # Queue-based pipeline stages (bounded to prevent OOM)
        self.audio_queue: queue.Queue = queue.Queue(maxsize=60)   # ~2 seconds of audio
        self.segment_queue: queue.Queue = queue.Queue(maxsize=20)  # speech segments
        self.text_queue: queue.Queue = queue.Queue(maxsize=10)     # transcribed text
        self.translate_queue: queue.Queue = queue.Queue(maxsize=10) # translations

        self._setup_components()

    def _setup_components(self):
        """Initialize all pipeline components from config."""
        audio_cfg = get_audio_config(self.config)
        vad_cfg = get_vad_config(self.config)
        asr_cfg = get_asr_config(self.config)
        trans_cfg = get_translation_config(self.config)

        # Audio capture (runs in WASAPI callback thread)
        self.capture = AudioCapture(
            mic_enabled=audio_cfg.get("mic_enabled", False),
            mic_ratio=audio_cfg.get("mic_ratio", 0.3),
        )

        # VAD processor (runs in dedicated worker thread)
        self.vad = SileroVADProcessor(
            silence_threshold=vad_cfg.get("silence_threshold", 0.5),
        )

        # ASR engine (lazy-loaded, managed by lifecycle manager)
        self.asr_config = asr_cfg
        self.asr_engine = None
        self.transcription_buffer = TranscriptionBuffer(max_segments=5)
        self.asr_lifecycle = ModelLifecycleManager(
            idle_timeout=300,
            load_func=self._load_asr_model,
            unload_func=self._unload_asr_model,
        )

        # Translation engine
        source_lang = asr_cfg.get("language", "ja")
        target_lang = trans_cfg.get("target_language", "zh")
        self.translator = create_translator(
            engine="builtin",
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self.translation_context = TranslationContext()

        # Overlay (MUST be on main thread)
        self.overlay_app = OverlayApp()
        self.overlay = self.overlay_app.overlay

    def _load_asr_model(self):
        """Load ASR model (called by lifecycle manager)."""
        logger.info("Loading ASR model...")
        self.asr_engine = create_asr_engine(
            engine_name=self.asr_config.get("engine", "faster-whisper"),
            model_size=self.asr_config.get("model", "small"),
            language=self.asr_config.get("language", "ja"),
            device=self.asr_config.get("device", "auto"),
            compute_type=self.asr_config.get("compute_type", "int8"),
        )
        self.asr_engine.load_model()
        logger.info("ASR model loaded")

    def _unload_asr_model(self):
        """Unload ASR model to free memory."""
        if self.asr_engine is not None:
            logger.info("Unloading ASR model...")
            self.asr_engine.unload()
            self.asr_engine = None
            logger.info("ASR model unloaded")

    # --- Stage 0: Audio Capture (runs in WASAPI callback thread) ---

    def _on_audio(self, audio_data: np.ndarray):
        """WASAPI callback: resample audio and push to queue.

        MUST be fast — no blocking operations. Runs in audio thread.
        """
        try:
            mono = resample_to_16khz(audio_data)
            if len(mono) == 0:
                return

            # Push to audio queue, drop oldest if full (backpressure)
            try:
                self.audio_queue.put(mono, timeout=0.01)
                self.metrics.processed_chunks += 1
            except queue.Full:
                # Backpressure: drop oldest chunk
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put(mono, timeout=0.01)
                    self.metrics.dropped_frames += 1
                except (queue.Empty, queue.Full):
                    pass
        except Exception as e:
            logger.error(f"Audio capture callback error: {e}")

    # --- Stage 1: VAD Worker ---

    class VADWorker(PipelineWorker):
        """Processes audio chunks through VAD and emits speech segments."""

        def __init__(self, pipeline: 'SimulTransPipeline'):
            super().__init__(
                "vad-worker",
                input_queue=pipeline.audio_queue,
                output_queue=pipeline.segment_queue,
            )
            self.pipeline = pipeline
            self.vad = pipeline.vad
            self.chunk_size = CHUNK_SIZE_16KHZ

        def process_item(self, audio_mono: np.ndarray):
            """Process audio through VAD, return segments or None."""
            for start in range(0, len(audio_mono), self.chunk_size):
                chunk = audio_mono[start:start + self.chunk_size]
                if len(chunk) < self.chunk_size // 2:
                    continue
                if len(chunk) != self.chunk_size:
                    padded = np.zeros(self.chunk_size, dtype=np.float32)
                    padded[:len(chunk)] = chunk
                    chunk = padded

                self.vad.process_chunk(chunk)

                if self.vad.should_segment():
                    segment = self.vad.pop_segment()
                    if len(segment) >= 1600:  # >=100ms, skip noise
                        self.pipeline.asr_lifecycle.mark_activity()
                        return segment
            return None

    # --- Stage 2: ASR Worker ---

    class ASRWorker(PipelineWorker):
        """Transcribes speech segments to text."""

        def __init__(self, pipeline: 'SimulTransPipeline'):
            super().__init__(
                "asr-worker",
                input_queue=pipeline.segment_queue,
                output_queue=pipeline.text_queue,
            )
            self.pipeline = pipeline

        def process_item(self, audio_segment: np.ndarray):
            """Transcribe audio to text."""
            pipeline = self.pipeline

            # Ensure ASR model is loaded (hot-reload if unloaded)
            pipeline.asr_lifecycle.load_model()

            if pipeline.asr_engine is None:
                return None

            t0 = time.perf_counter()
            text = pipeline.asr_engine.transcribe(audio_segment)
            elapsed = (time.perf_counter() - t0) * 1000
            pipeline.metrics.record_asr_latency(elapsed)

            if not text.strip():
                return None

            logger.info(f"ASR ({elapsed:.0f}ms): {text}")

            # Buffer to sentence
            sentence = pipeline.transcription_buffer.add_segment(text)
            return sentence

    # --- Stage 3: Translation Worker ---

    class TranslationWorker(PipelineWorker):
        """Translates text and updates overlay on main thread."""

        def __init__(self, pipeline: 'SimulTransPipeline'):
            super().__init__(
                "translation-worker",
                input_queue=pipeline.text_queue,
                output_queue=None,  # No output queue — updates overlay directly via signal
            )
            self.pipeline = pipeline

        def process_item(self, sentence: str):
            """Translate and show on overlay."""
            if not sentence:
                return None

            pipeline = self.pipeline
            t0 = time.perf_counter()
            translation = pipeline.translator.translate(sentence)
            elapsed = (time.perf_counter() - t0) * 1000
            pipeline.metrics.record_translation_latency(elapsed)

            if translation:
                logger.info(f"Translation ({elapsed:.0f}ms): {translation}")
                # Use QTimer to safely update overlay from main thread
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: pipeline.overlay.show_text(translation))

            return None

    # --- Lifecycle ---

    def _start_workers(self):
        """Start all pipeline worker threads."""
        self.vad_worker = self.VADWorker(self)
        self.asr_worker = self.ASRWorker(self)
        self.translation_worker = self.TranslationWorker(self)

        self.vad_worker.start()
        self.asr_worker.start()
        self.translation_worker.start()

        # Start model lifecycle background monitor
        self.asr_lifecycle.start_background_monitor(interval=30.0)

        # Start memory monitor (every 5 minutes)
        def _memory_check_loop():
            while self.running:
                time.sleep(300)  # 5 minutes
                self.memory_monitor.check()
                self.metrics.memory_usage_mb.append(self.memory_monitor.memory_percent)

        self._memory_check_timer = threading.Thread(
            target=_memory_check_loop,
            name="memory-monitor",
            daemon=True,
        )
        self._memory_check_timer.start()

        logger.info("All pipeline workers started")

    def _stop_workers(self):
        """Stop all pipeline worker threads."""
        logger.info("Stopping pipeline workers...")
        self.vad_worker.stop(drain=True)
        self.asr_worker.stop(drain=False)
        self.translation_worker.stop(drain=False)
        self.running = False
        logger.info("Pipeline workers stopped")

    # --- Public API ---

    def run(self):
        """Start the full async pipeline."""
        logger.info("=" * 50)
        logger.info("SimulTransOverlay Starting")
        logger.info("=" * 50)
        self.running = True

        # Start pipeline workers
        self._start_workers()

        # Start audio capture (calls _on_audio from WASAPI callback thread)
        self.capture.set_callback(self._on_audio)
        self.capture.start()
        logger.info("Audio capture started")

        # Show overlay (blocks on Qt event loop)
        logger.info("Showing overlay window")
        self.overlay_app.show()

    def stop(self):
        """Stop the pipeline gracefully."""
        logger.info("Shutting down...")
        self._stop_workers()
        self.capture.stop()
        self._unload_asr_model()
        self._log_final_metrics()

    def _log_final_metrics(self):
        """Log pipeline performance metrics."""
        if self.metrics.asr_latency_ms:
            logger.info(
                f"ASR latency: P50={sorted(self.metrics.asr_latency_ms)[len(self.metrics.asr_latency_ms)//2]:.0f}ms "
                f"P95={sorted(self.metrics.asr_latency_ms)[int(len(self.metrics.asr_latency_ms)*0.95)]:.0f}ms"
            )
        if self.metrics.translation_latency_ms:
            logger.info(
                f"Translation latency: "
                f"P50={sorted(self.metrics.translation_latency_ms)[len(self.metrics.translation_latency_ms)//2]:.0f}ms"
            )
        logger.info(
            f"Processed chunks: {self.metrics.processed_chunks}, "
            f"Dropped frames: {self.metrics.dropped_frames}"
        )
        logger.info("=" * 50)


def main():
    """Application entry point."""
    pipeline = SimulTransPipeline()
    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
