"""Tests for async pipeline engine."""

import time
import threading
from queue import Queue, Full, Empty
from unittest.mock import patch, MagicMock

import numpy as np
import pytest


class TestPipelineWorker:
    """管线工作单元测试"""

    def test_worker_create(self):
        """创建 Worker"""
        from src.pipeline import PipelineWorker
        q = Queue()
        # 使用一个简单 worker
        class SimpleWorker(PipelineWorker):
            def process_item(self, item):
                return item
        w = SimpleWorker("test", q)
        assert w.name == "test"
        assert w.is_running is False

    def test_worker_start_stop(self):
        """启动和停止"""
        from src.pipeline import PipelineWorker
        q = Queue()
        class SimpleWorker(PipelineWorker):
            def process_item(self, item):
                return item
        w = SimpleWorker("test", q)
        w.start()
        assert w.is_running
        w.stop()
        assert w.is_running is False

    def test_worker_process(self):
        """处理队列中的项目"""
        from src.pipeline import PipelineWorker
        in_q = Queue()
        out_q = Queue()
        class DoubleWorker(PipelineWorker):
            def process_item(self, item):
                return item * 2
        w = DoubleWorker("doubler", in_q, out_q)
        w.start()
        in_q.put(21)
        time.sleep(0.2)
        w.stop()
        result = out_q.get(timeout=1)
        assert result == 42

    def test_worker_backpressure(self):
        """背压处理不应崩溃"""
        from src.pipeline import PipelineWorker
        in_q = Queue()
        out_q = Queue(maxsize=1)
        class FastWorker(PipelineWorker):
            def process_item(self, item):
                return item
        w = FastWorker("fast", in_q, out_q)
        w.start()
        # 输出队列已满，继续输入应触发背压丢弃
        out_q.put("full", timeout=1)
        in_q.put(1)
        in_q.put(2)
        in_q.put(3)
        time.sleep(0.3)
        w.stop()
        assert True  # 没崩溃


class TestMemoryMonitor:
    """内存监控测试"""

    def test_monitor_create(self):
        """创建监控器"""
        from src.pipeline import MemoryMonitor
        m = MemoryMonitor(threshold_percent=80.0)
        assert m.threshold == 80.0

    def test_monitor_check(self):
        """检查内存"""
        from src.pipeline import MemoryMonitor
        m = MemoryMonitor(threshold_percent=100.0)  # 100% 不会触发
        result = m.check()
        assert isinstance(result, bool)

    def test_monitor_cooldown(self):
        """冷却期内不重复触发"""
        from src.pipeline import MemoryMonitor
        m = MemoryMonitor(threshold_percent=50.0, collection_interval=60.0)
        # 模拟刚执行过GC
        m.last_collection_time = time.time()
        assert m.is_in_cooldown()


class TestModelLifecycle:
    """模型生命周期测试"""

    def test_idle_timeout(self):
        """空闲超时检测"""
        from src.pipeline import ModelLifecycleManager
        mgr = ModelLifecycleManager(idle_timeout=0.1)  # 100ms
        mgr.model_loaded = True
        time.sleep(0.2)
        assert mgr.is_idle_timeout()

    def test_mark_activity(self):
        """标记活动重置空闲计时器"""
        from src.pipeline import ModelLifecycleManager
        mgr = ModelLifecycleManager(idle_timeout=10)
        mgr.model_loaded = True
        mgr.mark_activity()
        assert not mgr.is_idle_timeout()

    def test_load_unload(self):
        """加载和卸载回调"""
        from src.pipeline import ModelLifecycleManager
        load_called = False
        unload_called = False
        def load():
            nonlocal load_called
            load_called = True
        def unload():
            nonlocal unload_called
            unload_called = True
        mgr = ModelLifecycleManager(
            idle_timeout=0.1,
            load_func=load,
            unload_func=unload,
        )
        mgr.load_model()
        assert load_called
        assert mgr.model_loaded
        mgr.unload_model()
        assert unload_called
        assert not mgr.model_loaded


class TestPipelineE2E:
    """端到端稳定性测试"""

    def test_fast_start_stop(self):
        """快速启动停止100次不崩溃"""
        from src.pipeline import PipelineWorker
        q = Queue()
        class NopWorker(PipelineWorker):
            def process_item(self, item):
                return item
        for _ in range(100):
            w = NopWorker("nop", q)
            w.start()
            w.stop()
        assert True

    def test_thread_count_bounded(self):
        """工作线程数量有限"""
        from src.pipeline import PipelineWorker
        workers = []
        q = Queue()
        class NopWorker(PipelineWorker):
            def process_item(self, item):
                return item
        for i in range(10):
            w = NopWorker(f"worker-{i}", q)
            w.start()
            workers.append(w)

        threads = [t.name for t in threading.enumerate()
                   if t.name and t.name.startswith("worker-")]
        assert len(threads) == 10

        for w in workers:
            w.stop()
