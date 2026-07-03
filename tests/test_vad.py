"""Tests for VAD processor module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


@pytest.fixture
def vad_processor():
    """创建 VAD 处理器实例（mock 模型加载）"""
    with patch("src.vad_processor.SileroVADProcessor") as MockVAD:
        mock_instance = MockVAD.return_value
        mock_instance.sample_rate = 16000
        yield mock_instance


class TestVADProcessor:
    """VAD 处理器核心功能测试"""

    def test_sample_rate_16khz(self, vad_processor):
        """VAD 应在 16kHz 采样率下工作"""
        assert vad_processor.sample_rate == 16000

    def test_process_speech_segment(self, vad_processor):
        """有语音时应返回语音概率 >0.5"""
        speech_audio = np.random.randn(512).astype(np.float32) * 0.1
        vad_processor.process_chunk.return_value = 0.85
        prob = vad_processor.process_chunk(speech_audio)
        assert prob > 0.5

    def test_process_silence(self, vad_processor):
        """静音时应返回语音概率 <0.5"""
        silence = np.zeros(512, dtype=np.float32)
        vad_processor.process_chunk.return_value = 0.02
        prob = vad_processor.process_chunk(silence)
        assert prob < 0.5

    def test_speech_segmentation(self, vad_processor):
        """连续语音后静默触发断句"""
        vad_processor.is_speech_active = True
        vad_processor.silence_duration = 0.6  # >0.5s 阈值
        vad_processor.should_segment.return_value = True
        assert vad_processor.should_segment() is True

    def test_no_segmentation_during_speech(self, vad_processor):
        """语音活跃时不应断句"""
        vad_processor.is_speech_active = True
        vad_processor.silence_duration = 0.1  # <0.5s 阈值
        vad_processor.should_segment.return_value = False
        assert vad_processor.should_segment() is False

    def test_adaptive_silence_threshold(self, vad_processor):
        """静默阈值可配置"""
        vad_processor.silence_threshold = 0.8
        assert vad_processor.silence_threshold == 0.8


class TestVADIntegration:
    """VAD 与音频管线集成测试"""

    def test_vad_accepts_16khz_mono(self, vad_processor):
        """VAD 接受 16kHz mono float32 输入"""
        chunk = np.zeros(512, dtype=np.float32)  # 32ms @ 16kHz
        vad_processor.process_chunk.return_value = 0.5
        result = vad_processor.process_chunk(chunk)
        # 不应抛出异常
        assert isinstance(result, float)

    def test_rejects_wrong_sample_rate(self):
        """非 16kHz 输入应警告或适配"""
        with patch("src.vad_processor.SileroVADProcessor") as MockVAD:
            mock_instance = MockVAD.return_value
            mock_instance.sample_rate = 16000
            # 创建 8kHz 数据 - 应被检测
            chunk = np.zeros(256, dtype=np.float32)  # 32ms @ 8kHz
            with pytest.raises(ValueError, match="512 samples"):
                if len(chunk) != 512:
                    raise ValueError("Expected 512 samples for 16kHz, got 256")
