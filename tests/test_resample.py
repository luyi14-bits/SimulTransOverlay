"""Tests for audio resample module."""

import numpy as np
import pytest
from src.resample import resample_to_16khz, validate_audio_format


class TestValidateAudioFormat:
    """验证音频输入格式"""

    def test_valid_48khz_stereo(self):
        """48kHz stereo f32 是合法输入"""
        audio = np.zeros((2, 48000), dtype=np.float32)
        # 不应抛出异常
        validate_audio_format(audio, 48000)

    def test_rejects_wrong_sample_rate(self):
        """非 48kHz 输入应拒绝"""
        audio = np.zeros((2, 16000), dtype=np.float32)
        with pytest.raises(ValueError, match="sample_rate.*48000"):
            validate_audio_format(audio, 16000)

    def test_rejects_wrong_dtype(self):
        """非 float32 输入应拒绝"""
        audio = np.zeros((2, 48000), dtype=np.int16)
        with pytest.raises(ValueError, match="float32"):
            validate_audio_format(audio, 48000)


class TestResampleTo16kHz:
    """重采样正确性测试"""

    def test_output_shape_mono(self):
        """输出应为 1 通道 (mono)"""
        audio = np.zeros((2, 48000), dtype=np.float32)  # 1 秒 stereo
        result = resample_to_16khz(audio)
        assert result.ndim == 1, "输出应为 1D mono 数组"
        assert result.dtype == np.float32

    def test_output_sample_count(self):
        """1 秒 48kHz → 16000 个采样点"""
        audio = np.zeros((2, 48000), dtype=np.float32)
        result = resample_to_16khz(audio)
        assert len(result) == 16000, f"Expected 16000 samples, got {len(result)}"

    def test_half_second(self):
        """0.5 秒 48kHz → 8000 个采样点"""
        audio = np.zeros((2, 24000), dtype=np.float32)
        result = resample_to_16khz(audio)
        assert len(result) == 8000

    def test_output_not_all_zeros(self):
        """正弦波输入应产生非零输出"""
        t = np.linspace(0, 1, 48000, endpoint=False)
        sine_wave = np.sin(2 * np.pi * 440 * t)  # 440Hz
        stereo = np.stack([sine_wave, sine_wave]).astype(np.float32)
        result = resample_to_16khz(stereo)
        assert np.max(np.abs(result)) > 0.1, "输出不应全零"

    def test_mono_input_passthrough(self):
        """已经 mono 的输入应正确处理"""
        audio = np.zeros(48000, dtype=np.float32)
        result = resample_to_16khz(audio)
        assert len(result) == 16000

    def test_empty_input(self):
        """空输入应返回空数组"""
        audio = np.zeros((2, 0), dtype=np.float32)
        result = resample_to_16khz(audio)
        assert len(result) == 0


class TestResampleEdgeCases:
    """边界条件测试"""

    def test_short_audio(self):
        """极短音频（32ms = 1536 采样点）"""
        audio = np.zeros((2, 1536), dtype=np.float32)
        result = resample_to_16khz(audio)
        # 32ms × 16kHz = 512 采样点（允许 ±1 舍入误差）
        assert abs(len(result) - 512) <= 1, f"Expected ~512, got {len(result)}"

    def test_large_audio_no_crash(self):
        """10 秒音频不应崩溃"""
        audio = np.zeros((2, 480000), dtype=np.float32)
        result = resample_to_16khz(audio)
        assert len(result) == 160000
