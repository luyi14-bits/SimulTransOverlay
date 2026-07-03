"""Async pipeline module for SimulTransOverlay.

Provides thread-safe, queue-based 4-stage pipeline:
Audio Capture → VAD Processing → ASR Inference → UI Update

Features:
- Thread isolation with queue.Queue per stage
- Backpressure handling (discard oldest when overloaded)
- Memory water level monitoring + GC trigger
- Model hot-unload on idle, hot-reload on activity
"""

import gc
import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np
import psutil

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics."""
    dropped_frames: int = 0
    processed_chunks: int = 0
    asr_inference_count: int = 0
    translation_count: int = 0
    asr_latency_ms: list = field(default_factory=list)
    translation_latency_ms: list = field(default_factory=list)
    memory_usage_mb: list = field(default_factory=list)
    queue_depth: dict = field(default_factory=dict)

    def record_asr_latency(self, ms: float):
        self.asr_latency_ms.append(ms)
        if len(self.asr_latency_ms) > 1000:
            self.asr_latency_ms.pop(0)

    def record_translation_latency(self, ms: float):
        self.translation_latency_ms.append(ms)
        if len(self.translation_latency_ms) > 1000:
            self.translation_latency_ms.pop(0)


class PipelineWorker(ABC):
    """Base class for pipeline stage workers with queue-based isolation."""

    def __init__(
        self,
        name: str,
        input_queue: queue.Queue,
        output_queue: Optional[queue.Queue] = None,
        max_queue_size: int = 10,
    ):
        self.name = name
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.max_queue_size = max_queue_size
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False
        self.exception: Optional[Exception] = None

    @abstractmethod
    def process_item(self, item: Any) -> Any:
        """Process a single item from the input queue."""
        ...

    def start(self):
        """Start the worker thread."""
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=self.name,
            daemon=True,
        )
        self._thread.start()
        self.is_running = True
        logger.info(f"Worker '{self.name}' started")

    def stop(self, drain: bool = True):
        """Stop the worker, optionally draining remaining items."""
        self._stop_event.set()
        if drain and self._thread and self._thread.is_alive():
            # Process remaining items
            while not self.input_queue.empty():
                try:
                    item = self.input_queue.get_nowait()
                    result = self.process_item(item)
                    if self.output_queue is not None and result is not None:
                        self.output_queue.put(result)
                except queue.Empty:
                    break
        self.is_running = False
        logger.info(f"Worker '{self.name}' stopped")

    def _run_loop(self):
        """Main loop: read from input queue, process, write to output queue."""
        while not self._stop_event.is_set():
            try:
                item = self.input_queue.get(timeout=0.5)
                try:
                    result = self.process_item(item)
                    if self.output_queue is not None and result is not None:
                        # Handle backpressure: try to put, discard oldest if full
                        try:
                            self.output_queue.put(result, timeout=1.0)
                        except queue.Full:
                            # Backpressure: drain oldest item then retry
                            try:
                                self.output_queue.get_nowait()
                                self.output_queue.put(result, timeout=0.5)
                            except (queue.Empty, queue.Full):
                                logger.warning(
                                    f"Worker '{self.name}': dropped output"
                                )
                except Exception as e:
                    logger.error(
                        f"Worker '{self.name}' processing error: {e}"
                    )
                    self.exception = e
            except queue.Empty:
                continue


class BackpressureStrategy:
    """Backpressure handling strategies."""

    @staticmethod
    def on_backpressure(output_queue: queue.Queue) -> str:
        """Handle backpressure: try to drain oldest and return action."""
        try:
            output_queue.get_nowait()
            return "drain_oldest"
        except queue.Empty:
            return "no_action"

    @staticmethod
    def drop_oldest(q: queue.Queue) -> Any:
        """Drop the oldest item from queue and return it (for logging)."""
        try:
            item = q.get_nowait()
            return item
        except queue.Empty:
            return None


class MemoryMonitor:
    """Memory water level monitor with periodic GC trigger."""

    def __init__(
        self,
        threshold_percent: float = 80.0,
        collection_interval: float = 60.0,
    ):
        self.threshold = threshold_percent
        self.collection_interval = collection_interval
        self.last_collection_time: float = 0.0
        self.memory_percent: float = 0.0

    def check(self) -> bool:
        """Check memory usage and trigger GC if needed.

        Returns:
            True if collection was triggered
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        total = process.memory_percent()
        self.memory_percent = total

        if self.should_collect():
            return self._collect()

        return False

    def should_collect(self) -> bool:
        """Check if memory threshold is exceeded and not in cooldown."""
        return (
            self.memory_percent >= self.threshold
            and not self.is_in_cooldown()
        )

    def is_in_cooldown(self) -> bool:
        """Check if within cooldown period after last collection."""
        return (time.time() - self.last_collection_time) < self.collection_interval

    def _collect(self) -> bool:
        """Trigger garbage collection and cache clearing."""
        logger.info(
            f"Memory at {self.memory_percent:.1f}% (threshold: {self.threshold}%), "
            f"triggering GC..."
        )
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
        except ImportError:
            pass

        self.last_collection_time = time.time()
        logger.info("GC collection completed")
        return True


class ModelLifecycleManager:
    """Manages model hot-unload on idle and hot-reload on activity."""

    def __init__(
        self,
        idle_timeout: float = 300.0,  # 5 minutes
        load_func: Optional[Callable] = None,
        unload_func: Optional[Callable] = None,
    ):
        self.idle_timeout = idle_timeout
        self._load_func = load_func
        self._unload_func = unload_func
        self.model_loaded = False
        self.last_activity_time: float = time.time()
        self._lock = threading.Lock()

    def mark_activity(self):
        """Mark that there was recent activity (speech detected)."""
        self.last_activity_time = time.time()

    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.time() - self.last_activity_time

    def is_idle_timeout(self) -> bool:
        """Check if idle timeout has been exceeded."""
        return self.idle_seconds() > self.idle_timeout and self.model_loaded

    def load_model(self):
        """Load the model (hot-reload)."""
        with self._lock:
            if self.model_loaded:
                return
            if self._load_func:
                self._load_func()
            self.model_loaded = True
            self.last_activity_time = time.time()
            logger.info("Model loaded")

    def unload_model(self):
        """Unload the model to free memory (hot-unload)."""
        with self._lock:
            if not self.model_loaded:
                return
            if self._unload_func:
                self._unload_func()
            self.model_loaded = False
            logger.info("Model unloaded")

    def auto_manage(self):
        """Run in background: unload if idle, load if needed."""
        if self.is_idle_timeout():
            self.unload_model()

    def start_background_monitor(self, interval: float = 30.0):
        """Start a background thread to auto-manage model lifecycle."""
        def _monitor():
            while True:
                time.sleep(interval)
                self.auto_manage()

        thread = threading.Thread(
            target=_monitor,
            name="model-lifecycle",
            daemon=True,
        )
        thread.start()
