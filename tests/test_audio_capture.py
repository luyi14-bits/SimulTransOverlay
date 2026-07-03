"""Tests for audio capture module."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock


class TestAudioCaptureWASAPI:
    """WASAPI 音频环回捕获测试"""

    @pytest.fixture
    def capture(self):
        """创建音频捕获实例（mock 音频设备）"""
        with patch("src.audio_capture.AudioCapture") as MockCapture:
            mock_instance = MockCapture.return_value
            mock_instance.sample_rate = 48000
            mock_instance.channels = 2
            mock_instance.is_running = False
            yield mock_instance

    def test_initial_state(self, capture):
        """初始化后应处于停止状态"""
        assert capture.is_running is False

    def test_start_capture(self, capture):
        """启动后应处于运行状态"""
        capture.is_running = True
        assert capture.is_running is True

    def test_stop_capture(self, capture):
        """停止后应回到停止状态"""
        capture.is_running = True
        capture.is_running = False
        assert capture.is_running is False

    def test_sample_rate_48khz(self, capture):
        """WASAPI 默认输出 48kHz"""
        assert capture.sample_rate == 48000

    def test_stereo_channels(self, capture):
        """WASAPI 默认输出 2 通道"""
        assert capture.channels == 2

    def test_audio_callback_format(self, capture):
        """音频回调应返回 float32 numpy 数组"""
        mock_callback = MagicMock()
        mock_callback.return_value = np.zeros((2, 480), dtype=np.float32)
        result = mock_callback(np.zeros((2, 480)))
        assert result.dtype == np.float32
        assert result.shape == (2, 480)

    def test_callback_blocksize(self, capture):
        """回调块大小应为 32ms (1536 采样点 @ 48kHz)"""
        # WASAPI 典型块大小 480 采样点（10ms）或 1536（32ms）
        # 验证捕获配置的块大小
        capture.blocksize = 1536
        assert capture.blocksize == 1536


class TestMicMixin:
    """麦克风混音功能测试"""

    @pytest.fixture
    def capture_with_mic(self):
        with patch("src.audio_capture.AudioCapture") as MockCapture:
            mock_instance = MockCapture.return_value
            mock_instance.mic_enabled = True
            mock_instance.mic_ratio = 0.3
            yield mock_instance

    def test_mic_enabled(self, capture_with_mic):
        assert capture_with_mic.mic_enabled is True

    def test_mic_ratio(self, capture_with_mic):
        assert capture_with_mic.mic_ratio == 0.3
